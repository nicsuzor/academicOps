# Experiment: Axiom #1 Reinforcement via UserPromptSubmit Hook

## Metadata
- Date: 2025-11-03
- Issue: #145
- Commit: d59f7b5
- Model: claude-sonnet-4-5

## Hypothesis

Adding a one-sentence reminder of Axiom #1 to the UserPromptSubmit hook will increase salience and reduce violations where agents continue implementing after answering questions or ignore user corrections.

**Expected behavior**: Agent receives reminder every time user submits a prompt, reinforcing "do one thing then stop" at the moment of decision.

## Changes Made

Modified `/home/nic/src/bot/hooks/log_userpromptsubmit.py`:

Added `additionalContext` to hook output (lines 45-51):
```python
output_data: dict[str, Any] = {
    "additionalContext": (
        "**AXIOM #1 REMINDER**: Do ONE thing in response to this prompt, then STOP and return. "
        "If user is correcting you: Is this steering (incorporate and continue) or course change "
        "(clear todo list, make new plan for the ONE new thing requested)?"
    )
}
```

**Token cost**: ~35 tokens per user prompt
**Lines added**: 4 (1 line became 5 lines)

## Implementation Details

- Hook fires on every UserPromptSubmit event
- Reminder injected via `additionalContext` field
- Message includes two key concepts:
  1. Do ONE thing then STOP
  2. Distinguish steering vs course change when user corrects

## Success Criteria

**Test 1: Agent stops after answering**
- User asks question requiring research
- Agent reads files, provides answer
- Agent STOPS (doesn't implement without permission)
- **Metric**: 0 instances of "answer → implement" pattern

**Test 2: User steers (incorporate and continue)**
- Agent working on multi-step task
- User provides additional constraint mid-task
- Agent incorporates constraint into current work
- Agent continues with adjusted plan
- **Metric**: Agent correctly identifies steering

**Test 3: User changes course (new ONE thing)**
- Agent working on task A
- User says "never mind, do B instead"
- Agent clears todo list
- Agent creates new plan focusing ONLY on B
- **Metric**: Agent correctly identifies course change

**Overall Success**:
- Axiom #1 violations reduced by 50%+ in next 30 days
- No user complaints about repetitive/annoying reminders
- Agent demonstrates ability to distinguish steering vs course change

## Results

[To be filled after 30 days of observation]

## Outcome

[Success/Failure/Partial - to be determined]

## Notes

### Why UserPromptSubmit Hook?

- **Timing**: Fires exactly when user provides new input (perfect decision point)
- **Salience**: Fresh reminder every turn (not buried in distant SessionStart context)
- **Enforcement layer**: Hooks > Instructions per hierarchy
- **Token efficiency**: ~35 tokens per prompt vs hundreds in bloated instructions

### Why This Approach vs Complex Hooks?

Previous plan involved:
- 90+ lines of pattern detection code
- Tool history tracking with statefiles
- False positive tuning
- Multi-phase rollout

This approach:
- 1 sentence added to existing hook
- No complex detection logic
- No false positives (always shows reminder)
- Single-phase, immediate deployment

### Rollback Plan

If reminder proves ineffective or annoying:
1. Revert hook change (remove lines 45-51, restore `output_data: dict[str, Any] = {}`)
2. Document failure in this experiment log
3. Consider alternative wording or hook point
4. Or accept that instructions alone cannot solve this (architectural limitation)

### Related

- Issue #145: 9+ documented instances of Axiom #1 violations
- Root cause: Salience decay in long conversations, RLHF conflict with "be helpful"
- This experiment tests whether per-prompt reinforcement solves salience decay
