# Decompose Workflow

Break goals into actionable work under genuine uncertainty.

Extends: base-task-tracking

## When to Use

Use this workflow when:
- Working on multi-month projects (dissertations, books, grants)
- Answering "what does X actually require?"
- Facing vague deliverables with unclear dependencies
- The path forward is unknown

Do NOT use for:
- Known tasks with clear steps (use design or minor-edit)
- Work completable in one session (use minor-edit)

## Constraints

### Sequencing

Each step must complete before the next:

1. **Goal must be articulated** before identifying components
2. **Assumptions must be documented** before creating probes
3. **Probes must be identified** before creating components
4. **Review task must exist** before working on any subtask
5. **Review must be approved** before subtasks can be worked

### After Decomposition

- At least one task must be actionable NOW
- A review task must be created that blocks other subtasks

### Always True

- Keep decomposition coarse before fine-grained
- Acknowledge uncertainty explicitly
- Maintain at least one actionable task

### Never Do

- Never expand everything at once (premature detail)
- Never block on ambiguity (create placeholder tasks instead)
- Never hide assumptions
- Never plan as if everything is known
- Never over-decompose

### Conditional Rules

- If ambiguity exists: create a placeholder task rather than blocking
- If an unknown is discovered: create a probe task, not an implementation task
- If multiple probes are possible: select the cheapest probe first

## Triggers

- When goal is received → articulate the goal clearly
- When goal is articulated → surface assumptions
- When assumptions are documented → find affordable probes
- When probes are identified → create coarse components
- When components are created → create a blocking review task
- When review is approved → enable subtasks for work

## How to Check

- Goal articulated: task body contains a clear goal statement (not a vague request)
- Assumptions documented: task body contains "## Assumptions" or an explicit assumption list
- Probes identified: at least one child task exists with type "probe" or "learn"
- Review task exists: a child task with "REVIEW" in title exists and blocks other subtasks
- Review approved: review task status is "done"
- One task actionable now: at least one leaf task has no unmet dependencies and status is not "blocked"
- Coarse before fine: initial decomposition has 3-7 components (not 20+)
- Ambiguity exists: requirements contain "unclear", "TBD", or question marks
- Unknown discovered: during analysis, found a question that cannot be answered without research
- Multiple probes possible: more than one way exists to validate an assumption
