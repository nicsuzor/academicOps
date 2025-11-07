#!/usr/bin/env bash
# Initialize academicOps standards in a project repository
# Usage: init_project_standards.sh <target-repo-path>

set -euo pipefail

# Determine academicOps location
if [ -n "${ACADEMICOPS:-}" ] && [ -d "$ACADEMICOPS" ]; then
    AOPS_DIR="$ACADEMICOPS"
elif [ -d "/home/nic/src/writing/aops" ]; then
    AOPS_DIR="/home/nic/src/writing/aops"
else
    echo "Error: Cannot locate academicOps directory"
    echo "Set ACADEMICOPS environment variable or ensure /home/nic/src/writing/aops exists"
    exit 1
fi

TARGET_DIR="${1:-.}"

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Target directory does not exist: $TARGET_DIR"
    exit 1
fi

cd "$TARGET_DIR"
echo "Initializing academicOps standards in: $(pwd)"

# 1. Copy dprint configuration
echo "Installing dprint.json..."
cp "$AOPS_DIR/templates/dprint.json" .
echo "✓ dprint.json installed"

# 2. Install pre-commit config if not exists
if [ ! -f .pre-commit-config.yaml ]; then
    echo "Creating .pre-commit-config.yaml..."
    cat > .pre-commit-config.yaml << 'EOF'
repos:
  # Standard file hygiene
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
        exclude: |
          (?x)^(
            \.vscode/.*\.json|
            \.claude/.*\.json|
            .*\.ipynb
          )$
      - id: check-toml
      - id: mixed-line-ending
        args: ["--fix=lf"]

  # Python formatting (if Python project)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix, --unsafe-fixes, --exit-non-zero-on-fix]
      - id: ruff-format

  # academicOps framework hooks
  - repo: https://github.com/nicsuzor/academicOps
    rev: main
    hooks:
      - id: dprint
      - id: no-config-defaults
      - id: check-instruction-bloat
EOF
    echo "✓ .pre-commit-config.yaml created"
else
    echo "⚠ .pre-commit-config.yaml already exists, skipping"
fi

# 3. Check if dprint is installed
if ! command -v dprint &> /dev/null; then
    echo "⚠ dprint not found. Install with: npm i -g dprint"
    DPRINT_MISSING=1
else
    echo "✓ dprint is installed"
    DPRINT_MISSING=0
fi

# 4. Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "⚠ pre-commit not found. Install with: pip install pre-commit"
    PRECOMMIT_MISSING=1
else
    echo "✓ pre-commit is installed"
    PRECOMMIT_MISSING=0
fi

# 5. Install pre-commit hooks if pre-commit available
if [ $PRECOMMIT_MISSING -eq 0 ]; then
    echo "Installing pre-commit hooks..."
    pre-commit install
    echo "✓ Pre-commit hooks installed"
fi

# 6. Run initial format if dprint available
if [ $DPRINT_MISSING -eq 0 ]; then
    echo "Running initial format..."
    dprint fmt || echo "⚠ Some files could not be formatted"
    echo "✓ Initial format complete"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "academicOps standards initialized successfully!"
echo ""
echo "Installed:"
echo "  ✓ dprint.json (formatter config)"
if [ ! -f .pre-commit-config.yaml ]; then
    echo "  ✓ .pre-commit-config.yaml (pre-commit hooks)"
fi
if [ $PRECOMMIT_MISSING -eq 0 ]; then
    echo "  ✓ pre-commit hooks"
fi
echo ""
if [ $DPRINT_MISSING -eq 1 ] || [ $PRECOMMIT_MISSING -eq 1 ]; then
    echo "Action needed:"
    [ $DPRINT_MISSING -eq 1 ] && echo "  • Install dprint: npm i -g dprint"
    [ $PRECOMMIT_MISSING -eq 1 ] && echo "  • Install pre-commit: pip install pre-commit"
    echo ""
fi
echo "Test with:"
echo "  pre-commit run --all-files"
echo "  dprint check"
echo "═══════════════════════════════════════════════════════════"
