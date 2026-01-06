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
# - For repo-local .claude/ (settings-self.json), hooks use CLAUDE_PROJECT_DIR which is always set
#
# For local setup.sh: AOPS and ACA_DATA come from settings.local.json
# For remote/web: Derives AOPS from CLAUDE_PROJECT_DIR and writes to CLAUDE_ENV_FILE
#

set -euo pipefail

# Determine the AOPS path
# Priority:
# 1. Already set in environment (from settings.local.json via setup.sh)
# 2. Derived from CLAUDE_PROJECT_DIR (for web sessions and remote VMs)
# 3. Derived from this script's location (fallback)

if [ -n "${AOPS:-}" ] && [ -d "${AOPS}" ]; then
    # AOPS already set and valid - nothing to do
    echo "AOPS environment already configured: $AOPS" >&2
else
    # Need to derive AOPS path
    if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "${CLAUDE_PROJECT_DIR}" ]; then
        # Use CLAUDE_PROJECT_DIR (always set by Claude Code)
        AOPS="$CLAUDE_PROJECT_DIR"
        echo "Derived AOPS from CLAUDE_PROJECT_DIR: $AOPS" >&2
    else
        # Fallback: derive from this script's location
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        AOPS="$(dirname "$SCRIPT_DIR")"
        echo "Derived AOPS from script location: $AOPS" >&2
    fi

    # Validate the derived path has expected structure
    if [ ! -f "$AOPS/AXIOMS.md" ]; then
        echo "WARNING: Cannot validate AOPS path - AXIOMS.md not found at $AOPS" >&2
        echo "This may indicate the hook is running in an unexpected context" >&2
    fi

    export AOPS

    # Write to CLAUDE_ENV_FILE if available (persists for the session)
    if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
        # Only write if not already present to avoid duplicates
        if ! grep -q "export AOPS=" "$CLAUDE_ENV_FILE" 2>/dev/null; then
            echo "export AOPS=\"$AOPS\"" >> "$CLAUDE_ENV_FILE"
            echo "Wrote AOPS to CLAUDE_ENV_FILE" >&2
        fi

        # Only add to PYTHONPATH if not already present
        if ! grep -q "PYTHONPATH.*$AOPS" "$CLAUDE_ENV_FILE" 2>/dev/null; then
            echo "export PYTHONPATH=\"$AOPS:\${PYTHONPATH:-}\"" >> "$CLAUDE_ENV_FILE"
            echo "Updated PYTHONPATH in CLAUDE_ENV_FILE" >&2
        fi
    fi

    echo "AOPS set to: $AOPS" >&2
fi

# Output success (no additional context needed, just ensure env is set)
echo '{"continue": true}'
