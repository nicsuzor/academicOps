#!/bin/bash
# Trigger the GitHub Action webhook for scribe note capture
#
# SETUP:
#   export GITHUB_TOKEN=your_github_token
#
# USAGE:
#   ./trigger-scribe-webhook.sh "Note content" [source] [tags]
#
# EXAMPLES:
#   ./trigger-scribe-webhook.sh "Research idea about platform governance"
#   ./trigger-scribe-webhook.sh "Meeting notes" "mobile" "urgent,work"
#   ./trigger-scribe-webhook.sh "Quick thought" "web" "idea"
#
# ARGUMENTS:
#   $1 - Note content (required)
#   $2 - Source identifier (optional, default: "cli")
#   $3 - Comma-separated tags (optional)
#
# CONFIGURATION:
#   Set GITHUB_REPO to override default repository
#   Default: nicsuzor/writing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO="${GITHUB_REPO:-nicsuzor/writing}"
EVENT_TYPE="scribe-note"

# Check for required token
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}Error: GITHUB_TOKEN environment variable not set${NC}"
    echo "Usage: export GITHUB_TOKEN=your_token_here"
    echo "       $0 \"Your note content\" [source] [tags]"
    exit 1
fi

# Parse arguments
NOTE="$1"
SOURCE="${2:-cli}"
TAGS="${3:-}"

if [ -z "$NOTE" ]; then
    echo -e "${RED}Error: Note content required${NC}"
    echo "Usage: $0 \"Your note content\" [source] [tags]"
    echo ""
    echo "Examples:"
    echo "  $0 \"Research idea about content moderation\""
    echo "  $0 \"Meeting notes\" \"mobile\" \"urgent,work\""
    exit 1
fi

# Build payload
if [ -z "$TAGS" ]; then
    PAYLOAD=$(cat <<EOF
{
  "event_type": "$EVENT_TYPE",
  "client_payload": {
    "note": $(echo "$NOTE" | jq -Rs .),
    "source": "$SOURCE"
  }
}
EOF
)
else
    PAYLOAD=$(cat <<EOF
{
  "event_type": "$EVENT_TYPE",
  "client_payload": {
    "note": $(echo "$NOTE" | jq -Rs .),
    "source": "$SOURCE",
    "tags": "$TAGS"
  }
}
EOF
)
fi

echo -e "${YELLOW}Triggering scribe webhook...${NC}"
echo "Repository: $REPO"
echo "Source: $SOURCE"
[ -n "$TAGS" ] && echo "Tags: $TAGS"
echo ""

# Send webhook
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/$REPO/dispatches" \
  -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "204" ]; then
    echo -e "${GREEN}✓ Webhook triggered successfully!${NC}"
    echo ""
    echo "View workflow progress:"
    echo "  https://github.com/$REPO/actions"
    echo ""
    echo "Note content:"
    echo "  $NOTE"
else
    echo -e "${RED}✗ Failed to trigger webhook${NC}"
    echo "HTTP Status: $HTTP_CODE"
    [ -n "$BODY" ] && echo "Response: $BODY"
    exit 1
fi
