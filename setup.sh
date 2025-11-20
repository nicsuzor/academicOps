#!/usr/bin/env bash
#
# Setup script for aOps framework
#
# This script:
# 1. Sets environment variables in your shell RC file
# 2. Creates symlinks in ~/.claude/ pointing to framework
# 3. Validates the setup
#
# Usage:
#   ./setup.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "aOps Framework Setup"
echo "==================="
echo

# Determine paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AOPS_PATH="$SCRIPT_DIR"
ACA_DATA_PATH="${ACA_DATA}"
CLAUDE_DIR="$HOME/.claude"

echo "Framework paths:"
echo "  AOPS:     $AOPS_PATH"
echo "  ACA_DATA: $ACA_DATA_PATH"
echo

# Detect shell
SHELL_NAME="$(basename "$SHELL")"
case "$SHELL_NAME" in
    bash)
        RC_FILE="$HOME/.bashrc"
        ;;
    zsh)
        RC_FILE="$HOME/.zshrc"
        ;;
    *)
        echo -e "${YELLOW}Warning: Unknown shell '$SHELL_NAME'. Defaulting to ~/.bashrc${NC}"
        RC_FILE="$HOME/.bashrc"
        ;;
esac

echo "Detected shell: $SHELL_NAME"
echo "RC file: $RC_FILE"
echo

# Step 1: Add environment variables to RC file
echo "Step 1: Setting environment variables"
echo "-------------------------------------"

ENV_BLOCK="# aOps Framework Environment Variables
export AOPS=\"$AOPS_PATH\"
export ACA_DATA=\"$ACA_DATA_PATH\""

if grep -q "export AOPS=" "$RC_FILE" 2>/dev/null; then
    echo -e "${YELLOW}Environment variables already set in $RC_FILE${NC}"
    echo "Current values:"
    grep "AOPS\|ACA_DATA" "$RC_FILE" || true
else
    echo "$ENV_BLOCK" >> "$RC_FILE"
    echo -e "${GREEN}✓ Added environment variables to $RC_FILE${NC}"
fi

# Export for current session
export AOPS="$AOPS_PATH"
export ACA_DATA="$ACA_DATA_PATH"

echo

# Step 2: Create symlinks in ~/.claude/
echo "Step 2: Creating symlinks"
echo "-------------------------"

mkdir -p "$CLAUDE_DIR"

# Function to create or update symlink
create_symlink() {
    local name=$1
    local target=$2
    local link_path="$CLAUDE_DIR/$name"

    if [ -L "$link_path" ]; then
        # Exists as symlink
        current_target="$(readlink "$link_path")"
        if [ "$current_target" = "$target" ]; then
            echo "  $name → $target (already correct)"
        else
            echo -e "${YELLOW}  Updating $name symlink${NC}"
            echo "    Old: $current_target"
            echo "    New: $target"
            ln -sf "$target" "$link_path"
        fi
    elif [ -e "$link_path" ]; then
        # Exists but not a symlink
        echo -e "${RED}✗ $link_path exists but is not a symlink${NC}"
        echo "  Please backup and remove it manually, then re-run this script"
        return 1
    else
        # Doesn't exist
        ln -s "$target" "$link_path"
        echo -e "${GREEN}✓ Created $name → $target${NC}"
    fi
}

create_symlink "skills" "$AOPS_PATH/skills"
create_symlink "commands" "$AOPS_PATH/commands"
create_symlink "agents" "$AOPS_PATH/agents"
create_symlink "settings.json" "$AOPS_PATH/config/claude/settings.json"

# Create symlink for MCP configuration in home directory
echo
echo "Creating MCP configuration symlink..."
mcp_link="$HOME/.mcp.json"
mcp_target="$AOPS_PATH/config/claude/mcp.json"

if [ -L "$mcp_link" ]; then
    # Exists as symlink
    current_target="$(readlink "$mcp_link")"
    if [ "$current_target" = "$mcp_target" ]; then
        echo "  .mcp.json → $mcp_target (already correct)"
    else
        echo -e "${YELLOW}  Updating .mcp.json symlink${NC}"
        echo "    Old: $current_target"
        echo "    New: $mcp_target"
        ln -sf "$mcp_target" "$mcp_link"
    fi
elif [ -e "$mcp_link" ]; then
    # Exists but not a symlink
    echo -e "${YELLOW}⚠ $mcp_link exists but is not a symlink${NC}"
    echo "  Backing up to $mcp_link.backup"
    mv "$mcp_link" "$mcp_link.backup"
    ln -s "$mcp_target" "$mcp_link"
    echo -e "${GREEN}✓ Created .mcp.json → $mcp_target${NC}"
    echo -e "${GREEN}✓ Previous file backed up to ~/.mcp.json.backup${NC}"
else
    # Doesn't exist
    ln -s "$mcp_target" "$mcp_link"
    echo -e "${GREEN}✓ Created .mcp.json → $mcp_target${NC}"
fi

echo

# Step 3: Validate setup
echo "Step 3: Validating setup"
echo "------------------------"

VALIDATION_PASSED=true

# Check environment variables
if [ -z "${AOPS:-}" ]; then
    echo -e "${RED}✗ AOPS environment variable not set${NC}"
    VALIDATION_PASSED=false
else
    echo -e "${GREEN}✓ AOPS=$AOPS${NC}"
fi

if [ -z "${ACA_DATA:-}" ]; then
    echo -e "${RED}✗ ACA_DATA environment variable not set${NC}"
    VALIDATION_PASSED=false
else
    echo -e "${GREEN}✓ ACA_DATA=$ACA_DATA${NC}"
fi

# Check directories exist
if [ ! -d "$AOPS_PATH" ]; then
    echo -e "${RED}✗ AOPS directory doesn't exist: $AOPS_PATH${NC}"
    VALIDATION_PASSED=false
fi

if [ ! -d "$ACA_DATA_PATH" ]; then
    echo -e "${RED}✗ ACA_DATA directory doesn't exist: $ACA_DATA_PATH${NC}"
    VALIDATION_PASSED=false
fi

# Check symlinks
for link in skills commands agents settings.json; do
    if [ ! -L "$CLAUDE_DIR/$link" ]; then
        echo -e "${RED}✗ Symlink missing: $CLAUDE_DIR/$link${NC}"
        VALIDATION_PASSED=false
    fi
done

# Check MCP symlink
if [ ! -L "$HOME/.mcp.json" ]; then
    echo -e "${RED}✗ Symlink missing: $HOME/.mcp.json${NC}"
    VALIDATION_PASSED=false
fi

# Test Python path resolution
echo
echo "Testing Python path resolution..."
if python3 -c "from lib.paths import validate_environment; validate_environment()" 2>/dev/null; then
    echo -e "${GREEN}✓ Python path resolution working${NC}"
else
    echo -e "${YELLOW}⚠ Python path resolution test failed (env vars may not be loaded yet)${NC}"
    echo "  Run 'source $RC_FILE' and try again"
fi

echo
if [ "$VALIDATION_PASSED" = true ]; then
    echo -e "${GREEN}✓ Setup completed successfully!${NC}"
    echo
    echo "Next steps:"
    echo "  1. Reload your shell: source $RC_FILE"
    echo "  2. Verify: python3 -c 'from lib.paths import validate_environment; validate_environment()'"
    echo "  3. Test from any directory: cd /tmp && uv run python \$AOPS/skills/tasks/scripts/task_view.py"
    echo
    exit 0
else
    echo -e "${RED}✗ Setup validation failed${NC}"
    echo "Please fix the errors above and re-run this script"
    exit 1
fi
