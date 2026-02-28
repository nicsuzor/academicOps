# Swarm Supervisor: Decomposition and Review

## Phase 1: Decompose

The supervisor decomposes large tasks into PR-sized subtasks.

**PR-Sized Definition** (all must be true):

- Estimated effort ≤ 4 hours
- Touches ≤ 10 files
- Single logical unit (one "why")
- Testable in isolation
- Reviewable by human in ≤ 15 minutes

**Decomposition Protocol**:

```markdown
## Supervisor: Decompose Task

1. Read task body and context
2. Check parent hierarchy (P#101, P#106, P#107):
   a. Does this task have a parent? If not, find or create one.
   b. Is the parent the right abstraction level? (Task under epic, epic under project)
   c. Can you articulate WHY this task exists in terms of the parent's goals?
   d. Is the task typed correctly for its scale? (See P#107: multi-session → epic)
3. Identify natural boundaries (files, features, dependencies)
4. Create subtasks using decompose_task():
   - Each subtask passes PR-sized criteria
   - Dependencies explicit in depends_on
   - 3-7 subtasks ideal (>7 suggests intermediate grouping needed)
   - Each subtask must pass the WHY test relative to its parent
5. Check for star pattern: if parent already has >5 children, group under intermediate epics
6. **Completion loop (P#109)**: Create one additional subtask: "Verify: [parent goal] fully resolved" with `depends_on` set to ALL other subtasks and `assignee: null`. This task returns to the original problem after all implementation is done to confirm it's fully solved or iterate again.
7. **Post-decomposition self-checks** (run BEFORE finalizing):
   a. For each **decision** subtask: "What information does the user need to make this decision?" — if no upstream prep task exists, create one and add it to `depends_on`
   b. For each **execution** subtask: "Is this conditional on a decision that hasn't been made?" — if yes, add the decision task to `depends_on`
   c. For each **writing** subtask: "What analysis/data needs to be final before this can be written?" — if it depends on analysis results, add the analysis task to `depends_on`
   d. If the parent task produces **academic output** (paper, report, benchmark, analysis): ensure methodology tasks exist (methodological justification, validation approach, claim-evidence audit, limitations completeness)
8. Append decomposition summary to task body
9. Set task status to 'consensus'
```

**Hierarchy Quality Gate** (check BEFORE creating subtasks):

Before decomposing, verify the task's position in the graph is sound:

| Check             | Fail condition                        | Fix                               |
| ----------------- | ------------------------------------- | --------------------------------- |
| Parent exists     | `parent` is empty or missing          | Find or create appropriate epic   |
| Abstraction match | Task is direct child of project       | Create intermediate epic          |
| WHY test          | Can't justify task in terms of parent | Re-parent or create bridging epic |
| Type-scale match  | Multi-session work typed as `task`    | Retype as `epic`                  |
| Star pattern      | Parent has >5 direct children         | Group siblings under epics        |

If any check fails, fix the hierarchy BEFORE proceeding with decomposition.

**Post-Decomposition Self-Check Gate** (run AFTER creating subtasks, BEFORE finalizing):

| Check                | How to detect                                                     | Fix                                                      |
| -------------------- | ----------------------------------------------------------------- | -------------------------------------------------------- |
| Decision has prep    | Decision task has no upstream data-gathering dependency           | Create prep task, add to `depends_on`                    |
| Execution is gated   | Execution task is unconditional but depends on a decision outcome | Add decision task to `depends_on`                        |
| Writing has data     | Writing task depends on analysis results not yet complete         | Add analysis task to `depends_on`                        |
| Academic methodology | Academic output has no justification/validation/audit tasks       | Add methodology layer tasks (see [[decompose]] workflow) |

**Output Format** (appended to task body):

```markdown
## Decomposition Proposal

### Subtasks

| ID        | Title       | Estimate | Confidence |
| --------- | ----------- | -------- | ---------- |
| subtask-1 | Description | 2h       | medium     |

### Dependency Graph

subtask-1 -> subtask-2 (blocks)
subtask-1 ~> subtask-3 (informs)

### Information Spikes (must resolve first)

- [ ] spike-1: Question we need answered

### Assumptions (load-bearing, untested)

- Assumption 1

### Risks

- Risk 1 (mitigation: ...)
```

## Phase 2: Multi-Agent Review

Supervisor invokes reviewer agents and synthesizes their feedback before human approval.

**Reviewers**:

| Reviewer          | Role                                                        | Mandatory                                 | Model  |
| ----------------- | ----------------------------------------------------------- | ----------------------------------------- | ------ |
| Custodiet         | Authority check: is task within granted scope?              | Yes                                       | haiku  |
| Critic            | Pedantic review: assumptions, logical errors, missing cases | Yes                                       | opus   |
| Domain specialist | Subject matter expertise                                    | If task.tags intersect specialist.domains | varies |

---

### 2.1 Reviewer Invocation Protocol

**Step 1: Prepare Review Context**

Before invoking reviewers, prepare a context document containing:

```markdown
# Review Request: <task-id>

## Original Request

[User's original task description]

## Decomposition Proposal

[The decomposition from Phase 1]

## Files/Scope Affected

[List of files the subtasks will touch]

## Relevant Principles

[Extract relevant AXIOMS/HEURISTICS for this domain]
```

**Step 2: Invoke Reviewers in Parallel**

```python
# Spawn both mandatory reviewers simultaneously
    model='opus',
    prompt='''Review this decomposition proposal:

<context>
{review_context}
</context>

Check for:
1. Logical errors in the decomposition
2. Untested assumptions about dependencies
3. Missing edge cases or error handling
4. Scope drift from original request
5. PR-sizing violations (>4h, >10 files, multiple "whys")
6. Decision tasks without information prerequisites (every decision needs a prep task)
7. Execution tasks unblocked when they depend on an unmade decision
8. Academic outputs missing methodology layer (justification, validation, audit)

Return your assessment in this exact format:

## Critic Review

**Reviewing**: [1-line description]

### Issues Found
- [Issue]: [why it's a problem]

### Untested Assumptions
- [Assumption]: [why it matters if wrong]

### Verdict
[PROCEED / REVISE / HALT]

[If REVISE or HALT: specific changes needed]
''',
    description='Critic review of decomposition'
)

custodiet_task = Task(
    subagent_type='aops-core:custodiet',
    model='haiku',
    prompt='''Verify this task is within granted authority:

<context>
{review_context}
</context>

Check:
1. Does the decomposition stay within the original request scope?
2. Are there any scope expansions not explicitly authorized?
3. Do any subtasks assume permissions not granted?

Output exactly: OK, WARN, or BLOCK (see custodiet format spec)
''',
    description='Authority verification'
)
```

**Step 3: Collect and Parse Responses**

Wait for both reviewers (timeout: 5 minutes each).

Parse responses into structured verdicts:

| Critic Verdict | Custodiet Verdict | Combined Result          |
| -------------- | ----------------- | ------------------------ |
| PROCEED        | OK                | → APPROVED               |
| PROCEED        | WARN              | → APPROVED (log warning) |
| REVISE         | OK/WARN           | → NEEDS_REVISION         |
| HALT           | any               | → BLOCKED                |
| any            | BLOCK             | → BLOCKED                |

---

### 2.2 Verdict Synthesis Protocol

**On APPROVED**:

```markdown
## Review Synthesis

**Verdict**: APPROVED

### Reviewer Summary

| Reviewer  | Verdict | Key Points       |
| --------- | ------- | ---------------- |
| Critic    | PROCEED | [1-line summary] |
| Custodiet | OK      | Within scope     |

### Minor Suggestions (optional)

- [Any non-blocking improvements from reviewers]

→ Proceeding to human approval gate (status='waiting')
```

Then:

```python
update_task(id=task_id, status='waiting', body=synthesis_markdown)
```

**On NEEDS_REVISION**:

```markdown
## Review Synthesis

**Verdict**: NEEDS_REVISION

### Issues Requiring Resolution

- **Suggested fix**: [how to address]

2. [Issue from custodiet if WARN]: [scope concern]
   - **Suggested fix**: [how to narrow scope]

### Required Actions

- [ ] Address issue 1
- [ ] Address issue 2
- [ ] Re-run review after changes

→ Returning to decomposition (status='decomposing')
```

Then:

```python
update_task(id=task_id, status='active', body=synthesis_markdown)
# Re-enter Phase 1 with reviewer feedback
```

**On BLOCKED**:

```markdown
## Review Synthesis

**Verdict**: BLOCKED

### Blocking Issues

| Reviewer   | Issue   | Principle Violated |
| ---------- | ------- | ------------------ |
| [reviewer] | [issue] | [A#X or H#X]       |

### Resolution Required

[Specific action needed before this can proceed]

→ Escalating to human (status='blocked')
```

Then:

```python
update_task(id=task_id, status='blocked', body=synthesis_markdown)
```

---

### 2.3 Debate Resolution (When Reviewers Disagree)

If reviewers return conflicting verdicts (one PROCEED, one REVISE), initiate a debate round.

**Debate Protocol** (max 2 rounds):

```markdown
## Debate Round 1

### Conflicting Assessments

- **Critic** says PROCEED: "[rationale]"
- **Custodiet** says WARN: "[concern]"

### Resolution Attempt
```

```python
# Share concerns with the other reviewer
debate_task = Task(
    model='opus',
    prompt='''The custodiet raised this concern about the decomposition:

<concern>
{custodiet_concern}
</concern>

Your original assessment was PROCEED. Given this new information:

1. Do you MAINTAIN your PROCEED verdict?
2. Do you REVISE to account for this concern?

Respond with:
- MAINTAIN: [brief justification]
- REVISE: [what changes you now recommend]
''',
)
```

**Debate Outcomes**:

| Round Result                     | Action                        |
| -------------------------------- | ----------------------------- |
| Both reviewers align             | Use aligned verdict           |
| Still conflicting after 2 rounds | Synthesize for human decision |

**Synthesizing Unresolved Debates**:

```markdown
## Review Synthesis

**Verdict**: ESCALATE_TO_HUMAN

### Unresolved Reviewer Disagreement

**Critic Position** (after debate):
[Their final position]

**Custodiet Position** (after debate):
[Their final position]

### Core Tension

[Supervisor's 1-sentence summary of why they disagree]

### Options for Human

2. **Narrow scope**: Accept custodiet's constraint
3. **Request more info**: Specific question to resolve

→ Awaiting human decision (status='waiting')
```

---

### 2.4 Domain Specialist Invocation (Optional)

When task tags indicate specialized domain expertise is needed:

> **Configuration**: See Domain Specialists registry in [[WORKERS.md]] for
> available specialists and their domain mappings.

```markdown
## Domain Specialist Protocol

1. Load Domain Specialists table from WORKERS.md
2. Match task.tags against registered domains
3. For each matching domain:
   - Invoke the configured specialist agent
   - Provide review context and domain-specific focus areas
   - Collect structured feedback
4. Synthesize specialist input with mandatory reviewer verdicts
```

```python
# Invoke specialist (conceptual)
for domain in matching_domains:
    specialist = lookup_specialist(domain)  # from WORKERS.md
    specialist_task = Task(
        subagent_type=specialist.agent,
        prompt=build_specialist_prompt(domain, review_context),
        description=f'{domain} specialist review'
    )
```

**Note**: Domain specialists are advisory. Their concerns inform but don't automatically block—supervisor synthesizes their input alongside mandatory reviewers.
