# Experiment: Auto-commit Task Database Changes via PostToolUse Hook

## Metadata

- **Date**: 2025-11-03
- **Issue**: #185 (task-manager: Missing git commit/push enforcement after task operations)
- **Related Issues**: #27 (Critical: Agents must commit changes immediately)
- **Commit**: TBD
- **Model**: claude-sonnet-4-5

## Hypothesis

A PostToolUse hook that automatically commits task database changes after task script execution will prevent data loss and eliminate the need for agents to remember to commit changes (moving from instruction-based to hook-based enforcement).

## Problem

task-manager agent doesn't commit/push changes to `$ACADEMICOPS_PERSONAL/data/tasks/` after creating/modifying tasks. This violates data integrity principles and risks data loss.

**Root cause**: Relying on instructions (weakest enforcement tier) rather than automated enforcement.

## Changes Made

### 1. Created autocommit_tasks.py hook

**File**: `bot/hooks/autocommit_tasks.py`

**Functionality**:

- Detects Bash tool calls to task scripts (task_add.py, task_process.py, etc.)
- Checks for uncommitted changes in `data/tasks/`
- Auto-commits and pushes if changes detected
- Provides system message to inform user

**Design decisions**:

- Timeout: 35s (allows for network latency on push)
- Non-blocking: Errors logged but don't stop workflow
- Specific detection: Only triggers on task script patterns
- Scoped commits: Only `git add data/tasks/` (not entire repo)

### 2. Added hook to PostToolUse chain

**File**: `.claude/settings.json`

Added after existing log_posttooluse.py hook in PostToolUse array.

### 3. Made hook executable

```bash
chmod +x bot/hooks/autocommit_tasks.py
```

## Enforcement Hierarchy Justification

**Q1 (Scripts)**: Can automate commits? → YES (PostToolUse hook) **Q2 (Hooks)**: Can enforce at key moments? → YES (after task operations) **Q3 (Config)**: N/A **Q4 (Instructions)**: Currently using → REPLACED with hook

**Decision**: PostToolUse hook (automated enforcement) superior to instructions (agent memory).

## Success Criteria

- [ ] task-manager creates task → automatic commit triggered
- [ ] task-manager modifies task → automatic commit triggered
- [ ] scribe archives task → automatic commit triggered
- [ ] strategist views tasks → NO commit (read-only operation)
- [ ] User sees system message confirming auto-commit
- [ ] Changes pushed to remote successfully
- [ ] No false positives (commits when no changes)
- [ ] Hook doesn't block workflow on errors

## Test Plan

1. **Baseline**: Verify current state (no auto-commit)
2. **Create task**: Use task-manager or scribe to create new task
3. **Verify commit**: Check git log for auto-commit message
4. **Verify push**: Check remote repo has commit
5. **Modify task**: Update existing task priority/due date
6. **Verify commit**: Check git log for second auto-commit
7. **Archive task**: Complete and archive a task
8. **Verify commit**: Check git log for third auto-commit
9. **Read-only**: Run task_view.py manually
10. **Verify no commit**: Should not trigger commit
11. **Error handling**: Simulate git push failure (disconnect network)
12. **Verify graceful**: Hook logs error but doesn't block workflow

## Results

[To be filled after testing]

## Outcome

[Success/Failure/Partial - to be determined]

## Follow-up Actions

- [ ] Test with task-manager agent
- [ ] Test with scribe skill
- [ ] Test with strategist agent
- [ ] Monitor for false positives over 1 week
- [ ] Document in best practices if successful
- [ ] Update GitHub issue #185 with results
- [ ] Close issue #27 if this addresses the broader pattern

## Rollback Plan

If hook causes issues:

1. Edit `.claude/settings.json`
2. Remove autocommit_tasks.py entry from PostToolUse hooks array
3. Restart Claude Code
4. Document failure reason in this experiment log
5. Revert to instruction-based approach (weaker but known working)
