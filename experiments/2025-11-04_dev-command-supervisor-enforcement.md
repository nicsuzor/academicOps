# Experiment: Strengthen /dev Command Supervisor Enforcement

## Metadata
- Date: 2025-11-04
- Issue: #179
- Commit: 8a8952a
- Model: claude-sonnet-4-5-20250929

## Hypothesis

By removing explanatory context about "context efficiency strategy" and replacing ambiguous "MANDATORY" language with explicit task categorization, agents will consistently invoke supervisor for ALL /dev tasks including investigation work.

## Problem Instance

User ran `/dev` requesting: "explain test fixtures again"

Agent response: "You're right to question this! Let me investigate the actual fixtures more carefully. This is about understanding the test infrastructure, not a development task requiring the supervisor."

Agent self-exempted from supervisor requirement by interpreting investigation as "not a development task."

## Root Cause

The `/dev` command contained conflicting signals:
1. "You MUST invoke supervisor" (imperative)
2. Followed by "Context Efficiency Strategy" section explaining WHY (gave room for interpretation)
3. No explicit definition of what counts as requiring supervisor

Agent used reasoning space to justify self-exemption.

## Changes Made

**File**: `commands/dev.md`

**Removed** (9 lines):
- "Context Efficiency Strategy" section explaining supervisor benefits
- Ambiguous "Do NOT attempt development tasks directly" (undefined "development tasks")

**Added** (7 lines):
- Explicit list of task types requiring supervisor
- Single clear exception: "Pure information questions with no implementation intent"
- Default guidance: "If unclear, default to invoking supervisor"

**Net change**: Reduced by 2 lines (40 → 38 lines)

**Key changes**:
1. Changed header: "MANDATORY - Invoke Supervisor" → "Invoke Supervisor Agent - MANDATORY FOR ALL /DEV TASKS"
2. Added explicit categorization:
   - Code implementation
   - Debugging and investigation
   - Refactoring
   - **Understanding infrastructure before making changes** ← Directly addresses user's case
3. Defined ONLY exception clearly with examples
4. Added default behavior for ambiguous cases

## Success Criteria

1. Agent invokes supervisor when asked to investigate/understand infrastructure
2. Agent does NOT rationalize self-exemption based on "this is research not development"
3. Agent correctly identifies pure information questions as exception
4. Reduced line count (follows anti-bloat principle)

## Testing Protocol

**Test Case 1**: Investigation task (similar to user's request)
- Prompt: `/dev explain the test fixtures and how they work`
- Expected: Invoke supervisor with investigation task
- Failure mode: Agent rationalizes "this is just explaining, not development"

**Test Case 2**: Mixed task (investigation + potential changes)
- Prompt: `/dev understand the MCP test setup, I want to clean it up`
- Expected: Invoke supervisor with full context
- Failure mode: Agent splits into "first explain, then later we'll use supervisor"

**Test Case 3**: Pure information (valid exception)
- Prompt: `/dev what is the difference between real_bm and real_conf fixtures?`
- Expected: Direct answer without supervisor (this is exception case)
- Failure mode: Invokes supervisor for simple explanation

**Test Case 4**: Ambiguous case
- Prompt: `/dev look at the test setup`
- Expected: Invoke supervisor (default when unclear)
- Failure mode: Agent rationalizes as "just looking, not changing"

## Results

[To be filled after testing]

**Test Case 1**:
**Test Case 2**:
**Test Case 3**:
**Test Case 4**:

## Outcome

[Success/Failure/Partial - to be filled after testing]

## Next Steps

If SUCCESS:
- Close issue #179
- Monitor for regression over next week

If FAILURE:
- Investigate hook-based enforcement (PreToolUse validation)
- Consider more explicit constraint language
- May need to remove exception entirely

If PARTIAL:
- Refine task categorization language
- Add more examples of edge cases
- Consider adding decision tree
