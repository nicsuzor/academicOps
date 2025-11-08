# Supervisor Challenge Response Framework

This reference provides decision-making patterns for when the supervisor encounters challenges during orchestration.

## Decision Framework Overview

When challenges arise, the supervisor has THREE core responsibilities:

1. **ANALYZE** - Understand what went wrong and why
2. **DECIDE** - Choose the appropriate response strategy
3. **DELEGATE** - Give dev agent specific, actionable instructions

**NEVER**:

- Ask user "should I fix this?" - YOU decide
- Work around problems - Fix them or escalate
- Continue without addressing root cause
- Give up after first failure

## Challenge Categories

### Category 1: Test Failures

#### Scenario: Test fails after implementation

**Analysis checklist**:

- [ ] Is error message clear and specific?
- [ ] Is it a coding error (wrong logic)?
- [ ] Is it a configuration issue (wrong setup)?
- [ ] Is it a test issue (test written incorrectly)?
- [ ] Is file:line information available?

**Decision tree**:

```
Q: Is error message clear?
├─ YES → Can identify specific fix?
│   ├─ YES → Instruct dev to fix (Pattern A)
│   └─ NO → Instruct dev to investigate (Pattern B)
└─ NO → Instruct dev to add debugging (Pattern C)

Q: Has this been attempted 3+ times?
├─ YES → STOP, use aops-bug skill, ask user
└─ NO → Continue iteration
```

**Response Pattern A: Clear Fix Needed**

```
Task(subagent_type="dev", prompt="
Fix this test failure:

Test: [test name with full path]
Error: [exact error message]
File: [file:line if available]

Root cause: [your analysis of what's wrong]

Fix required:
- [Specific change needed]
- [Why this fix addresses the error]
- [Constraints: minimal change, fail-fast principles]

Steps:
1. Read [file] to understand current implementation
2. Edit [file] to [specific change]
3. Run test: uv run pytest [test path] -xvs
4. Verify error resolved

Report back:
- What you changed
- Test result (pass/fail)
- If still failing: new error message
")
```

**Response Pattern B: Investigation Needed**

```
Task(subagent_type="dev", prompt="
Investigate this test failure:

Test: [test name]
Error: [error message]

Unclear: [what's ambiguous about the error]

Investigation steps:
1. Read [affected file] around line [N]
2. Use Grep to search for [relevant pattern]
3. Check if [specific condition] exists
4. Report findings: what the code currently does vs what test expects

Do NOT fix yet - investigate and report back first.
")
```

**Response Pattern C: Add Debugging**

```
Task(subagent_type="dev", prompt="
Add debugging to diagnose test failure:

Test: [test name]
Error: [vague error message]

Add debug output:
1. Edit [test file] to add print statements showing:
   - Value of [variable] before operation
   - Type of [variable]
   - Result of [intermediate step]
2. Run test: uv run pytest [test] -xvs
3. Report: debug output showing where failure occurs

After diagnosing, we'll remove debug code and fix root cause.
")
```

#### Scenario: All tests pass but functionality doesn't work

**This indicates test is wrong, not implementation.**

**Response**:

```
Task(subagent_type="dev", prompt="
The test passes but functionality doesn't work correctly. Test needs fixing.

Current test: [test name]
Problem: [what's not being tested that should be]

Use test-writing skill to improve test:

Missing test coverage:
- [Scenario not tested]
- [Edge case not covered]
- [Expected behavior not verified]

Requirements:
- Test should FAIL right now (revealing the bug)
- Use real fixtures (real_bm or real_conf)
- Test actual behavior, not mocked behavior
- After test created and failing, we'll fix the implementation

Report back:
- Enhanced test location
- How to run it
- Confirm it fails (shows the real bug)
")
```

---

### Category 2: Code Quality Violations (git-commit skill failures)

#### Scenario: git-commit skill blocks with violations

**Analysis checklist**:

- [ ] Are violations clearly listed with file:line?
- [ ] Do I understand which rule was violated?
- [ ] Is fix straightforward?
- [ ] Are there multiple violations?

**Response Pattern: Fix Violations Serially**

```
Task(subagent_type="dev", prompt="
Fix these code quality violations:

git-commit skill blocked with:

Violation 1: [specific violation]
- File: [file:line]
- Rule: [which standard violated]
- Current code: [problematic pattern]
- Required fix: [specific change needed]

[If multiple violations, list all but fix ONE at a time]

Steps:
1. Read [file] to understand context
2. Edit [file] at line [N] to [specific fix]
3. Use git-commit skill again to re-validate

Fix ONLY Violation 1 in this step. Report back after re-validation.
")
```

**After first violation fixed**:

```
Violation 1: FIXED ✓

Moving to Violation 2:
[Repeat pattern for next violation]
```

**If violations keep appearing (3+ iterations)**:

```
Multiple violations persist after 3 fix attempts.

Possible issues:
- Systematic problem (whole file violates standards)
- git-commit skill misconfigured
- Understanding gap on what's required

Action: Use aops-bug skill to document issue:
- Pattern: Repeated git-commit violations
- Files affected: [list]
- Violations: [summary]
- Attempts made: [what was tried]

Then ask user: "Stuck on code quality violations. Should I:
A) Refactor entire file to meet standards
B) Review validation rules (may be too strict)
C) Different approach?"
```

---

### Category 3: Scope Drift Detection

#### Scenario: Plan has grown >20% from original

**Immediate action**: STOP work.

**Response to user**:

```
🚨 SCOPE DRIFT DETECTED

Original plan: [X tasks]
Current plan: [Y tasks] (+[Z]% growth)

Cause:
- [Why scope grew - discovered complexity, new requirements, etc.]

Current progress:
- Completed: [N tasks]
- Remaining: [M tasks]

Options:
A) Continue with expanded scope (commit to larger effort)
B) Re-scope to original boundaries (cut newly added tasks)
C) Pause and break into phases (complete current, plan next separately)

Which direction should I take?
```

**Do NOT**:

- Continue without user approval
- Silently expand scope
- Rationalize why growth is acceptable

**After user decides**:

- Update TodoWrite with approved scope
- Document decision in planning section
- Reset thrashing/drift counters

---

### Category 4: Thrashing Detection

#### Scenario: Same file modified 3+ times without progress

**Immediate action**: STOP work.

**Analysis**:

```
File: [filename]
Modifications:
1. [Commit 1]: [what changed]
2. [Commit 2]: [what changed]
3. [Commit 3]: [what changed]

Pattern:
- [ ] Undoing previous changes?
- [ ] Fixing same issue repeatedly?
- [ ] Different approaches tried?
- [ ] Tests still failing after 3 attempts?

Root cause hypothesis: [your analysis]
```

**Response**:

```
Use aops-bug skill to log thrashing:

Issue: Thrashing detected on [file]
Pattern: [describe modification pattern]
Attempts: [summarize 3+ modifications]
Status: No progress after [N] attempts

Hypothesis: [why thrashing occurred]

After logging, ask user:
"Stuck thrashing on [file]. Attempted approaches:
1. [Approach 1]
2. [Approach 2]
3. [Approach 3]

All failed with [outcome]. Need guidance on:
- Different architectural approach?
- Missing prerequisite fix?
- Mis understanding requirement?

How should I proceed?"
```

---

### Category 5: Dev Agent Not Following Instructions

#### Scenario: Dev agent does multiple steps instead of one

**Immediate response**:

```
Task(subagent_type="dev", prompt="
STOP. You did multiple steps when instructed to do ONE.

Required: [the ONE thing you were supposed to do]

What you did: [list multiple things dev did]

Consequences:
- I cannot verify each step individually
- Risk of compounding errors
- Violation of atomicity principle

Required action:
- Report current state
- Confirm you will do ONLY the ONE specified task in next instruction
- Wait for next single-task instruction
")
```

**After dev confirms**: Re-issue original instruction with STRONGER emphasis on single task.

**If pattern repeats (3+ times)**:

```
Use aops-bug skill to log:

Issue: Dev agent repeatedly violates atomicity (does multiple steps)
Pattern: Supervisor says "do X", dev does "X, Y, Z"
Instances: [list 3+ examples]
Impact: Cannot verify steps individually, work becomes uncontrollable

This is an agent behavior violation (Axiom #1: DO ONE THING).

After logging, continue with EXTREME explicit instructions:
"Do ONLY step 1. STOP after step 1. Do NOT proceed to step 2. Report back after step 1 completes."
```

---

#### Scenario: Dev agent skips required skill usage

**Immediate response**:

```
Task(subagent_type="dev", prompt="
STOP. You did not use the required skill.

Required: Use [skill-name] skill to [task]

What you did: [direct work without skill]

Why this is wrong:
- [Skill-name] skill enforces [standards/patterns]
- Direct work bypasses [quality gates]
- Results may not meet [requirements]

Required action:
1. Undo work done without skill (if applicable)
2. Use [skill-name] skill as instructed
3. Report results from skill usage
")
```

**If pattern repeats**:

```
Use aops-bug skill to log:

Issue: Dev agent skips required skill usage
Skill: [skill-name]
Pattern: Supervisor requires skill, dev works directly
Instances: [examples]
Impact: Quality gates bypassed, standards not enforced

After logging, strengthen instructions:
"MANDATORY: Use [skill-name] skill. This is not optional. The skill MUST be invoked. Report skill output, not direct work results."
```

---

### Category 6: Infrastructure Failures

#### Scenario: Script/hook/tool fails with error

**Analysis**:

```
Component: [script/hook/tool name]
Error: [full error message]
Context: [what operation was being attempted]

Is this:
- [ ] User error (wrong usage)?
- [ ] Environment issue (missing dependency)?
- [ ] Actual bug in infrastructure?
```

**Response Pattern: User Error**

```
Error is due to incorrect usage.

Correct usage: [show proper command/approach]

Retry with correct usage:
[specific corrected instruction]
```

**Response Pattern: Environment Issue**

```
Error indicates missing dependency or environment problem.

Issue: [specific problem - missing Python package, wrong PATH, etc.]

Cannot proceed until environment fixed.

Report to user:
"Infrastructure blocker: [component] requires [dependency] but it's [missing/wrong version].

Error: [error message]

Need: [specific fix required - install package, set env var, etc.]

Blocking further work until this is resolved."
```

**Response Pattern: Infrastructure Bug**

```
Use aops-bug skill to log infrastructure bug:

Component: [script/hook/tool]
Error: [full error with stack trace]
Expected: [what should happen]
Actual: [what happened]
Reproduction: [steps to trigger]

After logging:

Report to user:
"Infrastructure bug discovered in [component].

Issue: [brief description]
Logged: Issue #[number] in academicOps
Impact: [what's blocked]

Options:
A) Work around this issue (if possible) - you'll need to specify workaround
B) Fix infrastructure bug now (may take time)
C) Defer task until infrastructure fixed

How should I proceed?"
```

---

### Category 7: Uncertainty / Ambiguity

#### Scenario: Requirement is unclear or has multiple valid approaches

**DO NOT guess or assume.**

**Response to user**:

```
Ambiguity encountered: [specific unclear aspect]

Context: [what we're trying to accomplish]

Unclear:
- [Specific question 1]
- [Specific question 2]

Multiple valid approaches:
A) [Approach 1]: [tradeoffs]
B) [Approach 2]: [tradeoffs]
C) [Approach 3]: [tradeoffs]

Need decision on:
1. [Specific choice needed]
2. [Specific choice needed]

Which approach should I take?
```

**After user clarifies**:

- Document decision in plan
- Proceed with chosen approach
- Reference decision in commit messages

---

## Response Time Guidelines

| Challenge              | Analysis Time | Max Iterations  | Escalation Point                      |
| ---------------------- | ------------- | --------------- | ------------------------------------- |
| Test failure           | 30 seconds    | 3 attempts      | After 3rd failure                     |
| Code violation         | 20 seconds    | 5 violations    | After 3+ iteration loops              |
| Scope drift            | Immediate     | N/A             | Immediate (always escalate)           |
| Thrashing              | Immediate     | 3 modifications | After 3rd modification                |
| Agent non-compliance   | Immediate     | 3 violations    | After 3rd violation                   |
| Infrastructure failure | 1 minute      | 1 retry         | After 2nd failure or if bug confirmed |
| Uncertainty            | Immediate     | N/A             | Immediate (never guess)               |

## Anti-Patterns to Avoid

### ❌ Asking User About Routine Decisions

**BAD**:

```
"Test failed with NameError. Should I fix it?"
```

**GOOD**:

```
[Analyze error]
[Instruct dev to fix specific issue]
[Iterate if needed]
[Only escalate after 3+ failures]
```

---

### ❌ Continuing Despite Red Flags

**BAD**:

```
[Scope grows to 20 tasks from original 10]
[Supervisor continues without mentioning]
```

**GOOD**:

```
[Scope hits 20% growth threshold]
🚨 STOP IMMEDIATELY
[Notify user with options]
[Wait for approval]
```

---

### ❌ Vague Error Reporting

**BAD**:

```
"Something's wrong with the authentication code"
```

**GOOD**:

```
"Test failed at src/auth/oauth.py:45 with AttributeError: 'NoneType' has no attribute 'expiry'.
Root cause: Token validation doesn't check for None before accessing expiry.
Instructing dev to add explicit None check."
```

---

### ❌ Working Around Infrastructure Issues

**BAD**:

```
[Hook fails]
"Let's skip the hook and commit directly"
```

**GOOD**:

```
[Hook fails]
"Hook validation failed. This is an infrastructure issue.
Using aops-bug skill to log.
Blocking work until hook is fixed - we don't bypass quality gates."
```

---

## Decision-Making Principles

1. **Fail-Fast** - Stop immediately when thresholds hit (3 failures, 20% drift, 3 violations)

2. **Root Cause** - Always analyze WHY before deciding HOW to respond

3. **Explicit** - Give dev specific, actionable instructions (not "fix it")

4. **Accountable** - YOU make decisions on routine issues (test failures, violations)

5. **Escalate Appropriately** - User decides on scope, approach, priorities; YOU decide on implementation tactics

6. **Document** - Use aops-bug skill for patterns, infrastructure issues, systematic problems

7. **No Workarounds** - Fix problems or escalate; don't route around them

## Summary

When challenges arise:

1. **STOP** - Don't continue blindly
2. **ANALYZE** - Understand what and why
3. **DECIDE** - Choose response strategy from patterns above
4. **ACT** - Give dev specific instructions OR escalate to user
5. **VERIFY** - Check that response resolved the challenge
6. **ITERATE** - If not resolved, try next approach (up to threshold)
7. **ESCALATE** - When threshold hit, use aops-bug and ask user

The supervisor's job is to make the hard decisions so the dev agent can focus on atomic execution.
