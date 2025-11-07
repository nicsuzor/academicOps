# Supervisor Delegation Architecture

This reference clarifies the multi-level delegation system and provides patterns for effective orchestration.

## Terminology Clarification

### Three Levels of Abstraction

```
SUPERVISOR (orchestrator)
    ↓ invokes
SUB-AGENTS (specialized workers: dev, Plan, Explore, etc.)
    ↓ use
TOOLS (Read, Write, Bash, Grep, etc.)
    AND
SKILLS (test-writing, git-commit, etc.)
```

**Level 1: Supervisor**

- YOU - the orchestrator
- Breaks down complex tasks
- Delegates to sub-agents
- Makes decisions when challenges arise
- Manages TodoWrite and overall plan
- Does NOT directly use tools or write code

**Level 2: Sub-agents**

- Specialized workers (dev, Plan, Explore, analyst)
- Each does ONE SPECIFIC THING
- Uses tools (Read, Write, Bash) to accomplish work
- Invokes skills (test-writing, git-commit) when required
- Reports back to supervisor after completing atomic task

**Level 3: Tools & Skills**

- Tools: Built-in capabilities (Read, Write, Bash, Grep, Glob)
- Skills: Packaged workflows (test-writing, git-commit, aops-bug)
- Sub-agents use these to do their work
- Supervisor does NOT directly use these (delegates instead)

## Correct Delegation Patterns

### ❌ INCORRECT: Supervisor Using Tools Directly

```
# DON'T DO THIS - Supervisor shouldn't use tools directly
Supervisor:
  Read src/auth/oauth.py          # ❌ Wrong level
  Write tests/test_oauth.py       # ❌ Wrong level
  Bash: uv run pytest              # ❌ Wrong level
```

### ✅ CORRECT: Supervisor Delegates to Sub-agent, TELLS Which Tools to Use

```
# DO THIS - Supervisor delegates and SPECIFIES which tools to use
Supervisor:
  Task(subagent_type="dev", prompt="
    Tools to use:
    1. Read src/auth/oauth.py to understand token validation logic
    2. Use test-writing skill to create failing test for OAuth login
    3. Run test with Bash: uv run pytest tests/test_oauth.py -xvs

    Goal: Create failing test that shows OAuth login needs implementation
    Constraint: Use real_bm fixture, test complete workflow

    After test created, report:
    - Test location (file::function)
    - Failure message
    - Confirm test uses real_bm fixture
  ")
```

**In this pattern**:

- Supervisor: Delegates AND tells which tools (Read, Skill, Bash)
- Supervisor: Specifies goal and constraints (NOT exact code)
- Dev sub-agent: Uses specified tools, figures out exact implementation
- Dev sub-agent: Reports back
- Supervisor: Receives report, makes next decision

**Balance achieved**:

- Not too vague: Dev knows which tools and what to accomplish
- Not too detailed: Dev figures out exact implementation
- Clear success criteria: Dev knows what "done" looks like

---

## Addressing the Feedback: Moving from Monolithic to Delegated

The feedback correctly identifies that we need to break down workflows into explicit sub-agent calls.

### Current Pattern (Monolithic - What Feedback Saw)

```
Agent does everything:
1. Read code
2. Write test
3. Run test
4. Modify code
5. Run test again
6. Commit
```

This is ONE agent doing a sequence of tasks.

### Target Pattern (Delegated - What We're Building)

```
Supervisor orchestrates:

1. Task(subagent_type="dev", prompt="
     Use test-writing skill to create failing test.
     Report: test location, failure message
   ")

   [Wait for dev report]
   [Supervisor analyzes: test created correctly? ✓]

2. Task(subagent_type="dev", prompt="
     Read src/auth/oauth.py line 45 where error occurs.
     Edit to add token None check.
     Report: what changed
   ")

   [Wait for dev report]
   [Supervisor analyzes: change looks correct? ✓]

3. Task(subagent_type="dev", prompt="
     Run test: uv run pytest tests/test_oauth.py::test_login -xvs
     Report: pass or fail with error message
   ")

   [Wait for dev report]
   [Supervisor analyzes: test passed? ✓]

4. Task(subagent_type="dev", prompt="
     Use git-commit skill to validate and commit.
     Report: commit hash or violations
   ")

   [Wait for dev report]
   [Supervisor analyzes: commit succeeded? ✓]
```

**Key differences**:

- Each Task() is ONE atomic operation
- Supervisor waits for report after each
- Supervisor makes decision about next step
- Supervisor controls the flow, sub-agent executes

---

## Delegation Granularity Levels

The feedback suggests breaking down into smaller, more specialized sub-agents. Here's how to think about granularity:

### Level 1: Coarse-Grained (What We Have Now)

```
Task(subagent_type="dev", prompt="
  Create test, implement code, run tests, commit
")
```

**Problem**: Dev does too much autonomously, supervisor loses control.

### Level 2: Medium-Grained (Current Best Practice)

```
Task 1: "Create failing test using test-writing skill"
[Report back]

Task 2: "Implement minimal code to pass test"
[Report back]

Task 3: "Run all tests to check regressions"
[Report back]

Task 4: "Use git-commit skill to validate and commit"
[Report back]
```

**Good**: Supervisor controls flow, makes decisions between steps.

### Level 3: Fine-Grained (Future Direction)

```
Task 1: "Read src/auth/oauth.py and understand token validation"
[Report: summary of current implementation]

Task 2: "Use test-writing skill to create failing test"
[Report: test location, failure message]

Task 3: "Run test to verify it fails: uv run pytest [test]"
[Report: failure confirmed]

Task 4: "Edit src/auth/oauth.py line 45 to add None check"
[Report: exact change made]

Task 5: "Run test again to verify it passes"
[Report: test passes]

Task 6: "Run all tests to check regressions"
[Report: all tests pass]

Task 7: "Use git-commit skill to validate and commit"
[Report: commit hash]
```

**Most control**: Each sub-agent call does ONE operation, reports back immediately.

---

## When Dev Sub-agent Uses Tools vs Skills

### Dev Sub-agent Uses TOOLS for:

- Reading files: `Read src/file.py`
- Writing files: `Write tests/test.py`
- Editing files: `Edit src/file.py`
- Running commands: `Bash: uv run pytest`
- Searching: `Grep pattern`, `Glob *.py`

### Dev Sub-agent Invokes SKILLS for:

- Creating/modifying tests: `Skill(command: "test-writing")`
- Committing code: `Skill(command: "git-commit")`
- Logging bugs: `Skill(command: "aops-bug")`
- Managing issues: `Skill(command: "github-issue")`

**Supervisor's instruction pattern**:

```
Task(subagent_type="dev", prompt="
  [Instructions that tell dev which tools to use]
  [Instructions that require specific skills]

  Example:
  Read src/auth/oauth.py to understand current logic.

  Use test-writing skill to create failing test.

  Run test using Bash: uv run pytest tests/test_oauth.py -xvs

  Report back with test location and failure message.
")
```

---

## Supervisor's Decision-Making After Each Report

After each sub-agent reports back, supervisor must:

### 1. Verify Success Criteria Met

```
Dev reported:
- Test created: tests/test_oauth.py::test_user_login
- Test fails with: "AttributeError: token has no attribute 'expiry'"
- Test uses real_bm fixture ✓

Supervisor checks:
✓ Test location provided?
✓ Failure message shows missing implementation?
✓ test-writing skill was used?
✓ Real fixture used (not mocked)?

Decision: SUCCESS → Move to next step (implement code)
```

### 2. Handle Failures

```
Dev reported:
- Test created: tests/test_oauth.py::test_user_login
- Test fails with: "ImportError: cannot import real_bm"
- ERROR: This is a test setup error, not implementation missing

Supervisor checks:
✗ Failure shows missing implementation? NO - this is setup error

Decision: FAILURE → Instruct dev to fix test setup
  "Fix test setup error: import real_bm from correct location"
```

### 3. Make Strategic Decisions

```
Dev reported:
- Test fails with: "Database connection timeout"

Supervisor analyzes:
- This is infrastructure issue, not code bug
- Cannot proceed with implementation until DB fixed

Decision: ESCALATE to aops-bug skill
  "Use aops-bug skill to log infrastructure issue: DB timeout"
Then STOP and notify user
```

---

## Evolving to Higher-Level Instructions (Feedback Point 3)

The feedback suggests evolving from detailed instructions to high-level goals.

### Current (Detailed Instructions)

```
Task(subagent_type="dev", prompt="
  Edit src/auth/oauth.py.
  Find the validate_token() function at line 45.
  Add this code before the expiry check:
    if token is None:
        raise AuthenticationError('Token cannot be None')
  Make no other changes.
")
```

**Pros**: Very clear, low risk of mistakes **Cons**: Requires supervisor to know exact implementation details

### Near-Term Evolution (Goal + Constraints)

```
Task(subagent_type="dev", prompt="
  Implement token validation in src/auth/oauth.py.

  Goal: Add None check before accessing token.expiry
  Location: validate_token() function (around line 45)
  Behavior: Raise AuthenticationError if token is None

  Constraints:
  - Minimal change only (just the None check)
  - Follow fail-fast principles (explicit check, no .get())
  - Must make test pass: tests/test_oauth.py::test_user_login

  After implementation, report what you changed.
")
```

**Pros**: More autonomous, dev figures out exact implementation **Cons**: Still fairly prescribed

### Long-Term Vision (High-Level Goal)

```
Task(subagent_type="dev", prompt="
  Implement token validation to pass test: tests/test_oauth.py::test_user_login

  Test expects: AuthenticationError when token is None
  Current code: No None check, fails when accessing token.expiry

  Constraints:
  - Minimal change only
  - Follow fail-fast principles
  - Must handle None tokens gracefully

  Figure out the best approach and implement it.
  Report back with your implementation strategy and changes made.
")
```

**Pros**: Highly autonomous, dev agent reasons about solution **Cons**: Requires more sophisticated dev agent, risk of over-engineering

**Recommendation**: Start with **Near-Term Evolution** level. As dev agent demonstrates consistent good judgment, gradually increase autonomy.

---

## Improved Decision-Making for Challenges (Feedback Point 2)

The feedback suggests supervisor should handle unexpected challenges better.

### Current Pattern: Assume Success

```
Task: "Run tests"
[Dev reports test failure]
Supervisor: "Fix the error in line X"
[Assumes supervisor knows the fix]
```

### Improved Pattern: Analyze Before Deciding

```
Task: "Run tests"
[Dev reports: "Test failed with AttributeError at line 45"]

Supervisor analyzes:
Q1: Is error message clear enough to know the fix?
├─ YES → Instruct specific fix
└─ NO → Need more information
    ├─ Task: "Read line 45 and surrounding context"
    │   [Dev reports code]
    │   [Supervisor now understands issue]
    │   └─ Instruct specific fix
    └─ OR: Task: "Add debug print to show token value"
        [Dev adds debug, runs again]
        [Supervisor sees token is None]
        └─ Instruct fix for None handling
```

### Example: Multi-Step Diagnosis

```
1. Test fails with vague error
   Task: "Run test with -vv for more detail"

2. More detail shows line 45 error
   Task: "Read src/auth/oauth.py lines 40-50"

3. Code shows .expiry access without None check
   Task: "Edit to add None check before expiry access"

4. Test runs again
   [Success or different error → repeat diagnosis]
```

**Key principle**: Supervisor doesn't assume - it gathers information, analyzes, then decides.

---

## Specialized Sub-Agents Beyond "dev"

The current system has several sub-agent types. Here's when to use each:

### Plan Sub-agent

**Purpose**: Create detailed plans, break down complex tasks **When**: Before starting implementation, need to understand scope and steps

```
Task(subagent_type="Plan", prompt="
  Analyze the OAuth authentication feature request.
  Break down into testable components.
  Identify what tests are needed.
  Report: plan with micro-tasks
")
```

### Explore Sub-agent

**Purpose**: Understand codebase, find patterns, research **When**: Need to understand how something works before modifying

```
Task(subagent_type="Explore", prompt="
  Find all places in codebase where token validation occurs.
  Understand the patterns used.
  Report: summary of current validation approach
")
```

### Dev Sub-agent

**Purpose**: Write, modify, test code **When**: Implementing features, fixing bugs, running tests

```
Task(subagent_type="dev", prompt="
  Implement token None check in src/auth/oauth.py.
  Use test-writing skill for test.
  Use git-commit skill to commit.
  Report: what was implemented
")
```

---

## Summary: Supervisor's Role

The supervisor is the **decision-maker and orchestrator**, not the executor.

**Supervisor DOES**:

- ✅ Break tasks into atomic sub-agent calls
- ✅ Delegate to appropriate sub-agent type
- ✅ Wait for each report before next instruction
- ✅ Analyze reports and make decisions
- ✅ Handle challenges using decision frameworks
- ✅ Manage TodoWrite and overall plan
- ✅ Require specific skills when needed

**Supervisor DOES NOT**:

- ❌ Use tools directly (Read, Write, Bash, etc.)
- ❌ Write code or tests itself
- ❌ Run commands itself
- ❌ Do multiple unrelated tasks at once
- ❌ Continue blindly when challenges arise
- ❌ Ask user about routine decisions

**Sub-agents DO**:

- ✅ Execute one atomic task
- ✅ Use tools (Read, Write, Bash, Grep, Glob)
- ✅ Invoke skills when supervisor requires
- ✅ Report back immediately after completion
- ✅ Stop and wait for next instruction

**Pattern**:

```
Supervisor: Analyze, Decide, Delegate
Sub-agent: Execute, Report
Supervisor: Analyze report, Decide next step, Delegate
[Repeat until complete]
```

This is the multi-agent orchestration pattern we're building.
