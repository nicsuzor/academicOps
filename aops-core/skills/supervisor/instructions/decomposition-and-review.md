# Decomposition and Review

## Phase 1: Decompose

The supervisor decomposes large tasks into review-sized subtasks. The
"review-sized" criterion is deliverable-agnostic; for code deliverables,
"reviewable by human in ≤ 15 minutes" maps to a PR-sized change (see
[[code-deliverable]]). For other deliverable types (e.g. a methodology
section), the same criteria apply against the relevant artefact (file
count → section/figure count, "testable in isolation" → "verifiable in
isolation").

**Review-Sized Definition** (all must be true):

- Estimated effort ≤ 0.5d (4 hours)
- Touches ≤ 10 files / artefacts
- Single logical unit (one "why")
- Verifiable in isolation
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
   - Each subtask passes review-sized criteria
   - Dependencies explicit in depends_on
   - 3-7 subtasks ideal
   - **Prefer Depth over Breadth**: If decomposition produces >5 subtasks, group them under intermediate epics to maintain a deep, manageable hierarchy.
   - Each subtask must pass the WHY test relative to its parent
5. Check for **Star Pattern** (P#101): if parent or proposal has >5 direct children, group under intermediate epics.
6. Check for **Depth** (P#110): Multi-session projects should target a hierarchy of Project → Epic → Task → Action.
7. **Completion loop (P#109)**: Create one additional subtask: "Verify: [parent goal] fully resolved" with `depends_on` set to ALL other subtasks and `assignee: null`. This task returns to the original problem after all implementation is done to confirm it's fully solved or iterate again.
8. **Post-decomposition self-checks** (run BEFORE finalizing):
   a. For each **decision** subtask: "What information does the user need to make this decision?" — if no upstream prep task exists, create one and add it to `depends_on`
   b. For each **execution** subtask: "Is this conditional on a decision that hasn't been made?" — if yes, add the decision task to `depends_on`
   c. For each **writing** subtask: "What analysis/data needs to be final before this can be written?" — if it depends on analysis results, add the analysis task to `depends_on`
   d. If the parent task produces **academic output** (paper, report, benchmark, analysis): ensure methodology tasks exist (methodological justification, validation approach, claim-evidence audit, limitations completeness)
9. Append decomposition summary to task body. **Remove any `- [ ]` checklists** from the body that are now tracked as subtasks — the subtask graph is the single source of truth. Keeping both causes divergence over time.
10. Annotate the task body with supervisor phase `consensus` (status remains `in_progress` throughout decomposition and review)
```

**Hierarchy Quality Gate** (check BEFORE creating subtasks):

Before decomposing, verify the task's position in the graph is sound:

| Check             | Fail condition                          | Fix                                          |
| ----------------- | --------------------------------------- | -------------------------------------------- |
| Parent exists     | `parent` is empty or missing            | Find or create appropriate epic              |
| Abstraction match | Task is direct child of project         | Create intermediate epic                     |
| WHY test          | Can't justify task in terms of parent   | Re-parent or create bridging epic            |
| Type-scale match  | Multi-session work typed as `task`      | Retype as `epic`                             |
| Star pattern      | Parent/Proposal has >5 direct children  | Group siblings under sub-epics               |
| Depth check       | Project graph is shallow (Avg depth <2) | Deepen hierarchy with intermediate groupings |

If any check fails, fix the hierarchy BEFORE proceeding with decomposition.

**Post-Decomposition Self-Check Gate** (run AFTER creating subtasks, BEFORE finalizing):

| Check                | How to detect                                                     | Fix                                                      |
| -------------------- | ----------------------------------------------------------------- | -------------------------------------------------------- |
| Decision has prep    | Decision task has no upstream data-gathering dependency           | Create prep task, add to `depends_on`                    |
| Execution is gated   | Execution task is unconditional but depends on a decision outcome | Add decision task to `depends_on`                        |
| Writing has data     | Writing task depends on analysis results not yet complete         | Add analysis task to `depends_on`                        |
| Academic methodology | Academic output has no justification/validation/audit tasks       | Add methodology layer tasks (see [[decompose]] workflow) |
| No parallel tracking | Parent body contains `- [ ]` items that duplicate subtask titles  | Remove body checklists; replace with "See subtasks"      |
| A8 prose scan        | Subtask body / planned summary contains workaround framing        | Rewrite to a code-fix decomposition before posting       |

**A8 prose scan (MANDATORY before posting any decomposition)**

Search every subtask body and the planned plan-review summary for the
surface signatures of workaround framing. If any of the following appears
in a draft, **rewrite before posting** — do not post and "note it"; do
not post and ask the user to choose; rewrite to a fix-only decomposition.

Prohibited phrase patterns (verbatim list — see SKILL.md "Engineering
Integrity (A8) Is Non-Negotiable" for the canonical copy):

- `drift candidate`, `drift gate`, `drift framing` (in the relax-the-test sense)
- `skip on <host>`, `host-conditional`, `skip-on-env`, `xfail on <env>`
- `relax the assertion`, `softening the test`, `loosen the check`
- `pytest.skip`, `xfail`, `marker for env-specific`
- `fix-or-skip menu`, `fix vs skip`
- `we can either fix it or work around it`
- `may need test adjustment`, `test may be too strict`, `the assertion is too tight`
- `compat allowlist`, `fallback path` (when offered as a peer to the fix)

Prohibited structural patterns:

- Any list pairing "fix the code" with "adjust the test" / "skip the test" as peers
- Scope-drift prose that redefines what success means so a workaround qualifies
- Triage columns named "Drift candidate?", "Skip?", "Adjust test?" or similar

If a draft contains any of these, return to Phase 1 and re-decompose: the
correct shape is an investigation subtask that captures the missing
evidence, plus a code-fix subtask parameterised on that evidence. The
test stays as written.

**Output Format** (appended to task body):

```markdown
## Decomposition Proposal

### Subtasks

| ID        | Title       | Estimate | Confidence |
| --------- | ----------- | -------- | ---------- |
| subtask-1 | Description | 0.5d     | medium     |

### Dependency Graph

subtask-1 -> subtask-2 (blocks)
subtask-1 ~> subtask-3 (informs)

### Information Spikes (must resolve first)

- [ ] spike-1: Question we need answered

### Assumptions (load-bearing, untested)

- Assumption 1

### Risks

- Risk 1 (mitigation: ...)

### High-Risk Tags

[For each subtask that meets ANY critic-gate trigger criterion
(see [[worker-dispatch]] "Critic Gate"), add the `high-risk` tag.
This ensures the dispatch-time critic gate activates for these tasks.]
```

## Phase 2: Multi-Agent Review

Supervisor invokes reviewer agents and synthesizes their feedback before human approval.

**Reviewers**:

| Reviewer          | Role                                                        | Mandatory                                 | Model  |
| ----------------- | ----------------------------------------------------------- | ----------------------------------------- | ------ |
| RBG (enforcer)    | Authority check: is task within granted scope?              | Yes                                       | —      |
| Pauli             | Pedantic review: assumptions, logical errors, missing cases | Yes                                       | opus   |
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

[Extract relevant principles/heuristics for this domain — invoke `rbg` for axiom checks]
```

**Step 2: Invoke Reviewers in Parallel**

Dispatch both mandatory reviewers concurrently:

- **pauli** (`aops-core:pauli`, opus) — reviews the decomposition for logical errors, untested assumptions, missing edge cases, scope drift, review-sizing violations, decision/prep dependencies, academic methodology gaps. Returns `PROCEED / REVISE / HALT`.
- **rbg** (`aops-core:rbg`, haiku) — verifies the decomposition stays within granted authority and original scope, no unapproved expansions, no assumed permissions. Returns `OK / WARN / BLOCK`.

Both receive the same review context (decomposition proposal + files affected + relevant principles).

**Step 3: Collect and Parse Responses**

Wait for both reviewers (timeout: 5 minutes each).

Parse responses into structured verdicts:

| Pauli Verdict | RBG Verdict | Combined Result          |
| ------------- | ----------- | ------------------------ |
| PROCEED       | OK          | → APPROVED               |
| PROCEED       | WARN        | → APPROVED (log warning) |
| REVISE        | OK/WARN     | → NEEDS_REVISION         |
| HALT          | any         | → BLOCKED                |
| any           | BLOCK       | → BLOCKED                |

---

### 2.2 Verdict Synthesis Protocol

**On APPROVED**:

```markdown
## Review Synthesis

**Verdict**: APPROVED

### Reviewer Summary

| Reviewer | Verdict | Key Points       |
| -------- | ------- | ---------------- |
| Pauli    | PROCEED | [1-line summary] |
| RBG      | OK      | Within scope     |

### Minor Suggestions (optional)

- [Any non-blocking improvements from reviewers]

→ Proceeding to human approval gate (status='review')
```

Then call `mcp__pkb__update_task(id=task_id, updates={"status": "review", "body": synthesis_markdown})`.

---

## Plan-Review Gate (Phase 2.5)

After synthesizing Pauli + RBG verdicts (Phase 2) and BEFORE any DISPATCH
action, the supervisor MUST check the parent task's status. Per
[[../../remember/references/TAXONOMY.md]] (status transitions — see `TAXONOMY.md:172`),
agents pull only from `queued`. The transition from `review` → `queued` is
the **human approval record** — no separate marker, no extra metadata.

**Gate check** (run exactly once, immediately after Phase 2 synthesis): read `parent.status`. If it is **not** `queued`, halt — append a synthesis summary comment (subtask count, files affected, key risks, pauli + rbg verdicts) and set parent `status = review`. Resume only after the human promotes parent to `queued`; on the next ORIENT the supervisor falls through this gate to DISPATCH.

**Semantics** (explicit):

- If `parent.status != "queued"` (e.g. `review`, `inbox`): **HALT**.
  - Post synthesis summary as a comment on the parent task (subtask count,
    files affected, key risks, Pauli + RBG verdicts).
  - Set parent `status = "review"`.
  - Emit a user-facing summary describing what needs human review.
  - Do NOT transition any subtask out of `inbox` / `ready`.
  - Do NOT dispatch. STOP.
  - Resume only after the user promotes the parent to `queued`; on the next
    ORIENT the supervisor re-enters and falls through this gate to DISPATCH.
- If `parent.status == "queued"`: the human has approved. Proceed to
  DISPATCH exactly as today.

**Approval record**: there is no separate approval marker or metadata — the
status transition `review → queued` performed by the human **is** the
approval record. Do not invent parallel approval tracking.

### Permitted vs prohibited halt content (A8)

Before emitting the user-facing summary, run the A8 prose scan defined in
the Post-Decomposition Self-Check Gate against the _summary text itself_.

**Permitted in the user-facing summary**:

- Specific fix strategies for each failure (one or more, _all of which
  pass the test_)
- Questions of the form: "Which fix do you want?", "Is fix-strategy A or B
  preferred?"
- Genuine information requests where the user has unique knowledge ("Has
  X changed in the environment recently?")

**Prohibited in the user-facing summary**:

- "Drift candidate" columns or any column name signalling test-relaxation
  as a category
- Fix-vs-skip / fix-vs-xfail / fix-vs-allowlist menus
- "Test may be wrong" framings absent independent evidence the test is
  not actually testing what it claims to
- Soliciting user authorisation for an A8-prohibited path ("are you happy
  with X or do you want a workaround?")

**Permitted halt template** — use this exact shape:

```
A8 halt: <test name / failure>. Investigation produced <finding>. Two options:
  1. Fix <code path> at <file:line> by <change>. (chosen)
  2. <alternative implementation, also fixing the failure>
Test stays as written. Filing as <subtask id>.
```

Both options must be fixes that make the failing test pass. A "skip" or
"xfail" or "loosen the assertion" option is NEVER option 2.

**Prohibited halt template** (the prose scan must flag any draft matching
this shape):

```
Test failure: <name>. Drift candidate: test assumes <thing> that no
longer holds. Options:
  - Fix the code (real regression)
  - Update the test (env drift)
  - Skip on <host>
```

If the draft summary matches the prohibited shape, the supervisor MUST
rewrite to the permitted shape before posting. There is no "note the
concern in passing" carve-out — the prohibited content does not reach the
user at all.

---

**On NEEDS_REVISION**:

```markdown
## Review Synthesis

**Verdict**: NEEDS_REVISION

### Issues Requiring Resolution

- **Suggested fix**: [how to address]

2. [Issue from RBG if WARN]: [scope concern]
   - **Suggested fix**: [how to narrow scope]

### Required Actions

- [ ] Address issue 1
- [ ] Address issue 2
- [ ] Re-run review after changes

→ Returning to decomposition phase (status remains `in_progress`; phase annotation: decomposing)
```

Then call `mcp__pkb__update_task(id=task_id, updates={"status": "in_progress", "body": synthesis_markdown})` and re-enter Phase 1 with reviewer feedback.

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

Then call `mcp__pkb__update_task(id=task_id, updates={"status": "blocked", "body": synthesis_markdown})`.

---

### 2.3 Debate Resolution (When Reviewers Disagree)

If reviewers return conflicting verdicts (one PROCEED, one REVISE), initiate a debate round.

**Debate Protocol** (max 2 rounds):

````markdown
## Debate Round 1

### Conflicting Assessments

- **Pauli** says PROCEED: "[rationale]"
- **RBG** says WARN: "[concern]"

### Resolution Attempt

Share rbg's concern back with pauli (or vice versa) and ask whether they MAINTAIN or REVISE their original verdict given the new information. One round of cross-feedback per debate cycle.

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

**Pauli Position** (after debate):
[Their final position]

**Enforcer Position** (after debate):
[Their final position]

### Core Tension

[Supervisor's 1-sentence summary of why they disagree]

### Options for Human

2. **Narrow scope**: Accept RBG's constraint
3. **Request more info**: Specific question to resolve

→ Awaiting human decision (status='review')
```
````

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

**Note**: Domain specialists are advisory. Their concerns inform but don't automatically block — supervisor synthesizes their input alongside mandatory reviewers.
