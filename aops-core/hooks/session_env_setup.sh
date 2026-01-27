#!/bin/bash
#
# Session environment setup hook for Claude Code
#
# This hook runs at session start to ensure AOPS and related env vars are available.
# It works for both local and remote (web) Claude Code sessions.
#
# ARCHITECTURE:
# - Hooks receive env vars from Claude Code's settings "env" section
# - ~/.claude/settings.local.json (created by setup.sh) provides machine-specific paths
# - This hook handles web/remote sessions where settings.local.json doesn't exist
#
# For local: AOPS and ACA_DATA come from settings.local.json (set by setup.sh)
# For remote: Derives paths from $CLAUDE_PROJECT_DIR and writes to $CLAUDE_ENV_FILE
#

set -euo pipefail

# Read input JSON from stdin and extract session_id
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')

# Print session info for debugging
echo "session: ${SESSION_ID:-<not provided>}  ACA_DATA=${ACA_DATA:-<not set>}  AOPS=${AOPS:-<not set>}" >&2
echo "CLAUDE_ENV_FILE: ${CLAUDE_ENV_FILE:-<not set>}" >&2

# Persist session ID if available
if [ -n "${SESSION_ID:-}" ] && [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    if ! grep -q "export CLAUDE_SESSION_ID=" "$CLAUDE_ENV_FILE" 2>/dev/null; then
        echo "export CLAUDE_SESSION_ID=\"$SESSION_ID\"" >> "$CLAUDE_ENV_FILE"
    fi
fi

# Determine aops-core location for PYTHONPATH
# (Script is in aops-core/hooks/session_env_setup.sh -> ../.. is aops-core root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AOPS_CORE="$(dirname "$SCRIPT_DIR")"

# Validate structure partially
if [ ! -f "$AOPS_CORE/lib/hook_utils.py" ]; then
    echo "WARNING: Cannot validate aops-core path - lib/hook_utils.py not found at $AOPS_CORE" >&2
fi

# Write to CLAUDE_ENV_FILE if available (persists for the session)
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    # Only add to PYTHONPATH if not already present
    if ! grep -q "PYTHONPATH.*$AOPS_CORE" "$CLAUDE_ENV_FILE" 2>/dev/null; then
        echo "export PYTHONPATH=\"$AOPS_CORE:\${PYTHONPATH:-}\"" >> "$CLAUDE_ENV_FILE"
    fi

    # Add additional environment variables
    if ! grep -q "export NODE_ENV=" "$CLAUDE_ENV_FILE" 2>/dev/null; then
        echo 'export NODE_ENV=production' >> "$CLAUDE_ENV_FILE"
    fi

    if ! grep -q "export API_KEY=" "$CLAUDE_ENV_FILE" 2>/dev/null; then
        echo 'export API_KEY=your-api-key' >> "$CLAUDE_ENV_FILE"
    fi

    if ! grep -q "node_modules/.bin" "$CLAUDE_ENV_FILE" 2>/dev/null; then
        echo 'export PATH="$PATH:./node_modules/.bin"' >> "$CLAUDE_ENV_FILE"
    fi

    # Custodiet enforcement mode: "block" (default) or "warn"
    if ! grep -q "export CUSTODIET_MODE=" "$CLAUDE_ENV_FILE" 2>/dev/null; then
        echo 'export CUSTODIET_MODE="${CUSTODIET_MODE:-block}"' >> "$CLAUDE_ENV_FILE"
    fi
fi


# Derive ACA_SESSIONS from ACA_DATA (sibling directory pattern)
# Matches paths.py get_sessions_dir(): ACA_DATA/../sessions
if [ -n "${ACA_DATA:-}" ]; then
    ACA_DATA_PARENT="$(dirname "$ACA_DATA")"
    export ACA_SESSIONS="${ACA_DATA_PARENT}/sessions"

    if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
        if ! grep -q "export ACA_SESSIONS=" "$CLAUDE_ENV_FILE" 2>/dev/null; then
            echo "export ACA_SESSIONS=\"$ACA_SESSIONS\"" >> "$CLAUDE_ENV_FILE"
            echo "ACA_SESSIONS derived from ACA_DATA: $ACA_SESSIONS" >&2
        fi
    fi
fi

# Output success (no additional context needed, just ensure env is set)
echo '{"continue": true}'
