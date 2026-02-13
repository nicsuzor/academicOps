#!/usr/bin/env bash
# queue-drain.sh - Trigger a supervisor session to drain ready tasks.
#
# This is a pure trigger. It checks whether work exists, then starts a
# supervisor agent session. The supervisor reads WORKERS.md, inspects the
# queue, and decides what runners to dispatch and how many.
#
# Usage:
#   ./queue-drain.sh                    # Start supervisor if tasks ready
#   ./queue-drain.sh -p aops-core       # Filter to project
#   ./queue-drain.sh --dry-run          # Print what would happen
#
# Exit codes:
#   0 - Supervisor session started (or dry-run completed)
#   1 - Error
#   3 - No ready tasks (normal, not a failure)

set -euo pipefail

# --- Defaults ---
DRY_RUN="${DRY_RUN:-false}"
PROJECT=""

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--project) PROJECT="$2"; shift 2 ;;
        --dry-run) DRY_RUN="true"; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# --- Resolve AOPS path ---
AOPS="${AOPS:-$(cd "$(dirname "$0")/../../.." && pwd)}"

# --- Check: are there ready tasks? ---
# This is the only decision the shell makes: is the queue non-empty?
PROJECT_FILTER=""
if [[ -n "$PROJECT" ]]; then
    PROJECT_FILTER="--project $PROJECT"
fi

# Quick check via task index (no agent needed for this)
TASK_DIR="${AOPS}/data/aops/tasks"
READY_COUNT=0
if [[ -d "$TASK_DIR" ]]; then
    READY_COUNT=$(grep -rl "^status: active" "$TASK_DIR" 2>/dev/null | wc -l)
    READY_COUNT=$(echo "$READY_COUNT" | tr -d '[:space:]')
fi

echo "[queue-drain] Ready tasks: ${READY_COUNT}"

if [[ "$READY_COUNT" -eq 0 ]]; then
    echo "[queue-drain] Queue empty. Nothing to do."
    exit 3
fi

# --- Build supervisor prompt ---
PROMPT="You are the swarm supervisor. Check the ready task queue"
if [[ -n "$PROJECT" ]]; then
    PROMPT="${PROMPT} for project '${PROJECT}'"
fi
PROMPT="${PROMPT} and dispatch workers according to WORKERS.md."
PROMPT="${PROMPT} Use polecat swarm or polecat run as appropriate."

if [[ "$DRY_RUN" == "true" ]]; then
    echo "[queue-drain] DRY RUN: Would start supervisor session with prompt:"
    echo "  ${PROMPT}"
    exit 0
fi

# --- Start supervisor session ---
# The supervisor agent makes all dispatch decisions.
# Swap this command for any agent CLI that can run the swarm-supervisor skill.
echo "[queue-drain] Starting supervisor session..."
if command -v claude &>/dev/null; then
    exec claude --print --allowedTools "Bash,Read,Glob,Grep,Task,mcp__*" \
        "$PROMPT"
elif command -v gemini &>/dev/null; then
    exec gemini --prompt "$PROMPT"
else
    echo "[queue-drain] ERROR: No agent CLI found (claude, gemini)." >&2
    echo "[queue-drain] Install one or set AGENT_CMD to a custom runner." >&2
    exit 1
fi
