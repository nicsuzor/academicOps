# Debugging Workflow

Understand the problem before fixing it.

Extends: base-task-tracking, base-verification

## When to Use

Use this workflow when:
- Asking "why doesn't this work?"
- Investigating unexpected behavior
- Facing a bug where the cause is unknown

Do NOT use for:
- Cause already known (use design)

## Constraints

### Investigation Sequencing

1. **Define success criteria** before starting investigation (what does "fixed" mean?)
2. **Create a reproducing test** before attempting any fix (fails now, passes after fix)
3. **Document findings in the task** before routing to a fix workflow

### After Investigation

- Root cause must be documented in the task body

### Exit Routing

After debugging completes, route to the appropriate workflow:
- Fix identified → use design
- If unsure → ask the user

## Triggers

- When bug is reported → define success criteria
- When success criteria are defined → create reproducing test
- When test reproduces the bug → investigate
- When root cause is found → document findings
- When findings are documented → route to appropriate fix workflow

## How to Check

- Success criteria defined: task body contains "## Success Criteria" or explicit "fixed means X"
- Reproducing test exists: a test exists that fails now but will pass when fixed
- Findings documented: task body contains root cause analysis
- Root cause documented: task body contains "## Root Cause" or explicit cause statement
- Simple fix: fix is single-file, obvious change
- Complex fix: fix requires multiple files or design decisions
