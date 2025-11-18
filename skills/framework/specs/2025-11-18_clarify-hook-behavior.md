# Task Spec: Clarify Hook "Blocking Error" Messages

**Created**: 2025-11-18
**Status**: Approved
**Priority**: P2 - Documentation Clarity
**Pattern**: #hooks #user-experience #documentation

## Problem Statement

PostToolUse:TodoWrite hook displays "blocking error" messages that appear like failures but are actually intentional behavior. This creates confusion about whether the framework is broken.

**Example message**:
```
PostToolUse:TodoWrite hook blocking error from command:
"PYTHONPATH=$AOPS uv run --no-project python $AOPS/hooks/request_scribe.py":
[AOPS Framework Reminder: If this marks the end of a substantial chunk of work...]
```

**Actual behavior**:
- Hook successfully executes ✅
- Hook intentionally blocks to deliver reminder message ✅
- Message format makes it look like an error ❌

**User impact**:
- User thinks framework is failing when it's working correctly
- "Blocking error" language implies something went wrong
- Requested framework review based on perceived errors

## Architecture Context

**How request_scribe.py works** (by design):
1. PostToolUse:TodoWrite event triggers hook
2. Hook checks if documentation already requested this session
3. If first trigger: Blocks execution, displays reminder to document
4. If subsequent trigger: Allows execution (already reminded)
5. State flag cleared by UserPromptSubmit hook for next turn

**Exit codes**:
- `0` = Success (always returns 0, whether blocking or allowing)
- Blocking = intentional behavior, not error condition

**The hook is working correctly** - the issue is presentation language.

## Scope

### In Scope
1. Update hooks/README.md to explain "blocking" vs "error" distinction
2. Add section documenting request_scribe.py blocking behavior as intentional
3. Consider renaming displayed message from "blocking error" to "blocking reminder"
4. Add troubleshooting section: "When 'errors' are actually working correctly"
5. Update framework SKILL.md debugging workflow to distinguish blocking vs failures

### Out of Scope
- Changing hook blocking behavior (working as designed)
- Modifying hook execution messages (may be Claude Code system messages)
- Removing blocking functionality (intentional design)
- Creating new hooks or modifying hook logic

## Success Criteria

**Functional Requirements**:
1. Users understand blocking messages are intentional, not errors
2. Documentation clearly explains when hooks block vs when they fail
3. Troubleshooting guide helps distinguish working behavior from actual failures

**Documentation Requirements**:

Add to hooks/README.md:
```markdown
## Understanding Hook Blocking Behavior

### "Blocking Error" vs Actual Errors

**IMPORTANT**: Messages like "PostToolUse:TodoWrite hook blocking error" are
**NOT errors** - they indicate the hook is working correctly.

**What "blocking" means**:
- Hook intercepts execution to deliver a reminder message
- Agent receives the message and can act on it
- Execution continues normally after message delivered
- This is intentional behavior, not a failure

**Example of correct blocking behavior**:
```
PostToolUse:TodoWrite hook blocking error from command:
"PYTHONPATH=$AOPS uv run --no-project python $AOPS/hooks/request_scribe.py":
[AOPS Framework Reminder: If this marks the end of a substantial chunk of work,
use the bmem skill to document key decisions and outcomes.]
```

This is the hook successfully:
1. ✅ Detecting TodoWrite event
2. ✅ Executing request_scribe.py
3. ✅ Blocking to deliver reminder
4. ✅ Returning success (exit code 0)

**Actual hook errors look different**:
- Exit code non-zero
- Exception traceback in stderr
- Hook fails to execute at all
- Missing hook file or broken configuration

### request_scribe.py Hook

**Purpose**: Remind agent to document work at appropriate checkpoints

**Triggers on**:
- Stop/SubagentStop events (agent pausing)
- PostToolUse:TodoWrite (task planning captured)

**Behavior**:
- First trigger: Blocks with reminder message
- Creates state flag: `/tmp/claude_end_of_session_requested_{session_id}.flag`
- Subsequent triggers: Allows (already reminded)
- UserPromptSubmit hook clears flag for next turn

**This is not an error** - it's the hook working as designed.

## Troubleshooting

### "My TodoWrite hook shows blocking errors"

✅ **This is correct behavior**. The hook is reminding you to document your work.

**What to do**:
1. Acknowledge the reminder
2. If work substantial: Invoke bmem skill to document
3. If work minor: Continue (reminder delivered, can proceed)

### "How do I know if a hook actually failed?"

**Signs of actual hook failure**:
- Non-zero exit code
- Python exception traceback
- "Hook not found" or "Permission denied" errors
- Hook doesn't execute at all

**Signs of working hook that blocks**:
- Exit code 0
- Clean reminder message in brackets
- Hook completes and returns success
```

Update framework/SKILL.md debugging workflow:
```markdown
### Debugging Hook Issues

**First: Is this actually an error?**

"Blocking error" messages are often correct behavior:
- request_scribe.py blocks to remind about documentation
- This is intentional, not a failure
- See hooks/README.md for "blocking vs error" explanation

**Actual hook failures**:
- Non-zero exit codes
- Exception tracebacks
- Missing files or broken configuration
```

**Testing Strategy**:
- Review with user: Does documentation clarify confusion?
- Test: Can reader distinguish blocking (working) from failure?

## Implementation Notes

**Key messaging**:
1. "Blocking" ≠ "Error" (unfortunate terminology collision)
2. Exit code 0 = success, even when blocking
3. request_scribe.py blocking is intentional design
4. Provide clear indicators of actual failures vs working blocks

**Documentation improvements**:
- Hooks README: Add "Understanding Blocking" section at top
- Framework SKILL debugging: Reference hooks README for blocking explanation
- Consider adding visual indicators (✅ Working / ❌ Failing)

## Dependencies

**Blocks**: None (documentation only)

**Blocked By**: None

**Related**: User experience improvements for hook messages

## Risks

**Very Low Risk**: Documentation clarification only

**Potential improvement**: If Claude Code hook system allows custom message formatting,
could change "blocking error" to "blocking reminder" - but this may not be possible
(system-generated message format).

## Success Metrics

- User understands "blocking error" messages are correct behavior
- Future framework reviews distinguish working blocks from actual failures
- Hooks README clearly explains blocking vs error distinction
- Zero confusion about request_scribe.py blocking messages
