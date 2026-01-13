#!/bin/bash
# Wrapper for headless Claude Code invocations
#
# Runs claude from a temp directory to isolate session logs from interactive sessions.
# Session logs go to ~/.claude/projects/tmp-claude-headless-*/ instead of polluting
# the project's interactive session history.
#
# Usage: claude-headless.sh [claude args...]
# Example: claude-headless.sh -p "Process files" --allowedTools "Bash,Read"
#
# Environment:
#   CLAUDE_HEADLESS_ADD_DIRS - Additional directories to grant access (colon-separated)
#   CLAUDE_HEADLESS_KEEP_TMP - Set to 1 to preserve temp dir after run

set -euo pipefail

# Capture original working directory for --add-dir
ORIGINAL_CWD="$(pwd)"

# Create unique temp directory for session isolation
HEADLESS_CWD="/tmp/claude-headless-$$-$(date +%s)"
mkdir -p "$HEADLESS_CWD"

# Build --add-dir arguments
ADD_DIR_ARGS=("--add-dir" "$ORIGINAL_CWD")

# Add framework root if AOPS is set and different from cwd
if [[ -n "${AOPS:-}" && "$AOPS" != "$ORIGINAL_CWD" ]]; then
    ADD_DIR_ARGS+=("--add-dir" "$AOPS")
fi

# Add any extra directories from environment
if [[ -n "${CLAUDE_HEADLESS_ADD_DIRS:-}" ]]; then
    IFS=':' read -ra EXTRA_DIRS <<< "$CLAUDE_HEADLESS_ADD_DIRS"
    for dir in "${EXTRA_DIRS[@]}"; do
        [[ -n "$dir" ]] && ADD_DIR_ARGS+=("--add-dir" "$dir")
    done
fi

# Cleanup function
cleanup() {
    if [[ "${CLAUDE_HEADLESS_KEEP_TMP:-0}" != "1" ]]; then
        rm -rf "$HEADLESS_CWD" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Run claude from temp directory with all arguments passed through
cd "$HEADLESS_CWD"
exec claude "${ADD_DIR_ARGS[@]}" "$@"
