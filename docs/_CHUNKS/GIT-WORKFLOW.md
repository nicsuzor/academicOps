# Git Workflow

**Context:** The `bot/` directory is a git submodule in polyrepo setups.

## Submodule Commit Pattern

**CRITICAL:** Bash tool resets working directory for each separate call. Chain commands with `&&` in ONE call.

### ✅ Correct (Single Command Chain)

```bash
cd /path/to/bot && git add file.md && git commit -m "fix(prompts): description

Details here.

Fixes #123" && git push
```

**Why this works:**

- `cd` and git commands chained in ONE bash call
- Working directory change persists within that call
- All git operations execute in correct directory

### ❌ Wrong (Separate Calls)

```bash
# Separate cd doesn't persist:
cd /path/to/bot
git add file.md    # ← Executes in wrong directory!

# git -C doesn't work from within submodule:
git -C bot add file.md
```

## Conventional Commits

**Format:**

```
<type>(<scope>): <subject>

<body>

Fixes #<issue>
```

**Types:**

- `fix` - Bug fixes
- `feat` - New features
- `docs` - Documentation changes
- `refactor` - Code restructuring
- `test` - Test additions/changes
- `chore` - Maintenance tasks

**Scopes (for bot/ repo):**

- `prompts` - Agent instruction changes
- `infrastructure` - Scripts, hooks, configs
- `docs` - Documentation files

## Examples

```bash
# Agent instruction update
git commit -m "fix(prompts): Clarify TTD workflow in developer agent

Added explicit test-first requirement.

Fixes #45"

# Infrastructure change
git commit -m "feat(infrastructure): Add validation hook for tool usage

Implements PreToolUse hook to enforce agent permissions.

Fixes #78"
```
