#!/bin/bash
# Install git hooks via pre-commit framework.
# See .pre-commit-config.yaml for hook definitions.
#
# We deploy a stable hook template (scripts/hooks/pre-commit) that uses `uv run`
# at runtime rather than hardcoding the current venv path. This is required because
# polecat workers share the main repo's .git/hooks/ directory — if a worker ran
# `pre-commit install`, it would bake in its own venv path and break all other
# worktrees when that venv is cleaned up.

set -euo pipefail

# Find the shared hooks directory (works from main repo and any git worktree)
GIT_COMMON_DIR="$(git rev-parse --git-common-dir)"
# git may return a relative path; resolve it
if [[ "$GIT_COMMON_DIR" != /* ]]; then
  GIT_COMMON_DIR="$(cd "$GIT_COMMON_DIR" && pwd)"
fi
HOOKS_DIR="$GIT_COMMON_DIR/hooks"

# Remove legacy post-commit hook if present (overlaps with pre-commit)
if [ -f "$HOOKS_DIR/post-commit" ] && grep -q "Post-commit lint check" "$HOOKS_DIR/post-commit" 2>/dev/null; then
  echo "Removing legacy post-commit hook (superseded by pre-commit)."
  rm "$HOOKS_DIR/post-commit"
fi

# Deploy the stable hook template
REPO_ROOT="$(git rev-parse --show-toplevel)"
cp "$REPO_ROOT/scripts/hooks/pre-commit" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"

echo "Pre-commit hooks installed. See .pre-commit-config.yaml for details."
