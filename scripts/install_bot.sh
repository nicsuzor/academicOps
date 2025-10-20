#!/usr/bin/env bash
# install_bot.sh - Install academicOps framework in target repository using /bots/ structure
#
# This script configures any repository to work with academicOps framework
# using the new /bots/ directory standard for clean separation of concerns.
#
# Usage:
#   cd /path/to/your/project
#   $ACADEMICOPS_BOT/scripts/install_bot.sh
#
# Or from anywhere:
#   $ACADEMICOPS_BOT/scripts/install_bot.sh /path/to/your/project
#
# Options:
#   --no-symlink    Copy files instead of symlinking (for Windows/NTFS filesystems)
#
# Architecture:
#   target-repo/
#   ├── bots/                      # All academicOps installation
#   │   ├── .academicOps/          # Symlink to framework
#   │   ├── agents/                # Repo-local agent customizations
#   │   ├── commands/              # Repo-local slash commands
#   │   ├── docs/                  # Repo-local documentation
#   │   └── scripts/               # Repo-local automation
#   ├── .claude/
#   │   ├── agents -> bots/.academicOps/.claude/agents
#   │   ├── commands -> bots/.academicOps/.claude/commands
#   │   └── settings.json          # Repo-specific settings
#   └── docs/                      # User's existing docs (NEVER TOUCH)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse options
USE_SYMLINKS=true
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-symlink)
            USE_SYMLINKS=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS] [target-directory]"
            echo ""
            echo "Install academicOps framework in target repository."
            echo ""
            echo "Options:"
            echo "  --no-symlink    Copy files instead of symlinking"
            echo "  -h, --help      Show this help message"
            echo ""
            echo "If target-directory is not provided, uses current directory."
            exit 0
            ;;
        *)
            # Assume it's the target directory
            break
            ;;
    esac
done

echo -e "${BLUE}=== academicOps Installation: /bots/ Directory Standard ===${NC}"
echo

# Determine target directory
TARGET_DIR="${1:-$PWD}"
cd "$TARGET_DIR"
PROJECT_ROOT="$PWD"

echo "Installing in: $PROJECT_ROOT"
if [ "$USE_SYMLINKS" = false ]; then
    echo -e "Mode: ${YELLOW}Copy${NC} (--no-symlink enabled for Windows/NTFS compatibility)"
else
    echo -e "Mode: ${GREEN}Symlink${NC} (default)"
fi
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

# 2. Create /bots/ directory structure
echo
echo "Creating /bots/ directory structure..."

BOTS_DIR="$PROJECT_ROOT/bots"

if [ ! -d "$BOTS_DIR" ]; then
    mkdir -p "$BOTS_DIR"
    echo -e "${GREEN}✓${NC} Created $BOTS_DIR"
else
    echo -e "${GREEN}✓${NC} $BOTS_DIR already exists"
fi

# Create subdirectories for repo-local customizations
for subdir in agents commands docs scripts; do
    if [ ! -d "$BOTS_DIR/$subdir" ]; then
        mkdir -p "$BOTS_DIR/$subdir"
        echo -e "${GREEN}✓${NC} Created $BOTS_DIR/$subdir"
    else
        echo -e "${GREEN}✓${NC} $BOTS_DIR/$subdir already exists"
    fi
done

# 3. Symlink or copy framework as bots/.academicOps
echo
echo "Setting up framework link..."

ACADEMICOPS_LINK="$BOTS_DIR/.academicOps"

if [ -L "$ACADEMICOPS_LINK" ]; then
    CURRENT_TARGET=$(readlink "$ACADEMICOPS_LINK")
    if [ "$CURRENT_TARGET" = "$ACADEMICOPS_BOT" ]; then
        echo -e "${GREEN}✓${NC} bots/.academicOps already links to $ACADEMICOPS_BOT"
    else
        echo -e "${YELLOW}⚠${NC}  Updating bots/.academicOps symlink (was: $CURRENT_TARGET)"
        rm "$ACADEMICOPS_LINK"
        ln -s "$ACADEMICOPS_BOT" "$ACADEMICOPS_LINK"
        echo -e "${GREEN}✓${NC} Updated symlink to $ACADEMICOPS_BOT"
    fi
elif [ -d "$ACADEMICOPS_LINK" ]; then
    echo -e "${YELLOW}⚠${NC}  bots/.academicOps exists as directory, backing up to .academicOps.backup"
    mv "$ACADEMICOPS_LINK" "${ACADEMICOPS_LINK}.backup"
    ln -s "$ACADEMICOPS_BOT" "$ACADEMICOPS_LINK"
    echo -e "${GREEN}✓${NC} Created symlink (old directory backed up)"
else
    if [ "$USE_SYMLINKS" = true ]; then
        ln -s "$ACADEMICOPS_BOT" "$ACADEMICOPS_LINK"
        echo -e "${GREEN}✓${NC} Created symlink: bots/.academicOps -> $ACADEMICOPS_BOT"
    else
        # Use -L to follow symlinks and copy actual files
        cp -rL "$ACADEMICOPS_BOT" "$ACADEMICOPS_LINK"
        echo -e "${GREEN}✓${NC} Copied framework to bots/.academicOps"
    fi
fi

# 4. Setup .claude/ directory
echo
echo "Setting up Claude Code configuration..."

CLAUDE_DIR="$PROJECT_ROOT/.claude"

if [ ! -d "$CLAUDE_DIR" ]; then
    mkdir -p "$CLAUDE_DIR"
    echo -e "${GREEN}✓${NC} Created $CLAUDE_DIR"
else
    echo -e "${GREEN}✓${NC} $CLAUDE_DIR already exists"
fi

# 5. Symlink agents directory
AGENTS_LINK="$CLAUDE_DIR/agents"
AGENTS_SOURCE="../bots/.academicOps/.claude/agents"  # Relative path from .claude/

if [ -L "$AGENTS_LINK" ]; then
    echo -e "${YELLOW}⚠${NC}  Removing existing agents symlink"
    rm "$AGENTS_LINK"
elif [ -d "$AGENTS_LINK" ]; then
    echo -e "${YELLOW}⚠${NC}  Backing up existing agents directory to agents.backup"
    mv "$AGENTS_LINK" "${AGENTS_LINK}.backup"
fi

if [ "$USE_SYMLINKS" = true ]; then
    cd "$CLAUDE_DIR"
    ln -s "$AGENTS_SOURCE" agents
    cd "$PROJECT_ROOT"
    echo -e "${GREEN}✓${NC} Symlinked .claude/agents to framework"
else
    # Copy agents directory
    cp -rL "$BOTS_DIR/.academicOps/.claude/agents" "$AGENTS_LINK"
    echo -e "${GREEN}✓${NC} Copied agents to .claude/agents"
fi

# 6. Symlink commands directory (if exists in framework)
COMMANDS_LINK="$CLAUDE_DIR/commands"
COMMANDS_SOURCE="../bots/.academicOps/.claude/commands"  # Relative path from .claude/

if [ -d "$BOTS_DIR/.academicOps/.claude/commands" ]; then
    if [ -L "$COMMANDS_LINK" ]; then
        echo -e "${YELLOW}⚠${NC}  Removing existing commands symlink"
        rm "$COMMANDS_LINK"
    elif [ -d "$COMMANDS_LINK" ]; then
        echo -e "${YELLOW}⚠${NC}  Backing up existing commands directory to commands.backup"
        mv "$COMMANDS_LINK" "${COMMANDS_LINK}.backup"
    fi

    if [ "$USE_SYMLINKS" = true ]; then
        cd "$CLAUDE_DIR"
        ln -s "$COMMANDS_SOURCE" commands
        cd "$PROJECT_ROOT"
        echo -e "${GREEN}✓${NC} Symlinked .claude/commands to framework"
    else
        cp -rL "$BOTS_DIR/.academicOps/.claude/commands" "$COMMANDS_LINK"
        echo -e "${GREEN}✓${NC} Copied commands to .claude/commands"
    fi
else
    echo -e "${YELLOW}⚠${NC}  No commands directory in framework (skipping)"
fi

# 7. Copy settings.json template (if not exists)
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
DIST_SETTINGS="$BOTS_DIR/.academicOps/dist/.claude/settings.json"

if [ ! -f "$SETTINGS_FILE" ]; then
    if [ -f "$DIST_SETTINGS" ]; then
        # Update paths in template to use bots/.academicOps
        sed 's|\.academicOps/|bots/.academicOps/|g' "$DIST_SETTINGS" > "$SETTINGS_FILE"
        echo -e "${GREEN}✓${NC} Created .claude/settings.json from template"
    else
        echo -e "${YELLOW}⚠${NC}  Template settings.json not found at $DIST_SETTINGS"
        echo "    You'll need to configure .claude/settings.json manually"
    fi
else
    echo -e "${GREEN}✓${NC} .claude/settings.json already exists (not overwriting)"
    echo -e "${YELLOW}    NOTE: Ensure hooks reference bots/.academicOps/scripts/${NC}"
fi

# 8. Create template INSTRUCTIONS.md (if not exists)
INSTRUCTIONS_FILE="$BOTS_DIR/docs/INSTRUCTIONS.md"
DIST_INSTRUCTIONS="$BOTS_DIR/.academicOps/dist/agents/INSTRUCTIONS.md"

if [ ! -f "$INSTRUCTIONS_FILE" ]; then
    if [ -f "$DIST_INSTRUCTIONS" ]; then
        cp "$DIST_INSTRUCTIONS" "$INSTRUCTIONS_FILE"
        echo -e "${GREEN}✓${NC} Created bots/docs/INSTRUCTIONS.md template"
    else
        # Create minimal template
        cat > "$INSTRUCTIONS_FILE" << 'EOF'
# Project Instructions

Project-specific instructions for agents working in this repository.

## Project Context

- **Repository**: [owner/repo]
- **Purpose**: [Brief description]
- **Priority**: [P0-P3]

## Development Rules

1. [Project-specific standards]
2. [Testing requirements]
3. [Any special considerations]

For generic development methodology, see academicOps core instructions.
EOF
        echo -e "${GREEN}✓${NC} Created minimal bots/docs/INSTRUCTIONS.md template"
    fi
else
    echo -e "${GREEN}✓${NC} bots/docs/INSTRUCTIONS.md already exists"
fi

# 9. Update .gitignore
echo
echo "Updating .gitignore..."

GITIGNORE_FILE="$PROJECT_ROOT/.gitignore"

# Create .gitignore if it doesn't exist
if [ ! -f "$GITIGNORE_FILE" ]; then
    touch "$GITIGNORE_FILE"
    echo -e "${GREEN}✓${NC} Created .gitignore"
fi

# Add academicOps exclusions if not present
NEEDS_UPDATE=false

if ! grep -q "bots/.academicOps" "$GITIGNORE_FILE"; then
    NEEDS_UPDATE=true
fi

if [ "$NEEDS_UPDATE" = true ]; then
    echo "" >> "$GITIGNORE_FILE"
    echo "# academicOps framework (symlink to local installation)" >> "$GITIGNORE_FILE"
    echo "bots/.academicOps" >> "$GITIGNORE_FILE"
    echo "" >> "$GITIGNORE_FILE"
    echo "# Claude Code managed symlinks" >> "$GITIGNORE_FILE"
    echo ".claude/agents" >> "$GITIGNORE_FILE"
    echo ".claude/commands" >> "$GITIGNORE_FILE"
    echo -e "${GREEN}✓${NC} Added academicOps exclusions to .gitignore"
else
    echo -e "${GREEN}✓${NC} .gitignore already contains academicOps exclusions"
fi

# 10. Verify installation
echo
echo "Verifying installation..."

# Check directory structure
ERRORS=0

if [ ! -d "$BOTS_DIR/.academicOps" ]; then
    echo -e "${RED}✗${NC} bots/.academicOps not found"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓${NC} bots/.academicOps exists"
fi

if [ ! -d "$CLAUDE_DIR/agents" ] && [ ! -L "$CLAUDE_DIR/agents" ]; then
    echo -e "${RED}✗${NC} .claude/agents not found"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓${NC} .claude/agents exists"
fi

if [ ! -f "$SETTINGS_FILE" ]; then
    echo -e "${RED}✗${NC} .claude/settings.json not found"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓${NC} .claude/settings.json exists"
fi

# Test load_instructions.py
LOAD_SCRIPT="$BOTS_DIR/.academicOps/scripts/load_instructions.py"

if [ -f "$LOAD_SCRIPT" ]; then
    if python3 "$LOAD_SCRIPT" < /dev/null > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} load_instructions.py executes successfully"
    else
        echo -e "${YELLOW}⚠${NC}  load_instructions.py test had warnings (may be expected)"
    fi
else
    echo -e "${RED}✗${NC} load_instructions.py not found at $LOAD_SCRIPT"
    ERRORS=$((ERRORS + 1))
fi

# 11. Migration assistance (if old structure detected)
echo
echo "Checking for old installation structure..."

OLD_AGENTS_DIR="$PROJECT_ROOT/agents"
OLD_DOCS_BOTS="$PROJECT_ROOT/docs/bots"
MIGRATION_NEEDED=false

if [ -d "$OLD_AGENTS_DIR" ] && [ -f "$OLD_AGENTS_DIR/_CORE.md" ]; then
    echo -e "${YELLOW}⚠${NC}  Found old agents/_CORE.md"
    MIGRATION_NEEDED=true
fi

if [ -d "$OLD_DOCS_BOTS" ] && [ -f "$OLD_DOCS_BOTS/INSTRUCTIONS.md" ]; then
    echo -e "${YELLOW}⚠${NC}  Found old docs/bots/INSTRUCTIONS.md"
    MIGRATION_NEEDED=true
fi

if [ "$MIGRATION_NEEDED" = true ]; then
    echo
    echo -e "${BLUE}=== Migration Suggestions ===${NC}"
    echo "Detected old installation structure. To migrate:"
    echo ""
    
    if [ -f "$OLD_DOCS_BOTS/INSTRUCTIONS.md" ]; then
        echo "1. Review and merge content:"
        echo "   diff docs/bots/INSTRUCTIONS.md bots/docs/INSTRUCTIONS.md"
        echo "   # Then update bots/docs/INSTRUCTIONS.md with any missing content"
    fi
    
    if [ -f "$OLD_AGENTS_DIR/_CORE.md" ]; then
        echo "2. Move project-specific agent instructions:"
        echo "   mv agents/_CORE.md bots/docs/project-core.md  # If it contains project-specific content"
    fi
    
    echo ""
    echo "After migrating content, clean up:"
    echo "   rmdir agents  # If empty"
    echo "   rmdir docs/bots  # If empty"
    echo ""
fi

# 12. Success summary
echo
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}=== Installation Complete ===${NC}"
else
    echo -e "${YELLOW}=== Installation Complete with Warnings ===${NC}"
    echo -e "${YELLOW}$ERRORS error(s) detected. Please review above.${NC}"
fi

echo
echo "Created/verified:"
echo "  - bots/.academicOps/ (framework symlink)"
echo "  - bots/agents/ (repo-local agent customizations)"
echo "  - bots/commands/ (repo-local slash commands)"
echo "  - bots/docs/ (repo-local documentation)"
echo "  - bots/scripts/ (repo-local automation)"
echo "  - .claude/agents (symlink to framework)"
echo "  - .claude/commands (symlink to framework)"
echo "  - .claude/settings.json (hook configuration)"
echo "  - .gitignore (excludes framework symlink)"
echo

echo "Environment:"
echo "  - ACADEMICOPS_BOT=$ACADEMICOPS_BOT"
[ -n "${ACADEMICOPS_PERSONAL:-}" ] && echo "  - ACADEMICOPS_PERSONAL=$ACADEMICOPS_PERSONAL"
echo

if [ "$USE_SYMLINKS" = false ]; then
    echo -e "${YELLOW}NOTE: Running in copy mode (--no-symlink)${NC}"
    echo "  Updates to academicOps will NOT automatically sync to this project."
    echo "  Re-run this script to update after academicOps changes."
    echo
fi

echo "Next steps:"
echo "  1. Launch Claude Code from this directory"
echo "  2. Verify core instructions load at session start"
echo "  3. Test agent invocations (e.g., @agent-developer)"
echo "  4. Customize bots/docs/INSTRUCTIONS.md for your project"
echo ""
echo "Documentation:"
echo "  - Architecture: $ACADEMICOPS_BOT/docs/ARCHITECTURE.md"
echo "  - Customization: Create files in bots/agents/, bots/docs/, etc."
echo "  - Troubleshooting: Check GitHub issues at nicsuzor/academicOps"
echo
