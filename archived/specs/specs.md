---
title: Specification System
permalink: spec-system
type: spec
category: spec
tags: [aops, specs, architecture, design]
---

# Specification System

## User Story

**As** an academic with ADHD managing research workflows,
**I want** every framework feature to have a clear specification with user story and acceptance criteria,
**So that** features justify their existence, remain maintainable, and I can verify they work correctly.

> **Coherence check**: This spec system ensures the framework stays focused on its core mission. Features that can't articulate a user story connected to the narrative are candidates for removal.

## Acceptance Criteria

### Success Criteria (ALL must pass)

1. [ ] Every spec has User Story and Acceptance Criteria at the top
2. [ ] User stories connect to core narrative pillars (zero-friction capture, consistent quality, nothing lost, fail-fast, minimal maintenance)
3. [ ] Specs include implementation pointers to files that give them effect
4. [ ] Audit skill can validate spec structure

### Failure Modes (If ANY occur, implementation is WRONG)

1. [ ] Specs exist without user stories
2. [ ] Features exist without specs (violates AXIOMS #29)
3. [ ] Specs diverge from implementation

---

## Spec Requirements

Every spec MUST have (in this order, at the top of the file):

1. **User Story** - "As an academic with ADHD... I want... So that..." format
   - Must connect to core narrative: zero-friction capture, consistent quality, nothing lost, fail-fast, or minimal maintenance
   - Include coherence check explaining how feature serves the mission

2. **Acceptance Criteria** - Observable, testable outcomes
   - Success criteria (what USER can do/see when feature works)
   - Failure modes (conditions that mean implementation is wrong)

3. **Implementation pointers** - Bulleted list of [[wikilinks]] to files that implement the spec, with brief explanation of what each file does

Features that cannot articulate a user story connected to the core narrative are candidates for removal or consolidation.

## Spec Lifecycle

| Status        | Meaning                                  |
| ------------- | ---------------------------------------- |
| `draft`       | In development, not yet approved         |
| `approved`    | Approved design, awaiting implementation |
| `implemented` | Built and working                        |
| `requirement` | User story, not yet designed             |

## Implementation

- [[SPEC-TEMPLATE]] - Template for new specs (in `skills/framework/`)
- [[skills/framework/workflows/06-develop-specification]] - Workflow for developing specs collaboratively
- [[audit-skill]] - Validates spec structure (to be extended with user story checks)

## Discovery

Specs live in `$AOPS/specs/`. Use glob patterns or the audit skill to find specs by status or domain.
