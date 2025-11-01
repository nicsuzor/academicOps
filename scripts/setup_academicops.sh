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

# Verify ACADEMICOPS
if [ -z "${ACADEMICOPS:-}" ]; then
    echo -e "${RED}ERROR: ACADEMICOPS environment variable not set${NC}"
    echo "Add to shell profile: export ACADEMICOPS=/path/to/academicOps"
    exit 1
fi

if [ ! -d "$ACADEMICOPS" ]; then
    echo -e "${RED}ERROR: ACADEMICOPS directory not found: $ACADEMICOPS${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} ACADEMICOPS=$ACADEMICOPS"
echo

# Create ~/.claude if it doesn't exist
CLAUDE_HOME="$HOME/.claude"
mkdir -p "$CLAUDE_HOME"
echo -e "${GREEN}✓${NC} ~/.claude/ exists"
echo

# Symlink settings.json
echo "Setting up global Claude Code configuration..."

SETTINGS_SRC="$ACADEMICOPS/config/settings.json"
SETTINGS_DEST="$CLAUDE_HOME/settings.json"

[ -e "$SETTINGS_DEST" ] && rm -rf "$SETTINGS_DEST"
ln -s "$SETTINGS_SRC" "$SETTINGS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/settings.json → $SETTINGS_SRC"

# Symlink hooks directory
HOOKS_SRC="$ACADEMICOPS/hooks"
HOOKS_DEST="$CLAUDE_HOME/hooks"

[ -e "$HOOKS_DEST" ] && rm -rf "$HOOKS_DEST"
ln -s "$HOOKS_SRC" "$HOOKS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/hooks/ → $HOOKS_SRC"

# Symlink agents directory
AGENTS_SRC="$ACADEMICOPS/agents"
AGENTS_DEST="$CLAUDE_HOME/agents"

[ -e "$AGENTS_DEST" ] && rm -rf "$AGENTS_DEST"
ln -s "$AGENTS_SRC" "$AGENTS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/agents/ → $AGENTS_SRC"

# Symlink commands directory
COMMANDS_SRC="$ACADEMICOPS/commands"
COMMANDS_DEST="$CLAUDE_HOME/commands"

[ -e "$COMMANDS_DEST" ] && rm -rf "$COMMANDS_DEST"
ln -s "$COMMANDS_SRC" "$COMMANDS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/commands/ → $COMMANDS_SRC"

# Symlink skills directory
SKILLS_SRC="$ACADEMICOPS/skills"
SKILLS_DEST="$CLAUDE_HOME/skills"

[ -e "$SKILLS_DEST" ] && rm -rf "$SKILLS_DEST"
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
