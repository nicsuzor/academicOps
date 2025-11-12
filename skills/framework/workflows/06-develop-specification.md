# Workflow 6: Develop Automation Specification

**When**: User wants to automate a manual process or you've identified a good automation candidate.

**Purpose**: Collaboratively develop a complete task specification using TASK-SPEC-TEMPLATE.md before implementation begins.

**Steps**:

1. **Identify automation target**
   - User describes manual process causing pain
   - Or: Agent observes repeated manual work and suggests automation
   - Confirm this is actual pain point worth automating

2. **Check ROADMAP alignment**
   - Read `bots/skills/framework/ROADMAP.md`
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

5. **Define Success Criteria (collaborative)**
   - **Agent asks**: "How will we know this automation succeeded?"
   - Focus on measurable outcomes (time saved, error reduction, reliability)
   - **Agent asks**: "What quality threshold is acceptable?"
   - Define when it should fail-fast vs. best effort
   - Write 3-5 concrete success criteria

6. **Scope the work (collaborative)**
   - **Agent proposes**: Initial scope based on problem statement
   - **Agent asks**: "What's explicitly out of scope?"
   - Apply principles from [[../../../AXIOMS.md]] - keep scope minimal and focused
   - Define clear boundaries
   - **Agent asks**: "Does this feel like one focused task?"

7. **Identify dependencies**
   - **Agent checks**: What infrastructure must exist first?
   - **Agent checks**: What data is required?
   - **Agent asks**: "What happens if dependencies are missing?"
   - Document error handling per [[../../../AXIOMS.md]] principles

8. **Design integration test (collaborative, CRITICAL)**
   - **Agent proposes**: Test approach for success criteria
   - Walk through: Setup → Execute → Validate → Cleanup
   - **Agent asks**: "How do we prove this automation worked?"
   - Write concrete test steps before any implementation
   - Test must be designed to fail initially

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
    - Ensure alignment with [[../../../AXIOMS.md]] principles

12. **Finalize specification**
    - Move completed spec to appropriate location (e.g., `bots/skills/framework/specs/`)
    - Specification is now the contract for implementation
    - Ready to proceed with workflow 01 (Design New Component)

**Communication Guidelines** (from [[../../../ACCOMMODATIONS.md]]):

- **Match user's preparation level**:
  - If user provides vague idea → Help discover requirements through questions
  - If user provides detailed requirements → Give clear recommendation and next steps
- **Proactive action**: Don't ask permission for safe exploratory questions
- **Bias for action**: In defined workflow, proceed to next logical step
- **No unnecessary validation**: Skip "good idea" preambles, process directly

**Output**:

- Complete specification document ready for implementation
- Clear success criteria and test design
- Identified dependencies and risks
- User confident in scope and approach
