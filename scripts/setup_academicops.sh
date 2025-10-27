#!/usr/bin/env bash
# Setup script for academicOps - installs to ~/.claude/ (user global config)
#
# Symlinks settings, hooks, agents, commands, and skills to ~/.claude/
# so they apply globally to all Claude Code sessions.
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== academicOps Setup ==="
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

# Create ~/.claude if it doesn't exist
CLAUDE_HOME="$HOME/.claude"
mkdir -p "$CLAUDE_HOME"
echo -e "${GREEN}✓${NC} ~/.claude/ exists"
echo

# Symlink settings.json
echo "Setting up global Claude Code configuration..."

SETTINGS_SRC="$ACADEMICOPS_BOT/bots/config/settings.json"
SETTINGS_DEST="$CLAUDE_HOME/settings.json"

if [ -L "$SETTINGS_DEST" ]; then
    echo -e "${YELLOW}⚠${NC}  Removing existing settings.json symlink"
    rm "$SETTINGS_DEST"
elif [ -f "$SETTINGS_DEST" ]; then
    echo -e "${YELLOW}⚠${NC}  Backing up existing settings.json"
    mv "$SETTINGS_DEST" "$SETTINGS_DEST.backup"
fi

ln -s "$SETTINGS_SRC" "$SETTINGS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/settings.json → $SETTINGS_SRC"

# Symlink hooks directory
HOOKS_SRC="$ACADEMICOPS_BOT/bots/hooks"
HOOKS_DEST="$CLAUDE_HOME/hooks"

if [ -L "$HOOKS_DEST" ]; then
    rm "$HOOKS_DEST"
elif [ -d "$HOOKS_DEST" ]; then
    echo -e "${YELLOW}⚠${NC}  Backing up existing hooks/"
    mv "$HOOKS_DEST" "$HOOKS_DEST.backup"
fi

ln -s "$HOOKS_SRC" "$HOOKS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/hooks/ → $HOOKS_SRC"

# Symlink agents directory
AGENTS_SRC="$ACADEMICOPS_BOT/bots/agents"
AGENTS_DEST="$CLAUDE_HOME/agents"

if [ -L "$AGENTS_DEST" ]; then
    rm "$AGENTS_DEST"
elif [ -d "$AGENTS_DEST" ]; then
    echo -e "${YELLOW}⚠${NC}  Backing up existing agents/"
    mv "$AGENTS_DEST" "$AGENTS_DEST.backup"
fi

ln -s "$AGENTS_SRC" "$AGENTS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/agents/ → $AGENTS_SRC"

# Symlink commands directory
COMMANDS_SRC="$ACADEMICOPS_BOT/commands"
COMMANDS_DEST="$CLAUDE_HOME/commands"

if [ -L "$COMMANDS_DEST" ]; then
    rm "$COMMANDS_DEST"
elif [ -d "$COMMANDS_DEST" ]; then
    echo -e "${YELLOW}⚠${NC}  Backing up existing commands/"
    mv "$COMMANDS_DEST" "$COMMANDS_DEST.backup"
fi

ln -s "$COMMANDS_SRC" "$COMMANDS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/commands/ → $COMMANDS_SRC"

# Symlink skills directory
SKILLS_SRC="$ACADEMICOPS_BOT/skills"
SKILLS_DEST="$CLAUDE_HOME/skills"

if [ -L "$SKILLS_DEST" ]; then
    rm "$SKILLS_DEST"
elif [ -d "$SKILLS_DEST" ]; then
    echo -e "${YELLOW}⚠${NC}  Backing up existing skills/"
    mv "$SKILLS_DEST" "$SKILLS_DEST.backup"
fi

ln -s "$SKILLS_SRC" "$SKILLS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/skills/ → $SKILLS_SRC"

echo
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo
echo "Installed to ~/.claude/:"
echo "  - settings.json (symlinked)"
echo "  - hooks/ (symlinked)"
echo "  - agents/ (symlinked)"
echo "  - commands/ (symlinked)"
echo "  - skills/ (symlinked)"
echo
echo "All Claude Code sessions will now use academicOps configuration."
echo
echo "Next:"
echo "  1. Launch Claude Code in any project"
echo "  2. Verify hooks work"
echo "  3. Configuration is global - no per-project setup needed"
echo
