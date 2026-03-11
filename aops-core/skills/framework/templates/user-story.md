---
title: User Story Template
type: spec
category: template
permalink: skills/feature-dev/templates/user-story
description: Template for capturing user needs, requirements, and success criteria
tags: [template, feature-dev, requirements, user-story]
---

# User Story: [Feature Name]

**Date**: YYYY-MM-DD **Status**: [Draft | Requirements Complete | In Development | Testing | Done]

## Original Request

[Raw user input - captured exactly as provided, no polish required]

## Feature Summary

[1-3 sentence summary of what this feature does and why it matters]

## The User

_Write a paragraph inhabiting the user's situation when they encounter this feature. Not demographics — their cognitive/emotional state, what just happened, what they're trying to do, what constraints are active, what success feels like. This paragraph anchors all acceptance criteria. See [[skills/qa/references/qa-planning.md]] Phase 1._

[Persona paragraph here]

## Requirements

### Functional Requirements

**Core functionality**:

1. [Specific, testable requirement]
2. [Specific, testable requirement]

**User interactions**:

- [How users interact with this feature]
- [Expected user workflows]

**System behavior**:

- [How system should respond]
- [Edge cases to handle]

### Non-Functional Requirements

**Performance**: [Response time, scalability needs, etc.] **Security**: [Auth, data protection, input validation, etc.] **Maintainability**: [Code quality, documentation, etc.] **Compatibility**: [Browser, device, dependency requirements]

### Out of Scope

[Explicitly list what this feature will NOT do]

## Acceptance Criteria

_Design guidance: Consult [[skills/qa/references/qa-planning.md]] Phase 2. Write qualitative dimensions (questions requiring judgment) traced to user stories. Define what excellent and poor look like._

### Qualitative Acceptance Criteria

1. **[Dimension as question]** — serves [which user story/need]
   - _Excellent_: [What this looks and feels like when it works well]
   - _Poor_: [What this looks and feels like when it fails the user]

2. **[Dimension as question]** — serves [which user story/need]
   - _Excellent_: [description]
   - _Poor_: [description]

### Regression Checks

- [ ] [Binary check that prevents backsliding after acceptance]
- [ ] [Another regression guard]

**Acceptance gate**:

- [ ] All qualitative acceptance criteria evaluated (narrative, not pass/fail)
- [ ] All functional requirements met
- [ ] All regression checks pass
- [ ] Integration tests pass
- [ ] No regressions introduced

## Context

**User need**: [Why does the user want this?] **Current behavior**: [What happens now without this feature?] **Desired behavior**: [What should happen with this feature?] **Impact**: [How does this improve user experience/workflow?]

## Constraints

**Technical constraints**: [Platform, tool, or architectural limitations] **Time constraints**: [Deadlines, priorities] **Resource constraints**: [Dependencies, blockers]

## Questions & Decisions

[Capture ambiguities and decisions made during requirements analysis]

- **Q**: [Question that needed clarification]
  - **A**: [Decision made]
  - **Rationale**: [Why this decision]

## Notes

[Additional context, research findings, related work]

**References**:

- [[ACCOMMODATIONS.md]] - Work style requirements
- Dev plan template: [[dev-plan.md]]
- Experiment template: [[experiment-plan.md]]
- Test specification template: [[test-spec.md]]
