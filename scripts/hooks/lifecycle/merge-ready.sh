#!/usr/bin/env bash
# merge-ready.sh - Surface merge-ready tasks/PRs for human review.
#
# Trigger: cron, manual invocation.
# Contract: Lists tasks in merge_ready state, optionally auto-merges clean PRs.
# Configuration: See LIFECYCLE-HOOKS.md for tunable parameters.
#
# Usage:
#   ./merge-ready.sh                  # List merge-ready tasks
#   ./merge-ready.sh --auto-merge     # Auto-merge clean PRs
#   ./merge-ready.sh -p aops-core     # Filter to project
#
# Exit codes:
#   0 - Check completed
#   1 - Error
#   3 - No merge-ready tasks

set -euo pipefail

# --- Defaults (override via environment) ---
AUTO_MERGE_CLEAN="${AUTO_MERGE_CLEAN:-false}"
REQUIRE_HUMAN_REVIEW="${REQUIRE_HUMAN_REVIEW:-true}"
NOTIFY_CMD="${NOTIFY_CMD:-notify-send}"
PROJECT="${DEFAULT_PROJECT:-}"

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --auto-merge) AUTO_MERGE_CLEAN="true"; shift ;;
        -p|--project) PROJECT="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# --- Resolve paths ---
AOPS="${AOPS:-$(cd "$(dirname "$0")/../../.." && pwd)}"
export AOPS

echo "[merge-ready] Checking for merge-ready tasks..."

# --- List merge-ready tasks via polecat ---
PROJECT_FLAG=""
if [[ -n "$PROJECT" ]]; then
    PROJECT_FLAG="-p $PROJECT"
fi

# shellcheck disable=SC2086
MERGE_LIST=$(uv run --project "$AOPS" "$AOPS/polecat/cli.py" list \
    --status merge_ready $PROJECT_FLAG 2>&1) || true

if [[ -z "$MERGE_LIST" ]] || echo "$MERGE_LIST" | grep -qi "no.*tasks\|0 tasks"; then
    echo "[merge-ready] No merge-ready tasks."
    exit 3
fi

echo "[merge-ready] Merge-ready tasks:"
echo "$MERGE_LIST"

# --- Count for notification ---
MERGE_COUNT=$(echo "$MERGE_LIST" | grep -c "^" || echo "0")

# --- Auto-merge if enabled and human review not required ---
if [[ "$AUTO_MERGE_CLEAN" == "true" && "$REQUIRE_HUMAN_REVIEW" != "true" ]]; then
    echo "[merge-ready] Auto-merging clean PRs..."
    # List open polecat PRs and merge those with passing checks
    gh pr list --label polecat --json number,statusCheckRollup \
        --jq '.[] | select(.statusCheckRollup | all(.conclusion == "SUCCESS")) | .number' \
        2>/dev/null | while read -r PR_NUM; do
        echo "[merge-ready] Merging PR #${PR_NUM}..."
        gh pr merge "$PR_NUM" --squash --delete-branch 2>/dev/null || \
            echo "[merge-ready] Failed to merge PR #${PR_NUM}"
    done
else
    echo "[merge-ready] Auto-merge disabled or human review required."
fi

# --- Notify ---
NOTIFY_MSG="${MERGE_COUNT} task(s) ready for merge review"
case "$NOTIFY_CMD" in
    notify-send)
        notify-send -u normal "Polecat: Merge Ready" "$NOTIFY_MSG" 2>/dev/null || true
        ;;
    ntfy)
        NTFY_TOPIC="${NTFY_TOPIC:-polecat}"
        curl -s -d "$NOTIFY_MSG" "ntfy.sh/${NTFY_TOPIC}" 2>/dev/null || true
        ;;
    *)
        $NOTIFY_CMD "Polecat: Merge Ready" "$NOTIFY_MSG" 2>/dev/null || true
        ;;
esac

echo "[merge-ready] Done. ${MERGE_COUNT} task(s) surfaced."
