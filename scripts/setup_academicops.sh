#!/usr/bin/env bash
# Setup script for academicOps integration in third-party repositories
#
# This script configures any repository to work with academicOps framework
# when academicOps is in a flat directory structure.
#
# Usage:
#   ./scripts/setup_academicops.sh [target-directory]
#
# If target-directory is not provided, uses current directory (PWD)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== academicOps Setup for Third-Party Repository ==="
echo

# Determine target directory
TARGET_DIR="${1:-$PWD}"
cd "$TARGET_DIR"
PROJECT_ROOT="$PWD"

echo "Setting up: $PROJECT_ROOT"
echo

# 1. Verify environment variables
echo "Checking environment variables..."

if [ -z "${ACADEMICOPS_BOT:-}" ]; then
    echo -e "${RED}ERROR: ACADEMICOPS_BOT environment variable not set${NC}"
    echo "Please add to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo "  export ACADEMICOPS_BOT=/path/to/academicOps"
    exit 1
fi

if [ ! -d "$ACADEMICOPS_BOT" ]; then
    echo -e "${RED}ERROR: ACADEMICOPS_BOT directory does not exist: $ACADEMICOPS_BOT${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} ACADEMICOPS_BOT=$ACADEMICOPS_BOT"

if [ -n "${ACADEMICOPS_PERSONAL:-}" ]; then
    if [ -d "$ACADEMICOPS_PERSONAL" ]; then
        echo -e "${GREEN}✓${NC} ACADEMICOPS_PERSONAL=$ACADEMICOPS_PERSONAL (optional personal context)"
    else
        echo -e "${YELLOW}⚠${NC}  ACADEMICOPS_PERSONAL set but directory not found: $ACADEMICOPS_PERSONAL"
        echo "    Personal context will not be loaded"
    fi
else
    echo -e "${YELLOW}⚠${NC}  ACADEMICOPS_PERSONAL not set (optional - personal context disabled)"
fi

# 2. Create .claude directory if it doesn't exist
echo
echo "Setting up Claude Code configuration..."

CLAUDE_DIR="$PROJECT_ROOT/.claude"

if [ ! -d "$CLAUDE_DIR" ]; then
    mkdir -p "$CLAUDE_DIR"
    echo -e "${GREEN}✓${NC} Created $CLAUDE_DIR"
else
    echo -e "${GREEN}✓${NC} $CLAUDE_DIR already exists"
fi

# 3. Copy settings.json from dist/ template
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
DIST_SETTINGS="$ACADEMICOPS_BOT/dist/.claude/settings.json"

if [ ! -f "$DIST_SETTINGS" ]; then
    echo -e "${RED}ERROR: Template settings.json not found at $DIST_SETTINGS${NC}"
    exit 1
fi

cp "$DIST_SETTINGS" "$SETTINGS_FILE"
echo -e "${GREEN}✓${NC} Copied settings.json from dist/ template"

# 4. Symlink agents directory
AGENTS_LINK="$CLAUDE_DIR/agents"

if [ -L "$AGENTS_LINK" ]; then
    echo -e "${YELLOW}⚠${NC}  Removing existing agents symlink"
    rm "$AGENTS_LINK"
elif [ -d "$AGENTS_LINK" ]; then
    echo -e "${YELLOW}⚠${NC}  Backing up existing agents directory to agents.backup"
    mv "$AGENTS_LINK" "${AGENTS_LINK}.backup"
fi

ln -s "$ACADEMICOPS_BOT/.claude/agents" "$AGENTS_LINK"
echo -e "${GREEN}✓${NC} Symlinked agents from $ACADEMICOPS_BOT/.claude/agents"

# 5. Create agents/ directory for project-specific instructions if needed
PROJECT_AGENTS_DIR="$PROJECT_ROOT/agents"

if [ ! -d "$PROJECT_AGENTS_DIR" ]; then
    mkdir -p "$PROJECT_AGENTS_DIR"
    echo -e "${GREEN}✓${NC} Created $PROJECT_AGENTS_DIR"
else
    echo -e "${GREEN}✓${NC} $PROJECT_AGENTS_DIR already exists"
fi

# 6. Copy INSTRUCTIONS.md template if it doesn't exist
INSTRUCTIONS_FILE="$PROJECT_AGENTS_DIR/INSTRUCTIONS.md"
DIST_INSTRUCTIONS="$ACADEMICOPS_BOT/dist/INSTRUCTIONS.md"

if [ ! -f "$INSTRUCTIONS_FILE" ]; then
    if [ -f "$DIST_INSTRUCTIONS" ]; then
        cp "$DIST_INSTRUCTIONS" "$INSTRUCTIONS_FILE"
        echo -e "${GREEN}✓${NC} Created placeholder $INSTRUCTIONS_FILE from template"
    else
        echo -e "${YELLOW}⚠${NC}  Template INSTRUCTIONS.md not found, skipping"
    fi
else
    echo -e "${GREEN}✓${NC} $INSTRUCTIONS_FILE already exists"
fi

# 7. Update .gitignore to exclude academicOps managed files
GITIGNORE_FILE="$PROJECT_ROOT/.gitignore"
GITIGNORE_MARKER="# academicOps managed files"

if [ -f "$GITIGNORE_FILE" ] && grep -q "$GITIGNORE_MARKER" "$GITIGNORE_FILE"; then
    echo -e "${GREEN}✓${NC} .gitignore already contains academicOps exclusions"
else
    echo "" >> "$GITIGNORE_FILE"
    cat "$ACADEMICOPS_BOT/dist/.gitignore" >> "$GITIGNORE_FILE"
    echo -e "${GREEN}✓${NC} Added academicOps exclusions to .gitignore"
fi

# 8. Verify load_instructions.py exists and is executable
LOAD_SCRIPT="$ACADEMICOPS_BOT/scripts/load_instructions.py"

if [ ! -f "$LOAD_SCRIPT" ]; then
    echo -e "${RED}ERROR: load_instructions.py not found at $LOAD_SCRIPT${NC}"
    exit 1
fi

if [ ! -x "$LOAD_SCRIPT" ]; then
    chmod +x "$LOAD_SCRIPT"
    echo -e "${GREEN}✓${NC} Made $LOAD_SCRIPT executable"
fi

# 9. Test the setup
echo
echo "Testing configuration..."

if python3 "$LOAD_SCRIPT" < /dev/null > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} load_instructions.py executes successfully"
else
    echo -e "${YELLOW}⚠${NC}  load_instructions.py test had warnings (may be expected)"
fi

# 10. Success summary
echo
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo
echo "Created/verified:"
echo "  - $CLAUDE_DIR/settings.json (copied from dist/ template)"
echo "  - $CLAUDE_DIR/agents/ (symlinked to academicOps)"
echo "  - $PROJECT_AGENTS_DIR/INSTRUCTIONS.md (project context)"
echo "  - .gitignore (excludes academicOps managed files)"
echo
echo "Environment configuration:"
echo "  - ACADEMICOPS_BOT=$ACADEMICOPS_BOT"
[ -n "${ACADEMICOPS_PERSONAL:-}" ] && echo "  - ACADEMICOPS_PERSONAL=$ACADEMICOPS_PERSONAL"
echo
echo "Next steps:"
echo "  1. Launch Claude Code from this directory"
echo "  2. Verify core instructions load at session start"
echo "  3. Customize agents/INSTRUCTIONS.md for your project workflow"
echo
