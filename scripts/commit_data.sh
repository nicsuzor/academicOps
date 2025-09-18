#!/bin/bash
set -euo pipefail

# This script commits all changes in the data/ directory with a generic message.

# Check if inside a git repository
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git repository. Skipping commit."
  exit 0
fi

# Add all changes in the data directory
git add data/

# Commit with a generic message if there are staged changes
if git diff --cached --quiet; then
  echo "No changes to commit."
else
  git commit -m "feat(data): Update data sources"
fi
