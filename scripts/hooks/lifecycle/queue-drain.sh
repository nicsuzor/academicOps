#!/usr/bin/env bash
# queue-drain.sh - Drain ready tasks from the queue via worker swarm.
#
# Trigger: cron, manual invocation, or external scheduler.
# Contract: Checks queue depth, spawns workers if tasks are ready.
# Configuration: See LIFECYCLE-HOOKS.md for tunable parameters.
#
# Usage:
#   ./queue-drain.sh                    # Use defaults
#   ./queue-drain.sh -p aops-core       # Filter to project
#   ./queue-drain.sh --dry-run          # Simulate only
#   RUNNER_CMD="my-runner" ./queue-drain.sh  # Custom runner
#
# Exit codes:
#   0 - Workers dispatched (or dry-run completed)
#   1 - Error
#   3 - No ready tasks (normal, not a failure)

set -euo pipefail

# --- Defaults (override via environment or LIFECYCLE-HOOKS.md) ---
MIN_READY_TASKS="${MIN_READY_TASKS:-1}"
DEFAULT_PROJECT="${DEFAULT_PROJECT:-}"
CALLER_IDENTITY="${CALLER_IDENTITY:-polecat}"
DRY_RUN="${DRY_RUN:-false}"
MAX_CLAUDE_WORKERS="${MAX_CLAUDE_WORKERS:-2}"
MAX_GEMINI_WORKERS="${MAX_GEMINI_WORKERS:-3}"
SWARM_AUTO_SIZE="${SWARM_AUTO_SIZE:-true}"
RUNNER_CMD="${RUNNER_CMD:-polecat swarm}"

# --- Parse arguments ---
PROJECT="$DEFAULT_PROJECT"
while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--project) PROJECT="$2"; shift 2 ;;
        --dry-run) DRY_RUN="true"; shift ;;
        --caller) CALLER_IDENTITY="$2"; shift 2 ;;
        -c|--claude) MAX_CLAUDE_WORKERS="$2"; shift 2 ;;
        -g|--gemini) MAX_GEMINI_WORKERS="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# --- Resolve AOPS path ---
AOPS="${AOPS:-$(cd "$(dirname "$0")/../../.." && pwd)}"
export AOPS

# --- Check queue depth ---
# Use polecat summary or task_manager to count ready tasks.
# Falls back to the MCP task API via polecat CLI.
READY_COUNT=0

if command -v polecat &>/dev/null; then
    # Use polecat's task listing to count ready tasks
    PROJECT_FLAG=""
    if [[ -n "$PROJECT" ]]; then
        PROJECT_FLAG="-p $PROJECT"
    fi
    # shellcheck disable=SC2086
    READY_COUNT=$(uv run --project "$AOPS" "$AOPS/polecat/cli.py" list --status active --format count $PROJECT_FLAG 2>/dev/null || echo "0")
else
    # Fallback: count task files with status: active
    TASK_DIR="${AOPS}/data/aops/tasks"
    if [[ -d "$TASK_DIR" ]]; then
        READY_COUNT=$(grep -rl "^status: active" "$TASK_DIR" 2>/dev/null | wc -l || echo "0")
    fi
fi

# Trim whitespace
READY_COUNT=$(echo "$READY_COUNT" | tr -d '[:space:]')

echo "[queue-drain] Ready tasks: $READY_COUNT (minimum: $MIN_READY_TASKS)"

if [[ "$READY_COUNT" -lt "$MIN_READY_TASKS" ]]; then
    echo "[queue-drain] Below threshold. No workers needed."
    exit 3
fi

# --- Calculate swarm size ---
CLAUDE_COUNT="$MAX_CLAUDE_WORKERS"
GEMINI_COUNT="$MAX_GEMINI_WORKERS"

if [[ "$SWARM_AUTO_SIZE" == "true" ]]; then
    # Simple auto-sizing: scale workers to queue depth
    # These heuristics match the Swarm Sizing Defaults in WORKERS.md
    if [[ "$READY_COUNT" -le 2 ]]; then
        CLAUDE_COUNT=1
        GEMINI_COUNT=0
    elif [[ "$READY_COUNT" -le 5 ]]; then
        CLAUDE_COUNT=1
        GEMINI_COUNT=2
    elif [[ "$READY_COUNT" -le 10 ]]; then
        CLAUDE_COUNT=2
        GEMINI_COUNT=3
    fi

    # Clamp to maximums
    [[ "$CLAUDE_COUNT" -gt "$MAX_CLAUDE_WORKERS" ]] && CLAUDE_COUNT="$MAX_CLAUDE_WORKERS"
    [[ "$GEMINI_COUNT" -gt "$MAX_GEMINI_WORKERS" ]] && GEMINI_COUNT="$MAX_GEMINI_WORKERS"
fi

echo "[queue-drain] Swarm size: ${CLAUDE_COUNT} claude, ${GEMINI_COUNT} gemini"

# --- Dispatch workers ---
if [[ "$DRY_RUN" == "true" ]]; then
    echo "[queue-drain] DRY RUN: Would run: $RUNNER_CMD -c $CLAUDE_COUNT -g $GEMINI_COUNT"
    exit 0
fi

# Build the command
CMD=("$RUNNER_CMD")
CMD+=(-c "$CLAUDE_COUNT")
CMD+=(-g "$GEMINI_COUNT")
CMD+=(--caller "$CALLER_IDENTITY")

if [[ -n "$PROJECT" ]]; then
    CMD+=(-p "$PROJECT")
fi

echo "[queue-drain] Dispatching: ${CMD[*]}"
exec "${CMD[@]}"
