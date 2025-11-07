# Experiment: Fix task_process.py Regex Bug + Add Tool Failure Protocol

## Metadata

- **Date**: 2025-10-24
- **Issue**: #155
- **Commit**: da5e675fcf2a50f359de12b94a8fcf5e6775c944
- **Model**: claude-sonnet-4-5-20250929
- **Agent**: trainer

## Problem Context

**Agent behavior**: Tried 4 workarounds when `task_process.py` failed, violating Axiom #7 (Fail-Fast: No Workarounds).

**Root cause**: SCRIPT BUG, not just agent behavior.

## Bug Details

**File**: `.claude/skills/task-management/scripts/task_process.py` line 87

**Broken regex**:

```python
task_id_pattern = re.compile(r"^\d{8}-[0-9a-fA-F]{8}$")
# Expected: YYYYMMDD-XXXXXXXX
```

**Actual format** (from `task_add.py` line 52):

```python
task_id = f"{timestamp}-{hostname}-{task_uuid}"
# Example: 20250929-004918-nicwin-7ce2c06b
# Format: YYYYMMDD-HHMMSS-hostname-uuid
```

**Mismatch**: Regex only matches `YYYYMMDD-XXXXXXXX` but actual IDs are `YYYYMMDD-HHMMSS-hostname-uuid`.

## Changes Made

### Part 1: Fix Script Bug (Priority 1)

**File**: `.claude/skills/task-management/scripts/task_process.py`

**Changes**:

1. **Removed redundant regex validation** (lines 87-98 deleted)
2. **Removed `re` import** (no longer needed)
3. **Updated docstring** to document actual format: `YYYYMMDD-HHMMSS-hostname-uuid`

**Rationale**:

- `_find_task_by_id()` already searches for matching files (validation by existence)
- Regex check was redundant and incorrect
- DRY principle - don't duplicate validation
- Simpler code, more flexible (handles any ID format automatically)

**Before**:

```python
import re
...
task_id_pattern = re.compile(r"^\d{8}-[0-9a-fA-F]{8}$")
local_task = _find_task_by_id(task_id)

if not local_task and not task_id_pattern.match(str(task_id) or ""):
    print_json({"error": "invalid_task_id", ...})
    return {}

if not local_task:
    print_json({"error": "task_not_found", ...})
    return {}
```

**After**:

```python
# No re import needed
...
# Find the local task by searching for matching file
# No need for regex validation - file search is the validation
local_task = _find_task_by_id(task_id)

if not local_task:
    print_json({"error": "task_not_found", ...})
    return {}
```

### Part 2: Add Tool Failure Protocol (Priority 2)

**File**: `bots/agents/_CORE.md`

**Added**: "Tool Failure Protocol" section (~35 lines) after Behavioral Rules

**Content**:

- **1 retry maximum** when tool fails
- **Stop after 2nd failure** and report
- **NEVER** try 3+ variations
- **Example** of correct fail-fast response
- References existing rules (12b NO WORKAROUNDS, Axiom #8)

**Placement**: After "Error Handling" line 70, before "Key tools" section

## Hypothesis

**Part 1 (Script)**: Removing regex validation will allow `task_process.py` to accept actual task IDs from `current_view.json`.

**Part 2 (Behavior)**: Explicit Tool Failure Protocol will prevent agents from trying 3+ workarounds, stopping after 2nd failure instead.

## Success Criteria

**Part 1 - Script Fix**:

- [ ] `task_process.py` accepts IDs like `20250929-004918-nicwin-7ce2c06b`
- [ ] Archive command works with task IDs from `current_view.json`
- [ ] No false "invalid_task_id" errors
- [ ] Only get "task_not_found" if file doesn't exist

**Part 2 - Agent Behavior**:

- [ ] Agent stops after 2nd tool failure (not 3rd or 4th)
- [ ] Agent reports error message and hypothesis
- [ ] Agent asks user how to proceed
- [ ] No more defensive "let me explore filesystem" behavior

**Test Scenario**:

1. Give agent a task ID from real `current_view.json` (format: YYYYMMDD-HHMMSS-hostname-uuid)
2. Request archive
3. Should succeed (script accepts format)
4. If script fails for different reason, agent should stop after 2nd attempt

## Results

(To be filled after testing in real usage)

### Test 1: Script Fix Validation

- Date:
- Task ID tested:
- Outcome:

### Test 2: Agent Behavior (Tool Failure)

- Date:
- Scenario:
- Number of attempts before stopping:
- Outcome:

## Outcome

(To be marked after validation)

Options:

- **Success**: Script accepts real IDs + Agent stops after 2 failures
- **Partial**: One part works, other needs iteration
- **Failure**: Neither fix effective

## Next Steps

(To be determined based on outcome)

If script still fails:

- Check if `_find_task_by_id()` has other issues
- Verify task file search logic

If agent behavior persists:

- Consider adding PostToolUse hook to detect 3+ failures
- Track in separate issue
- May need stronger enforcement mechanism

## Related Issues

- #152 - Task management accomplishments boundary (related skill)
- #145 - Agent ignores explicit instruction, continues defensive coding
- #143 - Agent violated fail-fast by deleting file
