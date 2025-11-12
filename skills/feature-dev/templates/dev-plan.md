# Development Plan: [Feature Name]

**Date**: YYYY-MM-DD **Status**: [Planning | In Progress | Complete] **Complexity**: [Low | Medium | High]

## Overview

**Feature**: [Brief description] **Approach**: [High-level implementation strategy]

**Prerequisites**:

- [ ] User story complete with success criteria
- [ ] Experiment plan documented
- [ ] Integration tests written and failing
- [ ] Development environment ready

## Implementation Steps

### Step 1: [Descriptive name]

**Objective**: [What this step accomplishes]

**Actions**:

1. [Specific action]
2. [Specific action]

**Files to modify/create**:

- `path/to/file` - [what changes]

**Validation**:

- [How to verify this step is complete]
- [Test to run if applicable]

**Dependencies**: [What must be done before this step] **Risk**: [Low | Medium | High] - [Mitigation if high]

**Estimated effort**: [Rough estimate if useful]

---

### Step 2: [Descriptive name]

[Same structure as Step 1]

---

### Step 3: [Descriptive name]

[Same structure as Step 1]

---

[Add as many steps as needed - each should be completable in one work session]

## Dependencies & Order

**Dependency graph**:

```
Step 1 (foundation)
  ↓
Step 2 (depends on Step 1)
  ↓
Step 3 (depends on Step 2)
  ├→ Step 4 (parallel with Step 5)
  └→ Step 5 (parallel with Step 4)
  ↓
Step 6 (depends on Steps 4 & 5)
```

**Critical path**: [Steps that block other work] **Parallelizable**: [Steps that can be done concurrently]

## High-Risk Areas

**Step [N]**: [Why it's risky and how to mitigate]

- Risk: [Specific concern]
- Mitigation: [How to reduce risk]
- Fallback: [Alternative approach if this fails]

## Testing Strategy

**After each step**:

- [ ] Run step-specific validation
- [ ] Run relevant unit tests (if applicable)
- [ ] Check for regressions in existing tests

**After major milestones**:

- [ ] Run integration test for this feature
- [ ] Run full test suite
- [ ] Manual verification if needed

**Continuous validation**:

- [ ] Check documentation integrity
- [ ] Verify no bloat introduced
- [ ] Confirm single source of truth maintained
- [ ] Security review for new code

## Progress Tracking

**TodoWrite structure**:

```
- Step 1: [Name]
- Step 2: [Name]
- Step 3: [Name]
...
```

**Status updates**:

- Mark in_progress when starting step
- Mark completed immediately after finishing
- Only ONE step in_progress at a time
- Add new steps if discovered during implementation

## Implementation Guidelines

**Code quality**:

- Follow framework standard tools per `[[AXIOMS.md]]` #9
- Reference docs, don't duplicate
- No placeholders or TODOs in committed code
- Security review for user input, API calls, data handling

**Documentation**:

- Update relevant docs as you go
- Reference existing docs rather than duplicate
- Keep inline comments focused on "why" not "what"

**Error handling**:

- Fail-fast on configuration errors
- No silent failures or defaults
- Clear error messages with actionable guidance

**Commits**:

- Commit after each logical step completion
- Clear, descriptive commit messages
- Reference user story or experiment in commits
- Don't commit broken state

## Rollback Plan

**If step fails**:

1. Document failure in experiment log
2. Attempt fix once
3. If fix fails, revert step changes
4. Reassess approach

**If integration test fails after implementation**:

1. HALT immediately
2. Debug and fix, or
3. Revert entire feature

**Revert protocol**:

- Remove all feature code
- Keep integration tests (future requirement)
- Update experiment log with failure analysis
- No shame in reverting - fail-fast is a feature

## Completion Checklist

**Implementation complete**:

- [ ] All steps finished
- [ ] Integration test passes
- [ ] No regressions in existing tests
- [ ] Code reviewed for security issues
- [ ] Documentation updated
- [ ] No documentation conflicts
- [ ] Bloat check passed
- [ ] All success criteria met

**Ready for validation**:

- [ ] All tests passing
- [ ] Experiment log updated with results
- [ ] Evidence collected for success criteria
- [ ] Ready for keep/revert/iterate decision

## Notes & Discoveries

[Capture learnings and deviations from plan as work progresses]

**Deviations from plan**:

- [What changed and why]

**Challenges encountered**:

- [Problem and solution]

**Improvements for next time**:

- [Process or technical insight]

---

**References**:

- User story: `user-story.md`
- Experiment plan: `experiment-plan.md`
- Test specification: `test-spec.md`
- Framework principles: `[[AXIOMS.md]]`
- Work style: `[[ACCOMMODATIONS.md]]`
