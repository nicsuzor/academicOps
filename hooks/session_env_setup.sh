#!/bin/bash
#
# Session environment setup hook for Claude Code
#
# This hook runs at session start to ensure AOPS and related env vars are available.
# It works for both local and remote (web) Claude Code sessions.
#
# For local: Checks if env vars are already set (from settings.local.json)
# For remote: Derives paths from $CLAUDE_PROJECT_DIR and writes to $CLAUDE_ENV_FILE
#

set -euo pipefail

# Determine the AOPS path
# Priority:
# 1. Already set in environment (from settings.local.json)
# 2. Derived from CLAUDE_PROJECT_DIR (for web sessions)
# 3. Derived from this script's location (fallback)

if [ -n "${AOPS:-}" ] && [ -d "${AOPS}" ]; then
    # AOPS already set and valid - nothing to do
    echo "AOPS environment already configured: $AOPS" >&2
else
    # Need to derive AOPS path
    if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "${CLAUDE_PROJECT_DIR}" ]; then
        # Use CLAUDE_PROJECT_DIR (set by Claude Code)
        AOPS="$CLAUDE_PROJECT_DIR"
    else
        # Fallback: derive from this script's location
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        AOPS="$(dirname "$SCRIPT_DIR")"
    fi

    # Validate the derived path has expected structure
    if [ ! -f "$AOPS/AXIOMS.md" ]; then
        echo "WARNING: Cannot validate AOPS path - AXIOMS.md not found at $AOPS" >&2
    fi

    export AOPS

    # Write to CLAUDE_ENV_FILE if available (persists for the session)
    if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
        # Only write if not already present to avoid duplicates
        if ! grep -q "export AOPS=" "$CLAUDE_ENV_FILE" 2>/dev/null; then
            echo "export AOPS=\"$AOPS\"" >> "$CLAUDE_ENV_FILE"
            echo "Environment variables written to CLAUDE_ENV_FILE" >&2
        fi

        # Only add to PYTHONPATH if not already present
        if ! grep -q "PYTHONPATH.*$AOPS" "$CLAUDE_ENV_FILE" 2>/dev/null; then
            echo "export PYTHONPATH=\"$AOPS:\${PYTHONPATH:-}\"" >> "$CLAUDE_ENV_FILE"
        fi
    fi

    echo "AOPS set to: $AOPS" >&2
fi

# Output success (no additional context needed, just ensure env is set)
echo '{"continue": true}'
