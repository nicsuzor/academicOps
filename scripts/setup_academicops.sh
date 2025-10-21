#!/usr/bin/env bash
# Simplified setup script for academicOps integration
#
# Creates single .academicOps symlink and copies settings

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== academicOps Setup ==="
echo

# Determine target
TARGET_DIR="${1:-$PWD}"
cd "$TARGET_DIR"
PROJECT_ROOT="$PWD"

echo "Setting up: $PROJECT_ROOT"
echo

# Verify ACADEMICOPS_BOT
if [ -z "${ACADEMICOPS_BOT:-}" ]; then
    echo -e "${RED}ERROR: ACADEMICOPS_BOT environment variable not set${NC}"
    echo "Add to shell profile: export ACADEMICOPS_BOT=/path/to/academicOps"
    exit 1
fi

if [ ! -d "$ACADEMICOPS_BOT" ]; then
    echo -e "${RED}ERROR: ACADEMICOPS_BOT directory not found: $ACADEMICOPS_BOT${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} ACADEMICOPS_BOT=$ACADEMICOPS_BOT"
echo

# 1. Create single .academicOps symlink
echo "Creating .academicOps symlink..."

if [ -L ".academicOps" ]; then
    echo -e "${YELLOW}⚠${NC}  Removing existing symlink"
    rm ".academicOps"
elif [ -d ".academicOps" ]; then
    echo -e "${YELLOW}⚠${NC}  Backing up to .academicOps.backup"
    mv ".academicOps" ".academicOps.backup"
fi

ln -s "$ACADEMICOPS_BOT" ".academicOps"
echo -e "${GREEN}✓${NC} .academicOps → $ACADEMICOPS_BOT"
echo

# 2. Create .claude directory and symlink agents/commands
echo "Setting up Claude Code configuration..."

mkdir -p ".claude"

cp ".academicOps/dist/.claude/settings.json" ".claude/settings.json"
echo -e "${GREEN}✓${NC} Copied settings.json"

# Symlink agents directory
if [ -L ".claude/agents" ]; then
    rm ".claude/agents"
elif [ -d ".claude/agents" ]; then
    echo -e "${YELLOW}⚠${NC}  Backing up .claude/agents to .claude/agents.backup"
    mv ".claude/agents" ".claude/agents.backup"
fi
ln -s "../.academicOps/.claude/agents" ".claude/agents"
echo -e "${GREEN}✓${NC} Symlinked .claude/agents/"

# Symlink commands directory
if [ -L ".claude/commands" ]; then
    rm ".claude/commands"
elif [ -d ".claude/commands" ]; then
    echo -e "${YELLOW}⚠${NC}  Backing up .claude/commands to .claude/commands.backup"
    mv ".claude/commands" ".claude/commands.backup"
fi
ln -s "../.academicOps/.claude/commands" ".claude/commands"
echo -e "${GREEN}✓${NC} Symlinked .claude/commands/"
echo

# 3. Create bots/agents/ for project overrides
echo "Creating bots/agents/ for project-specific overrides..."

mkdir -p "bots/agents"

if [ ! -f "bots/agents/_CORE.md" ] && [ -f ".academicOps/dist/bots/agents/_CORE.md" ]; then
    cp ".academicOps/dist/bots/agents/_CORE.md" "bots/agents/_CORE.md"
    echo -e "${GREEN}✓${NC} Created bots/agents/_CORE.md template"
fi

echo -e "${GREEN}✓${NC} bots/agents/ ready"
echo

# 4. Update .gitignore
echo "Updating .gitignore..."

GITIGNORE_MARKER="# academicOps managed files"

if [ -f ".gitignore" ] && grep -q "$GITIGNORE_MARKER" ".gitignore"; then
    echo -e "${GREEN}✓${NC} .gitignore already updated"
else
    echo "" >> ".gitignore"
    cat ".academicOps/dist/.gitignore" >> ".gitignore"
    echo -e "${GREEN}✓${NC} Added academicOps exclusions to .gitignore"
fi

echo
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo
echo "Installed:"
echo "  - .academicOps/ → $ACADEMICOPS_BOT"
echo "  - .claude/settings.json"
echo "  - bots/agents/ (for project overrides)"
echo "  - .gitignore (updated)"
echo
echo "Next:"
echo "  1. Launch Claude Code"
echo "  2. Verify hooks work"
echo "  3. Customize bots/agents/_CORE.md"
echo
