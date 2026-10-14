#!/usr/bin/env bash
# fetch.sh — pull a Google Doc down as markdown + docx via rclone, and
# extract embedded images from the docx archive.
#
# Usage:
#   fetch.sh <gdoc-url-or-id> <output-dir>
#
# Produces, in <output-dir>:
#   doc.md                — markdown export
#   doc.docx              — docx export (source for figure extraction)
#   figures/image1.png…   — extracted from docx's word/media/ (Note: numbering
#                           may not match markdown references and requires mapping)
#
# Requires: rclone with a configured `gdrive:` remote (run `rclone config` once).
# Fails fast on any error. No fallback to gcloud / API keys.

set -euo pipefail

URL_OR_ID="${1:-}"
OUT="${2:-}"

if [[ -z "$URL_OR_ID" || -z "$OUT" ]]; then
  echo "usage: $0 <gdoc-url-or-id> <output-dir>" >&2
  exit 2
fi

if [[ "$URL_OR_ID" =~ /document/d/([A-Za-z0-9_-]+) ]]; then
  DOC_ID="${BASH_REMATCH[1]}"
else
  DOC_ID="$URL_OR_ID"
fi

if ! rclone lsd gdrive: >/dev/null 2>&1; then
  echo "FATAL: rclone remote 'gdrive' is not configured or not reachable." >&2
  echo "       Run: rclone config  (add a 'drive' remote named 'gdrive')" >&2
  exit 3
fi

mkdir -p "$OUT" "$OUT/figures"

# rclone can address Drive items by ID directly with --drive-root-folder-id
# or with `gdrive:{ID}` syntax; we use `backend copyid` which is purpose-built.
# --drive-export-formats picks which export to use when the source is a gdoc.

echo "→ downloading markdown export..." >&2
rclone backend copyid gdrive: "$DOC_ID" "$OUT/" \
  --drive-export-formats md --drive-import-formats md >/dev/null

echo "→ downloading docx export (for figure extraction)..." >&2
rclone backend copyid gdrive: "$DOC_ID" "$OUT/" \
  --drive-export-formats docx --drive-import-formats docx >/dev/null

# Rename the exports to predictable names regardless of the gdoc title.
shopt -s nullglob
MDFILE=("$OUT"/*.md)
DOCXFILE=("$OUT"/*.docx)
shopt -u nullglob

if [[ ${#MDFILE[@]} -ne 1 ]]; then
  echo "FATAL: expected exactly one .md in $OUT, got ${#MDFILE[@]}" >&2
  exit 4
fi
if [[ ${#DOCXFILE[@]} -ne 1 ]]; then
  echo "FATAL: expected exactly one .docx in $OUT, got ${#DOCXFILE[@]}" >&2
  exit 5
fi

mv "${MDFILE[0]}" "$OUT/doc.md"
mv "${DOCXFILE[0]}" "$OUT/doc.docx"

# Extract images from the .docx archive. Word stores them under word/media/.
# WARNING: docx storage order does NOT match markdown ![][imageN] prose order.
# The caller must map figures by visual context — see pkb-capture.md Step 3.
# We emit MANIFEST.txt so the caller can enumerate what was extracted.

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

unzip -q "$OUT/doc.docx" -d "$TMP"
if [[ -d "$TMP/word/media" ]]; then
  cp "$TMP/word/media/"* "$OUT/figures/" 2>/dev/null || true
fi

# Manifest of extracted figures
( cd "$OUT/figures" && ls -1 2>/dev/null | sort -V ) > "$OUT/figures/MANIFEST.txt" || true

N=$(wc -l < "$OUT/figures/MANIFEST.txt" 2>/dev/null || echo 0)
echo "→ done. markdown=$(wc -c <"$OUT/doc.md") bytes, docx=$(wc -c <"$OUT/doc.docx") bytes, figures=$N" >&2
