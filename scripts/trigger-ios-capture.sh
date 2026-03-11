#!/usr/bin/env bash
# Trigger the iOS Note Capture workflow via GitHub API
# Requires: GITHUB_TOKEN environment variable with 'repo' scope
#
# Location: This script lives in academicOps (not dotfiles) because it
# specifically interacts with the writing repo's task capture workflow.

set -euo pipefail

# Configuration
REPO_OWNER="nicsuzor"
REPO_NAME="writing"
EVENT_TYPE="capture-note"

# Check for required environment variable
GITHUB_TOKEN="${GITHUB_PERSONAL_ACCESS_TOKEN:-${GITHUB_TOKEN:-}}"
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_PERSONAL_ACCESS_TOKEN or GITHUB_TOKEN environment variable not set"
    echo "Create a Personal Access Token with 'repo' scope at:"
    echo "https://github.com/settings/tokens/new?scopes=repo"
    echo ""
    echo "Then export it:"
    echo "  export GITHUB_PERSONAL_ACCESS_TOKEN='your_token_here'"
    exit 1
fi

# Parse arguments
CONTENT="${1:-}"
TAGS="${2:-mobile-capture,inbox}"

if [ -z "$CONTENT" ]; then
    echo "Usage: $0 <content> [tags]"
    echo ""
    echo "Example:"
    echo "  $0 'Test note from curl' 'test,mobile-capture'"
    echo ""
    echo "Tags default to: mobile-capture,inbox"
    exit 1
fi

# Create JSON payload
PAYLOAD=$(jq -n \
    --arg event_type "$EVENT_TYPE" \
    --arg content "$CONTENT" \
    --arg tags "$TAGS" \
    '{
        "event_type": $event_type,
        "client_payload": {
            "content": $content,
            "tags": $tags
        }
    }')

echo "Triggering iOS Note Capture workflow..."
echo "Repository: $REPO_OWNER/$REPO_NAME"
echo "Event type: $EVENT_TYPE"
echo "Content: $CONTENT"
echo "Tags: $TAGS"
echo ""

# Send repository_dispatch event
HTTP_CODE=$(curl -s -w "%{http_code}" -o /tmp/github-response.json \
    -X POST \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/dispatches" \
    -d "$PAYLOAD")

if [ "$HTTP_CODE" = "204" ]; then
    echo "✅ Workflow triggered successfully!"
    echo ""
    echo "Monitor workflow execution at:"
    echo "https://github.com/$REPO_OWNER/$REPO_NAME/actions/workflows/note-capture.yml"
    echo ""
    echo "Expected result:"
    echo "  - New commit to $REPO_NAME repository"
    echo "  - Note created at: data/notes/mobile-captures/$(date +%Y-%m-%d)-*.md"
else
    echo "❌ Failed to trigger workflow (HTTP $HTTP_CODE)"
    echo ""
    echo "Response:"
    cat /tmp/github-response.json
    echo ""
    exit 1
fi
