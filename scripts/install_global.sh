#!/usr/bin/env bash
set -euo pipefail

# Global installation script for academicOps
# Installs hooks and skills into ~/.claude/ directory

echo "🤖 academicOps Global Installation"
echo "=================================="
echo

# Check prerequisites
if [ -z "${ACADEMICOPS_BOT:-}" ]; then
    echo "❌ ERROR: ACADEMICOPS_BOT environment variable not set"
    echo
    echo "Add to your shell profile (~/.bashrc or ~/.zshrc):"
    echo "  export ACADEMICOPS_BOT=/path/to/academicOps"
    echo
    exit 1
fi

if [ ! -d "$ACADEMICOPS_BOT" ]; then
    echo "❌ ERROR: ACADEMICOPS_BOT directory does not exist: $ACADEMICOPS_BOT"
    exit 1
fi

echo "✅ ACADEMICOPS_BOT: $ACADEMICOPS_BOT"

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "❌ ERROR: uv package manager not found"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv found: $(command -v uv)"
echo

# Create ~/.claude/ if it doesn't exist
mkdir -p ~/.claude

# Backup existing settings if present
if [ -f ~/.claude/settings.json ]; then
    echo "📦 Backing up existing ~/.claude/settings.json"
    cp ~/.claude/settings.json ~/.claude/settings.json.backup.$(date +%Y%m%d_%H%M%S)
fi

# Install or update ~/.claude/settings.json
echo "⚙️  Configuring ~/.claude/settings.json"

cat > ~/.claude/settings.json << 'EOF'
{
  "permissions": {
    "deny": []
  },
  "env": {
    "ACADEMICOPS_BOT": "${ACADEMICOPS_BOT}"
  },
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "if [ -f \"$ACADEMICOPS_BOT/bots/hooks/validate_tool.py\" ]; then uv run --directory \"$ACADEMICOPS_BOT\" python \"$ACADEMICOPS_BOT/bots/hooks/validate_tool.py\"; else echo '{\"continue\":true,\"systemMessage\":\"Hook not found: validate_tool.py\"}'; fi",
            "timeout": 3000
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "if [ -f \"$ACADEMICOPS_BOT/bots/hooks/validate_stop.py\" ]; then uv run --directory \"$ACADEMICOPS_BOT\" python \"$ACADEMICOPS_BOT/bots/hooks/validate_stop.py\" SubagentStop; else echo '{\"continue\":true}'; fi",
            "timeout": 2000
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "if [ -f \"$ACADEMICOPS_BOT/bots/hooks/validate_stop.py\" ]; then uv run --directory \"$ACADEMICOPS_BOT\" python \"$ACADEMICOPS_BOT/bots/hooks/validate_stop.py\" Stop; else echo '{\"continue\":true}'; fi",
            "timeout": 2000
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "if [ -f \"$ACADEMICOPS_BOT/bots/hooks/log_posttooluse.py\" ]; then uv run --directory \"$ACADEMICOPS_BOT\" python \"$ACADEMICOPS_BOT/bots/hooks/log_posttooluse.py\"; else echo '{}'; fi",
            "timeout": 2000
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "if [ -f \"$ACADEMICOPS_BOT/bots/hooks/log_userpromptsubmit.py\" ]; then uv run --directory \"$ACADEMICOPS_BOT\" python \"$ACADEMICOPS_BOT/bots/hooks/log_userpromptsubmit.py\"; else echo '{}'; fi",
            "timeout": 2000
          }
        ]
      }
    ]
  },
  "statusLine": {
    "type": "command",
    "command": "user=$(whoami); host=$(hostname -s); dir=$(pwd); dir=${dir/#$HOME/\\~}; git_info=''; if git rev-parse --git-dir >/dev/null 2>&1; then branch=$(git --no-optional-locks symbolic-ref --short HEAD 2>/dev/null || git --no-optional-locks rev-parse --short HEAD 2>/dev/null); if ! git --no-optional-locks diff --quiet 2>/dev/null || ! git --no-optional-locks diff --cached --quiet 2>/dev/null; then status='*'; else status=''; fi; [ -n \"$branch\" ] && git_info=$(printf ' \\033[38;5;99mon \\033[38;5;141m%s%s' \"$branch\" \"$status\"); fi; venv_info=''; [ -n \"$VIRTUAL_ENV\" ] && venv_info=$(printf ' \\033[38;5;45mvia \\033[38;5;51m%s' \"$(basename \"$VIRTUAL_ENV\")\"); printf '\\033[38;5;244m%s\\033[38;5;214m@%s \\033[38;5;75min \\033[38;5;81m%s%s%s' \"$user\" \"$host\" \"$dir\" \"$git_info\" \"$venv_info\""
  },
  "alwaysThinkingEnabled": false
}
EOF

# Substitute the actual ACADEMICOPS_BOT path
sed -i "s|\${ACADEMICOPS_BOT}|$ACADEMICOPS_BOT|g" ~/.claude/settings.json

echo "✅ Installed ~/.claude/settings.json with hooks"

# Deploy skills to ~/.claude/skills/
echo
echo "📦 Deploying skills to ~/.claude/skills/"
mkdir -p ~/.claude/skills

# Extract all packaged skills
if [ -d "$ACADEMICOPS_BOT/dist/skills" ]; then
    skill_count=0
    for skill_zip in "$ACADEMICOPS_BOT/dist/skills"/*.zip; do
        if [ -f "$skill_zip" ]; then
            skill_name=$(basename "$skill_zip" .zip)
            echo "  📦 Installing skill: $skill_name"

            # Remove existing skill directory
            rm -rf ~/.claude/skills/"$skill_name"

            # Extract skill
            unzip -q "$skill_zip" -d ~/.claude/skills/

            ((skill_count++))
        fi
    done
    echo "✅ Installed $skill_count skills"
else
    echo "⚠️  No packaged skills found in $ACADEMICOPS_BOT/dist/skills/"
fi

# Test hook execution
echo
echo "🧪 Testing hook execution"
if uv run --directory "$ACADEMICOPS_BOT" python "$ACADEMICOPS_BOT/bots/hooks/validate_tool.py" <<< '{}' > /dev/null 2>&1; then
    echo "✅ Hooks can execute successfully"
else
    echo "⚠️  Hook test failed (this may be expected if hooks require specific input)"
fi

echo
echo "✅ Installation complete!"
echo
echo "Next steps:"
echo "  1. Restart your shell or run: source ~/.bashrc"
echo "  2. Launch Claude Code from any directory: claude"
echo "  3. Verify \$ACADEMICOPS_BOT is set: echo \$ACADEMICOPS_BOT"
echo
echo "All Claude Code sessions will now use academicOps hooks and skills."
