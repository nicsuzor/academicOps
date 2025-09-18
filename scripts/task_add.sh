#!/bin/bash
set -euo pipefail
# task_add.sh --priority 1 --type email_reply --title "Reply to grant" --project voice-assistant --due 2024-08-14T17:00:00Z --preview "Need dates" --summary "Grant org asked for update" --metadata '{"key":"value"}'

usage() {
  echo "Usage: $0 --title <text> [--priority <int>] [--type <type>] [--project <slug>] [--due <ISO8601>] [--preview <text>] [--summary <text>] [--metadata <json>]" >&2
  exit 1
}

TITLE=""
PRIORITY=""
TYPE="todo"
PROJECT=""
DUE=""
PREVIEW=""
SUMMARY=""
METADATA="{}"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --title) TITLE="$2"; shift 2;;
    --priority) 
      if ! [[ "$2" =~ ^[0-9]+$ ]]; then
        echo "Error: --priority must be an integer." >&2
        exit 1
      fi
      PRIORITY="$2"; shift 2;;
    --type) TYPE="$2"; shift 2;;
    --project) PROJECT="$2"; shift 2;;
    --due) DUE="$2"; shift 2;;
    --preview) PREVIEW="$2"; shift 2;;
    --summary) SUMMARY="$2"; shift 2;;
    --metadata) METADATA="$2"; shift 2;;
    -h|--help) usage;;
    *) echo "Unknown arg: $1" >&2; usage;;
  esac
done

[[ -z "$TITLE" ]] && { echo "Error: --title required" >&2; usage; }

TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
HOSTNAME=$(hostname | cut -d'.' -f1)
if command -v uuidgen >/dev/null 2>&1; then
  UUID=$(uuidgen | cut -d'-' -f1)
else
  UUID=$(head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')
fi
TASK_ID="${TIMESTAMP}-${HOSTNAME}-${UUID}"
CREATED_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

FILE="data/tasks/inbox/${TASK_ID}.json"

mkdir -p "$(dirname "$FILE")"

JSON=$(cat <<EOF
{
  "id": "${TASK_ID}",
  "priority": $( [ -n "$PRIORITY" ] && echo "$PRIORITY" || echo null ),
  "type": "${TYPE}",
  "title": $(jq -Rn --arg v "$TITLE" '$v'),
  "preview": $(jq -Rn --arg v "$PREVIEW" '$v'),
  "summary": $(jq -Rn --arg v "$SUMMARY" '$v'),
  "project": $(jq -Rn --arg v "$PROJECT" '$v'),
  "created": "${CREATED_ISO}",
  "due": $( [ -n "$DUE" ] && echo "\"$DUE\"" || echo null ),
  "source": {},
  "metadata": ${METADATA}
}
EOF
)

echo "$JSON" > "$FILE"

echo "$JSON"
