#!/usr/bin/env bash
# merge-ready.sh - List merge-ready tasks and notify.
#
# Pure mechanical trigger — lists tasks in merge_ready state and
# sends a notification. Does NOT auto-merge; that decision belongs
# to the human or a supervisor session.
#
# Usage:
#   ./merge-ready.sh                  # List and notify
#   ./merge-ready.sh -p aops-core     # Filter to project
#
# Exit codes:
#   0 - Completed
#   3 - No merge-ready tasks

set -euo pipefail

NOTIFY_CMD="${NOTIFY_CMD:-notify-send}"
PROJECT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--project) PROJECT="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

echo "[merge-ready] Checking for merge-ready tasks..."

# List open polecat PRs
PR_LIST=$(gh pr list --label polecat --state open --json number,title,headRefName \
    --jq '.[] | "#\(.number) \(.title) (\(.headRefName))"' 2>/dev/null || echo "")

if [[ -z "$PR_LIST" ]]; then
    echo "[merge-ready] No merge-ready PRs."
    exit 3
fi

PR_COUNT=$(echo "$PR_LIST" | wc -l | tr -d '[:space:]')
echo "[merge-ready] ${PR_COUNT} PR(s) ready for review:"
echo "$PR_LIST"

# Notify
case "$NOTIFY_CMD" in
    notify-send)
        notify-send -u normal "Polecat: Merge Ready" "${PR_COUNT} PR(s) awaiting review" 2>/dev/null || true ;;
    ntfy)
        curl -s -d "${PR_COUNT} PR(s) awaiting review" "ntfy.sh/${NTFY_TOPIC:-polecat}" 2>/dev/null || true ;;
esac

echo "[merge-ready] Done."
