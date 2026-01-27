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

    # Remove Gemini config
    echo "Removing Gemini configuration..."
    GEMINI_DIR="$HOME/.gemini"
    
    # Uninstall Gemini extension if it exists
    if command -v gemini &> /dev/null; then
        # Try both names just in case
        gemini extensions uninstall aops-core academic-ops-core 2>/dev/null && echo "  Uninstalled aops-core extension" || true
    fi

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

# Step 1b: Create framework file symlinks at root
echo "Step 1b: Creating framework file symlinks"
echo "-----------------------------------------"

# Framework files live in aops-core/ but hydrator expects them at root
for file in WORKFLOWS.md SKILLS.md AXIOMS.md HEURISTICS.md; do
    target="aops-core/$file"
    link_path="$AOPS_PATH/$file"
    if [ -L "$link_path" ]; then
        current_target="$(readlink "$link_path")"
        if [ "$current_target" = "$target" ]; then
            echo "  $file → $target (already correct)"
            continue
        fi
        rm "$link_path"
    elif [ -e "$link_path" ]; then
        echo -e "${YELLOW}⚠ $file exists as regular file, skipping symlink${NC}"
        continue
    fi
    ln -s "$target" "$link_path"
    echo -e "${GREEN}  $file → $target${NC}"
done

# Generate .agent/PATHS.md
echo "Generating .agent/PATHS.md..."
if python3 "$AOPS_PATH/aops-core/scripts/generate_framework_paths.py"; then
    echo -e "${GREEN}✓ Generated .agent/PATHS.md${NC}"
else
    echo -e "${YELLOW}⚠ Failed to generate .agent/PATHS.md${NC}"
fi
echo

# Step 2: Build MCP Configuration
echo "Step 2: Building MCP Configuration"
echo "----------------------------------"

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

    # Legacy hooks symlink removed (handled by extension)
    
    # GEMINI.md generation (injects actual paths)
    if [ -L "$GEMINI_DIR/GEMINI.md" ] || [ -f "$GEMINI_DIR/GEMINI.md" ]; then
        rm "$GEMINI_DIR/GEMINI.md"
    fi

    # Read source and inject paths
    if [ -f "$AOPS_PATH/aops-core/GEMINI.md" ]; then
        sed -e "s|\${AOPS}|$AOPS_PATH|g" \
            -e "s|\${ACA_DATA}|$ACA_DATA_PATH|g" \
            "$AOPS_PATH/aops-core/GEMINI.md" > "$GEMINI_DIR/GEMINI.md"
        echo -e "${GREEN}  Generated ~/.gemini/GEMINI.md with paths injected${NC}"
    else
        echo -e "${YELLOW}⚠ aops-core/GEMINI.md not found, skipping generation${NC}"
    fi

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
    MCP_BUILD_DIR="$AOPS_PATH/aops-core/config/gemini"
    mkdir -p "$MCP_BUILD_DIR"
    MCP_SOURCE="$MCP_BUILD_DIR/aggregated_mcp.json"
    MCP_CONVERTED="$MCP_BUILD_DIR/mcp-servers.json"

    if command -v jq &> /dev/null; then
        # Start with empty mcpServers object
        echo '{"mcpServers": {}}' > "$MCP_SOURCE"
        
        # Merge each plugin's mcp.json
        for plugin_name in aops-core aops-tools; do
            plugin_mcp="$AOPS_PATH/$plugin_name/.mcp.json"
            if [ -f "$plugin_mcp" ]; then
                jq -s '.[0] * .[1]' "$MCP_SOURCE" "$plugin_mcp" > "$MCP_SOURCE.tmp" && mv "$MCP_SOURCE.tmp" "$MCP_SOURCE"
            fi
        done
        
        echo -e "${GREEN}✓ Aggregated plugin MCPs to $MCP_SOURCE${NC}"
    else
        echo -e "${RED}✗ jq not installed - cannot aggregate MCPs${NC}"
        # Continue anyway, might not be fatal if extension handles it
    fi

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

    # Generate and Link Gemini Extension
    echo
    echo "Setting up Gemini Extension..."
    EXTENSION_SETUP_SUCCESS=false
    
    if AOPS="$AOPS_PATH" ACA_DATA="$ACA_DATA_PATH" python3 "$AOPS_PATH/scripts/create_extension.py"; then
        echo -e "${GREEN}✓ Generated gemini-extension.json${NC}"
        
        if command -v gemini &> /dev/null; then
             # Link both extensions
             for ext_dir in aops-core aops-tools; do
                 full_ext_path="$AOPS_PATH/dist/$ext_dir"
                 if [ -d "$full_ext_path" ]; then
                     echo "Linking $ext_dir extension..."
                     set +e
                     LINK_OUTPUT=$(cd "$full_ext_path" && yes | gemini extensions link . 2>&1)
                     LINK_EXIT_CODE=$?
                     set -e

                     if [ $LINK_EXIT_CODE -eq 0 ] || echo "$LINK_OUTPUT" | grep -q "already installed"; then
                        echo -e "${GREEN}✓ Linked $ext_dir extension${NC}"
                     else
                        echo -e "${YELLOW}⚠ Failed to link $ext_dir extension${NC}"
                        echo "Output: $LINK_OUTPUT"
                     fi
                 fi
             done
             EXTENSION_SETUP_SUCCESS=true
        fi
    else
        echo -e "${RED}✗ Failed to generate gemini-extension.json${NC}"
    fi

    # Merge settings
    echo
    echo "Merging Gemini settings..."
    GEMINI_SETTINGS="$GEMINI_DIR/settings.json"
    
    # We no longer rely on config/gemini/config/settings.json.template since we deleted it.
    # We just ensure hooksConfig is enabled.
    
    if [ ! -f "$GEMINI_SETTINGS" ]; then
        echo "{}" > "$GEMINI_SETTINGS"
    fi

    # Basic merge to enable hooksConfig
    if command -v jq &> /dev/null; then
        MERGED=$(jq '.hooksConfig.enabled = true' "$GEMINI_SETTINGS")
        echo "$MERGED" > "$GEMINI_SETTINGS"
        echo -e "${GREEN}✓ Updated global settings (hooksConfig enabled)${NC}"
    fi

    # Set permissions
    # chmod +x "$AOPS_PATH/config/gemini/hooks/router.py" 2>/dev/null || true # Removed
    chmod +x "$AOPS_PATH/aops-core/hooks/gemini/router.py" 2>/dev/null || true
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

# Step 6: Polecats configuration
echo "Step 6: Polecats configuration"
echo "------------------------------"

POLECATS_DIR="$HOME/polecats"
mkdir -p "$POLECATS_DIR/.claude" "$POLECATS_DIR/.gemini" "$POLECATS_DIR/.repos" "$POLECATS_DIR/crew"

# Create .claude/settings.local.json for polecats
POLECAT_CLAUDE_SETTINGS="$POLECATS_DIR/.claude/settings.local.json"
cat > "$POLECAT_CLAUDE_SETTINGS" << 'CLAUDE_EOF'
{
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read(*)",
      "Write(*)",
      "Edit(*)",
      "Glob(*)",
      "Grep(*)",
      "mcp__plugin_aops-core_*(*)",
      "mcp__plugin_aops-tools_*(*)"
    ]
  }
}
CLAUDE_EOF
echo -e "${GREEN}✓ Created polecats .claude/settings.local.json${NC}"

# Create .gemini/settings.json for polecats
POLECAT_GEMINI_SETTINGS="$POLECATS_DIR/.gemini/settings.json"
cat > "$POLECAT_GEMINI_SETTINGS" << 'GEMINI_EOF'
{
  "hooks": {
    "preToolCall": [],
    "postToolCall": []
  },
  "permissions": {
    "allowAll": true
  }
}
GEMINI_EOF
echo -e "${GREEN}✓ Created polecats .gemini/settings.json${NC}"

# Create .env for polecats
POLECAT_ENV="$POLECATS_DIR/.env"
cat > "$POLECAT_ENV" << ENV_EOF
# Polecat environment configuration
# Loaded by crew/polecat sessions

# Framework paths
AOPS="$AOPS_PATH"
ACA_DATA="$ACA_DATA_PATH"

# Polecat-specific
POLECAT_ROOT="$POLECATS_DIR"
ENV_EOF
echo -e "${GREEN}✓ Created polecats .env${NC}"

echo

# Step 7: Install cron jobs
echo "Step 7: Cron jobs"
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
echo "Step 8: Validating setup"
echo "------------------------"

VALIDATION_PASSED=true

# Check environment variables
if [ -z "${AOPS:-}" ] || [ -z "${ACA_DATA:-}" ]; then
    echo -e "${RED}✗ AOPS/ACA_DATA check failed${NC}"
    VALIDATION_PASSED=false
fi

# Validate Gemini setup (if not skipped)
if [ "${GEMINI_SKIPPED:-true}" = "false" ]; then
    if [ -L "$GEMINI_DIR/GEMINI.md" ] || [ -f "$GEMINI_DIR/GEMINI.md" ]; then
        echo -e "${GREEN}✓ GEMINI.md present${NC}"
    fi

    if jq -e '.hooks' "$GEMINI_DIR/settings.json" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Gemini settings.json has hooks${NC}"
    fi

    # Check if extension manifest exists and has task_manager
    if [ -f "$AOPS_PATH/dist/aops-core/gemini-extension.json" ]; then
        if jq -e '.mcpServers.task_manager' "$AOPS_PATH/dist/aops-core/gemini-extension.json" > /dev/null 2>&1; then
             echo -e "${GREEN}✓ Extension manifest has task_manager MCP${NC}"
        else
             echo -e "${YELLOW}⚠ Extension manifest missing task_manager MCP${NC}"
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
