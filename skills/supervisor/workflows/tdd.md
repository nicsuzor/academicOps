---
name: tdd
category: instruction
description: Test-first development with pytest validation and python-dev skill
required-skills:
  - python-dev
scope:
  - Developing new features (test-first)
  - Debugging and fixing failing tests
  - Refactoring with test coverage
  - Any work where tests define success
---

# TDD Workflow Template

This workflow implements test-driven development: write failing test → minimal implementation → verify → commit.

## Workflow Compliance

Implements the mandatory workflow from [[CORE.md]]:

1. Plan (invoke Plan agent, get review, document the plan)
2. Small TDD cycles (test → code → commit+fix → document → push)
3. Done = committed + documented + pushed

**MANDATORY**: Development work MUST invoke the [[python-dev]] skill.

---

## ITERATION UNIT

One TDD cycle = ONE failing test → minimal implementation → passing test → commit + push

Each cycle:
1. Create ONE failing test
2. Implement MINIMAL code to pass
3. Validate with python-dev skill
4. Commit and push before next cycle

---

## QUALITY GATE

Before proceeding to next cycle:

- [ ] pytest passes for new test
- [ ] pytest passes for all tests (no regressions)
- [ ] Fail-fast compliance verified (no `.get()`, no defaults, no fallbacks)
- [ ] Code reviewed via python-dev skill validation
- [ ] Commit created and pushed

---

## STEP 1: TEST CREATION

### Pre-Check (MANDATORY)

Before delegating test creation, verify task does NOT involve:
- ❌ Creating new databases/collections
- ❌ Running vectorization/indexing pipelines
- ❌ Creating new configs
- ❌ Generating fake/mock data

If task violates these rules: **STOP**, report violation, request clarification.

### Subagent Prompt: Create Failing Test

```
Task(subagent_type="general-purpose", prompt="
Create ONE failing test.

**FIRST**: Invoke Skill(skill='python-dev') to load coding standards and test patterns.

Acceptance criterion being tested: {criterion}
Behavior to test: {behavior}
File: tests/test_{name}.py

Test requirements (python-dev skill enforces):
- Use EXISTING test infrastructure (check conftest.py for fixtures)
- Connect to EXISTING live data using project configs
- Use REAL production data (NO fake data, NO new databases)
- NEVER create new databases/collections for testing
- NEVER create new configs - use existing project configs
- NEVER run vectorization/indexing to create test data
- NEVER mock internal code (only external APIs)
- Integration test pattern testing complete workflow
- Test should fail with: {expected_error}

The python-dev skill will guide you through:
- Using existing test fixtures from conftest.py
- Connecting to live data via project configs
- External API mocking patterns (ONLY for external APIs)
- Arrange-Act-Assert structure

After completing, STOP and report:
- Test location: tests/test_{name}.py::test_{function_name}
- Run command: uv run pytest {test_location} -xvs
- Actual failure message received
- Confirm failure is due to missing implementation (not test setup error)
")
```

### Verification Checklist

- [ ] Subagent invoked `Skill(skill="python-dev")` (not just "created test")
- [ ] Test uses EXISTING fixtures from conftest.py (not new ones)
- [ ] Test connects to EXISTING live data (not new databases)
- [ ] Test does NOT create new configs or run indexing pipelines
- [ ] Test location provided with full path
- [ ] Run command provided
- [ ] Failure message confirms missing implementation

### Run Test, Verify Fails Correctly

```bash
uv run pytest tests/test_{name}.py::{function} -v
```

Verify: Fails with expected error (not setup error).

If test setup broken: Instruct subagent to fix setup, re-verify.

---

## STEP 2: IMPLEMENTATION

### Subagent Prompt: Implement Minimal Fix

```
Task(subagent_type="general-purpose", prompt="
Implement MINIMAL code to make this ONE test pass.

**FIRST**: Invoke Skill(skill='python-dev') to load coding standards.

Test: tests/test_{name}.py::{function}
Error message: {error_message}

Implementation requirements:
- File to modify: {file}
- Function/method: {location}
- Behavior needed: {behavior}
- Constraints: Minimal change, fail-fast principles (no .get(), no defaults)

Tools to use:
1. Read {file} to understand current implementation
2. Edit {file} to add functionality
3. Run test using Bash: uv run pytest {test_path} -xvs to verify
4. If test passes, run all tests: uv run pytest

Figure out the exact implementation yourself. Use your judgment within constraints.

After implementation, STOP and report:
- What you changed (describe the logic you added)
- Files modified
- Test results (specific test and full suite)
")
```

### Run Tests

```bash
uv run pytest tests/test_{name}.py::{function} -v  # New test
uv run pytest                                       # All tests (no regressions)
```

### IF TESTS FAIL → Iteration Protocol

DO NOT ASK USER. Handle this:

**Analyze failure:**
- Read error message carefully
- Identify specific issue (file:line if available)
- Determine what behavior is wrong

**Subagent Prompt: Fix Failure**

```
Task(subagent_type="general-purpose", prompt="
Fix this test failure.

**FIRST**: Invoke Skill(skill='python-dev') to load coding standards.

Test: {test_name}
Error: {exact_error_message}
File: {file:line if available}

Problem analysis: {what's_wrong}

Fix requirements:
- What needs to happen: {behavior_fix}
- Where: {file and location}
- Constraint: Minimal change, fail-fast principles (explicit checks, no .get())

Tools to use:
1. Read {file} around line {N} to understand context
2. Edit {file} to implement fix
3. Run test: uv run pytest {test_path} -xvs

Figure out the exact implementation. Report back with:
- What you changed (describe logic)
- Test result
")
```

**Re-run tests after fix. Iterate until all tests pass.**

Maximum 3 iterations per issue. If still failing:
- Log via framework skill: "Stuck on test failure: [details]"
- Ask user for help

---

## STEP 3: QUALITY CHECK (Before Commit)

### Subagent Prompt: Validate and Commit

```
Task(subagent_type="general-purpose", prompt="
Validate code quality and commit this change.

**FIRST**: Invoke Skill(skill='python-dev') to load quality standards.

Changes summary: {what_was_implemented}
Test: {test_name}
Files modified: {files}

Validation checklist (python-dev skill enforces):
1. Code quality against fail-fast principles (no .get(key, default), no defaults, no fallbacks)
2. Test patterns (real fixtures used, no mocked internal code)
3. Type safety and code structure
4. Execute commit ONLY if all validation passes

If validation FAILS:
- Report ALL violations with:
  - File:line numbers
  - Code showing violation
  - What rule was violated
  - How to fix it
- STOP and report violations
- DO NOT commit
- Wait for fix instructions

If validation PASSES:
- Create commit automatically
- Commit message follows conventional commits format
- Report commit hash

After validation completes, report:
- Status: PASS or FAIL
- If PASS: commit hash (e.g., a1b2c3d)
- If FAIL: complete list of violations with file:line references
")
```

### IF Quality Check Fails

Instruct subagent to fix violations:

```
Task(subagent_type="general-purpose", prompt="
Fix these code quality violations.

**FIRST**: Invoke Skill(skill='python-dev') to load coding standards.

Violations:
{specific_violations_with_file:line}

Fix requirements:
{specific_fix_for_each}

After fixing, validate and commit again.
")
```

Iterate until quality check passes and commit succeeds.

---

## STEP 4: PUSH TO REMOTE

### Subagent Prompt: Push Changes

```
Task(subagent_type="general-purpose", prompt="
Push committed changes to remote repository.

Tools to use:
1. Bash: git push

If push fails (e.g., diverged branches):
- DO NOT force push
- STOP and report error
- Wait for supervisor instructions

After successful push, report:
- Push status (success/failure)
- Remote branch updated
- Commit hash pushed
")
```

### Verification

- [ ] Subagent reported successful push
- [ ] Remote repository contains this cycle's commit
- [ ] No uncommitted changes remain (git status clean)

**If push fails**: DO NOT continue to next cycle. Fix remote sync issues first.

---

## COMPLETION CRITERIA

All TDD cycles complete when:
- All acceptance criteria have corresponding passing tests
- All tests pass (new and existing)
- All changes committed and pushed
- No quality violations remaining

---

## Reference: Available Skills and Subagents

**Skills subagents MUST invoke:**
- [[python-dev]]: Production Python development - **MANDATORY for all code work**
- [[feature-dev]]: Full feature development workflow with TDD

**Available subagent types:**
- `Plan`: Create detailed plans, break down complex tasks
- `Explore`: Understand codebase, find files, research patterns
- `general-purpose`: Implementation work (MUST invoke python-dev first)

---

## Example TDD Cycle

```
User: "Fix the authentication bug - it's failing for OAuth users"

Supervisor:
1. Planning Phase
   - Create acceptance criteria: "OAuth users can log in successfully"
   - Break into micro-task: "Write test for OAuth login with valid token"

2. Test Creation (Cycle 1)
   - Spawn subagent: "Create failing test for OAuth login"
   - Subagent invokes python-dev skill, creates test
   - Test location: tests/test_auth.py::test_oauth_login_with_valid_token
   - Running test: FAILS (expected - OAuth validation broken)

3. Implementation (Cycle 1)
   - Spawn subagent: "Fix OAuth token validation in auth/oauth.py"
   - Subagent invokes python-dev skill, implements fix
   - Running tests: PASS

4. Quality Check (Cycle 1)
   - Spawn subagent: "Validate and commit"
   - Subagent validates against python-dev standards
   - Quality check: PASSED
   - Commit: a1b2c3d
   - Push: SUCCESS

5. Iteration Gate
   - Cycle 1 complete
   - Scope unchanged
   - Moving to QA verification

6. Completion
   - QA verifies: OAuth login works with real OAuth token
   - All acceptance criteria met
   - Task complete ✓
```
