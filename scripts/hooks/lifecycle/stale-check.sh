#!/usr/bin/env bash
# stale-check.sh - Detect stalled in-progress tasks and optionally reset.
#
# Pure mechanical trigger — no agent judgment needed. Just checks task
# modification times against a threshold. Use --reset to act, otherwise
# dry-run by default.
#
# Usage:
#   ./stale-check.sh                  # Detect only (dry run)
#   ./stale-check.sh --reset          # Detect and reset stale tasks
#   ./stale-check.sh --hours 2        # Custom threshold
#
# Exit codes:
#   0 - Completed
#   1 - Error

set -euo pipefail

STALE_THRESHOLD_HOURS="${STALE_THRESHOLD_HOURS:-4}"
AUTO_RESET="false"
NOTIFY_CMD="${NOTIFY_CMD:-notify-send}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --reset) AUTO_RESET="true"; shift ;;
        --hours) STALE_THRESHOLD_HOURS="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

AOPS="${AOPS:-$(cd "$(dirname "$0")/../../.." && pwd)}"

echo "[stale-check] Threshold: ${STALE_THRESHOLD_HOURS}h, Reset: ${AUTO_RESET}"

if [[ "$AUTO_RESET" == "true" ]]; then
    polecat reset-stalled --hours "$STALE_THRESHOLD_HOURS" 2>&1
else
    polecat reset-stalled --hours "$STALE_THRESHOLD_HOURS" --dry-run 2>&1
fi

RESULT=$?
if [[ "$RESULT" -eq 0 ]]; then
    # Notify if anything was found/reset
    case "$NOTIFY_CMD" in
        notify-send)
            notify-send -u normal "Polecat" "Stale check complete (>${STALE_THRESHOLD_HOURS}h)" 2>/dev/null || true ;;
        ntfy)
            curl -s -d "Stale check complete" "ntfy.sh/${NTFY_TOPIC:-polecat}" 2>/dev/null || true ;;
    esac
fi
