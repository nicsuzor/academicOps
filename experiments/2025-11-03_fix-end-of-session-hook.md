# Fix End-of-Session Hook Integration

## Metadata
- Date: 2025-11-03
- Issue: #184
- Commit: [pending]
- Model: claude-sonnet-4-5-20250929

## Hypothesis
Reverting Stop/SubagentStop hooks from `validate_stop.py` → `request_scribe_stop.py` will restore automatic end-of-session agent invocation after substantial work completion.

## Changes Made

**config/settings.json** (lines 33-54):
- SubagentStop hook: `validate_stop.py` → `request_scribe_stop.py`
- Stop hook: `validate_stop.py` → `request_scribe_stop.py`
- Removed `SubagentStop`/`Stop` arguments (request_scribe_stop uses same logic for both)
- Changed fallback from `{\"continue\":true}` → `{}` (matches original pattern)

**hooks/log_userpromptsubmit.py** (line 23):
- Fixed state flag naming mismatch
- Was: `claude_scribe_requested_{session_id}.flag`
- Now: `claude_end_of_session_requested_{session_id}.flag`
- Matches flag name used by request_scribe_stop.py:31

## Root Causes Addressed

**Regression #1 - Wrong Stop hook (commit f03088b, Oct 31)**:
- Hook path resolution experiment inadvertently replaced functional Stop hook
- `validate_stop.py` only logs transitions (placeholder for future workflow chaining)
- `request_scribe_stop.py` actually blocks Stop and requests end-of-session invocation
- No design rationale documented for the switch

**Regression #2 - State flag naming mismatch (original bug)**:
- `request_scribe_stop.py` creates: `claude_end_of_session_requested_{session_id}.flag`
- `log_userpromptsubmit.py` cleaned up: `claude_scribe_requested_{session_id}.flag`
- Flags never cleaned up → Stop hook would only work once per boot
- Likely never tested in practice (hook wasn't configured until now)

**Original design (Oct 28-29)**:
- Created `request_scribe_stop.py` to invoke end-of-session agent
- Created `end-of-session.md` agent for automated commits/scribe/task updates
- System worked briefly before path resolution experiment broke it

## Success Criteria

- ✅ Stop hook blocks after substantial work
- ✅ Agent receives instruction to invoke end-of-session subagent
- ✅ end-of-session agent commits changes, invokes scribe, updates tasks
- ✅ No infinite loops (request_scribe_stop has state tracking via /tmp flag files)
- ✅ UserPromptSubmit hook cleans up state on new user interaction

## Results

**Testing Required**: User must complete substantial work in new session to verify:
1. Stop hook blocks with instruction to invoke end-of-session
2. Agent invokes end-of-session subagent
3. Commits are created automatically
4. Scribe captures context to accomplishments.md
5. Second Stop event allowed (after end-of-session completes)

**Technical validation complete**:
- ✅ Hook paths correct (`$ACADEMICOPS/hooks/request_scribe_stop.py`)
- ✅ State tracking implemented (/tmp flag files per session)
- ✅ Infinite loop prevention via flag existence check
- ✅ Cleanup on UserPromptSubmit (log_userpromptsubmit.py clears flags)

## Outcome

**Partial** - Configuration fix complete, awaiting user testing in production session.

**Expected behavior**:
- User completes substantial work (code changes, task completion, etc.)
- User attempts to stop session
- Stop hook blocks: "If this marks the end of substantial chunk of work..."
- Agent invokes: `Task(subagent_type='end-of-session', prompt='[work description]')`
- end-of-session agent commits changes and invokes scribe
- Agent can then stop normally
