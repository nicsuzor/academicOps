#!/bin/bash
#
# Session environment setup hook for Claude Code
#
# This hook runs at session start to ensure AOPS and related env vars are available.
# It works for both local and remote (web) Claude Code sessions.


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

# Set AOPS_SESSION_STATE_DIR for Claude Code sessions
# This ensures state files go to the same directory as hooks.jsonl
# Path format: ~/.claude/projects/-<cwd-with-dashes>/
# Example: /home/nic/src/academicOps -> ~/.claude/projects/-home-nic-src-academicOps/
CWD_ENCODED=$(pwd | sed 's|/|-|g')
AOPS_SESSION_STATE_DIR="$HOME/.claude/projects/$CWD_ENCODED"
export AOPS_SESSION_STATE_DIR
mkdir -p "$AOPS_SESSION_STATE_DIR"

# Write to CLAUDE_ENV_FILE if available (persists for the session)
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    # Only add to PYTHONPATH if not already present
    if ! grep -q "PYTHONPATH.*$AOPS_CORE" "$CLAUDE_ENV_FILE" 2>/dev/null; then
        echo "export PYTHONPATH=\"$AOPS_CORE:\${PYTHONPATH:-}\"" >> "$CLAUDE_ENV_FILE"
    fi

    # Persist AOPS_SESSION_STATE_DIR for subsequent hook invocations
    if ! grep -q "export AOPS_SESSION_STATE_DIR=" "$CLAUDE_ENV_FILE" 2>/dev/null; then
        echo "export AOPS_SESSION_STATE_DIR=\"$AOPS_SESSION_STATE_DIR\"" >> "$CLAUDE_ENV_FILE"
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

    # Gate enforcement modes: "block" or "warn" (default: warn for all)
    if ! grep -q "export CUSTODIET_MODE=" "$CLAUDE_ENV_FILE" 2>/dev/null; then
        echo 'export CUSTODIET_MODE="${CUSTODIET_MODE:-warn}"' >> "$CLAUDE_ENV_FILE"
    fi
    if ! grep -q "export TASK_GATE_MODE=" "$CLAUDE_ENV_FILE" 2>/dev/null; then
        echo 'export TASK_GATE_MODE="${TASK_GATE_MODE:-warn}"' >> "$CLAUDE_ENV_FILE"
    fi
    if ! grep -q "export HYDRATION_MODE=" "$CLAUDE_ENV_FILE" 2>/dev/null; then
        echo 'export HYDRATION_MODE="${HYDRATION_MODE:-warn}"' >> "$CLAUDE_ENV_FILE"
    fi
fi


# Output success (no additional context needed, just ensure env is set)
echo '{"continue": true}'
