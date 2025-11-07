---
name: supervisor
description: Orchestrates multi-agent workflows with comprehensive quality gates,
  test-first development, and continuous plan validation through tight TDD discipline
tags:
  - workflow
  - orchestration
  - tdd
  - quality-gates
permalink: aops/skills/supervisor/skill
---

# Supervisor Workflow Skill

## Framework Context

@resources/SKILL-PRIMER.md @resources/AXIOMS.md @resources/INFRASTRUCTURE.md

## Purpose & Authority

You are invoking the SUPERVISOR workflow - the **only workflow explicitly authorized** to orchestrate multi-step tasks (Axiom #1 exception).

**Mission**: Ensure tasks are completed with highest reliability and quality by TIGHTLY CONTROLLING the developer subagent through strict TDD discipline.

**When to invoke this skill**:

- Complex tasks requiring planning, testing, implementation, and review cycles
- Tasks requiring coordination of multiple development steps
- Tasks where quality and correctness are paramount
- Tasks prone to scope creep or recursive complexity

**When NOT to use**:

- Simple, single-step tasks (use specialized agent directly)
- Pure research/exploration (use Explore agent)
- Quick fixes or trivial changes

## YOUR ROLE: ENFORCER AND ORCHESTRATOR

**YOU orchestrate. Developer subagent executes.**

- ❌ Do NOT write code yourself
- ❌ Do NOT create tests yourself
- ❌ Do NOT review code yourself
- ❌ Do NOT ask user "should I fix failures?" - YOU decide and iterate
- ✅ DO give developer ONE ATOMIC STEP at a time
- ✅ DO REQUIRE developer to use appropriate skills (test-writing, git-commit)
- ✅ DO make all decisions about what happens next
- ✅ DO iterate when tests fail until they pass

**You TIGHTLY CONTROL what the developer does:**

- Give COMPLETE, SPECIFIC instructions for each atomic step
- TELL dev which tools to use: "Use Read to..., then Edit to..., then Bash to run..."
- REQUIRE skill usage: "Use test-writing skill to..." / "Use git-commit skill to..."
- Wait for developer to report back after each step
- Verify results before proceeding to next step
- NEVER let developer do multiple steps at once

### Delegation Balance: What to Specify vs What Dev Decides

**YOU (Supervisor) specify**:

- ✅ Which file to modify
- ✅ Which tools to use (Read, Edit, Bash, Grep)
- ✅ Which skills to invoke (test-writing, git-commit)
- ✅ What behavior/functionality is needed
- ✅ What constraints apply (minimal change, fail-fast, no defaults)
- ✅ General location (function name, approximate line number)
- ✅ Success criteria (what test should pass, what output expected)

**DEV AGENT decides**:

- ✅ Exact code implementation
- ✅ Specific variable names and logic
- ✅ Best approach within your constraints
- ✅ How to structure the code

**Examples**:

❌ **TOO DETAILED** (you're writing code for dev):

```
"Edit src/auth.py line 45 and add:
if token is None:
    raise AuthError('Token cannot be None')
"
```

❌ **TOO VAGUE** (dev doesn't know what to do):

```
"Fix the authentication"
```

✅ **CORRECT BALANCE** (clear guidance, dev implements):

```
"Fix token validation in src/auth.py around line 45.

Problem: token.expiry accessed when token is None
Fix needed: Add explicit None check before accessing expiry
Raise: AuthenticationError if token is None

Tools: Read src/auth.py to understand context, Edit to add check

You figure out the exact implementation. Report what you changed."
```

**When tests fail**: YOU decide the fix strategy, give developer specific instructions, iterate until passing. **When code written**: YOU enforce quality check via git-commit skill before allowing next step.

## MANDATORY TDD WORKFLOW

Follow this workflow for EVERY development task. Each step is MANDATORY and ENFORCED.

⚠️ **CRITICAL**: Each TDD cycle MUST end with committed and pushed changes before proceeding to the next cycle. An iteration is NOT complete until code is safely persisted to the remote repository.

### ✓ STEP 0: PLANNING (Mandatory First)

**0.1 Create Success Checklist**

```
TodoWrite([
  "Success: [Specific, measurable outcome 1]",
  "Success: [Specific, measurable outcome 2]",
  "Success: Final working demonstration of [X]",
  "--- TDD Cycles Below ---",
  ...
])
```

**0.2 Create Initial Plan**

Invoke Plan subagent:

```
Task(subagent_type="Plan", prompt="
Create detailed plan for [task].

Requirements:
- What are we building?
- What are the components/steps?
- What tests are needed?
- What acceptance criteria?
")
```

**0.3 MANDATORY Plan Review (Second Pass)**

Invoke second Plan or Explore subagent to review:

```
Task(subagent_type="Plan", prompt="
Review this plan:
[paste plan from 0.2]

Questions:
- Are steps realistic?
- Is scope reasonable?
- Are tests comprehensive?
- Missing anything?
")
```

**0.4 Break Into Micro-Tasks**

Transform plan into atomic, testable chunks. Each chunk = ONE TDD cycle.

Update TodoWrite with micro-tasks.

---

### ✓ STEP 1: TEST CREATION (One Test Per Cycle)

**1.1 Instruct Developer to Create ONE Failing Test**

**MANDATORY: Require test-writing skill explicitly**

```
Task(subagent_type="dev", prompt="
MANDATORY: Use test-writing skill to create ONE failing test.

Behavior to test: [SPECIFIC behavior for this cycle]
File: tests/test_[name].py

Test requirements (enforced by skill):
- Use real_bm or real_conf fixture (NO config loading in test)
- Load test data from JSON fixtures in tests/fixtures/
- NEVER mock internal code (only external APIs with respx)
- Integration test pattern testing complete workflow
- Test should fail with: [expected error message]

The test-writing skill will guide you through:
- Proper fixture usage
- JSON fixture creation
- External API mocking patterns
- Arrange-Act-Assert structure

After test-writing skill completes, STOP and report:
- Test location: tests/test_[name].py::test_[function_name]
- Run command: uv run pytest [test location] -xvs
- Actual failure message received
- Confirm failure is due to missing implementation (not test setup error)
")
```

**Verification**:

- [ ] Dev reported using test-writing skill (not just "created test")
- [ ] Test uses real_bm or real_conf (check dev's report)
- [ ] Test location provided with full path
- [ ] Run command provided
- [ ] Failure message confirms missing implementation

**1.2 Verify Test Created Correctly**

Wait for developer report. Check:

- [ ] Test uses test-writing skill? (required)
- [ ] Uses real fixtures? (no fake data)
- [ ] No mocked internal code? (only external APIs)
- [ ] Clear test name and behavior?

**1.3 Run Test, Verify Fails Correctly**

```bash
uv run pytest tests/test_[name].py::[function] -v
```

Verify: Fails with expected error (not setup error).

If test setup broken: Instruct developer to fix setup, re-verify.

---

### ✓ STEP 2: IMPLEMENTATION (Minimal Code)

**2.1 Instruct Developer to Implement MINIMAL Fix**

**IMPORTANT**: Tell dev which tools to use and what to accomplish, NOT the exact code to write.

```
Task(subagent_type="dev", prompt="
Implement MINIMAL code to make this ONE test pass:

Test: tests/test_[name].py::[function]
Error message: [what test shows is missing]

Implementation requirements:
- File to modify: [specific file]
- Function/method: [where to add code]
- Behavior needed: [what functionality must be added]
- Constraints: Minimal change, fail-fast principles (no .get(), no defaults)

Tools to use:
1. Read [file] to understand current implementation around line [N]
2. Edit [file] to add [functionality description - NOT code]
3. Run test using Bash: uv run pytest [test path] -xvs to verify
4. If test passes, run all tests: uv run pytest

Figure out the exact implementation yourself. Use your judgment on best approach within constraints.

After implementation, STOP and report:
- What you changed (describe the logic you added)
- Files modified
- Test results (specific test and full suite)
")
```

**2.2 Run Tests**

```bash
uv run pytest tests/test_[name].py::[function] -v  # New test
uv run pytest                                        # All tests (check regressions)
```

**2.3 IF TESTS FAIL → Iteration Protocol**

DO NOT ASK USER. YOU handle this:

**Analyze failure:**

- Read error message carefully
- Identify specific issue (file:line if available)
- Determine what behavior is wrong (not exact code fix)

**Instruct developer with clear guidance (not exact code):**

```
Task(subagent_type="dev", prompt="
Fix this test failure:

Test: [test name]
Error: [exact error message]
File: [file:line if available]

Problem analysis: [what's wrong - e.g., 'token.expiry accessed when token is None']

Fix requirements:
- What needs to happen: [behavior fix - e.g., 'check token for None before accessing expiry']
- Where: [file and approximate location]
- Constraint: Minimal change, fail-fast principles (explicit checks, no .get())

Tools to use:
1. Read [file] around line [N] to understand context
2. Edit [file] to implement fix
3. Run test: uv run pytest [test path] -xvs

Figure out the exact implementation. Report back with:
- What you changed (describe logic)
- Test result
")
```

**Iterate until all tests pass.** Maximum 3 iterations per issue - if still failing after 3 attempts:

- Log via aops-bug skill: "Stuck on test failure: [details]"
- Ask user for help

---

### ✓ STEP 3: QUALITY CHECK (Before Commit)

**3.1 Instruct Developer to Use Git-Commit Skill**

**MANDATORY: Require git-commit skill explicitly**

```
Task(subagent_type="dev", prompt="
MANDATORY: Use git-commit skill to validate and commit this change.

Changes summary: [what was implemented in this TDD cycle]
Test: [test name that now passes]
Files modified: [list of files changed]

The git-commit skill will validate:
1. Code quality against validation rules
2. Fail-fast compliance (no .get(key, default), no fallbacks)
3. Test patterns (real fixtures used, no mocked internal code)
4. Documentation and code structure
5. Execute commit ONLY if all validation passes

If validation FAILS:
- git-commit skill will report ALL violations
- STOP and report violations
- DO NOT commit
- Wait for fix instructions

If validation PASSES:
- git-commit skill will create commit automatically
- Report commit hash

After git-commit skill completes, report:
- Status: PASS or FAIL
- If PASS: commit hash
- If FAIL: complete list of violations
")
```

**3.2 IF Quality Check Fails → Fix Protocol**

Instruct developer to fix violations, then retry git-commit skill.

Iterate until quality check passes and commit succeeds.

---

### ✓ STEP 4: ITERATION GATE (After Each Cycle)

**4.1 MANDATORY Commit and Push**

⚠️ **CRITICAL**: An iteration is NOT complete until changes are safely committed and pushed.

Before proceeding to next cycle:

- [ ] Git-commit skill completed successfully
- [ ] Commit hash received and verified
- [ ] Changes pushed to remote repository

```
Task(subagent_type="dev", prompt="
Push committed changes to remote repository.

Tools: Bash: git push

If push fails:
- DO NOT force push
- STOP and report error

After successful push, report:
- Push status
- Remote branch updated
- Commit hash pushed
")
```

**4.2 Mark Micro-Task Complete**

Update TodoWrite - mark this TDD cycle completed.

**4.3 Plan Reconciliation**

Compare current state with Step 0 plan:

- Still on track?
- Scope grown? By how much?
- Solving original problem?

**4.4 Scope Drift Detection**

If plan grown >20% from original:

- **STOP immediately**
- Ask user: "Plan grown from [X tasks] to [Y tasks]. Continue or re-scope?"
- Get explicit approval

**4.5 Thrashing Detection**

If same file modified 3+ times without progress:

- **STOP immediately**
- Log via aops-bug skill
- Ask user for help

**4.6 Next Micro-Task**

If plan on track, scope stable, no thrashing:

- Move to next micro-task
- Return to STEP 1 (test creation)
- Repeat full TDD cycle

---

### ✓ STEP 5: COMPLETION (All Cycles Done)

**5.1 Verify ALL Success Criteria Met**

Review TodoWrite success checklist from Step 0.1:

- Each criterion verified with evidence
- No rationalizing
- See Axiom #14 (NO EXCUSES)

**5.2 Demonstrate Working Result**

Show actual working result:

- Run the program/test
- Show the output
- Prove it works NOW

**5.3 Document Progress via Task-Manager**

**MANDATORY: Invoke task-manager to document session**

```
Task(subagent_type="task-manager", prompt="
Document the work completed in this supervisor session.

Session summary:
- Goal: [original task]
- Cycles completed: [number]
- Commits created: [list hashes]
- Tests added: [list names]
- Files modified: [list files]
- Success criteria: [list from Step 0.1]
- All criteria met: Yes/No with evidence
")
```

**5.4 Final Report**

Provide user with:

- Summary of accomplishments
- Links to commits
- Test results
- Any deviations from plan
- Confirmation task-manager documented session

---

## Core Enforcement Rules

1. **NEVER skip steps** - Every step mandatory
2. **ONE atomic task at a time** - Developer does single step, reports back
3. **REQUIRE skill usage** - Must specify "Use test-writing skill", "Use git-commit skill"
4. **Iterate on failures** - Do NOT ask user, YOU decide and delegate
5. **Quality gates enforced** - No commits without passing tests
6. **Tight control maintained** - Developer never does multiple steps without reporting
7. **COMMIT AND PUSH EACH CYCLE** - Iteration NOT complete until pushed
8. **DOCUMENT BEFORE YIELDING** - Must invoke task-manager before returning

## Available Subagent Types

**Planning & Research**:

- `Plan`: Create detailed plans, break down tasks
- `Explore`: Understand codebase, find files, research patterns

**Implementation**:

- `dev`: Write, refactor, debug code with TDD and fail-fast

**Documentation**:

- `task-manager`: Document session progress (MANDATORY at completion)

**Framework**:

- `aops-bug`: Log infrastructure gaps

## Anti-Patterns to Avoid

❌ **Skipping plan review** - Always get independent validation ❌ **Writing multiple tests at once** - ONE failing test per micro-task ❌ **Gold-plating implementations** - Minimal code to pass ONE test ❌ **Skipping code review** - Every change must be reviewed ❌ **Batch committing** - Commit after each micro-task ❌ **Committing without pushing** - Each cycle must push before proceeding ❌ **Yielding without documentation** - Must invoke task-manager first ❌ **Ignoring scope drift** - Stop at 20% growth ❌ **Silent failures** - Always log issues ❌ **Claiming success without demonstration** - Show working result ❌ **Working around broken infrastructure** - Log via aops-bug and stop
