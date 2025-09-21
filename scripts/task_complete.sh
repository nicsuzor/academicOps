#!/bin/bash
set -euo pipefail
# task_complete.sh <filename.json>
FILE=$1
DST_DIR="data/tasks/completed"
SRC_INBOX="data/tasks/inbox/${FILE}"
SRC_QUEUE="data/tasks/queue/${FILE}"

SRC=""
if [[ -f "$SRC_INBOX" ]]; then
  SRC="$SRC_INBOX"
elif [[ -f "$SRC_QUEUE" ]]; then
  SRC="$SRC_QUEUE"
else
  echo "{\"error\":\"not_found\",\"file\":\"$FILE\"}" >&2
  exit 1
fi

mkdir -p "$DST_DIR"
mv "$SRC" "$DST_DIR/" || { echo "{\"error\":\"move_failed\"}" >&2; exit 1; }

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git add "$DST_DIR/${FILE}"
  git commit -m "Complete task: ${FILE}" >/dev/null 2>&1 || true
fi

# View rebuild is now inline in task_view.py; no separate rebuild needed.
echo "{\"status\":\"completed\",\"file\":\"${FILE}\"}"