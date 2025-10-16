# Installing academicOps

Agent framework for academic research repositories.

## Quick Start

```bash
# Add as submodule
git submodule add https://github.com/nicsuzor/academicOps.git bot

# Install
cd bot && uv sync && uv run pre-commit install
```

Create `.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": "uv run python bot/scripts/validate_env.py"
  }
}
```

Start Claude: `claude`

## Usage

**Agents:** `@agent-trainer` `@agent-strategist` `@agent-developer` `@agent-code-review`

**Customize:** Create `docs/agents/INSTRUCTIONS.md` for your context

**Update:** `cd bot && git pull && cd .. && git add bot && git commit -m "Update bot"`

See `bot/docs/ARCHITECTURE.md` for details.
