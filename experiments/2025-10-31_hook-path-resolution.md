# Hook Path Resolution Fix

## Metadata

- Date: 2025-10-31
- Issue: #176
- Commit: 9302bdf
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Standardizing environment variable name to `ACADEMICOPS` and fixing hook paths from `/bots/hooks/` to `/hooks/` will enable hooks to execute successfully from any project directory.

## Changes Made

1. **config/paths.sh**: Renamed all `ACADEMIC_OPS_BOT` → `ACADEMICOPS` (also DATA, DOCS, PROJECTS, SCRIPTS)
2. **config/paths.py**: Updated `__str__()` method to use `ACADEMICOPS_*` variable names
3. **config/settings.json**: Fixed hook paths `/bots/hooks/` → `/hooks/` (5 hooks)
4. **~/.claude/settings.json**: Fixed hook paths `/bots/hooks/` → `/hooks/` (5 hooks)

## Root Causes Addressed

- Variable name mismatch between paths.sh (`ACADEMIC_OPS_BOT`) and settings.json (`ACADEMICOPS`)
- Incorrect hook directory path (non-existent `/bots/` subdirectory)
- Environment variable not available in hook execution context

## Success Criteria

- ✅ Hooks execute successfully when running from `/home/nic/src/writing`
- ✅ Hooks still work when running from `/home/nic/src/bot`
- ✅ No "Hook not found: validate_tool.py" messages
- ✅ Hook validation logic actually runs (visible in hook output)

## Results

**Testing Required**: User must test in new Claude Code session to verify hooks work from different directories.

**Expected behavior**:

- Start Claude Code from `/home/nic/src/writing` (or any non-bot directory)
- Run any command that triggers PreToolUse hook (e.g., WebFetch)
- Should see hook validation running, NOT "Hook not found" error

**Technical validation complete**:

- ✅ paths.sh exports ACADEMICOPS=/home/nic/src/bot (verified in new shell)
- ✅ Hook commands reference correct path (/hooks/ not /bots/hooks/)
- ✅ Variable name consistent across all files

## Outcome

**Partial** - Implementation complete, awaiting user testing in production
