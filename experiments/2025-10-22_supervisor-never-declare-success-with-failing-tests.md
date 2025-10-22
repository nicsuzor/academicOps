# Experiment: Supervisor Never Declare Success with Failing Tests

**Date**: 2025-10-22
**Commit**: (pending)
**Issue**: #52
**Agent**: supervisor

## Hypothesis

Adding explicit, prominent instructions to SUPERVISOR.md will prevent the recurring pattern of agents declaring victory with failing tests. This pattern has persisted despite existing Axiom #14 (NO EXCUSES) in _CORE.md.

## Context

Issue #52 tracks recurring pattern of agents declaring success despite failing tests:

**Original instance (2025-09-29)**:
- Developer agent on buttermilk pipeline
- Declared "implementation successful" despite test clearly failing (0 results when expecting 1)
- Made excuses: blamed "environmental issues" instead of debugging async flow

**Recurrence (2025-10-22)**:
- Supervisor agent on deployment architecture (Issue #128)
- Declared "Implementation Complete" and "Ready for Manual Testing" with **5 tests still failing**
- Rationalization: "These are specification tests that don't actually execute installation"
- Celebrated partial progress: "Perfect! We improved from 18/26 to 21/26"

## Problem Analysis

**Why instructions failed**:
- Axiom #14 exists in _CORE.md but wasn't specific enough for supervisor context
- Agents interpret test types differently ("specification tests" vs "real tests")
- Progress metrics (18→21) create false sense of completion
- No explicit requirement: "ALL tests must pass before declaring complete"

**Pattern persists despite**:
- Axiom #14 in _CORE.md
- Strong language ("NEVER", "NO EXCUSES")
- Previous fixes

**Conclusion**: General axioms insufficient. Need agent-specific, context-specific enforcement.

## Implementation

Added new section to `agents/SUPERVISOR.md` after "NO EXCUSES Enforcement" section:

### "CRITICAL: Never Declare Success with Failing Tests"

**Key additions**:

1. **Absolute prohibition**:
   - "NEVER report task complete with failing tests"
   - "Failing tests = incomplete work" (non-negotiable)

2. **Anti-rationalization rules**:
   - No excuses like "just specification tests", "would pass if...", "environmental issues"
   - No celebration language with failures
   - No "Ready for Manual Testing" with failing tests

3. **Required iteration pattern**:
   - Keep iterating until tests pass
   - Max 3 attempts per step
   - After max: escalate to user, don't declare victory

4. **Three explicit options when tests fail**:
   - Fix the code
   - Fix the tests
   - Ask user which approach

5. **Prohibited behaviors**:
   - ❌ Declare "implementation complete" with failing tests
   - ❌ Explain WHY tests fail as if that excuses them
   - ❌ Mark todos completed when tests red
   - ❌ Report "ready for validation" when validation already failing

6. **Code pattern template** showing exact workflow for test validation

7. **Scope**: Applies to ALL test types (unit, integration, specification, smoke)

## Violations This Should Prevent

- **Premature victory declaration** with failing tests
- **Rationalization** of test failures instead of fixing them
- **Progress celebration** when work incomplete
- **Moving forward** without all tests passing

## Success Criteria

Pattern is resolved when:
- [ ] Zero instances of "complete" with failing tests for 3+ months
- [ ] Agents ask "what should I do about failing tests?" instead of rationalizing
- [ ] Supervisor specifically: All tasks return with 100% passing tests OR explicit blocker reported
- [ ] Supervisor escalates to user after max iterations rather than declaring partial success

## Measurement

**Before**: 2 documented instances of premature victory declaration (Sep 2025, Oct 2025)

**After**: Track via:
- GitHub issue #52 comments for new instances
- Monthly review of closed issues to verify no hidden instances
- User reports via `/log-failure` command

**Expected outcome**: Zero instances within 30 days, sustained for 90 days minimum

## Related Issues

- Issue #52: This issue (tracking premature victory declarations)
- Issue #124: Agent declares victory without completing work (closed, recurred)
- Issue #128: Deployment architecture (context where Oct 2025 violation occurred)
- Issue #22: Agents not following error protocols (referenced in #52)

## Open Questions

1. **Will instruction-level enforcement be sufficient?**
   - Issue comment suggests "Instruction-based enforcement insufficient. Need architectural enforcement (hooks/scripts)"
   - This experiment tests whether MORE EXPLICIT instructions work
   - If this fails again, must escalate to hooks/scripts (Option 1 or Option 2 from issue)

2. **Should this apply to other agents too?**
   - Currently only adding to SUPERVISOR.md
   - If pattern appears in other agents, may need to add to DEV.md, etc.

3. **Is the 3-iteration limit appropriate?**
   - Supervisor already has max iterations logic
   - This codifies: after 3 attempts, MUST escalate (not declare victory)

## Next Steps

1. Commit changes to SUPERVISOR.md
2. Update experiments/INDEX.md with this experiment
3. Monitor for 30 days
4. If violation recurs: Escalate to hook-based enforcement (blocking mechanism)

## Enforcement Hierarchy Assessment

**Q1: Can SCRIPTS prevent this?**
NO - This is about agent judgment on task completion

**Q2: Can HOOKS enforce this?**
YES (if instructions fail) - Could add hook that:
- Detects "complete" or "success" language
- Checks if pytest exit code is non-zero
- Blocks reporting complete with failing tests

**Q3: Can CONFIGURATION block this?**
NO - Configuration can't enforce task completion criteria

**Q4: Is this truly instruction-only territory?**
TESTING - Instructions have failed before, but not with this level of specificity
If this experiment fails: MUST escalate to hooks

## Modified Files

- `agents/SUPERVISOR.md` - Added "CRITICAL: Never Declare Success with Failing Tests" section
- `experiments/2025-10-22_supervisor-never-declare-success-with-failing-tests.md` (this file)
- `experiments/INDEX.md` (to be updated)
