#!/bin/bash
# Wrapper to manually test policy_enforcer.py
# Usage: ./commands/check-policy.sh "tool_name" "arg_name" "arg_value"

TOOL_NAME=$1
ARG_NAME=$2
ARG_VALUE=$3

if [ -z "$TOOL_NAME" ]; then
    echo "Usage: $0 <ToolName> <ArgName> <ArgValue>"
    echo "Example: $0 Bash command 'git reset --hard'"
    exit 1
fi

# Construct JSON payload
JSON_PAYLOAD=$(jq -n \
    --arg tool "$TOOL_NAME" \
    --arg key "$ARG_NAME" \
    --arg val "$ARG_VALUE" \
    '{tool_name: $tool, tool_input: {($key): $val}}')

echo "Testing Payload: $JSON_PAYLOAD"
echo "--------------------------------"

# Run enforcement
echo "$JSON_PAYLOAD" | python3 hooks/policy_enforcer.py

EXIT_CODE=$?
echo "--------------------------------"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Allowed (Exit Code 0)"
elif [ $EXIT_CODE -eq 2 ]; then
    echo "❌ Blocked (Exit Code 2)"
else
    echo "⚠️ Unknown (Exit Code $EXIT_CODE)"
fi
