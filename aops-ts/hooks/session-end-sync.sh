#!/usr/bin/env bash
# aops-ts SessionEnd hook — ship this session's transcript to a tailnet host.
#
# This is the observability companion to the bring-up hook: cloud/web sessions
# have no durable filesystem and no inbound access, so a session's transcript
# dies with the container unless it is pushed out. This hook runs aops-core's
# transcript.py over this session's JSONL and rsyncs the result to a host on the
# tailnet (the same tailnet the bring-up hook joins).
#
# Opt-in on three conditions; if ANY is unmet it no-ops (exit 0):
#   1. remote/cloud session   — CLAUDE_CODE_REMOTE=true
#   2. a destination is set   — AOPS_TS_SYNC_DEST
#   3. the tailnet is up      — `tailscale status` succeeds
#
# Config (env):
#   AOPS_TS_SYNC_DEST  rsync/ssh destination on the tailnet (REQUIRED), e.g.
#                      "nic@services-new:/data/aops-sessions/incoming/"
#   AOPS_TS_SSH_OPTS   extra ssh options (optional), e.g.
#                      "-o StrictHostKeyChecking=accept-new"
#   AOPS_SRC_DIR       aops-core source dir (optional; else the plugin cache is used)
#
# Dependency: parsing requires aops-core (transcript.py). If aops-core cannot be
# run, the hook falls back to shipping the RAW JSONL (unredacted — see note).
# Never blocks session end: always exits 0. Diagnostics → stderr.

set -uo pipefail
exec 1>&2   # keep stdout empty; SessionEnd stdout is not for the model

[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
[ -n "${AOPS_TS_SYNC_DEST:-}" ] || { echo "[aops-ts] AOPS_TS_SYNC_DEST unset; skipping session sync."; exit 0; }
command -v rsync >/dev/null 2>&1 || { echo "[aops-ts] rsync not installed; skipping session sync."; exit 0; }
if ! { command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; }; then
  echo "[aops-ts] tailnet not up; cannot reach $AOPS_TS_SYNC_DEST; skipping session sync."
  exit 0
fi

# --- resolve this session's transcript JSONL from the SessionEnd payload (stdin) ---
payload="$(cat 2>/dev/null || true)"
eval "$(printf '%s' "$payload" | python3 -c '
import sys, json, shlex
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
tp = d.get("transcript_path") or d.get("transcriptPath") or ""
sid = d.get("session_id") or d.get("sessionId") or ""
print("tp=" + shlex.quote(tp))
print("sid=" + shlex.quote(sid))
' 2>/dev/null || printf 'tp=\nsid=\n')"

if [ -z "${tp:-}" ] || [ ! -f "${tp:-}" ]; then
  tp="$(ls -t "$HOME"/.claude/projects/*/*.jsonl 2>/dev/null | head -1)"
fi
[ -n "${tp:-}" ] && [ -f "$tp" ] || { echo "[aops-ts] no transcript JSONL found; skipping session sync."; exit 0; }

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/aops-ts-sync.XXXXXX")" || { echo "[aops-ts] mktemp failed; skipping."; exit 0; }
trap 'rm -rf "$STAGE"' EXIT

# --- locate aops-core (sibling plugin) so we can run transcript.py ---
# Use a while-read over process substitution so paths containing spaces don't
# word-split (a silent split would drop us to the raw/unredacted fallback).
AOPS_CORE=""
if [ -f "${AOPS_SRC_DIR:-/nonexistent}/aops-core/scripts/transcript.py" ]; then
  AOPS_CORE="${AOPS_SRC_DIR}/aops-core"
else
  while IFS= read -r c; do
    [ -n "$c" ] || continue
    if [ -f "${c%/}/scripts/transcript.py" ]; then AOPS_CORE="${c%/}"; break; fi
  done < <(ls -d "$HOME"/.claude/plugins/cache/academicOps/aops-core/*/ 2>/dev/null | sort -rV)
fi

# transcript.py writes transcripts/ + summaries/ under $AOPS_SESSIONS; point that
# at the staging dir and pass --no-sync so it never tries to git-commit/push.
processed=""
if [ -n "$AOPS_CORE" ]; then
  py="$AOPS_CORE/.venv/bin/python"
  if [ -x "$py" ]; then
    AOPS_SESSIONS="$STAGE" "$py" "$AOPS_CORE/scripts/transcript.py" "$tp" --no-sync \
      >"$STAGE/transcript.log" 2>&1 && processed=1
  elif command -v uv >/dev/null 2>&1; then
    AOPS_SESSIONS="$STAGE" uv --directory "$AOPS_CORE" run python \
      "$AOPS_CORE/scripts/transcript.py" "$tp" --no-sync \
      >"$STAGE/transcript.log" 2>&1 && processed=1
  fi
fi

if [ -n "$processed" ]; then
  echo "[aops-ts] transcript.py processed session into staging dir"
else
  # Fallback: ship the raw JSONL. NOTE: raw transcripts are UNREDACTED — only do
  # this to a trusted tailnet host you control.
  echo "[aops-ts] transcript.py unavailable/failed; shipping RAW (unredacted) JSONL"
  mkdir -p "$STAGE/transcripts/raw"
  cp "$tp" "$STAGE/transcripts/raw/${sid:-session}.jsonl"
fi

# --- push everything to the tailnet host ---
# shellcheck disable=SC2086
if rsync -az --no-perms --no-owner --no-group --exclude 'transcript.log' \
     -e "ssh -o BatchMode=yes -o ConnectTimeout=10 ${AOPS_TS_SSH_OPTS:-}" \
     "$STAGE"/ "$AOPS_TS_SYNC_DEST"; then
  echo "[aops-ts] session synced to $AOPS_TS_SYNC_DEST"
else
  echo "[aops-ts] rsync to $AOPS_TS_SYNC_DEST failed (check ssh auth / dest path / tailnet ACL)"
fi

exit 0
