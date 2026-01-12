#!/bin/bash
# Format all files before staging for commit
# Pre-commit hooks validate only - run this script to auto-fix formatting
#
# Usage: ./scripts/format.sh [files...]
#   No args: format all tracked files
#   With args: format only specified files

set -e

echo "Formatting files..."

# Format markdown, JSON, TOML with dprint
echo "  Running dprint fmt..."
if [ $# -eq 0 ]; then
    /home/nic/.dprint/bin/dprint fmt
else
    /home/nic/.dprint/bin/dprint fmt "$@"
fi

# Fix Python linting issues with ruff
echo "  Running ruff check --fix..."
if [ $# -eq 0 ]; then
    ruff check --fix . 2>/dev/null || true
else
    ruff check --fix "$@" 2>/dev/null || true
fi

# Format Python with ruff
echo "  Running ruff format..."
if [ $# -eq 0 ]; then
    ruff format . 2>/dev/null || true
else
    ruff format "$@" 2>/dev/null || true
fi

echo "Done. Files are formatted and ready to stage."
