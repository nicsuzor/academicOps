#!/bin/bash
# Session Start Protocol for Gemini

# 1. Generate Session ID
SESSION_DATE=$(date +%Y-%m-%d)
SESSION_ID=$(openssl rand -hex 4)
SESSION_FILE="/tmp/gemini-session-${SESSION_DATE}-${SESSION_ID}.json"

# 2. Create Session File
cat <<EOF > "$SESSION_FILE"
{
  "session_id": "$SESSION_ID",
  "date": "$SESSION_DATE",
  "started_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "state": "active"
}
EOF

# 3. Output for Agent
echo "=== SESSION STARTED ==="
echo "ID: $SESSION_ID"
echo "Date: $SESSION_DATE"
echo "State File: $SESSION_FILE"
echo "======================="
echo "INSTRUCTIONS:"
echo "1. Analyze the user's intent."
echo "2. Select a workflow from WORKFLOWS.md."
echo "3. Execute step-by-step."
