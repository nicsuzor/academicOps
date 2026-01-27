---
id: hydrate
category: routing
bases: []
---

# Hydrate

Transform a user prompt into an execution plan. Determine **scope**, **workflow**, and **what to do now vs later**.

## Steps

1. **Framework Gate** - Check [[framework-gate]] FIRST
   - If framework work detected, route per framework-gate rules
   - Output Framework Change Context if applicable

2. **Gather Context**
   - Memory search for relevant knowledge
   - Review pre-loaded indexes (Skills, Workflows, Task State)

3. **Check Prior Work**
   - If task mentions specific files, check if they exist
   - If claiming existing task, check for prior work comments
   - Output "Prior work detected" if found

4. **Assess Scope**
   - **Single-session**: Clear, bounded, known path, one session
   - **Multi-session**: Goal-level, uncertain path, spans days/weeks

5. **Determine Execution Path**
   - **Direct**: `/command`, pure info request, no file mods
   - **Enqueue**: File modifications, multi-step, audit trail needed

6. **Assess Task Path** (for work tasks)
   - **EXECUTE**: What/Where/Why/How/Scope/Blockers all clear
   - **TRIAGE**: Any criterion unclear or blocked

7. **Classify Complexity** (see [[classify-task]])
   - `mechanical` / `requires-judgment` / `multi-step` / `needs-decomposition` / `blocked-human`

8. **Correlate with Existing Tasks**
   - Search task state for matches
   - Link to existing task or flag for new task creation

9. **Select Workflow** from WORKFLOWS.md decision tree

10. **Verify Constraints** (see [[constraint-check]])
    - Check selected workflow's constraints against plan
    - Report violations with remediation

11. **Output Plan** using appropriate format

## Output Formats

### EXECUTE Path

```markdown
## HYDRATION RESULT

**Intent**: [what user wants]
**Scope**: single-session | multi-session
**Path**: EXECUTE
**Execution Path**: direct | enqueue
**Complexity**: [complexity]
**Workflow**: [[workflows/[workflow-id]]]

### Task Routing
[Existing task / New task needed / No task needed]

### Acceptance Criteria
1. [Verifiable condition]

### Relevant Context
- [Key context from memory/codebase]

### Relevant Files
- `[path]`: [Why needed]

### Applicable Principles
From AXIOMS: **P#[n] [Name]**: [Why applies]
From HEURISTICS: **P#[n] [Name]**: [Why applies]

### Execution Plan
## Execution Steps
1. [Step 1]
2. [Step 2]
...

### Constraint Verification
**Status**: [satisfied/violations]
```

### TRIAGE Path

```markdown
## HYDRATION RESULT

**Intent**: [what user wants]
**Scope**: [scope]
**Path**: TRIAGE
**Complexity**: [needs-decomposition | blocked-human]
**Reason**: [which criterion triggered TRIAGE]

### Task Routing
[Existing task / New task needed]

### TRIAGE Assessment
**Why TRIAGE**: [Explain which EXECUTE criteria failed]
**Recommended Action**: [Assign to Role | Subtask explosion | Block for Clarification]
```

## Routing Rules

### Execution Path Detection

1. Starts with `/` → `direct`
2. Workflow is `simple-question` or `direct-skill` → `direct`
3. No file modifications implied → likely `direct`
4. Everything else → `enqueue`

### Task Path (EXECUTE vs TRIAGE)

**EXECUTE** requires ALL:
- **What**: Specific deliverable(s)
- **Where**: Target files known or locatable in 5 min
- **Why**: Context sufficient for decisions
- **How**: Steps known or determinable
- **Scope**: Completable this session
- **Blockers**: No external dependencies

**TRIAGE** if ANY:
- Requires human judgment/approval
- Unknowns requiring exploration beyond session
- Too vague for deliverables
- Depends on unavailable input
- Exceeds session scope

## Key Rules

1. **Always route to task** for file-modifying work (except simple-question)
2. **Prefer existing tasks** before creating new
3. **QA MANDATORY** for every plan (except simple-question)
4. **No execution** - provide plans only
