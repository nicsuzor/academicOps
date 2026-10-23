#!/usr/bin/env python3
"""Rewrite a deep-research markdown export to replace Google-Docs image refs
with either inline LaTeX (for simple math) or relative image links with
alt-text (for diagrams/charts). Also strips the trailing base64 reference
definitions that Google Docs emits.

Usage:
  rewrite.py <source.md> <note-id> <replacements.json> <output.md>

replacements.json shape:
  {
    "1": {"kind": "latex", "tex": "\\lambda"},
    "2": {"kind": "image", "alt": "The Epistemic Calibration Loop — ..."},
    "3": {"kind": "latex", "tex": "(f_t - o_t)^2"},
    ...
  }

Each key is a STRING markdown image number (not the docx filename number).
"""

import json
import re
import sys
from pathlib import Path

if len(sys.argv) < 5:
    print(
        f"usage: {sys.argv[0]} <source.md> <note-id> <replacements.json> <output.md>",
        file=sys.stderr,
    )
    sys.exit(2)
src, note_id, mapping_path, out = sys.argv[1:5]
source = Path(src).read_text()
mapping = json.loads(Path(mapping_path).read_text())


def replace_ref(match):
    n = match.group(1)
    entry = mapping.get(n)
    if not entry:
        # Unknown reference — leave a visible marker so we catch it
        return f"**[UNMAPPED image{n}]**"
    if entry["kind"] == "latex":
        return f"${entry['tex']}$"
    if entry["kind"] == "image":
        return f"![{entry['alt']}](figures/{note_id}/image{n}.png)"
    if entry["kind"] == "skip":
        return ""
    raise ValueError(f"bad entry for image{n}: {entry}")


# Replace inline refs
rewritten = re.sub(r"!\[\]\[image(\d+)\]", replace_ref, source)

# Strip the trailing [imageN]: <data:image/...> reference-link definitions
# Google Docs exports these as one line per image at the end of the file,
# separated by blank lines. Drop any line starting with [imageN]: plus the
# blank line immediately following.
lines = rewritten.splitlines()
cleaned = []
i = 0
while i < len(lines):
    if re.match(r"^\[image\d+\]:\s*<?data:image/", lines[i]):
        i += 1
        # skip following blank lines
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        continue
    cleaned.append(lines[i])
    i += 1

# Drop trailing blank lines
while cleaned and cleaned[-1].strip() == "":
    cleaned.pop()

Path(out).write_text("\n".join(cleaned) + "\n")
print(f"wrote {out}: {len(cleaned)} lines", file=sys.stderr)

# Sanity: flag any refs that had no mapping entry
unmapped = re.findall(r"\*\*\[UNMAPPED image\d+\]\*\*", "\n".join(cleaned))
if unmapped:
    print(f"WARNING: {len(unmapped)} UNMAPPED markers in output", file=sys.stderr)
