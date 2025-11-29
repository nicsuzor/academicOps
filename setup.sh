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

# Validate ACA_DATA is set
if [ -z "${ACA_DATA:-}" ]; then
    echo -e "${RED}ERROR: ACA_DATA environment variable not set${NC}"
    echo "Please set ACA_DATA to your data directory path and try again"
    echo "Example: export ACA_DATA=~/aca-data"
    exit 1
fi

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

# Step 2a: Create settings.local.json with machine-specific env vars
echo
echo "Creating settings.local.json for environment variables..."

LOCAL_SETTINGS="$CLAUDE_DIR/settings.local.json"

# Check if jq is available (required for safe JSON generation)
if ! command -v jq &> /dev/null; then
    echo -e "${RED}✗ jq not installed - required for settings.local.json${NC}"
    echo "  Install jq: sudo apt install jq"
    exit 1
fi

# Generate JSON content safely with jq
LOCAL_SETTINGS_CONTENT=$(jq -n --indent 2 \
    --arg aops "$AOPS_PATH" \
    --arg aca_data "$ACA_DATA_PATH" \
    '{ "env": { "AOPS": $aops, "ACA_DATA": $aca_data } }')

# Update or create settings.local.json
if [ -f "$LOCAL_SETTINGS" ]; then
    existing_aops=$(jq -r '.env.AOPS // ""' "$LOCAL_SETTINGS")
    if [ "$existing_aops" = "$AOPS_PATH" ]; then
        echo -e "${GREEN}✓ settings.local.json already correct${NC}"
    else
        echo "$LOCAL_SETTINGS_CONTENT" > "$LOCAL_SETTINGS"
        echo -e "${GREEN}✓ Updated settings.local.json${NC}"
    fi
else
    echo "$LOCAL_SETTINGS_CONTENT" > "$LOCAL_SETTINGS"
    echo -e "${GREEN}✓ Created settings.local.json${NC}"
fi

# Step 2b: Sync MCP servers to ~/.claude.json
# Note: Claude Code reads user-scoped MCP servers from ~/.claude.json mcpServers key,
# NOT from ~/.mcp.json. We merge our authoritative config into ~/.claude.json.
echo
echo "Syncing MCP servers to ~/.claude.json..."
mcp_source="$AOPS_PATH/config/claude/mcp.json"

if [ -f "$mcp_source" ] && command -v jq &> /dev/null; then
    if [ -f "$HOME/.claude.json" ]; then
        # Merge mcpServers from our config into ~/.claude.json
        jq -s '.[0] * {mcpServers: .[1].mcpServers}' "$HOME/.claude.json" "$mcp_source" > "$HOME/.claude.json.tmp" \
            && mv "$HOME/.claude.json.tmp" "$HOME/.claude.json"
        echo -e "${GREEN}✓ Synced MCP servers from $mcp_source to ~/.claude.json${NC}"
    else
        echo -e "${YELLOW}⚠ ~/.claude.json doesn't exist - will be created on first Claude Code run${NC}"
        echo "  Re-run this script after using Claude Code once"
    fi
elif [ ! -f "$mcp_source" ]; then
    echo -e "${YELLOW}⚠ MCP source not found: $mcp_source${NC}"
else
    echo -e "${RED}✗ jq not installed - cannot sync MCP servers${NC}"
    echo "  Install jq: sudo apt install jq"
fi

# Clean up legacy ~/.mcp.json symlink if it exists (no longer used)
if [ -L "$HOME/.mcp.json" ]; then
    rm "$HOME/.mcp.json"
    echo "  Removed legacy ~/.mcp.json symlink"
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

# Check settings.local.json
if [ -f "$CLAUDE_DIR/settings.local.json" ]; then
    echo -e "${GREEN}✓ settings.local.json exists${NC}"
    if command -v jq &> /dev/null; then
        local_aops=$(jq -r '.env.AOPS // ""' "$CLAUDE_DIR/settings.local.json" 2>/dev/null || echo "")
        if [ -n "$local_aops" ]; then
            echo "  AOPS=$local_aops"
        fi
    fi
else
    echo -e "${YELLOW}⚠ settings.local.json not found - Claude Code may not have AOPS set${NC}"
fi

# Check MCP servers in ~/.claude.json
if [ -f "$HOME/.claude.json" ] && command -v jq &> /dev/null; then
    mcp_count=$(jq '.mcpServers | length // 0' "$HOME/.claude.json")
    if [ "$mcp_count" -gt 0 ]; then
        echo -e "${GREEN}✓ MCP servers configured: $mcp_count servers in ~/.claude.json${NC}"
    else
        echo -e "${YELLOW}⚠ No MCP servers in ~/.claude.json${NC}"
    fi
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
