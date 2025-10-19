# Installing academicOps

Agent framework for academic research repositories.

## Prerequisites

- **Python 3.12+** with `uv` package manager
- **Claude Code CLI** installed and configured
- **Git** repository for your project

## Installation Methods

### Method 1: Automated Setup (Recommended)

The automated setup script configures everything for you.

**Step 1: Set Environment Variable**

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export ACADEMICOPS_BOT=/path/to/academicOps
```

Optional (for personal context):
```bash
export ACADEMICOPS_PERSONAL=/path/to/your/writing
```

**Step 2: Run Setup Script**

```bash
# Navigate to your project
cd /path/to/your/project

# Run setup
$ACADEMICOPS_BOT/scripts/setup_academicops.sh
```

**What it does:**

- ✅ Creates `.claude/settings.json` with hook configuration
- ✅ Symlinks `.claude/agents/` to academicOps agents
- ✅ Creates `agents/_CORE.md` template for project-specific context
- ✅ Symlinks validation scripts to `.academicOps/scripts/`
- ✅ Installs git pre-commit hooks for documentation quality enforcement
- ✅ Updates `.gitignore` to exclude managed files
- ✅ Validates environment variables and dependencies

**Step 3: Launch Claude Code**

```bash
claude
```

You'll see confirmation that core instructions loaded at session start.

---

### Method 2: Manual Setup (Advanced)

For custom installations or troubleshooting.

**1. Create Claude Code Configuration**

Create `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run pytest:*)",
      "Bash(uv run python:*)"
    ],
    "deny": [
      "Write(**/*.md)",
      "Write(**/*.env*)"
    ]
  },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run python $ACADEMICOPS_BOT/scripts/load_instructions.py",
            "timeout": 5000
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run python $ACADEMICOPS_BOT/scripts/validate_tool.py",
            "timeout": 3000
          }
        ]
      }
    ]
  }
}
```

**2. Symlink Agents**

```bash
ln -s $ACADEMICOPS_BOT/.claude/agents .claude/agents
```

**3. Create Project Context File**

```bash
mkdir -p agents
cp $ACADEMICOPS_BOT/dist/agents/INSTRUCTIONS.md agents/_CORE.md
```

Edit `agents/_CORE.md` with your project-specific context.

**4. Install Git Hooks**

```bash
$ACADEMICOPS_BOT/scripts/git-hooks/install-hooks.sh
```

**5. Update .gitignore**

```bash
cat $ACADEMICOPS_BOT/dist/.gitignore >> .gitignore
```

---

## Post-Installation

### Verify Installation

```bash
# Test instruction loading
uv run python $ACADEMICOPS_BOT/scripts/load_instructions.py

# Launch Claude and check for SessionStart confirmation
claude
```

You should see: `Loaded _CORE.md: ✓ bot ✓ project`

### Customize for Your Project

Edit `agents/_CORE.md` in your project to add:

- Project-specific rules and workflows
- Domain knowledge and terminology
- Team conventions and standards
- Tool configurations

### Available Agents

- `@agent-trainer` - Framework maintenance
- `@agent-strategist` - Planning and task management
- `@agent-developer` - Code implementation
- `@agent-code-review` - Code review and commits
- `@agent-analyst` - Data analysis workflows

### Slash Commands

- `/ops` - Framework help
- `/ttd` - Test-driven development workflow
- `/trainer` - Activate trainer mode

---

## Updating academicOps

### If Installed as Submodule

```bash
cd bot
git pull origin main
cd ..
git add bot
git commit -m "Update academicOps framework"
```

### If Using Flat Architecture

```bash
cd $ACADEMICOPS_BOT
git pull origin main
```

No project changes needed—symlinks automatically reference updated code.

---

## Troubleshooting

### "ACADEMICOPS_BOT not set" error

Add to your shell profile:
```bash
export ACADEMICOPS_BOT=/path/to/academicOps
source ~/.bashrc  # or ~/.zshrc
```

### SessionStart hook not running

Check `.claude/settings.json` exists and contains SessionStart hook configuration.

Run manually to debug:
```bash
uv run python $ACADEMICOPS_BOT/scripts/load_instructions.py
```

### Git hooks not working

Reinstall:
```bash
$ACADEMICOPS_BOT/scripts/git-hooks/install-hooks.sh --force
```

### PreToolUse validation failing

Check that validation scripts are accessible:
```bash
ls -la $ACADEMICOPS_BOT/scripts/validate_tool.py
```

---

## Architecture

See `ARCHITECTURE.md` for complete design documentation.
