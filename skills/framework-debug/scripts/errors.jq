# Claude Code error extraction filter
# Usage: jq -r -f errors.jq ~/.claude/projects/${repo}/agent-*.jsonl
#
# Add new error patterns by extending the select() conditions

# Pattern 1: Tool errors with is_error flag
select(.message.content[]? | .is_error == true) |

# Output format: timestamp | agentId | first line of error (truncated to 100 chars)
"\(.timestamp) | \(.agentId) | \(.toolUseResult | split("\n")[0][0:100])"
