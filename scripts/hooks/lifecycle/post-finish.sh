#!/usr/bin/env bash
# post-finish.sh - Post-task-completion hook.
#
# Trigger: Called after polecat finish completes (or any runner that
#          marks a task done/merge_ready).
# Contract: Sends notifications and optionally triggers follow-up actions.
# Configuration: See LIFECYCLE-HOOKS.md for tunable parameters.
#
# Usage:
#   ./post-finish.sh <task_id> <exit_code> [task_title]
#
# Exit codes:
#   0 - Notification sent successfully
#   1 - Error (non-fatal; callers should not abort on this)

set -euo pipefail

# --- Arguments ---
TASK_ID="${1:-unknown}"
EXIT_CODE="${2:-0}"
TASK_TITLE="${3:-}"

# --- Defaults (override via environment) ---
NOTIFY_ON_SUCCESS="${NOTIFY_ON_SUCCESS:-true}"
NOTIFY_ON_FAILURE="${NOTIFY_ON_FAILURE:-true}"
NOTIFY_CMD="${NOTIFY_CMD:-notify-send}"

# --- Determine outcome ---
if [[ "$EXIT_CODE" -eq 0 ]]; then
    OUTCOME="success"
    TITLE="Task Complete"
    BODY="${TASK_ID}: ${TASK_TITLE:-completed}"
    URGENCY="normal"
else
    OUTCOME="failure"
    TITLE="Task Failed"
    BODY="${TASK_ID} failed (exit ${EXIT_CODE})"
    URGENCY="critical"
fi

echo "[post-finish] ${OUTCOME}: ${TASK_ID} (exit ${EXIT_CODE})"

# --- Send notification ---
should_notify() {
    if [[ "$OUTCOME" == "success" && "$NOTIFY_ON_SUCCESS" == "true" ]]; then
        return 0
    fi
    if [[ "$OUTCOME" == "failure" && "$NOTIFY_ON_FAILURE" == "true" ]]; then
        return 0
    fi
    return 1
}

if should_notify; then
    case "$NOTIFY_CMD" in
        notify-send)
            if command -v notify-send &>/dev/null; then
                notify-send -u "$URGENCY" "$TITLE" "$BODY" 2>/dev/null || true
            fi
            ;;
        ntfy)
            # ntfy.sh push notification
            NTFY_TOPIC="${NTFY_TOPIC:-polecat}"
            curl -s -d "$BODY" "ntfy.sh/${NTFY_TOPIC}" 2>/dev/null || true
            ;;
        *)
            # Custom command: pass title and body as arguments
            $NOTIFY_CMD "$TITLE" "$BODY" 2>/dev/null || true
            ;;
    esac
    echo "[post-finish] Notification sent via ${NOTIFY_CMD}"
else
    echo "[post-finish] Notification skipped (${OUTCOME} notifications disabled)"
fi
