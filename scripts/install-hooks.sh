#!/bin/bash
# Install git hooks via pre-commit framework.
# See .pre-commit-config.yaml for hook definitions.
#
# The post-commit hook in .git/hooks/ is deprecated and should be removed
# if present -- pre-commit handles all linting.

set -euo pipefail

if ! command -v pre-commit &>/dev/null; then
    echo "Installing pre-commit..."
    uv tool install pre-commit
fi

# Remove legacy post-commit hook if present (overlaps with pre-commit)
if [ -f .git/hooks/post-commit ] && grep -q "Post-commit lint check" .git/hooks/post-commit 2>/dev/null; then
    echo "Removing legacy post-commit hook (superseded by pre-commit)."
    rm .git/hooks/post-commit
fi

pre-commit install
echo "Pre-commit hooks installed. See .pre-commit-config.yaml for details."
