#!/usr/bin/env bash
# aops-ts SessionEnd hook — ship session transcript(s) to a tailnet host.
#
# The observability companion to the bring-up hook: cloud/web sessions have no
# durable filesystem and no inbound access, so a session's transcript dies with
# the container unless it is pushed out. This hook renders the ending session's
# JSONL through the transcript pipeline and ships the result to a host on the
# tailnet — the same tailnet the bring-up hook joins.
#
# Nothing here has a default. Every host, path, and program is either named by
# the environment or looked up on PATH. A missing destination is a clean no-op,
# never a guess and never an error.
#
# Session resolution:
#   - SessionEnd fires with a transcript_path in its stdin payload (the normal
#     case) -> single-session mode: only that one session is processed.
#   - No usable transcript_path (a manual or standalone run) -> batch mode: the
#     runner is invoked with --all and no file argument, handing discovery to
#     its own find_session_files() (every provider it knows) rather than a
#     bash-side glob.
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
#   AOPS_TS_SYNC_DEST  [user@]host:path on the tailnet (REQUIRED). Both host AND
#                      path are required — a malformed dest (no host, or no
#                      ":path") is a hard error (exit 1), never a silent
#                      default. `path` is the base directory; the payload lands
#                      under it as:
#                        <base>/transcripts/  rendered markdown/html/json
#                        <base>/incoming/     raw JSONL (opt-in only, see below)
#   AOPS_SRC_DIR       Path to an academicOps source checkout. REQUIRED for
#                      rendering: the transcript pipeline (lib/py/transcripts)
#                      needs third-party dependencies, so it runs out of that
#                      checkout's environment, not out of this plugin.
#   AOPS_TS_SYNC_RAW   Set to 1 to permit shipping the RAW session JSONL when
#                      the pipeline is unavailable or fails. Raw transcripts are
#                      UNREDACTED. Unset means unavailable-pipeline is a
#                      skipped sync, so nothing unredacted ever leaves by
#                      default.
#   AOPS_TS_SSH_CMD    Remote-shell override (optional). Program name only, no
#                      host and no path; the destination always comes from
#                      AOPS_TS_SYNC_DEST. Defaults to `tailscale ssh` when
#                      tailscale is on PATH, else `ssh`.
#   AOPS_TS_SSH_OPTS   Extra ssh options for the plain-ssh path (optional), e.g.
#                      "-o StrictHostKeyChecking=accept-new"
#
# Never blocks session end: always exits 0 except on a malformed destination.
# Diagnostics -> stderr.

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
# (exit 1) before doing any work, never guess a landing directory.
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

# A valid transcript_path from the payload selects single-session mode;
# otherwise fall through to batch mode (--all, see header note).
BATCH_MODE=1
if [ -n "${tp:-}" ] && [ -f "${tp:-}" ]; then
  BATCH_MODE=""
fi

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/aops-ts-sync.XXXXXX")" || { echo "[aops-ts] mktemp failed; skipping."; exit 0; }
trap 'rm -rf "$STAGE"' EXIT

# --- locate the transcript pipeline ---
# From AOPS_SRC_DIR and nowhere else. The pipeline (lib/py/transcripts) has
# third-party dependencies, so it must run out of a checkout that has an
# environment for them; this plugin cannot carry it. No search path is baked
# here: an unset or wrong AOPS_SRC_DIR means no renderer, and the raw-JSONL
# path below is opt-in, so the failure mode is a skipped sync.
AOPS_PY=""
if [ -f "${AOPS_SRC_DIR:-/nonexistent}/lib/py/transcripts/runner.py" ]; then
  AOPS_PY="${AOPS_SRC_DIR}/lib/py"
else
  echo "[aops-ts] AOPS_SRC_DIR does not point at a checkout containing lib/py/transcripts/runner.py; no renderer available."
fi

# The runner writes transcripts/ under $AOPS_SESSIONS; point that at the staging
# dir and pass --no-sync so it never tries to git-commit/push. Single-session
# mode names the one file that just ended; batch mode passes --all and no file
# argument, so the runner's own discovery finds every session it knows about.
if [ -n "$BATCH_MODE" ]; then
  RUN_ARGS=(--all)
else
  RUN_ARGS=("$tp")
fi

processed=""
if [ -n "$AOPS_PY" ]; then
  py="${AOPS_SRC_DIR}/.venv/bin/python"
  if [ -x "$py" ]; then
    AOPS_SESSIONS="$STAGE" PYTHONPATH="$AOPS_PY" "$py" -m transcripts.runner \
      "${RUN_ARGS[@]}" --no-sync >"$STAGE/transcript.log" 2>&1 && processed=1
  elif command -v uv >/dev/null 2>&1; then
    AOPS_SESSIONS="$STAGE" PYTHONPATH="$AOPS_PY" uv --directory "$AOPS_SRC_DIR" run \
      python -m transcripts.runner "${RUN_ARGS[@]}" --no-sync \
      >"$STAGE/transcript.log" 2>&1 && processed=1
  else
    echo "[aops-ts] no python environment for the pipeline (no $AOPS_SRC_DIR/.venv, no uv on PATH)."
  fi
fi

if [ -n "$processed" ]; then
  if [ -n "$BATCH_MODE" ]; then
    echo "[aops-ts] pipeline rendered all available sessions into the staging dir"
  else
    echo "[aops-ts] pipeline rendered the ending session into the staging dir"
  fi
elif [ -n "$BATCH_MODE" ]; then
  echo "[aops-ts] pipeline unavailable/failed; batch mode has no raw path; skipping sync."
  exit 0
elif [ "${AOPS_TS_SYNC_RAW:-}" = "1" ]; then
  # Opt-in only. Raw transcripts are UNREDACTED — set AOPS_TS_SYNC_RAW=1 solely
  # for a tailnet host you control and are willing to hand unredacted sessions.
  echo "[aops-ts] pipeline unavailable/failed; AOPS_TS_SYNC_RAW=1, shipping RAW (unredacted) JSONL"
  mkdir -p "$STAGE/incoming"
  cp "$tp" "$STAGE/incoming/${sid:-session}.jsonl"
else
  echo "[aops-ts] pipeline unavailable/failed; set AOPS_TS_SYNC_RAW=1 to ship the raw, UNREDACTED JSONL instead. Skipping sync."
  exit 0
fi

# --- push everything to the tailnet host (REMOTE_HS/REMOTE_PATH parsed above) ---
# Remote shell: keyless `tailscale ssh` when tailscale is present (the tailnet
# authenticates it), else the system ssh. Both are program names resolved on
# PATH, not destinations — every host and path in play comes from
# AOPS_TS_SYNC_DEST. AOPS_TS_SSH_CMD overrides the program. Left unquoted below
# so a two-word command ("tailscale ssh") word-splits into argv.
if [ -n "${AOPS_TS_SSH_CMD:-}" ]; then
  case "$AOPS_TS_SSH_CMD" in
    ssh|ssh\ *) RSH="$AOPS_TS_SSH_CMD -o BatchMode=yes -o ConnectTimeout=10 ${AOPS_TS_SSH_OPTS:-}" ;;
    *)         RSH="$AOPS_TS_SSH_CMD" ;;
  esac
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
