---
title: Develop Automation Specification
type: automation
category: instruction
permalink: workflow-develop-specification
description: Process for collaboratively developing task specifications before implementation
---

# Workflow 6: Develop Automation Specification

**When**: User wants to automate a manual process or you've identified a good automation candidate.

**Purpose**: Collaboratively develop a complete task specification using TASK-SPEC-TEMPLATE.md before implementation begins.

**Detailed procedures and criteria**: See **[[spec-development-details]]**.

**Steps**:

1. **Identify automation target**: Confirm a manual process worth automating.
2. **Create specification document**: Copy `SPEC-TEMPLATE.md` to `specs/[name].md`.
3. **Fill Problem Statement section**: Collaborative answers on what, why, and for whom.
4. **Define Acceptance Criteria**: User-owned criteria including persona paragraph and qualitative dimensions (see [[spec-development-details#Step 4]]).
5. **Scope the work**: Propose initial scope and explicitly define boundaries.
6. **Identify dependencies**: Check required infrastructure and data; document error handling.
7. **Design integration test**: Tests that validate EACH acceptance criterion and detect EACH failure mode (see [[spec-development-details#Step 7]]).
8. **Plan implementation approach**: Technical design with components, data flow, and risk assessment.
9. **Assess effort and risk**: Time estimates and mitigation plans.
10. **Review and refine**: Complete summary review with the user.
11. **Finalize and submit for bazaar review**: Move completed spec to `specs/` and open a GitHub PR. After approval, proceed with implementation.

**Output**:

- Complete specification document.
- GitHub PR for review with task ID references.
- User-owned acceptance criteria and integration test design.

**Verification before proceeding**:

- [ ] Acceptance criteria section complete.
- [ ] Integration test design maps to each criterion.
- [ ] User confirms these criteria define "done".
