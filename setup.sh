#!/usr/bin/env bash
#
# Setup script for aOps framework (Claude Code + Gemini CLI)
#
# This script:
# 1. Creates symlinks in ~/.claude/ pointing to framework
# 2. Configures MCP servers for Claude Code and Claude Desktop
# 3. Sets up Gemini CLI (if installed) with hooks and commands
# 4. Validates the setup
#
# Prerequisites:
#   - AOPS and ACA_DATA environment variables set
#   - jq installed
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

create_symlink "settings.json" "$AOPS_PATH/config/claude/settings.json"
create_symlink "CLAUDE.md" "$AOPS_PATH/CLAUDE.md"

# Create plugins directory and symlink all aops plugins
# Note: skills, commands, agents, hooks now live in plugins (not top-level)
mkdir -p "$CLAUDE_DIR/plugins"

# Auto-discover and link all aops-* plugins
for plugin_dir in "$AOPS_PATH"/aops-*; do
    if [ -d "$plugin_dir" ] && [ -f "$plugin_dir/.claude-plugin/plugin.json" ]; then
        plugin_name=$(basename "$plugin_dir")
        create_symlink "plugins/$plugin_name" "$plugin_dir"
    fi
done

# Clean up legacy symlinks (content moved to aops-core plugin)
for legacy in skills commands agents hooks; do
    if [ -L "$CLAUDE_DIR/$legacy" ]; then
        rm "$CLAUDE_DIR/$legacy"
        echo -e "${YELLOW}  Removed legacy symlink: $legacy${NC}"
    fi
done

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
mcp_base="$AOPS_PATH/aops-tools/config/claude/mcp-base.json"
mcp_outlook="$AOPS_PATH/aops-tools/config/claude/mcp-outlook-${OUTLOOK_MODE}.json"
mcp_source="$AOPS_PATH/aops-tools/config/claude/mcp.json"

# Check for MCP tokens (required for gh and memory servers)
if [ -z "${GH_MCP_TOKEN:-}" ]; then
    echo -e "${YELLOW}⚠ GH_MCP_TOKEN not set - GitHub MCP server will not authenticate${NC}"
    echo "  Set in shell RC: export GH_MCP_TOKEN='your-github-token'"
fi
if [ -z "${MCP_MEMORY_API_KEY:-}" ]; then
    echo -e "${YELLOW}⚠ MCP_MEMORY_API_KEY not set - Memory MCP server will not authenticate${NC}"
    echo "  Set in shell RC: export MCP_MEMORY_API_KEY='your-memory-token'"
fi

if [ -f "$mcp_base" ] && [ -f "$mcp_outlook" ] && command -v jq &> /dev/null; then
    # Deep merge: base + outlook fragment, then substitute env vars for tokens
    jq -s '.[0] * .[1]' "$mcp_base" "$mcp_outlook" | \
        sed -e "s|\${GH_MCP_TOKEN}|${GH_MCP_TOKEN:-}|g" \
            -e "s|\${MCP_MEMORY_API_KEY}|${MCP_MEMORY_API_KEY:-}|g" \
        > "$mcp_source"
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

        # Remove plugin-specific MCPs from global config (they're now in plugin .mcp.json files)
        # Build list of MCPs that are in plugin templates
        plugin_mcps=()
        for plugin_name in aops-core aops-tools; do
            template_file="$AOPS_PATH/$plugin_name/.mcp.json.template"
            if [ -f "$template_file" ]; then
                # Extract MCP server names from template
                while IFS= read -r mcp_name; do
                    plugin_mcps+=("$mcp_name")
                done < <(jq -r '.mcpServers | keys[]' "$template_file" 2>/dev/null)
            fi
        done

        # Remove plugin MCPs from global ~/.claude.json
        if [ ${#plugin_mcps[@]} -gt 0 ]; then
            plugin_mcps_json=$(printf '%s\n' "${plugin_mcps[@]}" | jq -R . | jq -s .)
            jq --argjson remove "$plugin_mcps_json" '
                .mcpServers |= (with_entries(select(.key | IN($remove[]) | not)))
            ' "$HOME/.claude.json" > "$HOME/.claude.json.tmp" && mv "$HOME/.claude.json.tmp" "$HOME/.claude.json"
            echo "  Removed ${#plugin_mcps[@]} plugin-specific MCPs from global config"
        fi
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
    mkdir -p "$REPO_CLAUDE" "$REPO_CLAUDE/plugins"

    # Link settings.json and CLAUDE.md
    ln -sf ../config/claude/settings.json "$REPO_CLAUDE/settings.json"
    ln -sf ../CLAUDE.md "$REPO_CLAUDE/CLAUDE.md"

    # Auto-discover and link all aops-* plugins
    for plugin_dir in "$AOPS_PATH"/aops-*; do
        if [ -d "$plugin_dir" ] && [ -f "$plugin_dir/.claude-plugin/plugin.json" ]; then
            plugin_name=$(basename "$plugin_dir")
            ln -sf "../../$plugin_name" "$REPO_CLAUDE/plugins/$plugin_name"
        fi
    done

    echo -e "${GREEN}✓ Repository .claude/ configured (manual fallback)${NC}"
fi

# Step 2d-1: Generate plugin-specific MCP configs from templates
echo
echo "Generating plugin-specific MCP configs..."

# List of plugins with MCP templates
for plugin_name in aops-core aops-tools; do
    plugin_dir="$AOPS_PATH/$plugin_name"
    template_file="$plugin_dir/.mcp.json.template"
    output_file="$plugin_dir/.mcp.json"

    if [ -f "$template_file" ]; then
        # Substitute environment variables in template
        sed -e "s|\${CONTEXT7_API_KEY}|${CONTEXT7_API_KEY:-}|g" \
            -e "s|\${MCP_MEMORY_API_KEY}|${MCP_MEMORY_API_KEY:-}|g" \
            -e "s|\${GH_MCP_TOKEN}|${GH_MCP_TOKEN:-}|g" \
            "$template_file" > "$output_file"
        echo -e "${GREEN}✓ Generated $plugin_name/.mcp.json from template${NC}"
    else
        echo -e "${YELLOW}⚠ No template found: $template_file${NC}"
    fi
done

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

# Step 3: Gemini CLI setup
echo "Step 3: Gemini CLI setup"
echo "------------------------"

GEMINI_DIR="$HOME/.gemini"
ANTIGRAVITY_DIR="$GEMINI_DIR/antigravity"
GLOBAL_WORKFLOWS_DIR="$ANTIGRAVITY_DIR/global_workflows"

# Check if gemini CLI is installed
if ! command -v gemini &> /dev/null; then
    echo -e "${YELLOW}⚠ gemini CLI not found - skipping Gemini setup${NC}"
    echo "  Install from: https://github.com/google-gemini/gemini-cli"
    GEMINI_SKIPPED=true
else
    GEMINI_SKIPPED=false
    echo -e "${GREEN}✓ gemini CLI found${NC}"

    # Create ~/.gemini/ directory
    mkdir -p "$GEMINI_DIR"

    # Create symlinks for Gemini
    gemini_create_symlink() {
        local name=$1
        local target=$2
        local link_path="$GEMINI_DIR/$name"

        if [ -L "$link_path" ]; then
            current_target="$(readlink "$link_path")"
            if [ "$current_target" = "$target" ]; then
                echo "  $name → $target (already correct)"
                return
            fi
            rm "$link_path"
        elif [ -e "$link_path" ]; then
            rm -rf "$link_path"
        fi

        ln -s "$target" "$link_path"
        echo -e "${GREEN}  $name → $target${NC}"
    }

    # Only create symlinks for directories that exist
    [ -d "$AOPS_PATH/config/gemini/hooks" ] && gemini_create_symlink "hooks" "$AOPS_PATH/config/gemini/hooks"
    [ -d "$AOPS_PATH/config/gemini/commands" ] && gemini_create_symlink "commands" "$AOPS_PATH/config/gemini/commands"

    # GEMINI.md generation (injects actual paths)
    if [ -L "$GEMINI_DIR/GEMINI.md" ] || [ -f "$GEMINI_DIR/GEMINI.md" ]; then
        rm "$GEMINI_DIR/GEMINI.md"
    fi

    # Read source and inject paths
    sed -e "s|~/src/academicOps|$AOPS_PATH|g" \
        -e "s|~/writing/data|$ACA_DATA_PATH|g" \
        "$AOPS_PATH/GEMINI.md" > "$GEMINI_DIR/GEMINI.md"

    echo -e "${GREEN}  Generated ~/.gemini/GEMINI.md with paths injected${NC}"

    # Also update the Antigravity global workflow link to point to this generated file
    # so Antigravity agents also see the correct paths
    GLOBAL_GEMINI_MD="$GLOBAL_WORKFLOWS_DIR/GEMINI.md"
    if [ -L "$GLOBAL_GEMINI_MD" ]; then
        rm "$GLOBAL_GEMINI_MD"
        ln -s "$GEMINI_DIR/GEMINI.md" "$GLOBAL_GEMINI_MD"
        echo -e "${GREEN}  Updated Antigravity GEMINI.md link to use generated file${NC}"
    elif [ ! -e "$GLOBAL_GEMINI_MD" ]; then
         ln -s "$GEMINI_DIR/GEMINI.md" "$GLOBAL_GEMINI_MD"
         echo -e "${GREEN}  Linked Antigravity GEMINI.md to generated file${NC}"
    fi

    # Convert commands to TOML
    echo
    echo "Converting commands to TOML..."
    if python3 "$AOPS_PATH/scripts/convert_commands_to_toml.py" 2>/dev/null; then
        TOML_COUNT=$(ls -1 "$AOPS_PATH/config/gemini/commands/"*.toml 2>/dev/null | wc -l)
        echo -e "${GREEN}✓ Converted $TOML_COUNT commands to TOML${NC}"
    else
        echo -e "${YELLOW}⚠ Command conversion failed - Gemini commands may not work${NC}"
    fi

    # Convert MCP servers from Claude format to Gemini format
    # This aggregates plugin MCPs + global mcp.json into Gemini format
    echo
    echo "Converting MCP servers for Gemini..."
    MCP_SOURCE="$AOPS_PATH/aops-tools/config/claude/mcp.json"
    MCP_CONVERTED="$AOPS_PATH/config/gemini/mcp-servers.json"
    mkdir -p "$AOPS_PATH/config/gemini"

    if AOPS="$AOPS_PATH" python3 "$AOPS_PATH/scripts/convert_mcp_to_gemini.py" "$MCP_SOURCE" "$MCP_CONVERTED" 2>&1; then
        MCP_COUNT=$(jq '.mcpServers | keys | length' "$MCP_CONVERTED" 2>/dev/null || echo "0")
        echo -e "${GREEN}✓ Converted $MCP_COUNT MCP servers to Gemini format${NC}"
    else
        echo -e "${YELLOW}⚠ MCP conversion failed - check script output above${NC}"
    fi

    # Merge settings
    echo
    echo "Merging Gemini settings..."
    GEMINI_SETTINGS="$GEMINI_DIR/settings.json"
    MERGE_FILE="$AOPS_PATH/config/gemini/config/settings-merge.json"

    if [ ! -f "$GEMINI_SETTINGS" ]; then
        echo "{}" > "$GEMINI_SETTINGS"
    fi

    if [ -f "$MERGE_FILE" ]; then
        MERGE_CONTENT=$(cat "$MERGE_FILE" | sed "s|\\\$AOPS|$AOPS_PATH|g")

        # Also merge converted MCP servers if available
        if [ -f "$MCP_CONVERTED" ]; then
            MCP_CONTENT=$(cat "$MCP_CONVERTED")
            MERGED=$(jq -s '
                .[0] as $existing |
                .[1] as $new |
                .[2] as $mcp |
                $existing * {
                    hooks: (($existing.hooks // {}) * ($new.hooks // {})),
                    mcpServers: (($existing.mcpServers // {}) * ($new.mcpServers // {}) * ($mcp.mcpServers // {}))
                } | del(.["$comment"])
            ' "$GEMINI_SETTINGS" <(echo "$MERGE_CONTENT") <(echo "$MCP_CONTENT"))
        else
            MERGED=$(jq -s '
                .[0] as $existing |
                .[1] as $new |
                $existing * {
                    hooks: (($existing.hooks // {}) * ($new.hooks // {})),
                    mcpServers: (($existing.mcpServers // {}) * ($new.mcpServers // {}))
                } | del(.["$comment"])
            ' "$GEMINI_SETTINGS" <(echo "$MERGE_CONTENT"))
        fi
        echo "$MERGED" > "$GEMINI_SETTINGS"
        echo -e "${GREEN}✓ Merged hooks and MCP servers into Gemini settings.json${NC}"
    fi

    # Set permissions
    chmod +x "$AOPS_PATH/config/gemini/hooks/router.py" 2>/dev/null || true
fi

echo

# Step 3a: Antigravity setup
echo "Step 3a: Antigravity setup"
echo "------------------------"

ANTIGRAVITY_DIR="$GEMINI_DIR/antigravity"
GLOBAL_WORKFLOWS_DIR="$ANTIGRAVITY_DIR/global_workflows"

# Create directories
mkdir -p "$GLOBAL_WORKFLOWS_DIR"

# Generate Antigravity mcp_config.json from converted MCPs
# Antigravity uses 'serverUrl' for HTTP servers instead of 'url'
ANTIGRAVITY_MCP_CONFIG="$ANTIGRAVITY_DIR/mcp_config.json"
if [ -f "$MCP_CONVERTED" ] && command -v jq &> /dev/null; then
    # Convert Gemini format to Antigravity format (url -> serverUrl for HTTP servers)
    jq '{mcpServers: (.mcpServers | to_entries | map(
        if .value.url then
            {key: .key, value: ((.value | del(.url)) * {serverUrl: .value.url})}
        else .
        end
    ) | from_entries)}' "$MCP_CONVERTED" > "$ANTIGRAVITY_MCP_CONFIG"
    AG_MCP_COUNT=$(jq '.mcpServers | keys | length' "$ANTIGRAVITY_MCP_CONFIG" 2>/dev/null || echo "0")
    echo -e "${GREEN}✓ Generated Antigravity mcp_config.json with $AG_MCP_COUNT servers${NC}"
else
    echo -e "${YELLOW}⚠ Could not generate Antigravity mcp_config.json${NC}"
fi

# Install skills from all aops plugins as global workflows
echo "Installing skills as Antigravity workflows..."
for plugin_dir in "$AOPS_PATH"/aops-*; do
    if [ -d "$plugin_dir" ] && [ -f "$plugin_dir/.claude-plugin/plugin.json" ]; then
        plugin_name=$(basename "$plugin_dir")
        skills_dir="$plugin_dir/skills"

        if [ ! -d "$skills_dir" ]; then
            continue
        fi

        for skill_dir in "$skills_dir"/*; do
            if [ -d "$skill_dir" ] && [ ! -L "$skill_dir" ]; then
                skill_name=$(basename "$skill_dir")
                # Skip __pycache__ and other non-skill dirs
                if [[ "$skill_name" == __* ]]; then
                    continue
                fi

                skill_file="$skill_dir/SKILL.md"

                if [ -f "$skill_file" ]; then
                    # Link as ~/.gemini/antigravity/global_workflows/<skill_name>.md
                    # This enables /<skill_name> invocation in Antigravity
                    target="$skill_file"
                    link_path="$GLOBAL_WORKFLOWS_DIR/$skill_name.md"

                    if [ -L "$link_path" ]; then
                        current_target="$(readlink "$link_path")"
                        if [ "$current_target" != "$target" ]; then
                            rm "$link_path"
                            ln -s "$target" "$link_path"
                            echo "  Updated $skill_name (from $plugin_name)"
                        else
                            echo "  $skill_name (already linked from $plugin_name)"
                        fi
                    elif [ -e "$link_path" ]; then
                        echo -e "${YELLOW}⚠ $link_path exists and is not a symlink - skipping${NC}"
                    else
                        ln -s "$target" "$link_path"
                        echo "  Linked $skill_name (from $plugin_name)"
                    fi
                fi
            fi
        done
    fi
done

# Install core rules for Antigravity (Project Level)
echo "Installing core rules for Antigravity..."
PROJECT_RULES_DIR="$AOPS_PATH/.agent/rules"
mkdir -p "$PROJECT_RULES_DIR"

# Link AXIOMS.md
target="$AOPS_PATH/AXIOMS.md"
link_path="$PROJECT_RULES_DIR/axioms.md"
if [ -L "$link_path" ]; then
    current_target="$(readlink "$link_path")"
    if [ "$current_target" != "$target" ]; then
        rm "$link_path"
        ln -s "$target" "$link_path"
        echo "  Updated axioms.md link"
    fi
elif [ -e "$link_path" ]; then
    rm "$link_path" # Replace file with symlink (enforce SSoT)
    ln -s "$target" "$link_path"
    echo -e "${GREEN}  Replaced axioms.md file with symlink${NC}"
else
    ln -s "$target" "$link_path"
    echo "  Linked axioms.md"
fi

# Link HEURISTICS.md
target="$AOPS_PATH/HEURISTICS.md"
link_path="$PROJECT_RULES_DIR/heuristics.md"
if [ -L "$link_path" ]; then
    current_target="$(readlink "$link_path")"
    if [ "$current_target" != "$target" ]; then
        rm "$link_path"
        ln -s "$target" "$link_path"
        echo "  Updated heuristics.md link"
    fi
elif [ -e "$link_path" ]; then
    rm "$link_path" # Replace file with symlink (enforce SSoT)
    ln -s "$target" "$link_path"
    echo -e "${GREEN}  Replaced heuristics.md file with symlink${NC}"
else
    ln -s "$target" "$link_path"
    echo "  Linked heuristics.md"
fi

# Link core.md (hydrator + bd workflow instructions)
target="$AOPS_PATH/config/antigravity/rules/core.md"
link_path="$PROJECT_RULES_DIR/core.md"
if [ -L "$link_path" ]; then
    current_target="$(readlink "$link_path")"
    if [ "$current_target" != "$target" ]; then
        rm "$link_path"
        ln -s "$target" "$link_path"
        echo "  Updated core.md link"
    fi
elif [ -e "$link_path" ]; then
    rm "$link_path" # Replace file with symlink (enforce SSoT)
    ln -s "$target" "$link_path"
    echo -e "${GREEN}  Replaced core.md file with symlink${NC}"
else
    ln -s "$target" "$link_path"
    echo "  Linked core.md"
fi

echo

# Step 3b: Install cron job for task index regeneration
echo "Step 3b: Task index cron job"
echo "----------------------------"

CRON_MARKER="# aOps task index"
CRON_CMD="*/5 * * * * cd $AOPS_PATH && ACA_DATA=$ACA_DATA_PATH uv run python scripts/regenerate_task_index.py >> /tmp/task-index.log 2>&1"

# Check if cron is available
if command -v crontab &> /dev/null; then
    # Check if cron job already exists
    # Note: grep -q exits 1 if no match, which with pipefail exits the script
    # Capture existing crontab first to avoid pipefail issues
    existing_crontab=$(crontab -l 2>/dev/null || true)
    if echo "$existing_crontab" | grep -q "$CRON_MARKER"; then
        echo -e "${GREEN}✓ Task index cron job already installed${NC}"
    else
        # Add cron job (append to existing)
        if (echo "$existing_crontab"; echo "$CRON_MARKER"; echo "$CRON_CMD") | crontab -; then
            echo -e "${GREEN}✓ Installed task index cron job (every 5 minutes)${NC}"
        else
            echo -e "${YELLOW}⚠ Could not install cron job - install manually:${NC}"
            echo "  crontab -e"
            echo "  Add: $CRON_CMD"
        fi
    fi
else
    echo -e "${YELLOW}⚠ crontab not available - task index cron job not installed${NC}"
    echo "  Run manually: cd \$AOPS && uv run python scripts/regenerate_task_index.py"
fi

echo

# Step 3c: Install cron job for session insights
echo "Step 3c: Session insights cron job"
echo "----------------------------------"

SESSION_CRON_MARKER="# aOps session insights"
# Jitter (0-300s) in crontab prevents thundering herd across machines
SESSION_CRON_CMD="*/30 * * * * sleep \$((RANDOM \% 300)) && cd $AOPS_PATH && ACA_DATA=$ACA_DATA_PATH scripts/cron_session_insights.sh >> /tmp/session-insights.log 2>&1"

if command -v crontab &> /dev/null; then
    # Refresh existing_crontab (may have been updated by Step 3b)
    existing_crontab=$(crontab -l 2>/dev/null || true)
    if echo "$existing_crontab" | grep -q "$SESSION_CRON_MARKER"; then
        echo -e "${GREEN}✓ Session insights cron job already installed${NC}"
    else
        if (echo "$existing_crontab"; echo "$SESSION_CRON_MARKER"; echo "$SESSION_CRON_CMD") | crontab -; then
            echo -e "${GREEN}✓ Installed session insights cron job (every 30 minutes)${NC}"
        else
            echo -e "${YELLOW}⚠ Could not install cron job - install manually:${NC}"
            echo "  crontab -e"
            echo "  Add: $SESSION_CRON_CMD"
        fi
    fi
else
    echo -e "${YELLOW}⚠ crontab not available - session insights cron job not installed${NC}"
    echo "  Run manually: cd \$AOPS && scripts/cron_session_insights.sh"
fi

echo

# Step 4: Validate setup
echo "Step 4: Validating setup"
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

# Check symlinks (only settings.json, CLAUDE.md, and plugin remain at top level)
for link in settings.json CLAUDE.md; do
    if [ ! -L "$CLAUDE_DIR/$link" ]; then
        echo -e "${RED}✗ Symlink missing: $CLAUDE_DIR/$link${NC}"
        VALIDATION_PASSED=false
    fi
done

# Check plugin symlinks (auto-discover all aops-* plugins)
plugin_count=0
for plugin_dir in "$AOPS_PATH"/aops-*; do
    if [ -d "$plugin_dir" ] && [ -f "$plugin_dir/.claude-plugin/plugin.json" ]; then
        plugin_name=$(basename "$plugin_dir")
        if [ ! -L "$CLAUDE_DIR/plugins/$plugin_name" ]; then
            echo -e "${RED}✗ Plugin symlink missing: $CLAUDE_DIR/plugins/$plugin_name${NC}"
            VALIDATION_PASSED=false
        else
            echo -e "${GREEN}✓ Plugin $plugin_name linked${NC}"
            plugin_count=$((plugin_count + 1))
        fi
    fi
done

if [ "$plugin_count" -eq 0 ]; then
    echo -e "${YELLOW}⚠ No aops plugins found${NC}"
fi

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

# Validate Gemini setup (if not skipped)
if [ "${GEMINI_SKIPPED:-true}" = "false" ]; then
    echo
    echo "Gemini CLI validation:"
    # Only validate symlinks for directories that exist in source
    for link in hooks commands; do
        if [ -d "$AOPS_PATH/config/gemini/$link" ]; then
            if [ -L "$GEMINI_DIR/$link" ]; then
                echo -e "${GREEN}✓ Gemini $link symlink OK${NC}"
            else
                echo -e "${RED}✗ Gemini $link symlink missing${NC}"
                VALIDATION_PASSED=false
            fi
        fi
    done

    if [ -L "$GEMINI_DIR/GEMINI.md" ] || [ -f "$GEMINI_DIR/GEMINI.md" ]; then
        echo -e "${GREEN}✓ GEMINI.md present${NC}"
    else
        echo -e "${YELLOW}⚠ GEMINI.md missing${NC}"
    fi

    if jq -e '.hooks' "$GEMINI_DIR/settings.json" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Gemini settings.json has hooks${NC}"
    fi

    TOML_COUNT=$(ls -1 "$AOPS_PATH/config/gemini/commands/"*.toml 2>/dev/null | wc -l)
    if [ "$TOML_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ $TOML_COUNT Gemini TOML commands${NC}"
    fi
fi

echo
if [ "$VALIDATION_PASSED" = true ]; then
    echo -e "${GREEN}✓ Setup completed successfully!${NC}"
    if [ "${GEMINI_SKIPPED:-true}" = "false" ]; then
        echo "  Both Claude Code and Gemini CLI are configured."
    else
        echo "  Claude Code configured. Install Gemini CLI and re-run for Gemini support."
    fi
    exit 0
else
    echo -e "${RED}✗ Setup validation failed${NC}"
    echo "Please fix the errors above and re-run this script"
    exit 1
fi
