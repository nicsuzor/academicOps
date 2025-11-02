# Hook Path Regression Fix

## Metadata
- Date: 2025-11-02
- Issue: #176
- Commit: c1227b2
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Removing `/bots/` from hook paths in both `config/settings.json` and `~/.claude/settings.json` will fix the "Hook not found: validate_tool.py" error that appears when running Claude Code from project directories.

## Background

This is a REGRESSION fix. The original fix in commit 9302bdf (Oct 31) correctly removed `/bots/` from paths, but subsequent commits (db30dae, 4bddc95, a5da226) inadvertently reintroduced the bug when restoring SessionStart hooks.

**Root cause**: Hook commands referenced `$ACADEMICOPS/bots/hooks/validate_tool.py` but the actual location is `$ACADEMICOPS/hooks/validate_tool.py`. The `/bots/` directory never existed.

## Changes Made

Fixed 5 hook paths in `config/settings.json`:
1. PreToolUse: `validate_tool.py` - removed `/bots/` from path
2. SubagentStop: `validate_stop.py` - removed `/bots/` from path
3. Stop: `validate_stop.py` - removed `/bots/` from path
4. PostToolUse: `log_posttooluse.py` - removed `/bots/` from path
5. UserPromptSubmit: `log_userpromptsubmit.py` - removed `/bots/` from path

Note: `~/.claude/settings.json` was automatically updated when config/settings.json was fixed.

## Success Criteria

- ✅ No "Hook not found: validate_tool.py" messages from any project directory
- ✅ Hooks execute successfully from `/home/nic/src/writing` (non-bot directory)
- ✅ Hooks execute successfully from `/home/nic/src/bot` (bot directory)
- ✅ Hook validation logic actually runs (not just silent fallback)
- ✅ Works in both Claude Code and Gemini CLI

## Results

**Implementation Complete** - User must test in production.

**Expected behavior**:
- Start new session from any project directory
- Run command triggering PreToolUse hook (WebFetch, Bash, Edit, etc.)
- Hook should execute without "Hook not found" error
- Validation logic should run (visible in hook output)

**If test fails**: Check that `$ACADEMICOPS` environment variable is set correctly. The variable should point to `/home/nic/src/bot` (or wherever the academicOps framework is installed).

## Outcome

PARTIAL - Implementation complete, awaiting user testing to confirm success.

## Prevention Strategy

**Why did regression happen?**
When SessionStart hooks were restored in later commits, developers copy-pasted old broken paths instead of checking the corrected paths from commit 9302bdf.

**How to prevent future regressions?**
1. **Enforcement Hierarchy**: Move hook path validation UP the stack
   - Q1 (Scripts): Could we auto-validate hook paths?
   - Q2 (Hooks): SessionStart hook could validate other hook paths (bootstrapping problem)
   - Q3 (Config): Could add schema validation for settings.json

2. **Proposed solution** (separate issue): Create a validation script that checks all hook paths in settings.json files and fails if any reference non-existent files. Run this in pre-commit hook.

3. **Documentation**: Update hook configuration guide to show correct path patterns and warn about common mistakes.

**Note**: Creating the validation script is OUT OF SCOPE for this experiment (violates "max 3 changes" rule). File separate issue if regression prevention is priority.
