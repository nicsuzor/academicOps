# Installing academicOps

Agent framework for academic research repositories.

## Prerequisites

- **Python 3.12+** with `uv` package manager
- **Claude Code CLI** installed and configured
- **Git** (optional, for version control)

## Installation Overview

academicOps installs **globally** into `~/.claude/` and makes itself available everywhere via the `$ACADEMICOPS_BOT` environment variable. Individual projects can optionally add local overrides.

## Installation Steps

### Step 1: Clone academicOps

```bash
git clone https://github.com/nicsuzor/academicOps.git ~/academicOps
# or your preferred location
```

### Step 2: Set Environment Variable

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export ACADEMICOPS_BOT=~/academicOps
```

Reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc
```

Optional (for personal context):
```bash
export ACADEMICOPS_PERSONAL=/path/to/your/writing
```

### Step 3: Run Global Installation Script

```bash
$ACADEMICOPS_BOT/scripts/install_global.sh
```

**What it does:**

- ✅ Configures `~/.claude/settings.json` with global hooks and environment variables
- ✅ Installs all skills to `~/.claude/skills/` (extracted from `dist/skills/*.zip`)
- ✅ Sets up validation hooks that run before every tool use
- ✅ Makes `$ACADEMICOPS_BOT` available to all Claude Code sessions
- ✅ Validates Python dependencies and environment

### Step 4: Verify Installation

Launch Claude Code from **any directory**:

```bash
cd ~  # Or any directory
claude
```

The global hooks should activate and you'll have access to all academicOps skills.

Test environment variable:
```bash
echo $ACADEMICOPS_BOT  # Should print your installation path
```

---

## Optional: Project-Specific Overrides

Individual projects can add local configuration in `.claude/settings.json` to override or extend global settings.

### Example: Project with Local Hooks

```bash
cd /path/to/your/project
mkdir -p .claude agents hooks

# Create local settings
cat > .claude/settings.json << 'EOF'
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "test -f $CLAUDE_PROJECT_DIR/hooks/load_instructions.py && uv run python $CLAUDE_PROJECT_DIR/hooks/load_instructions.py || echo 'No project instructions'",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
EOF
```

Project-local settings **merge with or override** global `~/.claude/settings.json` depending on hook configuration.

---

## Updating academicOps

Pull latest changes and re-run installation:

```bash
cd $ACADEMICOPS_BOT
git pull origin main
$ACADEMICOPS_BOT/scripts/install_global.sh
```

The installation script will:
- Update `~/.claude/settings.json` if needed
- Re-deploy updated skills to `~/.claude/skills/`
- Preserve any custom configuration you've added

---

## Troubleshooting

### "ACADEMICOPS_BOT not set" error

Add to your shell profile and reload:
```bash
echo 'export ACADEMICOPS_BOT=~/academicOps' >> ~/.bashrc
source ~/.bashrc
```

### Hooks not running

Check global settings exist:
```bash
cat ~/.claude/settings.json
```

Should contain `"env"` section with `ACADEMICOPS_BOT`.

### Skills not found

Verify skills are deployed:
```bash
ls ~/.claude/skills/
```

Re-run installation if missing:
```bash
$ACADEMICOPS_BOT/scripts/install_global.sh
```

### Hook scripts failing

Test manually with `uv run --directory`:
```bash
uv run --directory "$ACADEMICOPS_BOT" python "$ACADEMICOPS_BOT/bots/hooks/validate_tool.py"
```

---

## Architecture

See `ARCHITECTURE.md` for complete design documentation.
