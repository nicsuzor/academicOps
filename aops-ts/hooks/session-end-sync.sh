#!/usr/bin/env bash
# aops-ts SessionEnd hook — ship this session's transcript to a tailnet host.
#
# This is the observability companion to the bring-up hook: cloud/web sessions
# have no durable filesystem and no inbound access, so a session's transcript
# dies with the container unless it is pushed out. This hook runs aops-core's
# transcript.py over this session's JSONL and ships the result to a host on the
# tailnet (the same tailnet the bring-up hook joins).
#
# Opt-in on four conditions; if ANY is unmet it no-ops (exit 0):
#   1. remote/cloud session   — CLAUDE_CODE_REMOTE=true
#   2. a destination is set   — AOPS_TS_SYNC_DEST
#   3. the tailnet is up      — `tailscale status` succeeds
#   4. a transport exists     — `tar` + `ssh` on PATH
#
# Transport: tar-over-ssh, preferring `tailscale ssh` — which authenticates via
# the tailnet (NO ssh keys needed) as long as the destination runs the Tailscale
# SSH server with an ACL permitting this node. `rsync` is NOT required; the
# remote only needs `tar`. (`tailscale ssh` is a thin wrapper around the system
# `ssh` binary, so openssh-client must be installed — do it in your environment
# setup script, alongside the Tailscale install.)
#
# Config (env):
#   AOPS_TS_SYNC_DEST  [user@]host:path on the tailnet (REQUIRED), e.g.
#                      "nic@services-new:src/sessions/". Both host AND path are
#                      required — a malformed dest (no host, or no ":path") is a
#                      hard error (exit 1), never a silent default. `path` is the
#                      base directory; the payload lands under it as:
#                        <base>/transcripts/  redacted markdown (transcript.py)
#                        <base>/summaries/    summary JSON      (transcript.py)
#                        <base>/incoming/     raw JSONL         (fallback only)
#   AOPS_TS_SSH_CMD    remote-shell override (optional); defaults to
#                      "tailscale ssh" when tailscale is present, else "ssh".
#                      Set e.g. to "ssh" to use key-based auth to a plain host.
#   AOPS_TS_SSH_OPTS   extra ssh options for the plain-ssh path (optional), e.g.
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
command -v tar >/dev/null 2>&1 || { echo "[aops-ts] tar not installed; skipping session sync."; exit 0; }
command -v ssh >/dev/null 2>&1 || { echo "[aops-ts] ssh (openssh-client) not installed — install it in your environment setup script; skipping session sync."; exit 0; }
if ! { command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; }; then
  echo "[aops-ts] tailnet not up; cannot reach $AOPS_TS_SYNC_DEST; skipping session sync."
  exit 0
fi

# Parse & validate the destination up front — [user@]host:path, both parts
# REQUIRED. A malformed dest is an operator misconfiguration: fail fast and loud
# (exit 1) before doing any work, never guess a default landing directory.
case "$AOPS_TS_SYNC_DEST" in
  *:*) REMOTE_HS="${AOPS_TS_SYNC_DEST%%:*}"; REMOTE_PATH="${AOPS_TS_SYNC_DEST#*:}";;
  *)   echo "[aops-ts] FATAL: AOPS_TS_SYNC_DEST ('$AOPS_TS_SYNC_DEST') has no ':path'; expected [user@]host:path. Aborting session sync."; exit 1;;
esac
[ -n "$REMOTE_HS" ]   || { echo "[aops-ts] FATAL: AOPS_TS_SYNC_DEST ('$AOPS_TS_SYNC_DEST') has an empty host; expected [user@]host:path. Aborting session sync."; exit 1; }
[ -n "$REMOTE_PATH" ] || { echo "[aops-ts] FATAL: AOPS_TS_SYNC_DEST ('$AOPS_TS_SYNC_DEST') has an empty path; expected [user@]host:path. Aborting session sync."; exit 1; }

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
  mkdir -p "$STAGE/incoming"
  cp "$tp" "$STAGE/incoming/${sid:-session}.jsonl"
fi

# --- push everything to the tailnet host (REMOTE_HS/REMOTE_PATH parsed above) ---
# Remote shell: keyless `tailscale ssh` by default (tailnet-authenticated). When
# AOPS_TS_SSH_CMD is set it is used verbatim (a full override — bake any ssh
# options into it); otherwise the auto-selected plain-ssh fallback carries
# AOPS_TS_SSH_OPTS. Left unquoted below so a two-word command ("tailscale ssh")
# word-splits into argv — matching the old `-e` convention.
if [ -n "${AOPS_TS_SSH_CMD:-}" ]; then
  RSH="$AOPS_TS_SSH_CMD"
elif command -v tailscale >/dev/null 2>&1; then
  RSH="tailscale ssh"
else
  RSH="ssh -o BatchMode=yes -o ConnectTimeout=10 ${AOPS_TS_SSH_OPTS:-}"
fi

# Single-quote REMOTE_PATH for safe interpolation into the remote shell command:
# wrap in single quotes and escape any embedded single quote as '\''. This makes
# spaces/metacharacters inert and closes the remote-command-injection vector for
# an operator-supplied path.
REMOTE_PATH_Q="'$(printf '%s' "$REMOTE_PATH" | sed "s/'/'\\\\''/g")'"

# tar-over-ssh: stream the staging tree through the remote shell and unpack it.
# The remote needs only `tar`; no rsync on either side. transcript.log is local
# diagnostics, so it is excluded from the payload.
# shellcheck disable=SC2086
if tar czf - --exclude='transcript.log' -C "$STAGE" . \
     | $RSH "$REMOTE_HS" "mkdir -p $REMOTE_PATH_Q && tar xzf - -C $REMOTE_PATH_Q"; then
  echo "[aops-ts] session synced to $REMOTE_HS:$REMOTE_PATH"
else
  echo "[aops-ts] transfer to $REMOTE_HS:$REMOTE_PATH failed (check Tailscale SSH ACL / dest path / tailnet reachability)"
fi

exit 0
