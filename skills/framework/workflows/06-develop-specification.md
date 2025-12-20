---
title: Develop Automation Specification
type: workflow
permalink: workflow-develop-specification
description: Process for collaboratively developing task specifications before implementation
---

# Workflow 6: Develop Automation Specification

**When**: User wants to automate a manual process or you've identified a good automation candidate.

**Purpose**: Collaboratively develop a complete task specification using TASK-SPEC-TEMPLATE.md before implementation begins.

**Steps**:

1. **Identify automation target**
   - User describes manual process causing pain
   - Or: Agent observes repeated manual work and suggests automation
   - Confirm this is actual pain point worth automating

2. **Check [[ROADMAP.md]] alignment**
   - Read `$ACA_DATA/projects/aops/ROADMAP.md`
   - Verify automation fits current stage (likely Stage 2: Scripted Tasks)
   - Confirm prerequisites/dependencies exist from earlier stages
   - HALT if trying to skip stages

3. **Create specification document**
   - Copy `bots/skills/framework/TASK-SPEC-TEMPLATE.md` to working location
   - Name: `data/tasks/inbox/[descriptive-name]-spec.md` (or similar temporary location)
   - This is a collaborative working document

4. **Fill Problem Statement section (collaborative)**
   - **Agent asks**: "What manual work are we automating?"
   - **Agent asks**: "Why does this matter?" (time saved, quality gains)
   - **Agent asks**: "Who benefits and how?"
   - Write clear, specific answers

5. **Define Acceptance Criteria (collaborative, USER-OWNED)**
   - **CRITICAL**: These criteria define "done" and are user-owned (agents cannot modify them)
   - **Agent asks**: "How will we know this automation succeeded?"
   - Focus on observable, testable outcomes (time saved, error reduction, reliability)
   - **Agent asks**: "What would indicate this implementation is WRONG?"
   - **Agent asks**: "What quality threshold is acceptable?"
   - Define when it should fail-fast vs. best effort
   - Write 3-5 concrete acceptance criteria (Success Tests)
   - Write 2-3 failure modes that indicate wrong implementation
   - **Agent confirms**: "These criteria will be implemented as tests. Agents cannot modify them."

6. **Scope the work (collaborative)**
   - **Agent proposes**: Initial scope based on problem statement
   - **Agent asks**: "What's explicitly out of scope?"
   - Keep scope minimal and focused
   - Define clear boundaries
   - **Agent asks**: "Does this feel like one focused task?"

7. **Identify dependencies**
   - **Agent checks**: What infrastructure must exist first?
   - **Agent checks**: What data is required?
   - **Agent asks**: "What happens if dependencies are missing?"
   - Document error handling (fail-fast, no silent failures)

8. **Design integration test (collaborative, CRITICAL)**
   - **CRITICAL**: Tests IMPLEMENT acceptance criteria from step 5, not new criteria
   - **Agent proposes**: Test approach that validates EACH acceptance criterion
   - Map each test to specific acceptance criterion: "Test 1 validates criterion #1"
   - Walk through: Setup → Execute → Validate → Cleanup
   - **Agent asks**: "How do we prove EACH acceptance criterion is met?"
   - **Agent asks**: "How do we detect EACH failure mode?"
   - Write concrete test steps before any implementation
   - Test must be designed to fail initially
   - **Verify**: Every acceptance criterion has corresponding test

9. **Plan implementation approach**
   - **Agent proposes**: High-level technical design
   - Identify components and data flow
   - Justify technology choices
   - **Agent asks**: "What could go wrong?" (failure modes)
   - Document error handling strategy

10. **Assess effort and risk**
    - **Agent estimates**: Time required for each phase
    - Identify risks and mitigations
    - **Agent asks**: "Are we confident in this estimate?"
    - Flag any open questions that need resolution

11. **Review and refine**
    - **Agent reads back**: Complete specification summary
    - **Agent asks**: "Does this feel right? Anything missing?"
    - Iterate on any unclear or incomplete sections

12. **Finalize specification**
    - Move completed spec to `$ACA_DATA/projects/aops/specs/` (AUTHORITATIVE location)
    - Specification is now the contract for implementation
    - Ready to proceed with workflow 01 (Design New Component)

**Communication Guidelines** (from [[ACCOMMODATIONS.md]]):

- **Match user's preparation level**:
  - If user provides vague idea → Help discover requirements through questions
  - If user provides detailed requirements → Give clear recommendation and next steps
- **Proactive action**: Don't ask permission for safe exploratory questions
- **Bias for action**: In defined workflow, proceed to next logical step
- **No unnecessary validation**: Skip "good idea" preambles, process directly

**Output**:

- Complete specification document ready for implementation
- User-owned acceptance criteria (observable, testable, cannot be modified by agents)
- Integration tests that implement each acceptance criterion
- Identified dependencies and risks
- User confident in scope and approach

**Verification before proceeding**:
- [ ] Acceptance criteria section complete (Success Tests + Failure Modes)
- [ ] Each acceptance criterion is observable and testable
- [ ] Integration test design maps to each criterion
- [ ] User confirms these criteria define "done"
