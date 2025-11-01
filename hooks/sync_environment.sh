#!/usr/bin/env bash
# SessionStart hook: Sync Python environment dependencies
# Ensures uv dependencies are up to date when Claude Code session starts

set -euo pipefail

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo '{"continue":true,"systemMessage":"uv not installed - skipping environment sync"}'
    exit 0
fi

# Sync environment dependencies
cd "$ACADEMICOPS"
uv sync --group dev --quiet 2>&1 > /dev/null || true

# Always continue (non-blocking)
echo '{"continue":true}'
