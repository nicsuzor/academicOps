---
name: feature-dev
description: Rigorous test-first feature development from idea to validated implementation.
allowed-tools: Read,Edit,Write,Bash,Skill,TodoWrite
version: 1.0.0
permalink: skills-feature-dev-skill
---

# Feature Development Skill

**Purpose**: Guide rigorous, test-first feature development from idea to validated implementation.

**When to use**: Adding new features, building significant functionality, implementing user-requested capabilities.

**When NOT to use**: Bug fixes (unless requiring new functionality), simple refactoring, documentation-only changes.

## Core Principles

This skill enforces framework principles from [[AXIOMS.md]]:

- **Test-First**: Integration tests before implementation
- **Explicit Success Criteria**: Define measurable outcomes upfront
- **Fail-Fast**: No partial success, fix or revert
- **Single Source of Truth**: Reference, don't duplicate
- **Experiment-Driven**: Document as formal experiments
- **Bias for Action**: Execute without unnecessary confirmation (per [[ACCOMMODATIONS.md]])

## Overview

Feature development follows seven phases:

1. **User Story Capture** - Zero-friction idea intake
2. **Requirements Analysis** - Transform into testable requirements
3. **Experiment Design** - Formalize plan with hypothesis
4. **Test-First Design** - Write integration tests first
5. **Development Planning** - Break into discrete steps
6. **Execution** - Build with continuous validation
7. **Validation** - Verify and decide keep/revert/iterate

## Workflow

### Phase 1: User Story Capture

**Objective**: Capture the feature request with zero friction.

**Actions**:

1. Accept input in ANY format (fragments, voice-to-text, stream-of-consciousness)
2. Use template `templates/user-story.md` to structure captured input
3. Don't ask for clarification yet - capture first
4. Create initial TodoWrite list with phases as items

**Output**: Completed user story document with raw requirements.

**ADHD Accommodation**: Zero-friction capture means accepting messy input without requesting polish.

---

### Phase 2: Requirements Analysis

**Objective**: Transform user story into clear, testable requirements.

**Actions**:

1. Extract functional requirements from user story
2. Identify constraints and non-functional requirements
3. Define explicit success criteria (measurable, objective)
4. Clarify ambiguities NOW (ask user for specific decisions)
5. Document in user story under "Requirements" and "Success Criteria" sections

**Critical Questions**:

- What defines "done" for this feature?
- How will we know it works correctly?
- What edge cases must be handled?
- What should NOT be in scope?

**Output**: User story enhanced with explicit requirements and success criteria.

**Fail-Fast**: If requirements conflict or are unclear after discussion, HALT - don't proceed with ambiguity.

---

### Phase 3: Experiment Design

**Objective**: Formalize feature as testable experiment.

**Actions**:

1. Use template `templates/experiment-plan.md`
2. Write clear hypothesis (expected outcome of implementing feature)
3. Define success criteria (from Phase 2)
4. Specify scope boundaries (what's in/out)
5. Identify control state (current behavior without feature)
6. Create experiment log: `data/projects/aops/experiments/YYYY-MM-DD_feature-name.md`

**Experiment Log Required For**:

- Features touching framework infrastructure
- Significant new capabilities
- Changes affecting multiple components
- User explicitly requests formal experiment

**Experiment Log Optional For**:

- Small, isolated features
- Project-specific functionality (may log in project repo instead)

**Output**: Experiment plan document defining hypothesis, success criteria, and scope.

---

### Phase 4: Test-First Design

**Objective**: Write integration tests before writing feature code.

**Actions**:

1. Use template `templates/test-spec.md` to design tests
2. Write actual integration test code that will validate success criteria
3. Run test - MUST FAIL (proves test is testing correctly)
4. Document test location and how to run it
5. Commit test code (yes, failing tests are committed as part of TDD)

**Test Requirements**:

- Tests complete user-facing workflow end-to-end
- Tests validate each success criterion
- Tests check error conditions
- Tests are executable and automated
- Tests fail before feature exists, pass after feature complete

**Test Location**:

- Framework features: `bots/skills/framework/tests/`
- Project features: Within project test directory
- Cross-cutting features: Dedicated test directory with clear ownership

**Output**: Executable integration test that currently fails.

**Fail-Fast**: If you can't define how to test success criteria, go back to Phase 2.

---

### Phase 5: Development Planning

**Objective**: Break implementation into discrete, trackable steps.

**Actions**:

1. Use template `templates/dev-plan.md`
2. Break feature into minimal implementation steps
3. Identify dependencies between steps
4. Estimate complexity/risk for each step
5. Create detailed TodoWrite list with all steps
6. Mark first step as in_progress

**Planning Principles**:

- Steps should be completable in single work session
- Each step should be testable independently if possible
- High-risk steps flagged for extra validation
- No placeholders or TODOs in plan - specific actions only

**Output**: Development plan with discrete, ordered steps.

**ADHD Accommodation**: Visual progress tracking via todos provides at-a-glance status.

---

### Phase 6: Execution

**Objective**: Implement feature following plan with continuous validation.

**Actions**:

**For each development step**:

1. Mark step as in_progress in TodoWrite
2. Implement step following framework principles
3. Run relevant tests (unit tests if applicable)
4. Verify no regressions (run existing test suite)
5. Mark step completed
6. Move to next step

**Continuous Validation**:

- Run integration test after each major step
- Check documentation integrity
- Verify no bloat introduced
- Confirm single source of truth maintained

**During Implementation**:

- Reference existing documentation, don't duplicate
- Follow standard tools (per AXIOMS.md #9)
- No workarounds or silent failures
- If blocked, update experiment log and halt (don't work around)

**Output**: Implemented feature with integration test passing.

**Fail-Fast**:

- Integration test fails → Stop, fix, or revert
- Documentation conflicts → Stop, resolve
- Bloat detected → Stop, refactor
- No partial success - feature works completely or doesn't ship

---

### Phase 7: Validation & Decision

**Objective**: Verify against success criteria and decide keep/revert/iterate.

**Actions**:

**Validation Checklist**:

1. Run complete integration test suite - ALL MUST PASS
2. Verify each success criterion met with evidence
3. Check documentation integrity (no conflicts, references resolve)
4. Verify bloat check passes (file size limits)
5. Confirm framework principles followed
6. Review code for security issues (injection, XSS, etc.)

**Decision Matrix**:

| Outcome                             | Action                                          |
| ----------------------------------- | ----------------------------------------------- |
| All criteria met + all tests pass   | **KEEP** - Commit and document success          |
| Some criteria not met OR tests fail | **REVERT** - Remove feature, document why       |
| Close to success with clear fix     | **ITERATE** - One more cycle with specific plan |

**Revert Protocol**:

- Remove all feature code
- Keep integration tests (document as future requirement)
- Update experiment log with failure analysis
- No shame in reverting - fail-fast is a feature

**Keep Protocol**:

- Final commit with feature code
- Update experiment log with success evidence
- Mark all todos completed
- Document lessons learned

**Iterate Protocol**:

- Define exactly what needs to change
- Set limit (max 1 iteration)
- If iteration fails, REVERT
- Update experiment log with iteration notes

**Output**: Feature committed (keep), removed (revert), or refined (iterate once).

**Fail-Fast**: Never commit partial success. Better to revert and learn than ship broken features.

---

## Templates

All templates in `templates/` subdirectory:

- [[templates/user-story.md]] - Capture feature request
- [[templates/experiment-plan.md]] - Formalize as experiment
- [[templates/test-spec.md]] - Design integration tests
- [[templates/dev-plan.md]] - Plan implementation steps

Templates follow single-source-of-truth principle by referencing framework docs rather than duplicating them.

## Progress Tracking

Use TodoWrite at key points:

**Initial setup** (Phase 1):

```
- Capture user story
- Analyze requirements
- Design experiment
- Write integration tests
- Plan development
- Execute implementation
- Validate and decide
```

**Development phase** (Phase 5): Break into specific implementation steps per dev-plan.md.

**Update status**:

- Mark in_progress when starting phase/step
- Mark completed immediately after finishing
- Only ONE item in_progress at a time

## Error Handling

**When tests fail**:

- HALT immediately
- Do not rationalize failure
- Do not work around
- Fix or revert
- Update experiment log

**When blocked on infrastructure**:

- Update experiment log with blocker
- HALT - do not work around
- Report infrastructure issue
- Wait for fix, don't proceed

**When requirements unclear**:

- Go back to Phase 2
- Get explicit clarification
- Update user story
- Don't guess or assume

## Integration with Framework

**This skill produces**:

- Experiment logs in `data/projects/aops/experiments/`
- Integration tests in `bots/skills/framework/tests/` or project tests
- Features following framework principles

**This skill enforces**:

- All axioms from [[AXIOMS.md]]
- Test-first development
- Documentation integrity
- Fail-fast behavior
- Single source of truth

**This skill supports**:

- ADHD accommodations from [[ACCOMMODATIONS.md]]
- Zero-friction capture
- Bias for action
- Visual progress tracking
- Clear phase separation

## Quick Reference

**Starting feature development**:

1. Invoke skill: "I want to build [feature]"
2. Skill captures story (Phase 1)
3. Skill analyzes requirements (Phase 2) - may ask clarifying questions
4. Skill designs experiment (Phase 3)
5. Skill writes tests (Phase 4) - should fail
6. Skill plans development (Phase 5)
7. Skill implements feature (Phase 6)
8. Skill validates and decides (Phase 7)

**At each phase**:

- Update TodoWrite status
- Verify framework principles followed
- Document in appropriate template
- Move to next phase only when current complete

**Remember**:

- Test before code
- Define success upfront
- Fail-fast on problems
- Reference, don't duplicate
- Visual progress tracking
- Bias for action
