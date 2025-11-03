# Stop Hook: Suppress Reminder on AskUserQuestion

## Metadata
- Date: 2025-11-03
- Issue: #188
- Commit: 78533dd595ea8ea899380e13d466b0840a51cca4
- Model: claude-sonnet-4-5

## Hypothesis

When agent uses `AskUserQuestion` to legitimately ask user for input, the Stop hook's conditional reminder is misinterpreted as permission to proceed without waiting for answer.

**Expected behavior after fix**: Hook detects `AskUserQuestion` in last 1-2 assistant messages and suppresses reminder, allowing stop cleanly.

## Changes Made

Modified `/home/nic/src/bot/hooks/request_scribe_stop.py`:

1. Added `has_recent_ask_user_question()` function to read transcript and detect AskUserQuestion tool use
2. Modified `main()` to check for AskUserQuestion before showing reminder
3. If detected, allow stop without reminder (return `{}`)
4. Otherwise, proceed with existing conditional reminder logic

**Implementation details**:
- Reads transcript JSONL file line by line
- Collects all assistant messages
- Checks last 2 messages for `AskUserQuestion` tool_use blocks
- Fails open (doesn't suppress) on error to prevent breaking hook

## Success Criteria

**Test 1: Agent asks question**
- Agent uses `AskUserQuestion` tool
- Stop hook fires
- Hook detects AskUserQuestion in transcript
- Hook allows stop without reminder
- Agent waits for user response (doesn't proceed)

**Test 2: Agent completes work**
- Agent completes substantial work without asking question
- Stop hook fires
- Hook does NOT detect AskUserQuestion
- Hook blocks with conditional reminder
- Agent invokes end-of-session subagent (if appropriate)

**Test 3: Agent in mid-conversation**
- Agent in middle of interactive conversation
- Stop hook fires
- Hook does NOT detect AskUserQuestion
- Hook blocks with conditional reminder
- Agent reads "not during interactive conversation" and doesn't invoke end-of-session

## Results

[To be filled after testing]

## Outcome

[Success/Failure/Partial]

## Notes

- Edge case handled: If agent asked question 5 turns ago but continued work, reminder is still shown (only check last 2 messages)
- Fail-safe: On transcript read error, hook doesn't suppress (shows reminder as usual)
- Architectural correctness: Hook layer solution (Q2) rather than instruction layer (Q4)
