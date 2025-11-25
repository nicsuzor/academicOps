#!/usr/bin/env bash
# Setup script for aOps - installs to both ~/.claude/ and repo/.claude/
#
# Creates two sets of symlinks:
# 1. ~/.claude/ (user global config) - for local development
# 2. $AOPS/.claude/ (repo config) - for remote coding, checked into git
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== Bots Setup ==="
echo

# Get the script directory and derive bots path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$BOTS_DIR/.." && pwd)"

echo -e "${GREEN}✓${NC} Bots directory: $BOTS_DIR"
echo -e "${GREEN}✓${NC} Repository root: $REPO_ROOT"
echo

# Create ~/.claude if it doesn't exist
CLAUDE_HOME="$HOME/.claude"
mkdir -p "$CLAUDE_HOME"
echo -e "${GREEN}✓${NC} ~/.claude/ exists"
echo

# Symlink settings.json
echo "Setting up global Claude Code configuration..."

SETTINGS_SRC="$BOTS_DIR/config/claude/settings.json"
SETTINGS_DEST="$CLAUDE_HOME/settings.json"

[ -e "$SETTINGS_DEST" ] && rm -rf "$SETTINGS_DEST"
ln -s "$SETTINGS_SRC" "$SETTINGS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/settings.json → $SETTINGS_SRC"

# Symlink hooks directory
HOOKS_SRC="$BOTS_DIR/hooks"
HOOKS_DEST="$CLAUDE_HOME/hooks"

[ -e "$HOOKS_DEST" ] && rm -rf "$HOOKS_DEST"
ln -s "$HOOKS_SRC" "$HOOKS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/hooks/ → $HOOKS_SRC"

# Symlink agents directory
AGENTS_SRC="$BOTS_DIR/agents"
AGENTS_DEST="$CLAUDE_HOME/agents"

[ -e "$AGENTS_DEST" ] && rm -rf "$AGENTS_DEST"
ln -s "$AGENTS_SRC" "$AGENTS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/agents/ → $AGENTS_SRC"

# Symlink skills directory
SKILLS_SRC="$BOTS_DIR/skills"
SKILLS_DEST="$CLAUDE_HOME/skills"

[ -e "$SKILLS_DEST" ] && rm -rf "$SKILLS_DEST"
ln -s "$SKILLS_SRC" "$SKILLS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/skills/ → $SKILLS_SRC"

# Symlink commands directory
COMMANDS_SRC="$BOTS_DIR/commands"
COMMANDS_DEST="$CLAUDE_HOME/commands"

[ -e "$COMMANDS_DEST" ] && rm -rf "$COMMANDS_DEST"
ln -s "$COMMANDS_SRC" "$COMMANDS_DEST"
echo -e "${GREEN}✓${NC} ~/.claude/commands/ → $COMMANDS_SRC"

# NOTE: We do NOT symlink CLAUDE.md to ~/.claude/
# Each repository should have its own CLAUDE.md with repo-specific instructions
# Only skills/hooks/commands/agents are shared via ~/.claude/

echo
echo "=== Setting up repository .claude/ (for remote coding) ==="
echo

# Create .claude in repository root
REPO_CLAUDE="$BOTS_DIR/.claude"
mkdir -p "$REPO_CLAUDE"
echo -e "${GREEN}✓${NC} $BOTS_DIR/.claude/ created"

# Symlink settings.json (relative path)
REPO_SETTINGS_DEST="$REPO_CLAUDE/settings.json"
[ -e "$REPO_SETTINGS_DEST" ] && rm -rf "$REPO_SETTINGS_DEST"
ln -s ../config/claude/settings.json "$REPO_SETTINGS_DEST"
echo -e "${GREEN}✓${NC} .claude/settings.json → config/claude/settings.json (relative)"

# Symlink hooks directory (relative path)
REPO_HOOKS_DEST="$REPO_CLAUDE/hooks"
[ -e "$REPO_HOOKS_DEST" ] && rm -rf "$REPO_HOOKS_DEST"
ln -s ../hooks "$REPO_HOOKS_DEST"
echo -e "${GREEN}✓${NC} .claude/hooks/ → hooks/ (relative)"

# Symlink agents directory (relative path)
REPO_AGENTS_DEST="$REPO_CLAUDE/agents"
[ -e "$REPO_AGENTS_DEST" ] && rm -rf "$REPO_AGENTS_DEST"
ln -s ../agents "$REPO_AGENTS_DEST"
echo -e "${GREEN}✓${NC} .claude/agents/ → agents/ (relative)"

# Symlink skills directory (relative path)
REPO_SKILLS_DEST="$REPO_CLAUDE/skills"
[ -e "$REPO_SKILLS_DEST" ] && rm -rf "$REPO_SKILLS_DEST"
ln -s ../skills "$REPO_SKILLS_DEST"
echo -e "${GREEN}✓${NC} .claude/skills/ → skills/ (relative)"

# Symlink commands directory (relative path)
REPO_COMMANDS_DEST="$REPO_CLAUDE/commands"
[ -e "$REPO_COMMANDS_DEST" ] && rm -rf "$REPO_COMMANDS_DEST"
ln -s ../commands "$REPO_COMMANDS_DEST"
echo -e "${GREEN}✓${NC} .claude/commands/ → commands/ (relative)"

# Symlink CLAUDE.md (relative path)
REPO_CLAUDE_MD_DEST="$REPO_CLAUDE/CLAUDE.md"
[ -e "$REPO_CLAUDE_MD_DEST" ] && rm -rf "$REPO_CLAUDE_MD_DEST"
ln -s ../CLAUDE.md "$REPO_CLAUDE_MD_DEST"
echo -e "${GREEN}✓${NC} .claude/CLAUDE.md → CLAUDE.md (relative)"

echo
echo "=== Configuring Basic Memory (bmem) ==="
echo

# Configure bmem with default project mode
# The config file location depends on the basicmemory package implementation
# Try to set default project if bmem is available
if command -v uvx &> /dev/null; then
    echo "Setting bmem default project to 'main'..."
    uvx basic-memory project default main 2>/dev/null || echo -e "${YELLOW}⚠${NC}  Could not set bmem default project (may need manual configuration)"
    echo -e "${GREEN}✓${NC} bmem configured for default project mode"
else
    echo -e "${YELLOW}⚠${NC}  uvx not found, skipping bmem configuration"
fi

echo
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo
echo "Installed to TWO locations:"
echo
echo "1. ~/.claude/ (user global, for local development)"
echo "   - settings.json (symlinked)"
echo "   - hooks/ (symlinked)"
echo "   - skills/ (symlinked)"
echo "   - commands/ (symlinked)"
echo "   - agents/ (symlinked)"
echo "   - CLAUDE.md NOT symlinked (each repo has its own)"
echo
echo "2. $BOTS_DIR/.claude/ (repository, for remote coding)"
echo "   - All symlinks use relative paths"
echo "   - Checked into git for remote environments"
echo
echo "3. Basic Memory (bmem) default project: main"
echo
echo "Next:"
echo "  1. Commit $BOTS_DIR/.claude/ to git (not ignored)"
echo "  2. Launch Claude Code anywhere to use aOps"
echo "  3. Remote coding will use repo .claude/ automatically"
echo
