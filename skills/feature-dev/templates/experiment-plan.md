# Experiment: [Feature Name]

**Date**: YYYY-MM-DD **Status**: [Planning | In Progress | Validating | Complete]

**Hypothesis**: [Clear, testable statement of expected outcome from implementing this feature]

**Success Criteria**: [Reference user story success criteria - do not duplicate] → See `user-story.md` section "Success Criteria"

## Design

**Objective**: [What this feature accomplishes]

**Scope**:

- **In scope**: [What will be built]
- **Out of scope**: [What explicitly won't be built]
- **Boundaries**: [Where this feature starts and stops]

**Variable**: [What's changing - the feature being added]

**Approach**: [High-level implementation approach]

## Control

**Current state**: [Behavior/functionality before this feature exists]

**Baseline metrics** (if applicable):

- [Measurable aspect of current state]
- [Performance, usage, or quality metric]

**Known pain points**:

- [Problem this feature solves]
- [User friction being addressed]

## Implementation Plan

**Architecture**:

- [Key components to add/modify]
- [Integration points with existing system]
- [Data flow or control flow]

**Files to create**:

- `path/to/new/file` - [purpose]

**Files to modify**:

- `path/to/existing/file` - [what changes]

**Tests to create**:

- `path/to/test/file` - [what it validates]

**Dependencies**:

- [External dependencies or libraries needed]
- [Internal components this feature depends on]
- [Features that will depend on this]

**Risks**:

- [Technical risk] - Mitigation: [approach]
- [Integration risk] - Mitigation: [approach]

## Development Steps

**Detailed plan**: → See `dev-plan.md`

**Estimated complexity**: [Low | Medium | High] **Estimated time**: [Rough estimate if useful]

## Validation Plan

**Integration tests**: [What tests will validate success] → See `test-spec.md` for detailed test design

**Success criteria validation**:

- [How criterion 1 will be verified]
- [How criterion 2 will be verified]

**Regression testing**:

- [Existing tests that must still pass]
- [Areas to check for unintended impact]

## Results

[Completed after implementation]

**Actual implementation**:

- [What was actually built]
- [Deviations from plan and why]

**Evidence**:

- [Test results]
- [Metrics collected]
- [Observations]

## Evaluation

[Completed during validation phase]

Check against success criteria:

- [ ] Success criterion 1 met - [evidence]
- [ ] Success criterion 2 met - [evidence]
- [ ] All integration tests pass
- [ ] No regressions introduced
- [ ] No documentation conflicts
- [ ] Bloat check passed
- [ ] Security review clean

## Decision

- [ ] **Keep** - All criteria met, tests pass, no conflicts
- [ ] **Revert** - Criteria not met OR conflicts/failures
- [ ] **Iterate** - Close to success with clear fix path (max 1 iteration)

**Rationale**: [Why this decision - completed during validation]

## Lessons

[Completed after decision]

**What worked well**:

- [Practice or approach that was effective]

**What didn't work**:

- [Practice or approach that caused problems]

**What to try next time**:

- [Improvement based on this experience]

**Framework implications**:

- [Any insights for improving the feature-dev skill itself]

---

**References**:

- User story: `user-story.md`
- Test specification: `test-spec.md`
- Development plan: `dev-plan.md`
- Framework principles: `[[AXIOMS.md]]`
