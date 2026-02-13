---
title: Constraint Checking Test Cases
type: spec
category: testing
status: draft
created: 2026-01-23
related: [workflow-constraints, prompt-hydrator, predicate-registry]
---

# Constraint Checking Test Cases

## Giving Effect

- [[specs/workflow-constraints.md]] - Constraint system this tests
- [[specs/predicate-registry.md]] - Predicates used in test cases
- [[workflows/feature-dev.md]] - Feature-dev workflow tested
- [[workflows/decompose.md]] - Decompose workflow tested
- [[workflows/tdd-cycle.md]] - TDD cycle workflow tested

Test cases demonstrating constraint checking for the three pilot workflows: feature-dev, decompose, and tdd-cycle.

## Test Case Format

Each test case includes:

- **Scenario**: What the user requested
- **Proposed Plan**: TodoWrite steps the hydrator would generate
- **Constraint Check**: Which constraints apply and how they're evaluated
- **Expected Result**: Pass, fail, or remediation needed

---

## Feature-Dev Workflow Tests

### Test 1: Valid Feature Implementation Plan

**Scenario**: User requests "Add user authentication to the app"

**Proposed Plan**:

```javascript
TodoWrite(todos=[
  {content: "Claim task aops-xxx", status: "pending", activeForm: "Claiming task"},
  {content: "Capture user story: As a user, I want to log in", status: "pending", activeForm: "Capturing user story"},
  {content: "Document requirements: JWT-based auth, session management", status: "pending", activeForm: "Documenting requirements"},
  {content: "Define success criteria: Login works, tokens refresh", status: "pending", activeForm: "Defining success criteria"},
  {content: "Design experiment: Test auth endpoints", status: "pending", activeForm: "Designing experiment"},
  {content: "Write failing tests for auth endpoints", status: "pending", activeForm: "Writing failing tests"},
  {content: "CHECKPOINT: Verify tests fail", status: "pending", activeForm: "Verifying test failure"},
  {content: "Plan implementation approach", status: "pending", activeForm: "Planning implementation"},
  {content: "Get plan approval", status: "pending", activeForm: "Getting approval"},
  {content: "Implement auth endpoints", status: "pending", activeForm: "Implementing auth"},
  {content: "Run tests and verify pass", status: "pending", activeForm: "Running tests"},
  {content: "Task(subagent_type='critic', prompt='Review auth implementation')", status: "pending", activeForm: "Critic review"},
  {content: "Commit feature", status: "pending", activeForm: "Committing"},
  {content: "Update spec documentation", status: "pending", activeForm: "Updating spec"},
  {content: "Complete task", status: "pending", activeForm: "Completing"}
])
```

**Constraint Check**:

| Constraint                                   | Check                                                       | Result  |
| -------------------------------------------- | ----------------------------------------------------------- | ------- |
| BEFORE implement: tests_exist AND tests_fail | "Write failing tests" (step 6) before "Implement" (step 10) | ✅ Pass |
| BEFORE implement: plan_approved              | "Get plan approval" (step 9) before "Implement" (step 10)   | ✅ Pass |
| BEFORE commit: tests_pass                    | "Run tests" (step 11) before "Commit" (step 13)             | ✅ Pass |
| BEFORE commit: critic_reviewed               | "Critic review" (step 12) before "Commit" (step 13)         | ✅ Pass |
| NEVER: implement_without_plan                | Plan approval exists before implementation                  | ✅ Pass |
| AFTER complete: update_spec                  | "Update spec" (step 14) before "Complete" (step 15)         | ✅ Pass |

**Expected Result**: ✅ All constraints satisfied

---

### Test 2: Missing Test-First Constraint

**Scenario**: User requests "Add dark mode toggle"

**Proposed Plan** (INCORRECT):

```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Capture user story", status: "pending", activeForm: "Capturing story"},
  {content: "Implement dark mode toggle", status: "pending", activeForm: "Implementing"},  // ⚠️ No tests first!
  {content: "Write tests for dark mode", status: "pending", activeForm: "Writing tests"},
  {content: "Run tests", status: "pending", activeForm: "Running tests"},
  {content: "Commit", status: "pending", activeForm: "Committing"}
])
```

**Constraint Check**:

| Constraint                                   | Check                                                      | Result  |
| -------------------------------------------- | ---------------------------------------------------------- | ------- |
| BEFORE implement: tests_exist AND tests_fail | "Implement" (step 3) appears BEFORE "Write tests" (step 4) | ❌ FAIL |
| BEFORE implement: plan_approved              | No plan approval step exists                               | ❌ FAIL |
| BEFORE commit: critic_reviewed               | No critic review step                                      | ❌ FAIL |

**Expected Result**: ⚠️ 3 violations found

**Constraint Violations**:

```markdown
### Constraint Violations

⚠️ Plan violates 3 workflow constraint(s):

1. **BEFORE**: "Tests must exist and fail before implementation begins"
   - **Violation**: "Implement dark mode toggle" (step 3) appears before "Write tests" (step 4)
   - **Remediation**: Move "Write tests for dark mode" before "Implement dark mode toggle" and add checkpoint to verify tests fail

2. **BEFORE**: "Plan must be approved before implementation begins"
   - **Violation**: No plan approval step exists in the plan
   - **Remediation**: Add "Plan implementation approach" and "Get plan approval" steps before implementation

3. **BEFORE**: "Critic must have reviewed before commit"
   - **Violation**: No critic review step before commit
   - **Remediation**: Add `Task(subagent_type='critic', ...)` step before commit
```

---

### Test 3: Missing Commit Gate

**Scenario**: User requests "Fix login bug"

**Proposed Plan** (INCORRECT):

```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Write failing test reproducing bug", status: "pending", activeForm: "Writing test"},
  {content: "Verify test fails", status: "pending", activeForm: "Verifying failure"},
  {content: "Fix the login bug", status: "pending", activeForm: "Fixing bug"},
  {content: "Commit fix", status: "pending", activeForm: "Committing"}  // ⚠️ No test verification!
])
```

**Constraint Check**:

| Constraint                                   | Check                                               | Result  |
| -------------------------------------------- | --------------------------------------------------- | ------- |
| BEFORE implement: tests_exist AND tests_fail | "Write failing test" (step 2) before "Fix" (step 4) | ✅ Pass |
| BEFORE commit: tests_pass                    | No "Run tests" step before "Commit" (step 5)        | ❌ FAIL |
| NEVER: commit_with_failing_tests             | Can't verify tests pass before commit               | ❌ FAIL |

**Expected Result**: ⚠️ 2 violations found (related)

**Constraint Violations**:

```markdown
### Constraint Violations

⚠️ Plan violates 2 workflow constraint(s):

1. **BEFORE**: "All tests must pass before commit"
   - **Violation**: No "Run tests" or "Verify tests pass" step before "Commit fix"
   - **Remediation**: Add "Run tests and verify pass" step between "Fix the login bug" and "Commit fix"

2. **NEVER**: "Never commit with failing tests"
   - **Violation**: Cannot verify tests pass without explicit test run step
   - **Remediation**: Same as above - add test verification before commit
```

---

## Decompose Workflow Tests

### Test 4: Valid Decomposition Plan

**Scenario**: User requests "Plan my dissertation"

**Proposed Plan**:

```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Articulate goal: Complete PhD dissertation on X", status: "pending", activeForm: "Articulating goal"},
  {content: "Document assumptions: Timeline, scope, resources", status: "pending", activeForm: "Documenting assumptions"},
  {content: "Identify probes: Literature gap analysis, method validation", status: "pending", activeForm: "Identifying probes"},
  {content: "Create coarse components: 5 chapters + defense prep", status: "pending", activeForm: "Creating components"},
  {content: "Create blocking review task", status: "pending", activeForm: "Creating review task"},
  {content: "Complete decomposition task", status: "pending", activeForm: "Completing"}
])
```

**Constraint Check**:

| Constraint                                      | Check                                                             | Result  |
| ----------------------------------------------- | ----------------------------------------------------------------- | ------- |
| BEFORE identifying components: goal articulated | "Articulate goal" (step 2) before "Create components" (step 5)    | ✅ Pass |
| BEFORE creating probes: assumptions documented  | "Document assumptions" (step 3) before "Identify probes" (step 4) | ✅ Pass |
| BEFORE probes: assumptions documented           | "Assumptions" (step 3) before "Probes" (step 4)                   | ✅ Pass |
| AFTER decomposition: review task exists         | "Create blocking review task" (step 6) exists                     | ✅ Pass |
| ALWAYS: at least one actionable task            | Components create actionable tasks                                | ✅ Pass |
| NEVER: over_decompose                           | 5 chapters + prep = 6 items (reasonable)                          | ✅ Pass |

**Expected Result**: ✅ All constraints satisfied

---

### Test 5: Missing Assumptions Step

**Scenario**: User requests "Break down the grant proposal"

**Proposed Plan** (INCORRECT):

```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Articulate goal: Submit NSF grant", status: "pending", activeForm: "Articulating goal"},
  {content: "Create components: Aims, Background, Methods, Budget", status: "pending", activeForm: "Creating components"},  // ⚠️ Skipped assumptions!
  {content: "Complete task", status: "pending", activeForm: "Completing"}
])
```

**Constraint Check**:

| Constraint                                     | Check                          | Result  |
| ---------------------------------------------- | ------------------------------ | ------- |
| BEFORE creating probes: assumptions documented | No "Document assumptions" step | ❌ FAIL |
| AFTER decomposition: review task exists        | No review task created         | ❌ FAIL |
| NEVER: hide_assumptions                        | Assumptions not documented     | ❌ FAIL |

**Expected Result**: ⚠️ 3 violations found

**Constraint Violations**:

```markdown
### Constraint Violations

⚠️ Plan violates 3 workflow constraint(s):

1. **BEFORE**: "Assumptions must be documented before creating probes"
   - **Violation**: No "Document assumptions" step before creating components
   - **Remediation**: Add "Document assumptions: funding timeline, co-PI availability, preliminary data status" before creating components

2. **AFTER**: "A review task must be created that blocks other subtasks"
   - **Violation**: No review task creation step
   - **Remediation**: Add "Create blocking review task" before completing decomposition

3. **NEVER**: "Never hide assumptions"
   - **Violation**: Moving directly to components without surfacing assumptions
   - **Remediation**: Explicitly document assumptions, even if they seem obvious
```

---

## TDD-Cycle Workflow Tests

### Test 6: Valid TDD Cycle

**Scenario**: User requests "Add email validation to signup form"

**Proposed Plan**:

```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Write test: valid email accepted", status: "pending", activeForm: "Writing test"},
  {content: "CHECKPOINT: Verify test fails", status: "pending", activeForm: "Verifying failure"},
  {content: "Implement email validation", status: "pending", activeForm: "Implementing"},
  {content: "Run test, verify pass", status: "pending", activeForm: "Running test"},
  {content: "Refactor if needed", status: "pending", activeForm: "Refactoring"},
  {content: "Verify tests still pass", status: "pending", activeForm: "Verifying"},
  {content: "Commit", status: "pending", activeForm: "Committing"}
])
```

**Constraint Check**:

| Constraint                                   | Check                                                                       | Result  |
| -------------------------------------------- | --------------------------------------------------------------------------- | ------- |
| BEFORE implement: test_exists AND test_fails | "Write test" (step 2) + "Verify fails" (step 3) before "Implement" (step 4) | ✅ Pass |
| BEFORE commit: test_passes                   | "Run test, verify pass" (step 5) before "Commit" (step 8)                   | ✅ Pass |
| AFTER refactor: tests_still_pass             | "Verify tests still pass" (step 7) after "Refactor" (step 6)                | ✅ Pass |
| NEVER: implement_before_test                 | Test written before implementation                                          | ✅ Pass |
| NEVER: commit_failing_test                   | Test verification before commit                                             | ✅ Pass |

**Expected Result**: ✅ All constraints satisfied

---

### Test 7: Missing Red Phase Verification

**Scenario**: User requests "Add password strength indicator"

**Proposed Plan** (INCORRECT):

```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Write test for password strength", status: "pending", activeForm: "Writing test"},
  {content: "Implement strength indicator", status: "pending", activeForm: "Implementing"},  // ⚠️ No failure verification!
  {content: "Run tests", status: "pending", activeForm: "Running tests"},
  {content: "Commit", status: "pending", activeForm: "Committing"}
])
```

**Constraint Check**:

| Constraint                                   | Check                                             | Result    |
| -------------------------------------------- | ------------------------------------------------- | --------- |
| BEFORE implement: test_exists AND test_fails | Test exists but no "Verify test fails" checkpoint | ⚠️ PARTIAL |
| TRIGGER: ON test_passes_unexpectedly: HALT   | No mechanism to catch unexpected pass             | ❌ FAIL   |

**Expected Result**: ⚠️ 1 violation found

**Constraint Violations**:

```markdown
### Constraint Violations

⚠️ Plan violates 1 workflow constraint(s):

1. **BEFORE**: "Test must fail before implementation (proves test is meaningful)"
   - **Violation**: No "Verify test fails" checkpoint between "Write test" and "Implement"
   - **Remediation**: Add "CHECKPOINT: Verify test fails" step after writing test and before implementation
   - **Rationale**: If test passes before implementation, the test may not be testing what you think
```

---

### Test 8: Implementation Before Test

**Scenario**: User requests "Fix the date parsing bug"

**Proposed Plan** (INCORRECT):

```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Fix date parsing in utils.py", status: "pending", activeForm: "Fixing"},  // ⚠️ No test first!
  {content: "Write test for date parsing", status: "pending", activeForm: "Writing test"},
  {content: "Run tests", status: "pending", activeForm: "Running tests"},
  {content: "Commit", status: "pending", activeForm: "Committing"}
])
```

**Constraint Check**:

| Constraint                                   | Check                                               | Result  |
| -------------------------------------------- | --------------------------------------------------- | ------- |
| BEFORE implement: test_exists AND test_fails | "Fix" (step 2) appears BEFORE "Write test" (step 3) | ❌ FAIL |
| NEVER: implement_before_test                 | Implementation step before test step                | ❌ FAIL |

**Expected Result**: ⚠️ 2 violations found (same root cause)

**Constraint Violations**:

```markdown
### Constraint Violations

⚠️ Plan violates 2 workflow constraint(s):

1. **BEFORE**: "A test must exist before implementation begins"
   - **Violation**: "Fix date parsing" (step 2) appears before "Write test for date parsing" (step 3)
   - **Remediation**: Reorder to write failing test first, then implement fix

2. **NEVER**: "Never implement before writing a test"
   - **Violation**: Same as above - implementation precedes test
   - **Remediation**: For bug fixes, write a test that reproduces the bug FIRST, verify it fails, then fix
```

---

## Summary

| Workflow    | Test                       | Result  | Violations |
| ----------- | -------------------------- | ------- | ---------- |
| feature-dev | Valid plan                 | ✅ Pass | 0          |
| feature-dev | Missing test-first         | ❌ Fail | 3          |
| feature-dev | Missing commit gate        | ❌ Fail | 2          |
| decompose   | Valid plan                 | ✅ Pass | 0          |
| decompose   | Missing assumptions        | ❌ Fail | 3          |
| tdd-cycle   | Valid plan                 | ✅ Pass | 0          |
| tdd-cycle   | Missing red verification   | ❌ Fail | 1          |
| tdd-cycle   | Implementation before test | ❌ Fail | 2          |

These test cases validate that the constraint checking system can:

1. ✅ Recognize valid plans that satisfy all constraints
2. ❌ Detect ordering violations (BEFORE constraints)
3. ❌ Detect missing steps (required predicates)
4. ❌ Detect prohibited patterns (NEVER constraints)
5. 📝 Provide specific remediation guidance
