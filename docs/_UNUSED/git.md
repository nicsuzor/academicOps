

## Git Workflow for Submodule Commits

The bot/ directory is a git submodule. Agent instruction files live in `bot/agents/`.

**CRITICAL**: Bash tool resets to ${ACADEMICOPS_BOT}/` for each separate call. Use `cd` with `&&` chaining in a single command.

**Correct workflow (from bot submodule):**
```bash
cd ${ACADEMICOPS_BOT}/ && git add agents/[filename].md && git commit -m "fix(prompts): [description]

[details]

Fixes #[issue_number]" && git push
```

**Why this works:**
- The `cd` and git commands are chained in ONE bash call
- Working directory change persists within that single call
- All git operations execute in the correct directory

**WRONG (will fail):**
```bash
# ❌ Separate cd doesn't persist:
cd ${ACADEMICOPS_BOT}/
git add agents/[filename].md

# ❌ git -C doesn't work (resets to bot/, bot/ doesn't exist from bot/):
git -C bot add agents/[filename].md
```