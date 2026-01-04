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

# Detect container runtime (docker, podman, orbstack all provide 'docker' CLI)
detect_container_runtime() {
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        echo "docker"
    elif command -v podman &> /dev/null; then
        echo "podman"
    else
        echo ""
    fi
}

CONTAINER_RUNTIME=$(detect_container_runtime)

echo "Framework paths:"
echo "  AOPS:     $AOPS_PATH"
echo "  ACA_DATA: $ACA_DATA_PATH"
if [ -n "$CONTAINER_RUNTIME" ]; then
    echo -e "  Container: ${GREEN}$CONTAINER_RUNTIME${NC}"
else
    echo -e "  Container: ${YELLOW}none detected${NC}"
fi
echo

# Step 1: Verify environment variables
echo "Step 1: Checking environment variables"
echo "--------------------------------------"

if [ -z "${AOPS:-}" ] || [ -z "${ACA_DATA:-}" ]; then
    echo -e "${RED}✗ Required environment variables not set${NC}"
    echo
    echo "Add to your shell RC file (~/.zshrc or ~/.bashrc):"
    echo "  export AOPS=\"$AOPS_PATH\""
    echo "  export ACA_DATA=\"/path/to/your/data\""
    echo
    echo "Then: source ~/.zshrc && ./setup.sh"
    exit 1
fi

echo -e "${GREEN}✓ AOPS=$AOPS${NC}"
echo -e "${GREEN}✓ ACA_DATA=$ACA_DATA${NC}"
echo

# Step 2: Create symlinks in ~/.claude/
echo "Step 2: Creating symlinks"
echo "-------------------------"

mkdir -p "$CLAUDE_DIR"

# Function to create or update symlink (force overwrite - no backups per AXIOMS #15)
create_symlink() {
    local name=$1
    local target=$2
    local link_path="$CLAUDE_DIR/$name"

    if [ -L "$link_path" ]; then
        current_target="$(readlink "$link_path")"
        if [ "$current_target" = "$target" ]; then
            echo "  $name → $target (already correct)"
            return
        fi
        echo -e "${YELLOW}  Updating $name: $current_target → $target${NC}"
    elif [ -e "$link_path" ]; then
        echo -e "${YELLOW}  Replacing $name (was not a symlink)${NC}"
    fi

    # Force overwrite whatever exists (git is the backup system)
    rm -rf "$link_path"
    ln -s "$target" "$link_path"
    echo -e "${GREEN}✓ $name → $target${NC}"
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

# Step 2b: Build and sync MCP servers to ~/.claude.json
# Note: Claude Code reads user-scoped MCP servers from ~/.claude.json mcpServers key,
# NOT from ~/.mcp.json. We merge our authoritative config into ~/.claude.json.
echo
echo "Building MCP configuration..."

# Detect platform for outlook config selection
detect_outlook_mode() {
    # Allow env override
    if [ -n "${MCP_OUTLOOK_MODE:-}" ]; then
        echo "$MCP_OUTLOOK_MODE"
        return
    fi

    case "$(uname -s)" in
        Darwin)
            echo "macos"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "windows"
            ;;
        Linux)
            # Linux uses proxy (could be dev3 server or WSL client)
            echo "proxy"
            ;;
        *)
            echo "proxy"
            ;;
    esac
}

OUTLOOK_MODE=$(detect_outlook_mode)
echo "  Platform outlook mode: $OUTLOOK_MODE"

# Merge base config with outlook fragment
mcp_base="$AOPS_PATH/config/claude/mcp-base.json"
mcp_outlook="$AOPS_PATH/config/claude/mcp-outlook-${OUTLOOK_MODE}.json"
mcp_source="$AOPS_PATH/config/claude/mcp.json"

if [ -f "$mcp_base" ] && [ -f "$mcp_outlook" ] && command -v jq &> /dev/null; then
    # Deep merge: base + outlook fragment
    jq -s '.[0] * .[1]' "$mcp_base" "$mcp_outlook" > "$mcp_source"
    echo -e "${GREEN}✓ Built mcp.json from base + outlook-${OUTLOOK_MODE}${NC}"
elif [ ! -f "$mcp_base" ]; then
    echo -e "${RED}✗ Missing $mcp_base${NC}"
    exit 1
elif [ ! -f "$mcp_outlook" ]; then
    echo -e "${RED}✗ Missing $mcp_outlook${NC}"
    exit 1
fi

echo "Syncing MCP servers to ~/.claude.json..."

if [ -f "$mcp_source" ] && command -v jq &> /dev/null; then
    if [ -f "$HOME/.claude.json" ]; then
        # Read MCP config, patch container runtime, expand $HOME
        if [ -n "$CONTAINER_RUNTIME" ]; then
            mcp_patched=$(jq --arg runtime "$CONTAINER_RUNTIME" --arg home "$HOME" '
                .mcpServers | to_entries | map(
                    if .value.command == "podman" or .value.command == "docker" then
                        .value.command = $runtime
                    else . end
                    | .value.args = (.value.args // [] | map(gsub("\\$HOME"; $home)))
                ) | from_entries | {mcpServers: .}
            ' "$mcp_source")
            echo "  Using container runtime: $CONTAINER_RUNTIME"
        else
            # No container runtime - filter out container-based servers entirely
            mcp_patched=$(jq --arg home "$HOME" '
                .mcpServers | to_entries
                | map(select(.value.command != "podman" and .value.command != "docker"))
                | map(.value.args = (.value.args // [] | map(gsub("\\$HOME"; $home))))
                | from_entries | {mcpServers: .}
            ' "$mcp_source")
            echo -e "${YELLOW}  No container runtime - excluding container-based MCP servers (zot, osb)${NC}"
        fi
        # Replace mcpServers in ~/.claude.json (authoritative source wins, stale servers removed)
        echo "$mcp_patched" | jq -s '.[0] + .[1]' "$HOME/.claude.json" - > "$HOME/.claude.json.tmp" \
            && mv "$HOME/.claude.json.tmp" "$HOME/.claude.json"
        echo -e "${GREEN}✓ Synced MCP servers to ~/.claude.json${NC}"

        # Clean up stale project-specific MCP servers (remove servers not in authoritative source)
        valid_servers=$(jq -r '.mcpServers | keys | @json' "$mcp_source")
        jq --argjson valid "$valid_servers" '
            .projects |= (to_entries | map(
                .value.mcpServers |= (if . then with_entries(select(.key | IN($valid[]))) else . end)
            ) | from_entries)
        ' "$HOME/.claude.json" > "$HOME/.claude.json.tmp" && mv "$HOME/.claude.json.tmp" "$HOME/.claude.json"
        echo "  Cleaned up stale project-specific MCP servers"
    else
        echo -e "${YELLOW}⚠ ~/.claude.json doesn't exist - will be created on first Claude Code run${NC}"
        echo "  Re-run this script after using Claude Code once"
    fi
elif [ ! -f "$mcp_source" ]; then
    echo -e "${YELLOW}⚠ MCP source not found: $mcp_source${NC}"
else
    echo -e "${RED}✗ jq not installed - cannot sync MCP servers${NC}"
    echo "  Install jq: brew install jq"
fi

# Clean up legacy ~/.mcp.json symlink if it exists (no longer used)
if [ -L "$HOME/.mcp.json" ]; then
    rm "$HOME/.mcp.json"
    echo "  Removed legacy ~/.mcp.json symlink"
fi

# Step 2c: Configure Claude Desktop
echo
echo "Configuring Claude Desktop..."

# Detect Claude Desktop config location (cross-platform)
case "$(uname -s)" in
    Darwin)
        CLAUDE_DESKTOP_DIR="$HOME/Library/Application Support/Claude"
        ;;
    Linux)
        CLAUDE_DESKTOP_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/Claude"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        CLAUDE_DESKTOP_DIR="$APPDATA/Claude"
        ;;
    *)
        CLAUDE_DESKTOP_DIR=""
        ;;
esac

if [ -n "$CLAUDE_DESKTOP_DIR" ] && [ -d "$CLAUDE_DESKTOP_DIR" ] && command -v jq &> /dev/null; then
    CLAUDE_DESKTOP_CONFIG="$CLAUDE_DESKTOP_DIR/claude_desktop_config.json"

    # Remove existing config (symlink or file)
    [ -e "$CLAUDE_DESKTOP_CONFIG" ] && rm -f "$CLAUDE_DESKTOP_CONFIG"

    # Find uvx path
    UVX_PATH=$(command -v uvx 2>/dev/null || echo "uvx")

    # Build PATH for GUI apps (they don't inherit shell PATH)
    GUI_PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

    # Generate config: filter http servers and container servers (if no runtime), expand $HOME/$AOPS
    if [ -n "$CONTAINER_RUNTIME" ]; then
        jq --arg uvx "$UVX_PATH" --arg path "$GUI_PATH" --arg runtime "$CONTAINER_RUNTIME" \
           --arg home "$HOME" --arg aops "$AOPS" --arg aca_data "$ACA_DATA" '
            .mcpServers | to_entries
            | map(select(.value.type != "http"))  # Filter out http transport (not supported)
            | map(
                if .value.command == "uvx" then
                    .value.command = $uvx |
                    .value.env = (.value.env // {}) + {"PATH": $path}
                elif .value.command == "podman" or .value.command == "docker" then
                    .value.command = $runtime
                else . end
                | .value.args = (.value.args // [] | map(gsub("\\$HOME"; $home) | gsub("\\$AOPS"; $aops)))
                | .value.env = ((.value.env // {}) + {"AOPS": $aops, "ACA_DATA": $aca_data})
            ) | from_entries | {mcpServers: .}
        ' "$mcp_source" > "$CLAUDE_DESKTOP_CONFIG"
    else
        # No container runtime - exclude container-based servers
        jq --arg uvx "$UVX_PATH" --arg path "$GUI_PATH" \
           --arg home "$HOME" --arg aops "$AOPS" --arg aca_data "$ACA_DATA" '
            .mcpServers | to_entries
            | map(select(.value.type != "http"))  # Filter out http transport (not supported)
            | map(select(.value.command != "podman" and .value.command != "docker"))  # No container runtime
            | map(
                if .value.command == "uvx" then
                    .value.command = $uvx |
                    .value.env = (.value.env // {}) + {"PATH": $path}
                else . end
                | .value.args = (.value.args // [] | map(gsub("\\$HOME"; $home) | gsub("\\$AOPS"; $aops)))
                | .value.env = ((.value.env // {}) + {"AOPS": $aops, "ACA_DATA": $aca_data})
            ) | from_entries | {mcpServers: .}
        ' "$mcp_source" > "$CLAUDE_DESKTOP_CONFIG"
    fi

    echo -e "${GREEN}✓ Created $CLAUDE_DESKTOP_CONFIG${NC}"
    echo "  uvx path: $UVX_PATH"
elif [ -z "$CLAUDE_DESKTOP_DIR" ]; then
    echo -e "${YELLOW}⚠ Unknown platform - skipping Claude Desktop config${NC}"
elif [ ! -d "$CLAUDE_DESKTOP_DIR" ]; then
    echo -e "${YELLOW}⚠ Claude Desktop not installed - skipping${NC}"
else
    echo -e "${YELLOW}⚠ jq not installed - cannot configure Claude Desktop${NC}"
fi

echo

# Step 2d: Create repo-local .claude/ for remote coding (using sync_web_bundle.py)
echo "Setting up repository .claude/ (for remote coding)..."

if python3 "$AOPS_PATH/scripts/sync_web_bundle.py" --self > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Repository .claude/ configured via sync_web_bundle.py --self${NC}"
else
    echo -e "${YELLOW}⚠ sync_web_bundle.py failed - creating symlinks manually${NC}"
    REPO_CLAUDE="$AOPS_PATH/.claude"
    mkdir -p "$REPO_CLAUDE"
    for item in settings.json:../config/claude/settings.json agents:../agents skills:../skills commands:../commands CLAUDE.md:../CLAUDE.md; do
        name="${item%%:*}"
        target="${item#*:}"
        [ -e "$REPO_CLAUDE/$name" ] && rm -rf "$REPO_CLAUDE/$name"
        ln -s "$target" "$REPO_CLAUDE/$name"
    done
    echo -e "${GREEN}✓ Repository .claude/ configured (manual fallback)${NC}"
fi

# Step 2e: Configure memory server default project
echo
echo "Configuring memory server..."

MEMORY_CONFIG="$HOME/.memory/config.json"

if command -v uvx &> /dev/null; then
    # Check if 'main' project already configured in config.json (fast, no subprocess)
    if [ -f "$MEMORY_CONFIG" ] && command -v jq &> /dev/null; then
        existing_main=$(jq -r '.projects.main // ""' "$MEMORY_CONFIG" 2>/dev/null || echo "")
        existing_default=$(jq -r '.default_project // ""' "$MEMORY_CONFIG" 2>/dev/null || echo "")
        if [ -n "$existing_main" ] && [ "$existing_default" = "main" ]; then
            echo -e "${GREEN}✓ memory server project 'main' already configured at: $existing_main${NC}"
        elif [ -n "$existing_main" ]; then
            echo "  Project 'main' exists but is not default"
            # Set as default via config.json directly (no subprocess)
            jq '.default_project = "main" | .default_project_mode = true' "$MEMORY_CONFIG" > "$MEMORY_CONFIG.tmp" \
                && mv "$MEMORY_CONFIG.tmp" "$MEMORY_CONFIG" \
                && echo -e "${GREEN}✓ memory server default project set to 'main'${NC}" \
                || echo -e "${YELLOW}⚠ Could not update memory server config${NC}"
        else
            # Project doesn't exist - add it via jq (no subprocess)
            jq --arg path "$ACA_DATA_PATH" '.projects.main = $path | .default_project = "main" | .default_project_mode = true' "$MEMORY_CONFIG" > "$MEMORY_CONFIG.tmp" \
                && mv "$MEMORY_CONFIG.tmp" "$MEMORY_CONFIG" \
                && echo -e "${GREEN}✓ memory server project 'main' added at $ACA_DATA_PATH${NC}" \
                || echo -e "${YELLOW}⚠ Could not update memory server config${NC}"
        fi
    elif [ -f "$MEMORY_CONFIG" ]; then
        echo -e "${YELLOW}⚠ jq not installed - cannot configure memory server${NC}"
        echo "  Install jq: brew install jq"
    else
        # No config.json exists - create it
        mkdir -p "$HOME/.memory"
        cat > "$MEMORY_CONFIG" << EOF
{
  "projects": {
    "main": "$ACA_DATA_PATH"
  },
  "default_project": "main",
  "default_project_mode": true
}
EOF
        echo -e "${GREEN}✓ memory server config created with project 'main' at $ACA_DATA_PATH${NC}"
    fi
else
    echo -e "${YELLOW}⚠ uvx not found, skipping memory server configuration${NC}"
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
if PYTHONPATH="$AOPS" python3 -c "from lib.paths import validate_environment; validate_environment()" 2>/dev/null; then
    echo -e "${GREEN}✓ Python path resolution working${NC}"
else
    echo -e "${YELLOW}⚠ Python path resolution test failed${NC}"
fi

echo
if [ "$VALIDATION_PASSED" = true ]; then
    echo -e "${GREEN}✓ Setup completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}✗ Setup validation failed${NC}"
    echo "Please fix the errors above and re-run this script"
    exit 1
fi
