# academicOps Framework Development Context

This repository is the academicOps framework - the core instruction and tooling system.

## Directory Structure

See `paths.toml` in repo root for canonical path definitions.

**Key directories:**

- `core/` - Universal instructions loaded at SessionStart
- `agents/` - Self-contained agentic workflows (subagents)
- `commands/` - User-invoked slash commands
- `skills/` - Claude Code skills
- `hooks/` - SessionStart, PostToolUse, Stop hooks
- `scripts/` - Python automation
- `docs/bots/` - Framework development instructions (this directory)
- `dist/` - Build artifacts (packaged skills)

## Three-Tier Loading System

1. **Framework** (`$ACADEMICOPS/core/`): Universal instructions
2. **Personal** (`$ACADEMICOPS_PERSONAL/core/`): User customizations
3. **Project** (`$PWD/docs/bots/`): Project-specific instructions

All `.md` files support 3-tier stacking when read by agents.

## Maintenance

When adding/moving instruction files:

1. Update `paths.toml` if new directory types needed
2. Update `docs/INSTRUCTION-INDEX.md` with file registry
3. Run `scripts/check_instruction_orphans.py` to verify linkage
4. Document changes in GitHub issue

## Development Workflows

- Testing: `uv run pytest`
- Linting: `pre-commit run --all-files`
- Skill packaging: `scripts/package_skill.sh <skill-name>`
