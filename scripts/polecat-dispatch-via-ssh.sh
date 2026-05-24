#!/usr/bin/env bash
#
# polecat-dispatch-via-ssh.sh — Dispatch a polecat worker on the host via SSH+tmux.
#
# In-container wrapper: opens an SSH session to the host and runs `polecat run`
# inside a host-side tmux window. Idempotent: re-dispatching the same task ID
# detects the existing tmux session and returns success without spawning.
#
# Usage:
#   echo '{"id":"aops-abc123"}' | polecat-dispatch-via-ssh.sh [OPTIONS] [-- EXTRA_RUN_ARGS...]
#   polecat-dispatch-via-ssh.sh -t aops-abc123 [OPTIONS] [-- EXTRA_RUN_ARGS...]
#
# Options:
#   -t ID, --task-id ID   Task ID to dispatch (alternative to stdin JSON)
#   --dry-run             Print derived values without executing SSH
#
# Required env (must point to HOST-SIDE paths, not container-side):
#   POLECAT_HOME          Host polecat home directory
#   AOPS_SESSIONS         Host sessions directory
#
# Optional env:
#   POLECAT_HOST          SSH host (default: host.docker.internal)
#                         Set this explicitly on Linux Docker where
#                         host.docker.internal may not resolve.
#   POLECAT_SSH_KEY       SSH private key path inside the container
#   POLECAT_SSH_USER      SSH username (default: current user)
#   POLECAT_SSH_PORT      SSH port (default: 22)
#
# Forwarded env vars (passed to the host-side tmux session if set):
#   PKB_MCP_URL, PKB_MCP_TOKEN
#   AOPS_BOT_GH_TOKEN, CLAUDE_CODE_OAUTH_TOKEN
#   AOPS, AOPS_SRC_DIR, AOPS_POLECAT_CONFIG
#
# Outputs:
#   stdout: tmux session name (e.g. polecat-aops-abc123)
#   exit 0: success (session started or already running)
#   exit 1: error (missing config, SSH failure, JSON parse error)

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

TASK_ID=""
DRY_RUN=false
EXTRA_ARGS=()
PASSTHROUGH=false

while [[ $# -gt 0 ]]; do
    if $PASSTHROUGH; then
        EXTRA_ARGS+=("$1"); shift; continue
    fi
    case "$1" in
        -t|--task-id) TASK_ID="$2"; shift 2;;
        --task-id=*)  TASK_ID="${1#--task-id=}"; shift;;
        --dry-run)    DRY_RUN=true; shift;;
        --)           PASSTHROUGH=true; shift;;
        -h|--help)
            sed -n '2,/^set -euo/p' "$0" | grep '^#' | sed 's/^# \?//'
            exit 0;;
        *) EXTRA_ARGS+=("$1"); shift;;
    esac
done

# ---------------------------------------------------------------------------
# Task ID — from flag or stdin JSON
# ---------------------------------------------------------------------------

if [[ -z "$TASK_ID" ]]; then
    if [[ -t 0 ]]; then
        echo "Error: provide -t <task-id> or pipe task JSON to stdin." >&2
        echo "Usage: echo '{\"id\":\"TASK_ID\"}' | $0 [OPTIONS]" >&2
        exit 1
    fi
    STDIN_JSON=$(cat)
    TASK_ID=$(printf '%s' "$STDIN_JSON" | python3 -c \
        "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || true)
    if [[ -z "$TASK_ID" ]]; then
        echo "Error: could not parse 'id' field from stdin JSON." >&2
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Validate required env vars
# ---------------------------------------------------------------------------

if [[ -z "${POLECAT_HOME:-}" ]]; then
    echo "Error: POLECAT_HOME is required (set to the HOST-SIDE polecat home path)." >&2
    exit 1
fi
if [[ -z "${AOPS_SESSIONS:-}" ]]; then
    echo "Error: AOPS_SESSIONS is required (set to the HOST-SIDE sessions path)." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# SSH target resolution
# ---------------------------------------------------------------------------

# host.docker.internal is automatically resolvable on Mac/Windows Docker.
# On Linux Docker, it requires either --add-host host.docker.internal:host-gateway
# (already set by polecat's _build_docker_cmd) or an explicit POLECAT_HOST.
SSH_HOST="${POLECAT_HOST:-host.docker.internal}"

SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new)
[[ -n "${POLECAT_SSH_PORT:-}" ]] && SSH_OPTS+=(-p "$POLECAT_SSH_PORT")
[[ -n "${POLECAT_SSH_KEY:-}" ]]  && SSH_OPTS+=(-i "$POLECAT_SSH_KEY")

if [[ -n "${POLECAT_SSH_USER:-}" ]]; then
    SSH_TARGET="${POLECAT_SSH_USER}@${SSH_HOST}"
else
    SSH_TARGET="${SSH_HOST}"
fi

# ---------------------------------------------------------------------------
# Derive tmux session name (task-ID-derived: predictable, re-discoverable)
# ---------------------------------------------------------------------------

SESSION_NAME="polecat-${TASK_ID}"

# ---------------------------------------------------------------------------
# Build the window command forwarding required env vars.
#
# tmux new-session -d does NOT inherit the SSH session environment, so every
# required variable must be forwarded explicitly via an `env` prefix.
# The full window command has the form:
#   env POLECAT_HOME=... AOPS_SESSIONS=... [OPTIONAL_VARS=...] polecat run -t TASK_ID [ARGS...]
# ---------------------------------------------------------------------------

WINDOW_CMD="env POLECAT_HOME=${POLECAT_HOME} AOPS_SESSIONS=${AOPS_SESSIONS}"

# Optional env vars forwarded only when set and non-empty
_OPT_VARS=(PKB_MCP_URL PKB_MCP_TOKEN AOPS_BOT_GH_TOKEN CLAUDE_CODE_OAUTH_TOKEN \
           AOPS AOPS_SRC_DIR AOPS_POLECAT_CONFIG)
for _var in "${_OPT_VARS[@]}"; do
    _val="${!_var:-}"
    [[ -n "$_val" ]] && WINDOW_CMD+=" ${_var}=${_val}"
done

WINDOW_CMD+=" polecat run -t ${TASK_ID}"
for _arg in "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"; do
    WINDOW_CMD+=" ${_arg}"
done

# ---------------------------------------------------------------------------
# Dry-run: print derived values and exit (used by unit tests and diagnostics)
# ---------------------------------------------------------------------------

if [[ "$DRY_RUN" == "true" ]]; then
    printf 'ssh_target:   %s\n' "$SSH_TARGET"
    printf 'ssh_options:  %s\n' "${SSH_OPTS[*]}"
    printf 'session_name: %s\n' "$SESSION_NAME"
    printf 'window_cmd:   %s\n' "$WINDOW_CMD"
    printf '%s\n' "$SESSION_NAME"
    exit 0
fi

# ---------------------------------------------------------------------------
# SSH dispatch
#
# Values are base64-encoded before embedding in the remote heredoc to safely
# pass through SSH quoting layers regardless of special characters in paths
# or tokens. python3 is required on the host (polecat itself depends on it).
# ---------------------------------------------------------------------------

SESSION_B64=$(printf '%s' "$SESSION_NAME" | python3 -c \
    "import sys,base64; sys.stdout.write(base64.b64encode(sys.stdin.buffer.read()).decode())")
WINDOW_CMD_B64=$(printf '%s' "$WINDOW_CMD" | python3 -c \
    "import sys,base64; sys.stdout.write(base64.b64encode(sys.stdin.buffer.read()).decode())")

# The heredoc uses a non-quoting delimiter so ${SESSION_B64} and ${WINDOW_CMD_B64}
# are expanded locally (safe: base64 alphabet is [A-Za-z0-9+/=] only).
# Remote variables use \$ to prevent local expansion.
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" bash << END_REMOTE
set -euo pipefail
SESSION_NAME=\$(python3 -c "import base64; print(base64.b64decode('${SESSION_B64}').decode(), end='')")
WINDOW_CMD=\$(python3 -c "import base64; print(base64.b64decode('${WINDOW_CMD_B64}').decode(), end='')")
if tmux has-session -t "\${SESSION_NAME}" 2>/dev/null; then
    printf '[polecat-dispatch] session already running: %s\n' "\${SESSION_NAME}" >&2
else
    tmux new-session -d -s "\${SESSION_NAME}" "\${WINDOW_CMD}"
fi
printf '%s\n' "\${SESSION_NAME}"
END_REMOTE
