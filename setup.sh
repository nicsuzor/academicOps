#!/usr/bin/env bash
#
# Setup script for aOps framework on Gemini CLI
#
# This script configures the Gemini CLI to work with the aOps framework.
# It converts the framework's MCP configuration and installs necessary hooks.
#
# Prerequisites:
#   - AOPS and ACA_DATA environment variables set
#   - jq installed
#   - gemini CLI installed
#
# Usage:
#   ./setup.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "aOps Framework Setup (Gemini CLI)"
echo "================================="
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

# Check for emergency disable flag
if [[ "${1:-}" == "--disable" ]]; then
    echo -e "${RED}EMERGENCY DISABLE TRIGGERED${NC}"
    echo "Removing aOps configuration..."

    # Remove cron jobs
    if command -v crontab &> /dev/null; then
        echo "Removing cron jobs..."
        # Use a temporary file to avoid pipefail issues
        TEMP_CRON=$(mktemp)
        crontab -l 2>/dev/null > "$TEMP_CRON" || true
        # Filter out aOps jobs
        grep -v "# aOps task index" "$TEMP_CRON" | grep -v "scripts/regenerate_task_index.py" | \
        grep -v "# aOps session insights" | grep -v "scripts/cron_session_insights.sh" | \
        grep -v "# aOps transcripts" | grep -v "scripts/transcript.py" > "$TEMP_CRON.new"
        crontab "$TEMP_CRON.new"
        rm "$TEMP_CRON" "$TEMP_CRON.new"
        echo -e "${GREEN}✓ Cron jobs removed${NC}"
    fi

<<<<<<< HEAD
    # Uninstall Claude plugins
    echo "Uninstalling Claude plugins..."
    if command -v claude &> /dev/null; then
        claude plugin uninstall aops-core 2>/dev/null && echo "  Uninstalled aops-core" || true
        claude plugin uninstall aops-tools 2>/dev/null && echo "  Uninstalled aops-tools" || true
    fi
    rm -f "$CLAUDE_DIR/settings.local.json"
    # Clean up legacy symlinks
    rm -f "$CLAUDE_DIR/CLAUDE.md"
    rm -f "$CLAUDE_DIR/skills" "$CLAUDE_DIR/commands" "$CLAUDE_DIR/agents" "$CLAUDE_DIR/hooks"
    echo -e "${GREEN}✓ Claude plugins uninstalled${NC}"
    echo -e "${YELLOW}Note: ~/.claude/settings.json not removed (user-managed file)${NC}"

=======
>>>>>>> academicOps-gemini
    # Remove Gemini config
    echo "Removing Gemini configuration..."
    GEMINI_DIR="$HOME/.gemini"
    rm -f "$GEMINI_DIR/hooks"
    rm -f "$GEMINI_DIR/commands"
    rm -f "$GEMINI_DIR/GEMINI.md"
    rm -rf "$GEMINI_DIR/antigravity/global_workflows"
    echo -e "${YELLOW}Note: ~/.gemini/settings.json was not removed. Please check it manually.${NC}"
    echo -e "${GREEN}✓ Gemini symlinks removed${NC}"

    # Remove Project Rules
    echo "Removing Project Rules..."
    rm -rf "$AOPS_PATH/.agent/rules"
    echo -e "${GREEN}✓ Project rules removed${NC}"

    echo
    echo -e "${GREEN}aOps framework disabled.${NC}"
    exit 0
fi

echo "Framework paths:"
echo "  AOPS:     $AOPS_PATH"
echo "  ACA_DATA: $ACA_DATA_PATH"
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

<<<<<<< HEAD
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

# Copy settings.json if it doesn't exist (user manages their own settings)
SETTINGS_SRC="$AOPS_PATH/config/claude/settings.json"
SETTINGS_DST="$CLAUDE_DIR/settings.json"
if [ -L "$SETTINGS_DST" ]; then
    # Convert symlink (old setup) to file
    echo -e "${YELLOW}  Converting settings.json from symlink to file${NC}"
    rm "$SETTINGS_DST"
    cp "$SETTINGS_SRC" "$SETTINGS_DST"
    echo -e "${GREEN}✓ Converted settings.json to file (edit ~/.claude/settings.json to customize)${NC}"
elif [ ! -f "$SETTINGS_DST" ]; then
    cp "$SETTINGS_SRC" "$SETTINGS_DST"
    echo -e "${GREEN}✓ Copied settings.json (edit ~/.claude/settings.json to customize)${NC}"
else
    echo "  settings.json already exists (not overwriting)"
fi

# Note: CLAUDE.md symlink removed - use repo-level CLAUDE.md instead

# Install plugins via Claude Code CLI
echo
echo "Installing plugins via Claude Code..."

if command -v claude &> /dev/null; then
    # Add marketplace (idempotent - won't fail if already added)
    if claude plugin marketplace add @nicsuzor/academicOps 2>/dev/null; then
        echo -e "${GREEN}✓ Added @nicsuzor/academicOps marketplace${NC}"
    else
        echo "  Marketplace @nicsuzor/academicOps already configured"
    fi

    # Install plugins
    for plugin_name in aops-core aops-tools; do
        if claude plugin install "$plugin_name" 2>/dev/null; then
            echo -e "${GREEN}✓ Installed plugin: $plugin_name${NC}"
        else
            echo "  Plugin $plugin_name already installed or install failed"
        fi
    done
else
    echo -e "${YELLOW}⚠ claude CLI not found - install plugins manually:${NC}"
    echo "  claude plugin marketplace add @nicsuzor/academicOps"
    echo "  claude plugin install aops-core"
    echo "  claude plugin install aops-tools"
fi

# Clean up legacy symlinks (content moved to plugins)
for legacy in skills commands agents hooks; do
    if [ -L "$CLAUDE_DIR/$legacy" ]; then
        rm "$CLAUDE_DIR/$legacy"
        echo -e "${YELLOW}  Removed legacy symlink: $legacy${NC}"
    fi
done

# Clean up old plugin symlinks (now using CLI install)
if [ -d "$CLAUDE_DIR/plugins" ]; then
    for plugin_link in "$CLAUDE_DIR/plugins"/aops-*; do
        if [ -L "$plugin_link" ]; then
            rm "$plugin_link"
            echo -e "${YELLOW}  Removed legacy plugin symlink: $(basename "$plugin_link")${NC}"
        fi
    done
fi

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

# Step 2b: Build and sync MCP servers
# Note: Claude Code reads user-scoped MCP servers from ~/.claude.json mcpServers key.
# However, since we use plugins (symlinked to ~/.claude/plugins/), Claude Code will automatically
# load MCP servers defined in each plugin's mcp.json file.
# We no longer write to ~/.claude.json to avoid conflicts.
echo
echo "Building MCP configuration..."
=======
# Step 2: Build MCP Configuration
echo "Step 2: Building MCP Configuration"
echo "----------------------------------"
>>>>>>> academicOps-gemini

# Check for MCP tokens (required for gh and memory servers)
if [ -z "${GH_MCP_TOKEN:-}" ]; then
    echo -e "${YELLOW}⚠ GH_MCP_TOKEN not set - GitHub MCP server will not authenticate${NC}"
    echo "  Set in shell RC: export GH_MCP_TOKEN='your-github-token'"
fi
if [ -z "${MCP_MEMORY_API_KEY:-}" ]; then
    echo -e "${YELLOW}⚠ MCP_MEMORY_API_KEY not set - Memory MCP server will not authenticate${NC}"
    echo "  Set in shell RC: export MCP_MEMORY_API_KEY='your-memory-token'"
fi

echo "Generating plugin-specific MCP configs..."

# List of plugins with MCP templates
for plugin_name in aops-core aops-tools; do
    plugin_dir="$AOPS_PATH/$plugin_name"
    template_file="$plugin_dir/.mcp.json.template"
    output_file="$plugin_dir/.mcp.json"

    if [ -f "$template_file" ]; then
        # Use python for safe substitution (handles special chars in env vars better than sed)
        python3 - << 'EOF' "$template_file" "$output_file" "$plugin_dir"
import os
import sys

template_path = sys.argv[1]
output_path = sys.argv[2]
plugin_dir = sys.argv[3]

try:
    with open(template_path, "r") as f:
        content = f.read()

    # Manual substitution to match specific placeholders
    replacements = {
        "${CONTEXT7_API_KEY}": os.environ.get("CONTEXT7_API_KEY", ""),
        "${MCP_MEMORY_API_KEY}": os.environ.get("MCP_MEMORY_API_KEY", ""),
        "${GH_MCP_TOKEN}": os.environ.get("GH_MCP_TOKEN", ""),
        "${CLAUDE_PLUGIN_ROOT}": plugin_dir,
    }

    for key, value in replacements.items():
        content = content.replace(key, value)

    with open(output_path, "w") as f:
        f.write(content)
except Exception as e:
    print(f"Error processing template: {e}", file=sys.stderr)
    sys.exit(1)
EOF
        echo -e "${GREEN}✓ Generated $plugin_name/.mcp.json from template${NC}"
    else
        echo -e "${YELLOW}⚠ No template found: $template_file${NC}"
    fi
done

echo "Aggregating plugin MCPs..."
AGGREGATED_MCP="$AOPS_PATH/config/gemini/aggregated_mcp.json"
mkdir -p "$AOPS_PATH/config/gemini"

if command -v jq &> /dev/null; then
    # Start with empty mcpServers object
    echo '{"mcpServers": {}}' > "$AGGREGATED_MCP"
    
    # Merge each plugin's mcp.json
    for plugin_name in aops-core aops-tools; do
        plugin_mcp="$AOPS_PATH/$plugin_name/.mcp.json"
        if [ -f "$plugin_mcp" ]; then
            jq -s '.[0] * .[1]' "$AGGREGATED_MCP" "$plugin_mcp" > "$AGGREGATED_MCP.tmp" && mv "$AGGREGATED_MCP.tmp" "$AGGREGATED_MCP"
        fi
    done
    
    echo -e "${GREEN}✓ Aggregated plugin MCPs to $AGGREGATED_MCP${NC}"
else
    echo -e "${RED}✗ jq not installed - cannot aggregate MCPs${NC}"
    exit 1
fi

echo 

# Step 3: Configure memory server default project
echo "Step 3: Configuring memory server"
echo "---------------------------------"

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

# Step 4: Gemini CLI setup
echo "Step 4: Gemini CLI setup"
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
    
    # GEMINI.md generation (injects actual paths)
    if [ -L "$GEMINI_DIR/GEMINI.md" ] || [ -f "$GEMINI_DIR/GEMINI.md" ]; then
        rm "$GEMINI_DIR/GEMINI.md"
    fi

    # Read source and inject paths
    sed -e "s|~/src/academicOps|$AOPS_PATH|g" \
        -e "s|~/writing/data|$ACA_DATA_PATH|g" \
        "$AOPS_PATH/config/gemini/GEMINI.md" > "$GEMINI_DIR/GEMINI.md"

    echo -e "${GREEN}  Generated ~/.gemini/GEMINI.md with paths injected${NC}"

    # Update Antigravity global workflow link
    mkdir -p "$GLOBAL_WORKFLOWS_DIR"
    GLOBAL_GEMINI_MD="$GLOBAL_WORKFLOWS_DIR/GEMINI.md"
    if [ -L "$GLOBAL_GEMINI_MD" ]; then
        rm "$GLOBAL_GEMINI_MD"
        ln -s "$GEMINI_DIR/GEMINI.md" "$GLOBAL_GEMINI_MD"
        echo -e "${GREEN}  Updated Antigravity GEMINI.md link${NC}"
    elif [ ! -e "$GLOBAL_GEMINI_MD" ]; then
         ln -s "$GEMINI_DIR/GEMINI.md" "$GLOBAL_GEMINI_MD"
         echo -e "${GREEN}  Linked Antigravity GEMINI.md${NC}"
    fi

    # Convert MCP servers from Claude format to Gemini format
    echo
    echo "Converting MCP servers for Gemini..."
    MCP_SOURCE="$AOPS_PATH/config/gemini/aggregated_mcp.json"
    MCP_CONVERTED="$AOPS_PATH/config/gemini/mcp-servers.json"
    mkdir -p "$AOPS_PATH/config/gemini"

    if [ -f "$MCP_SOURCE" ]; then
        if AOPS="$AOPS_PATH" python3 "$AOPS_PATH/scripts/convert_mcp_to_gemini.py" "$MCP_SOURCE" "$MCP_CONVERTED" 2>&1; then
            # Post-process to filter: Only keep task_manager
            jq '{mcpServers: {task_manager: .mcpServers.task_manager}}' "$MCP_CONVERTED" > "$MCP_CONVERTED.tmp" && mv "$MCP_CONVERTED.tmp" "$MCP_CONVERTED"
            MCP_COUNT=$(jq '.mcpServers | keys | length' "$MCP_CONVERTED" 2>/dev/null || echo "0")
            echo -e "${GREEN}✓ Converted $MCP_COUNT MCP servers to Gemini format (task_manager only)${NC}"
        else
            echo -e "${YELLOW}⚠ MCP conversion failed - check script output above${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ No aggregated MCP source found at $MCP_SOURCE${NC}"
    fi

    # Merge settings
    echo
    echo "Merging Gemini settings..."
    GEMINI_SETTINGS="$GEMINI_DIR/settings.json"
    
    if [ -f "$AOPS_PATH/config/gemini/config/settings.json.template" ]; then
        MERGE_FILE="$AOPS_PATH/config/gemini/config/settings.json.template"
    else
        MERGE_FILE="$AOPS_PATH/config/gemini/config/settings-merge.json"
    fi

    if [ ! -f "$GEMINI_SETTINGS" ]; then
        echo "{}" > "$GEMINI_SETTINGS"
    else
        if ! jq . "$GEMINI_SETTINGS" > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠ Existing Gemini settings.json is invalid - backing up and resetting${NC}"
            mv "$GEMINI_SETTINGS" "$GEMINI_SETTINGS.bak.$(date +%s)"
            echo "{}" > "$GEMINI_SETTINGS"
        fi
    fi

    if [ -f "$MERGE_FILE" ]; then
        # Substitute both ${AOPS} and $AOPS for backward compatibility using python
        MERGE_CONTENT=$(python3 - << 'EOF' "$MERGE_FILE" "$AOPS_PATH"
import sys
import os

filepath = sys.argv[1]
aops_path = sys.argv[2]

try:
    with open(filepath, "r") as f:
        content = f.read()
    
    # Replace ${AOPS} and $AOPS
    content = content.replace("${AOPS}", aops_path).replace("$AOPS", aops_path)
    print(content)
except Exception as e:
    sys.exit(1)
EOF
)

        # Merge new config with existing settings
        # We overwrite hooks/hooksConfig with new values to ensure clean state
        # We merge mcpServers to preserve any user-added servers
        if [ -f "$MCP_CONVERTED" ]; then
            MCP_CONTENT=$(cat "$MCP_CONVERTED")
            MERGED=$(jq -s ' 
                .[0] as $existing |
                .[1] as $new |
                .[2] as $mcp |
                $existing * {
                    hooksConfig: ($new.hooksConfig // {}),
                    hooks: ($new.hooks // {}),
                    mcpServers: (($existing.mcpServers // {}) * ($new.mcpServers // {}) * ($mcp.mcpServers // {}))
                } | del(.["$comment"])
            ' "$GEMINI_SETTINGS" <(echo "$MERGE_CONTENT") <(echo "$MCP_CONTENT"))
        else
            MERGED=$(jq -s ' 
                .[0] as $existing |
                .[1] as $new |
                $existing * {
                    hooksConfig: ($new.hooksConfig // {}),
                    hooks: ($new.hooks // {}),
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

# Step 5: Antigravity setup
echo "Step 5: Antigravity setup"
echo "------------------------"

ANTIGRAVITY_DIR="$GEMINI_DIR/antigravity"
GLOBAL_WORKFLOWS_DIR="$ANTIGRAVITY_DIR/global_workflows"
mkdir -p "$GLOBAL_WORKFLOWS_DIR"

# Generate Antigravity mcp_config.json
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

# Install core rules for Antigravity (Project Level)
echo "Installing core rules for Antigravity..."
PROJECT_RULES_DIR="$AOPS_PATH/.agent/rules"
mkdir -p "$PROJECT_RULES_DIR"

for rule_file in AXIOMS.md HEURISTICS.md; do
    target="$AOPS_PATH/$rule_file"
    link_path="$PROJECT_RULES_DIR/${rule_file,,}" # to lowercase
    if [ -e "$link_path" ] || [ -L "$link_path" ]; then
        rm "$link_path"
    fi
    ln -s "$target" "$link_path"
    echo "  Linked ${rule_file,,}"
done

# Link core.md
target="$AOPS_PATH/config/antigravity/rules/core.md"
link_path="$PROJECT_RULES_DIR/core.md"
if [ -e "$link_path" ] || [ -L "$link_path" ]; then
    rm "$link_path"
fi
ln -s "$target" "$link_path"
echo "  Linked core.md"

echo

# Step 6: Install cron jobs
echo "Step 6: Cron jobs"
echo "-----------------"

CRON_MARKER="# aOps task index"
CRON_CMD="*/5 * * * * cd $AOPS_PATH && ACA_DATA=$ACA_DATA_PATH uv run python scripts/regenerate_task_index.py >> /tmp/task-index.log 2>&1"

TRANSCRIPT_CRON_MARKER="# aOps transcripts"
TRANSCRIPT_CRON_CMD="*/30 * * * * cd $AOPS_PATH && ACA_DATA=$ACA_DATA_PATH uv run python aops-core/scripts/transcript.py --recent >> /tmp/aops-transcripts.log 2>&1"

if command -v crontab &> /dev/null; then
    existing_crontab=$(crontab -l 2>/dev/null || true)
    
    # Remove old session insights job if present
    existing_crontab=$(echo "$existing_crontab" | grep -v "# aOps session insights" | grep -v "scripts/cron_session_insights.sh" || true)

    # Task Index
    if echo "$existing_crontab" | grep -q "$CRON_MARKER"; then
        echo -e "${GREEN}✓ Task index cron job already installed${NC}"
    else
        existing_crontab="${existing_crontab}
${CRON_MARKER}
${CRON_CMD}"
        echo -e "${GREEN}✓ Installed task index cron job${NC}"
    fi

    # Transcripts
    if echo "$existing_crontab" | grep -q "$TRANSCRIPT_CRON_MARKER"; then
        echo -e "${GREEN}✓ Transcripts cron job already installed${NC}"
    else
        existing_crontab="${existing_crontab}
${TRANSCRIPT_CRON_MARKER}
${TRANSCRIPT_CRON_CMD}"
        echo -e "${GREEN}✓ Installed transcripts cron job${NC}"
    fi
    
    # Install updated crontab
    echo "$existing_crontab" | crontab -
else
    echo -e "${YELLOW}⚠ crontab not available - cron jobs not installed${NC}"
fi

echo
echo "Step 7: Validating setup"
echo "------------------------"

VALIDATION_PASSED=true

# Check environment variables
if [ -z "${AOPS:-}" ] || [ -z "${ACA_DATA:-}" ]; then
    echo -e "${RED}✗ AOPS/ACA_DATA check failed${NC}"
    VALIDATION_PASSED=false
<<<<<<< HEAD
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

# Check settings.json exists (file, not symlink - user-managed)
if [ -f "$CLAUDE_DIR/settings.json" ]; then
    if [ -L "$CLAUDE_DIR/settings.json" ]; then
        echo -e "${YELLOW}⚠ settings.json is a symlink (old setup) - consider running setup.sh again to convert to file${NC}"
    else
        echo -e "${GREEN}✓ settings.json exists${NC}"
    fi
else
    echo -e "${RED}✗ settings.json missing: $CLAUDE_DIR/settings.json${NC}"
    VALIDATION_PASSED=false
fi

# Check plugins installed via Claude CLI
INSTALLED_PLUGINS="$CLAUDE_DIR/plugins/installed_plugins.json"
if [ -f "$INSTALLED_PLUGINS" ] && command -v jq &> /dev/null; then
    for plugin_name in aops-core aops-tools; do
        # Plugin keys include marketplace suffix, e.g., "aops-core@academicOps"
        if jq -e ".plugins | keys[] | select(startswith(\"$plugin_name@\"))" "$INSTALLED_PLUGINS" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Plugin $plugin_name installed${NC}"
        else
            echo -e "${RED}✗ Plugin $plugin_name not installed${NC}"
            echo "  Run: claude plugin install $plugin_name"
            VALIDATION_PASSED=false
        fi
    done
elif [ -f "$INSTALLED_PLUGINS" ]; then
    echo -e "${YELLOW}⚠ jq not installed - cannot verify plugins${NC}"
else
    echo -e "${RED}✗ No plugins installed (missing installed_plugins.json)${NC}"
    echo "  Run: claude plugin marketplace add @nicsuzor/academicOps"
    echo "  Run: claude plugin install aops-core aops-tools"
    VALIDATION_PASSED=false
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
=======
>>>>>>> academicOps-gemini
fi

# Validate Gemini setup (if not skipped)
if [ "${GEMINI_SKIPPED:-true}" = "false" ]; then
    # Only validate symlinks for directories that exist in source
    for link in hooks; do
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
    fi

    if jq -e '.hooks' "$GEMINI_DIR/settings.json" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Gemini settings.json has hooks${NC}"
    fi

    MCP_COUNT=$(jq '.mcpServers | length // 0' "$GEMINI_DIR/settings.json")
    if [ "$MCP_COUNT" -gt 0 ]; then
        if jq -e '.mcpServers.task_manager' "$GEMINI_DIR/settings.json" > /dev/null 2>&1; then
             echo -e "${GREEN}✓ Gemini settings.json has task_manager MCP${NC}"
        else
             echo -e "${YELLOW}⚠ Gemini settings.json missing task_manager MCP${NC}"
        fi
    fi
fi

echo
if [ "$VALIDATION_PASSED" = true ]; then
    echo -e "${GREEN}✓ Setup completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}✗ Setup validation failed${NC}"
    exit 1
fi
