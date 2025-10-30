# Supervisor Tight Orchestration Experiment

## Metadata
- Date: 2025-10-30
- Issue: Related to #149 (test-writing not invoked), #126 (code-review not invoked), #52 (premature victory)
- Commit: 83087da
- Model: claude-sonnet-4-5

## Hypothesis

Adding explicit tight orchestration instructions to SUPERVISOR.md will enable the supervisor to:
1. Maintain strict TDD discipline through complete development sessions
2. Delegate atomic tasks to dev subagent with mandatory skill usage
3. Enforce quality gates at every step (plan review, test creation, code review)
4. Iterate systematically when tests fail instead of asking user

**Key insight**: Supervisor must be DIRECTIVE, not suggestive. It ENFORCES workflows by giving dev subagent tightly constrained single-step instructions and requiring skill usage.

## Problem Evidence

User scenario: Supervisor orchestrating feature development
- Unit tests: 5/5 passed (but used mocks - violation)
- Integration tests: 2/4 failed (real system)
- Supervisor asked user what to do instead of continuing TDD cycles

**Failures**:
1. Supervisor didn't REQUIRE dev subagent to use test-writing skill
2. Supervisor didn't ENFORCE TDD methodology (one thing at a time)
3. Supervisor didn't know how to handle test failures systematically
4. Mocked tests reached commits (violates framework standards)

## Root Causes

1. **Authority boundary confusion** - Instructions say "invoke test-writing skill/subagent" but don't mandate it's REQUIRED
2. **Missing test failure recovery protocol** - No systematic "tests failed, now iterate" workflow
3. **Weak orchestration guidance** - Doesn't explicitly state supervisor's role as ENFORCER giving atomic instructions
4. **Unclear skill enforcement** - Doesn't tell supervisor to REQUIRE dev to use specific skills

## Changes Made

### SUPERVISOR.md Changes

**1. New mandatory TDD workflow at top** (replaces existing scattered guidance):
- Checklist format for each step
- Explicit enforcement language ("REQUIRE", "ENFORCE", "MANDATE")
- Clear iteration protocol when tests fail
- Atomic task delegation pattern

**2. Tight control emphasis**:
- "You TIGHTLY CONTROL what developer does"
- "Give developer ONE STEP at a time"
- "REQUIRE developer to use appropriate skill"
- "Developer reports back after each step"

**3. Quality gates restructured**:
- Mandatory planning step
- Mandatory plan review step (second pass)
- Mandatory quality check after implementation
- Commit step with fix iteration if quality check fails

**4. Test failure handling**:
- Explicit iteration protocol
- "NEVER ask user what to do - YOU decide and iterate"
- Specific instructions for invoking dev with fix requirements

### DEVELOPER.md Changes

**5. Added supervisor reporting protocol**:
- When working under supervisor, report back after completing each atomic task
- Include what was done, results, and wait for next instruction

## Success Criteria

**Scenario**: Ask supervisor to implement a feature using TDD

**Must observe**:
- [ ] Supervisor creates initial plan
- [ ] Supervisor invokes second planning review
- [ ] Supervisor instructs dev: "Use test-writing skill to create ONE failing test for [specific behavior]"
- [ ] Dev creates test using test-writing skill (real fixtures, no mocking)
- [ ] Dev reports back to supervisor
- [ ] Supervisor verifies test fails correctly
- [ ] Supervisor instructs dev: "Implement MINIMAL code to pass this ONE test in [file]"
- [ ] Dev implements, reports back
- [ ] Supervisor runs tests
- [ ] If tests fail: Supervisor instructs dev with specific fix (NO asking user)
- [ ] Supervisor iterates until tests pass
- [ ] Supervisor instructs dev: "Use git-commit skill to validate and commit"
- [ ] Cycle repeats for next feature increment

**Must NOT observe**:
- [ ] Dev creating tests without test-writing skill
- [ ] Mocked internal code in tests
- [ ] Supervisor asking user "should I fix or are failures acceptable?"
- [ ] Batch changes (multiple features before commit)
- [ ] Supervisor writing code itself

## Test Plan

**Test 1: Simple feature addition**
- Request: "Add [small feature] using TDD"
- Verify: Full cycle observed with tight supervision

**Test 2: Implementation with failing tests**
- Request: "Implement [feature that will have test failures]"
- Verify: Supervisor iterates with dev, doesn't ask user

**Test 3: Multi-step feature**
- Request: "Build [feature requiring 3+ TDD cycles]"
- Verify: Supervisor maintains discipline through all cycles, commits atomically

## Results

[To be filled after testing]

**Metrics to track**:
- Times supervisor delegated vs did work itself: [X delegated / Y self]
- Times test-writing skill invoked for tests: [X of X test creations]
- Times supervisor asked user vs decided: [X asked / Y decided]
- Test failures resolved through iteration: [X of X resolved]
- Commits with mocked internal code: [X] (target: 0)

## Outcome

[Success/Failure/Partial - to be determined after testing]

## Notes

- Skipped hook implementation for now (uncertain if PreToolUse can detect skill context)
- Focus on behavioral enforcement through explicit instructions
- Supervisor file will grow but reorganized for clarity (TDD workflow at top)
- If this fails, may need to revisit hyper-specific subagents (test-validator, code-writer, etc.)
