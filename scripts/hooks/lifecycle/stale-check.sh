#!/usr/bin/env bash
# stale-check.sh - Detect and optionally reset stalled in-progress tasks.
#
# Trigger: cron, manual invocation.
# Contract: Finds tasks stuck in_progress beyond threshold, optionally resets.
# Configuration: See LIFECYCLE-HOOKS.md for tunable parameters.
#
# Usage:
#   ./stale-check.sh                  # Detect and report (dry run)
#   ./stale-check.sh --reset          # Detect and reset stale tasks
#   ./stale-check.sh --hours 2        # Custom threshold
#
# Exit codes:
#   0 - Check completed (stale tasks found or not)
#   1 - Error

set -euo pipefail

# --- Defaults (override via environment) ---
STALE_THRESHOLD_HOURS="${STALE_THRESHOLD_HOURS:-4}"
AUTO_RESET="${AUTO_RESET:-false}"
NOTIFY_ON_STALE="${NOTIFY_ON_STALE:-true}"
NOTIFY_CMD="${NOTIFY_CMD:-notify-send}"

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reset) AUTO_RESET="true"; shift ;;
        --hours) STALE_THRESHOLD_HOURS="$2"; shift 2 ;;
        --notify-cmd) NOTIFY_CMD="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# --- Resolve paths ---
AOPS="${AOPS:-$(cd "$(dirname "$0")/../../.." && pwd)}"
export AOPS

echo "[stale-check] Threshold: ${STALE_THRESHOLD_HOURS}h, Auto-reset: ${AUTO_RESET}"

# --- Run stale check via polecat ---
if [[ "$AUTO_RESET" == "true" ]]; then
    echo "[stale-check] Resetting stale tasks..."
    RESULT=$(uv run --project "$AOPS" "$AOPS/polecat/cli.py" reset-stalled \
        --hours "$STALE_THRESHOLD_HOURS" 2>&1) || true
else
    echo "[stale-check] Dry run (detecting only)..."
    RESULT=$(uv run --project "$AOPS" "$AOPS/polecat/cli.py" reset-stalled \
        --hours "$STALE_THRESHOLD_HOURS" --dry-run 2>&1) || true
fi

echo "$RESULT"

# --- Notify if stale tasks found ---
if echo "$RESULT" | grep -qi "reset\|stale\|found"; then
    if [[ "$NOTIFY_ON_STALE" == "true" ]]; then
        STALE_MSG="Stale tasks detected (>${STALE_THRESHOLD_HOURS}h)"
        case "$NOTIFY_CMD" in
            notify-send)
                notify-send -u normal "Polecat: Stale Tasks" "$STALE_MSG" 2>/dev/null || true
                ;;
            ntfy)
                NTFY_TOPIC="${NTFY_TOPIC:-polecat}"
                curl -s -d "$STALE_MSG" "ntfy.sh/${NTFY_TOPIC}" 2>/dev/null || true
                ;;
            *)
                $NOTIFY_CMD "Polecat: Stale Tasks" "$STALE_MSG" 2>/dev/null || true
                ;;
        esac
        echo "[stale-check] Notification sent"
    fi
fi

echo "[stale-check] Done."
