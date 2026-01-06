#!/bin/bash
# Cron wrapper: check for unprocessed sessions, pass paths to skill
#
# Called by cron every 30 minutes. Only invokes Claude if work is needed.
# Only processes sessions from the framework's installation project by default.
#
# Exit codes:
#   0 - Success (either processed sessions or nothing to do)
#   1 - Error (missing dependencies, check script failed with code 2)

set -euo pipefail

# Change to framework root
cd "$(dirname "$0")/.."
FRAMEWORK_ROOT="$(pwd)"

# Source environment from settings.local.json if ACA_DATA not set
if [[ -z "${ACA_DATA:-}" ]]; then
    if [[ -f "$HOME/.claude/settings.local.json" ]]; then
        ACA_DATA=$(jq -r '.env.ACA_DATA // empty' "$HOME/.claude/settings.local.json")
        export ACA_DATA
    fi
fi

# Fail-fast if ACA_DATA still not set
if [[ -z "${ACA_DATA:-}" ]]; then
    echo "ERROR: ACA_DATA not set and not found in settings.local.json" >&2
    exit 1
fi

# Derive project pattern from AOPS or framework root
# /home/nic/src/academicOps -> academicOps
if [[ -n "${AOPS:-}" ]]; then
    PROJECT_PATTERN=$(basename "$AOPS")
else
    PROJECT_PATTERN=$(basename "$FRAMEWORK_ROOT")
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - Checking for unprocessed sessions (project: $PROJECT_PATTERN)..."

# Run check script, capture output
# Exit codes: 0 = work needed, 1 = nothing to do, 2 = config error
set +e
SESSIONS=$(uv run python scripts/check_unprocessed_sessions.py --allowed-projects "$PROJECT_PATTERN" 2>&1)
CHECK_EXIT=$?
set -e

if [[ $CHECK_EXIT -eq 1 ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - No unprocessed sessions in age window. Skipping."
    exit 0
elif [[ $CHECK_EXIT -eq 2 ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Configuration error: $SESSIONS" >&2
    exit 1
elif [[ $CHECK_EXIT -ne 0 ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Unexpected error (exit $CHECK_EXIT): $SESSIONS" >&2
    exit 1
fi

# Count sessions (one path per line)
SESSION_COUNT=$(echo "$SESSIONS" | wc -l)
echo "$(date '+%Y-%m-%d %H:%M:%S') - Found $SESSION_COUNT unprocessed session(s)"

# Pass sessions to Claude via headless mode with natural language
# Note: Slash commands don't work in -p mode - must use natural language
SESSIONS_INLINE=$(echo "$SESSIONS" | tr '\n' ' ')
echo "$(date '+%Y-%m-%d %H:%M:%S') - Invoking claude -p with session-insights task"

# Use natural language prompt with required tools enabled
# --dangerously-skip-permissions allows unattended operation
claude -p "Invoke the session-insights skill to process these session files: $SESSIONS_INLINE" \
    --dangerously-skip-permissions \
    --allowedTools "Bash,Read,Write,Edit,Glob,Grep,Task,Skill,mcp__memory__store_memory"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Session insights processing complete"
