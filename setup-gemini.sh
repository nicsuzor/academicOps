#!/usr/bin/env bash
#
# Setup script for Gemini CLI integration with aOps framework
#
# This script:
# 1. Creates symlinks in ~/.gemini/ pointing to framework
# 2. Converts commands from markdown to TOML
# 3. Merges hooks and MCP servers into settings.json
# 4. Validates the setup
#
# Usage:
#   ./setup-gemini.sh
#
# Prerequisites:
#   - AOPS and ACA_DATA environment variables set
#   - Gemini CLI installed
#   - jq installed (for JSON manipulation)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Gemini CLI Integration Setup"
echo "============================"
echo

# Determine paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AOPS_PATH="$SCRIPT_DIR"
GEMINI_DIR="$HOME/.gemini"

# Step 1: Validate prerequisites
echo "Step 1: Checking prerequisites"
echo "------------------------------"

# Check AOPS
if [ -z "${AOPS:-}" ]; then
    echo -e "${RED}ERROR: AOPS environment variable not set${NC}"
    echo "Run Claude Code setup.sh first, or set AOPS manually"
    exit 1
fi
echo -e "${GREEN}✓ AOPS=$AOPS${NC}"

# Check ACA_DATA
if [ -z "${ACA_DATA:-}" ]; then
    echo -e "${RED}ERROR: ACA_DATA environment variable not set${NC}"
    exit 1
fi
echo -e "${GREEN}✓ ACA_DATA=$ACA_DATA${NC}"

# Check jq
if ! command -v jq &> /dev/null; then
    echo -e "${RED}ERROR: jq not installed${NC}"
    echo "Install with: brew install jq (macOS) or apt install jq (Linux)"
    exit 1
fi
echo -e "${GREEN}✓ jq installed${NC}"

# Check gemini CLI
if ! command -v gemini &> /dev/null; then
    echo -e "${YELLOW}⚠ gemini CLI not found in PATH${NC}"
    echo "  Install from: https://github.com/google-gemini/gemini-cli"
fi

echo

# Step 2: Ensure ~/.gemini/ exists
echo "Step 2: Creating directory structure"
echo "------------------------------------"

mkdir -p "$GEMINI_DIR"
echo -e "${GREEN}✓ $GEMINI_DIR exists${NC}"
echo

# Step 3: Create/update symlinks
echo "Step 3: Creating symlinks"
echo "-------------------------"

create_symlink() {
    local name=$1
    local target=$2
    local link_path="$GEMINI_DIR/$name"

    if [ -L "$link_path" ]; then
        current_target="$(readlink "$link_path")"
        if [ "$current_target" = "$target" ]; then
            echo "  $name → $target (already correct)"
            return
        fi
        echo -e "${YELLOW}  Updating $name: $current_target → $target${NC}"
        rm "$link_path"
    elif [ -e "$link_path" ]; then
        echo -e "${YELLOW}  Removing existing $name (was file/dir)${NC}"
        rm -rf "$link_path"
    fi

    ln -s "$target" "$link_path"
    echo -e "${GREEN}  $name → $target${NC}"
}

# Create symlinks
create_symlink "hooks" "$AOPS_PATH/gemini/hooks"
create_symlink "commands" "$AOPS_PATH/gemini/commands"

# GEMINI.md symlink (project root)
if [ -L "$GEMINI_DIR/GEMINI.md" ]; then
    current_target="$(readlink "$GEMINI_DIR/GEMINI.md")"
    if [ "$current_target" != "$AOPS_PATH/GEMINI.md" ]; then
        rm "$GEMINI_DIR/GEMINI.md"
        ln -s "$AOPS_PATH/GEMINI.md" "$GEMINI_DIR/GEMINI.md"
        echo -e "${GREEN}  GEMINI.md → $AOPS_PATH/GEMINI.md${NC}"
    else
        echo "  GEMINI.md → $AOPS_PATH/GEMINI.md (already correct)"
    fi
elif [ -e "$GEMINI_DIR/GEMINI.md" ]; then
    # Check if it's empty or has minimal content
    if [ ! -s "$GEMINI_DIR/GEMINI.md" ]; then
        rm "$GEMINI_DIR/GEMINI.md"
        ln -s "$AOPS_PATH/GEMINI.md" "$GEMINI_DIR/GEMINI.md"
        echo -e "${GREEN}  GEMINI.md → $AOPS_PATH/GEMINI.md (replaced empty file)${NC}"
    else
        echo -e "${YELLOW}  GEMINI.md exists with content - skipping (manual merge needed)${NC}"
    fi
else
    ln -s "$AOPS_PATH/GEMINI.md" "$GEMINI_DIR/GEMINI.md"
    echo -e "${GREEN}  GEMINI.md → $AOPS_PATH/GEMINI.md${NC}"
fi

echo

# Step 4: Convert commands to TOML
echo "Step 4: Converting commands to TOML"
echo "------------------------------------"

python3 "$AOPS_PATH/scripts/convert_commands_to_toml.py"
echo

# Step 5: Merge settings
echo "Step 5: Merging settings"
echo "------------------------"

SETTINGS_FILE="$GEMINI_DIR/settings.json"
MERGE_FILE="$AOPS_PATH/gemini/config/settings-merge.json"

# Ensure settings.json exists
if [ ! -f "$SETTINGS_FILE" ]; then
    echo "{}" > "$SETTINGS_FILE"
    echo "  Created empty $SETTINGS_FILE"
fi

# Read merge template and expand $AOPS
MERGE_CONTENT=$(cat "$MERGE_FILE" | sed "s|\\\$AOPS|$AOPS_PATH|g")

# Merge hooks and mcpServers
# Strategy: deep merge hooks and mcpServers, preserve other settings
MERGED=$(jq -s '
    .[0] as $existing |
    .[1] as $new |
    $existing * {
        hooks: (($existing.hooks // {}) * ($new.hooks // {})),
        mcpServers: (($existing.mcpServers // {}) * ($new.mcpServers // {}))
    } | del(.["$comment"])
' "$SETTINGS_FILE" <(echo "$MERGE_CONTENT"))

# Write merged settings
echo "$MERGED" > "$SETTINGS_FILE"
echo -e "${GREEN}✓ Merged hooks and MCP servers into settings.json${NC}"

# Show what was added
echo "  Hooks configured:"
echo "$MERGED" | jq -r '.hooks | keys[]' | while read hook; do
    echo "    - $hook"
done

echo "  MCP servers configured:"
echo "$MERGED" | jq -r '.mcpServers | keys[]' | while read server; do
    echo "    - $server"
done

echo

# Step 6: Make hook router executable
echo "Step 6: Setting permissions"
echo "---------------------------"

chmod +x "$AOPS_PATH/gemini/hooks/router.py"
echo -e "${GREEN}✓ gemini/hooks/router.py is executable${NC}"
echo

# Step 7: Validation
echo "Step 7: Validation"
echo "------------------"

ERRORS=0

# Check symlinks
for link in hooks commands; do
    if [ -L "$GEMINI_DIR/$link" ]; then
        echo -e "${GREEN}✓ $link symlink OK${NC}"
    else
        echo -e "${RED}✗ $link symlink missing${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check GEMINI.md
if [ -L "$GEMINI_DIR/GEMINI.md" ] || [ -f "$GEMINI_DIR/GEMINI.md" ]; then
    echo -e "${GREEN}✓ GEMINI.md present${NC}"
else
    echo -e "${RED}✗ GEMINI.md missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check settings has hooks
if jq -e '.hooks' "$SETTINGS_FILE" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ settings.json has hooks${NC}"
else
    echo -e "${RED}✗ settings.json missing hooks${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check settings has mcpServers
if jq -e '.mcpServers' "$SETTINGS_FILE" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ settings.json has mcpServers${NC}"
else
    echo -e "${RED}✗ settings.json missing mcpServers${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check TOML commands exist
TOML_COUNT=$(ls -1 "$AOPS_PATH/gemini/commands/"*.toml 2>/dev/null | wc -l)
if [ "$TOML_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ $TOML_COUNT TOML commands generated${NC}"
else
    echo -e "${RED}✗ No TOML commands generated${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo

# Summary
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}Setup complete!${NC}"
    echo
    echo "To use Gemini CLI with aOps:"
    echo "  1. Run 'gemini' in your project directory"
    echo "  2. Framework context loads via GEMINI.md"
    echo "  3. Commands available as /command-name"
    echo
    echo "Known limitations (see gemini/README.md):"
    echo "  - No Task() subagent spawning"
    echo "  - No Skill() tool (use Read skills/X/SKILL.md)"
    echo "  - Commands /do, /meta run in degraded mode"
else
    echo -e "${RED}Setup completed with $ERRORS errors${NC}"
    echo "Please fix the errors above and re-run setup"
    exit 1
fi
