# Experiment: Failed to Answer Direct Question - Launched Into Solutions

**Date**: 2025-10-20 **Commit**: (buttermilk project work) **Issue**: #132 **Agent**: General agent (no specific agent active)

## Hypothesis

User asked "what makes you think it's not working?" expecting a direct answer pointing to the error message.

## Implementation

Agent instead:

1. Went down rabbit hole trying Hydra syntax variations
2. Created GitHub issue #276 prematurely
3. Attempted to "fix" Makefile during user's config refactor
4. Ignored user correction: "it looks like it's working"
5. Failed to recognize work-in-progress state

## Violations

### Failed to Answer Direct Questions Directly

- **Location**: _CORE.md Axiom 4 "NO EXCUSES"
- **Violation**: User asked "why do you think it's not working" → Agent launched into configuration archaeology instead of pointing at error message
- **Expected**: Simple answer: "The error shows 'Flow 'trans' not found. Available flows: []' - flows aren't loading"

### Didn't Listen to User Corrections

- **Location**: _CORE.md line 21 "STOP WHEN INTERRUPTED"
- **Violation**: User said "it looks like it's working" → Agent continued trying to fix non-existent problem
- **Expected**: Re-evaluate entire approach immediately

### Premature Action / Issue Creation

- **Location**: Related to #52, #124 (declaring victory/acting without understanding)
- **Violation**: Created GitHub issue without understanding full context (user mid-refactor)
- **Expected**: Ask clarifying questions first, understand transitional state

### Failed to Recognize Work-in-Progress

- **Violation**: Makefile syntax is "aspirationally correct" for planned config structure
- **Expected**: Ask "are you migrating configs?" before trying to "fix" working code

## Outcome

**FAILED**

- Wasted user time with solutions to non-problems
- Created noise in project issue tracker (#276)
- Didn't help with actual debugging need

## Lessons

### For _CORE.md Enforcement

**CRITICAL ADDITION NEEDED**: "Answer questions directly FIRST, then investigate"

Proposed addition to _CORE.md after line 22 "VERIFY FIRST":

```markdown
4. **ANSWER DIRECT QUESTIONS DIRECTLY**
   - When user asks "why do you think X?", point to the evidence immediately
   - THEN investigate deeper if needed
   - Never launch into solutions before answering the question asked
```

### For All Agent Instructions

**Pattern to prevent**:

- User asks question → Agent ignores question and tries to solve problem
- User corrects → Agent doesn't re-evaluate

**Pattern to enforce**:

- User asks question → Agent answers with evidence
- User corrects → Agent stops immediately, re-evaluates entire approach
- Transitional/WIP state → Ask before "fixing"

### For /log-failure Command

**REMOVE** repository verification step (lines 15-22).

**Rationale**:

- Agents know their repository from git context
- _CORE.md already has repository structure
- Verification blocked `/log-failure` from working in buttermilk
- Creates friction for legitimate use case

## Related Issues

- #52: Developer agent declares victory with failing tests
- #124: Agent declares victory without completing requested work
- #125: Agent ignores instructions

Similar pattern: Acting without listening/understanding context

## Modified Files

- experiments/2025-10-20_failed-to-answer-direct-question.md (created)
- experiments/INDEX.md (pending update)
- .claude/commands/log-failure.md (needs fix - remove repo verification)
- agents/_CORE.md (needs addition - direct answer axiom)
