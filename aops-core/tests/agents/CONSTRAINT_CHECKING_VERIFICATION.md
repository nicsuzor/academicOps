# Constraint Checking: Verification Test Cases

**Component**: prompt-hydrator agent - constraint checking extension
**Task**: aops-8abaaf9e - Extend hydrator: constraint-checking on workflow rules
**Date**: 2026-01-23
**Status**: DRAFT

## Summary

Test cases verifying that the prompt-hydrator correctly checks workflow constraints when generating execution plans. These are manual verification cases - run them by prompting the hydrator with specific scenarios and checking the output.

## Test Structure

Each test case specifies:
1. **Input**: User prompt and workflow selected
2. **Plan**: The execution plan to verify
3. **Expected**: Which constraints should be checked and their status
4. **Violations**: Any violations that should be detected

---

## Pilot Workflow: feature-dev

### Test 1.1: Valid Feature Development Plan

**Input**: "Add a new field 'priority' to the Task model"
**Workflow**: feature-dev

**Plan**:
```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Capture user story for priority field", status: "pending", activeForm: "Capturing user story"},
  {content: "Document requirements and success criteria", status: "pending", activeForm: "Documenting requirements"},
  {content: "Write failing test for priority field", status: "pending", activeForm: "Writing failing test"},
  {content: "Plan implementation approach", status: "pending", activeForm: "Planning implementation"},
  {content: "Implement priority field", status: "pending", activeForm: "Implementing"},
  {content: "Run tests and validate", status: "pending", activeForm: "Validating"},
  {content: "Task(subagent_type='critic', ...)", status: "pending", activeForm: "Critic review"},
  {content: "Commit and complete", status: "pending", activeForm: "Completing"}
])
```

**Expected Constraint Checks**:
| Constraint | Rule | Status |
|------------|------|--------|
| Sequencing | User story before requirements | ✅ Satisfied |
| Sequencing | Requirements before tests | ✅ Satisfied |
| Sequencing | Tests exist before implementation | ✅ Satisfied |
| Sequencing | Plan approved before implement | ✅ Satisfied |
| Postcondition | Run tests after implement | ✅ Satisfied |
| Postcondition | Critic review before commit | ✅ Satisfied |
| Prohibition | Never implement without tests | ✅ Satisfied |
| Prohibition | Never commit failing tests | ✅ (runtime check) |

**Violations**: None expected

---

### Test 1.2: Missing Test Step (Violation)

**Input**: "Add validation to email field"
**Workflow**: feature-dev

**Plan** (INTENTIONALLY FLAWED):
```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Document requirements", status: "pending", activeForm: "Documenting"},
  {content: "Implement email validation", status: "pending", activeForm: "Implementing"},
  {content: "Commit", status: "pending", activeForm: "Committing"}
])
```

**Expected Violations**:

```markdown
### Constraint Violations

⚠️ Plan violates 3 workflow constraint(s):

1. **Sequencing (BEFORE)**: "Tests must exist and fail before planning development"
   - **Violation**: No test-writing step exists in plan
   - **Remediation**: Add "Write failing test for email validation" before implementation

2. **Prohibition (NEVER)**: "Never implement without tests existing first"
   - **Violation**: Implementation step at position 3 with no prior test step
   - **Remediation**: Add test step before implementation

3. **Postcondition (AFTER)**: "After implementation: critic must review"
   - **Violation**: No critic review step before commit
   - **Remediation**: Add Task(subagent_type='critic', ...) before commit step
```

---

### Test 1.3: Wrong Order (Violation)

**Input**: "Refactor authentication module"
**Workflow**: feature-dev

**Plan** (INTENTIONALLY FLAWED):
```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Implement refactoring", status: "pending", activeForm: "Implementing"},
  {content: "Write tests for new structure", status: "pending", activeForm: "Writing tests"},
  {content: "Run tests", status: "pending", activeForm: "Testing"},
  {content: "Commit", status: "pending", activeForm: "Committing"}
])
```

**Expected Violations**:

```markdown
### Constraint Violations

⚠️ Plan violates 2 workflow constraint(s):

1. **Sequencing (BEFORE)**: "Tests must exist and fail before planning development"
   - **Violation**: "Write tests" at position 3, "Implement" at position 2
   - **Remediation**: Reorder: move test-writing step before implementation

2. **Prohibition (NEVER)**: "Never implement before writing a test"
   - **Violation**: Implementation precedes test creation
   - **Remediation**: Move test step to position 2, implementation to position 3+
```

---

## Pilot Workflow: decompose

### Test 2.1: Valid Decomposition Plan

**Input**: "Plan the dissertation literature review chapter"
**Workflow**: decompose

**Plan**:
```javascript
TodoWrite(todos=[
  {content: "Claim goal task", status: "pending", activeForm: "Claiming task"},
  {content: "Articulate goal: comprehensive lit review of X", status: "pending", activeForm: "Articulating goal"},
  {content: "Document assumptions about scope and sources", status: "pending", activeForm: "Documenting assumptions"},
  {content: "Identify probe: test search in database Y", status: "pending", activeForm: "Identifying probes"},
  {content: "Create coarse components (3-5 subtasks)", status: "pending", activeForm: "Creating components"},
  {content: "Create REVIEW task blocking subtasks", status: "pending", activeForm: "Creating review gate"},
  {content: "Complete decomposition", status: "pending", activeForm: "Completing"}
])
```

**Expected Constraint Checks**:
| Constraint | Rule | Status |
|------------|------|--------|
| Sequencing | Goal articulated before components | ✅ Satisfied |
| Sequencing | Assumptions documented before probes | ✅ Satisfied |
| Sequencing | Probes identified before components | ✅ Satisfied |
| Sequencing | Review task exists before subtasks worked | ✅ Satisfied |
| Invariant | Keep decomposition coarse | ✅ (3-5 subtasks) |
| Prohibition | Never expand everything at once | ✅ Satisfied |

**Violations**: None expected

---

### Test 2.2: Missing Review Gate (Violation)

**Input**: "Break down API integration project"
**Workflow**: decompose

**Plan** (INTENTIONALLY FLAWED):
```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Articulate goal", status: "pending", activeForm: "Articulating"},
  {content: "Create 8 subtasks for each API endpoint", status: "pending", activeForm: "Creating subtasks"},
  {content: "Start working on first subtask", status: "pending", activeForm: "Working"}
])
```

**Expected Violations**:

```markdown
### Constraint Violations

⚠️ Plan violates 3 workflow constraint(s):

1. **Sequencing (BEFORE)**: "Review task must exist before working on any subtask"
   - **Violation**: No review task created, but "Start working" step exists
   - **Remediation**: Add "Create REVIEW task blocking subtasks" before working

2. **Invariant (ALWAYS)**: "Keep decomposition coarse before fine-grained"
   - **Violation**: "8 subtasks" exceeds coarse threshold (3-7)
   - **Remediation**: Create intermediate grouping tasks or reduce to 5-7 components

3. **Prohibition (NEVER)**: "Never expand everything at once (premature detail)"
   - **Violation**: Creating 8 detailed subtasks without review gate
   - **Remediation**: Start with 3-5 coarse components, add review, then refine
```

---

## Pilot Workflow: tdd-cycle

### Test 3.1: Valid TDD Cycle Plan

**Input**: "Fix bug where empty strings aren't validated"
**Workflow**: tdd-cycle

**Plan**:
```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Write failing test for empty string case", status: "pending", activeForm: "Writing failing test"},
  {content: "Verify test fails", status: "pending", activeForm: "Verifying failure"},
  {content: "Implement empty string validation", status: "pending", activeForm: "Implementing"},
  {content: "Run test, verify pass", status: "pending", activeForm: "Verifying pass"},
  {content: "Refactor if needed", status: "pending", activeForm: "Refactoring"},
  {content: "Verify tests still pass", status: "pending", activeForm: "Final verification"},
  {content: "Commit", status: "pending", activeForm: "Committing"}
])
```

**Expected Constraint Checks**:
| Constraint | Rule | Status |
|------------|------|--------|
| Sequencing | Test exists before implementation | ✅ Satisfied |
| Sequencing | Test fails before implementation | ✅ Satisfied |
| Postcondition | Run test after implementation | ✅ Satisfied |
| Postcondition | Tests pass after refactor | ✅ Satisfied |
| Prohibition | Never implement before test | ✅ Satisfied |
| Prohibition | Never commit failing test | ✅ (runtime check) |

**Violations**: None expected

---

### Test 3.2: Missing Failure Verification (Violation)

**Input**: "Add input sanitization"
**Workflow**: tdd-cycle

**Plan** (INTENTIONALLY FLAWED):
```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Write test for sanitization", status: "pending", activeForm: "Writing test"},
  {content: "Implement sanitization", status: "pending", activeForm: "Implementing"},
  {content: "Run tests", status: "pending", activeForm: "Running tests"},
  {content: "Commit", status: "pending", activeForm: "Committing"}
])
```

**Expected Violations**:

```markdown
### Constraint Violations

⚠️ Plan violates 1 workflow constraint(s):

1. **Sequencing (BEFORE)**: "The test must fail before implementation (this proves the test is meaningful)"
   - **Violation**: No "verify failure" step between "Write test" and "Implement"
   - **Remediation**: Add "Verify test fails" step after writing test, before implementation
```

---

### Test 3.3: Refactor Without Green Tests (Violation)

**Input**: "Optimize database query performance"
**Workflow**: tdd-cycle

**Plan** (INTENTIONALLY FLAWED):
```javascript
TodoWrite(todos=[
  {content: "Claim task", status: "pending", activeForm: "Claiming task"},
  {content: "Write performance test", status: "pending", activeForm: "Writing test"},
  {content: "Verify test fails (slow)", status: "pending", activeForm: "Verifying"},
  {content: "Refactor query for performance", status: "pending", activeForm: "Refactoring"},
  {content: "Check if faster", status: "pending", activeForm: "Checking"},
  {content: "Commit", status: "pending", activeForm: "Committing"}
])
```

**Expected Violations**:

```markdown
### Constraint Violations

⚠️ Plan violates 2 workflow constraint(s):

1. **Sequencing (BEFORE)**: "Tests must pass before refactoring"
   - **Violation**: "Refactor" step occurs without prior "tests pass" state
   - **Remediation**: Add "Implement minimal fix" + "Verify pass" before refactoring

2. **Postcondition (AFTER)**: "After refactor: tests must still pass"
   - **Violation**: "Check if faster" doesn't explicitly verify all tests pass
   - **Remediation**: Replace with "Run all tests, verify still passing"
```

---

## Conditional Constraint Tests

### Test 4.1: Framework Feature Detection

**Input**: "Add a new workflow for documentation changes"
**Context**: Task touches `aops-core/workflows/`

**Expected Conditional Check**:
- Condition: "If this is a framework feature"
- Detected: ✅ Yes (modifies aops-core/)
- Required: "use detailed critic"
- Plan must include: `Task(subagent_type='critic', model='opus', ...)`

If plan uses haiku critic or no critic:
```markdown
### Constraint Violations

⚠️ Plan violates 1 workflow constraint(s):

1. **Conditional (IF-THEN)**: "If this is a framework feature: use detailed critic"
   - **Violation**: Plan uses fast critic (haiku) for framework modification
   - **Remediation**: Change to Task(subagent_type='critic', model='opus', ...)
```

---

## Runtime Check Deferral Tests

### Test 5.1: Predicates Requiring Execution

**Input**: Any feature development task
**Workflow**: feature-dev

The following predicates cannot be verified at plan time:
- `tests_pass` - requires actually running tests
- `validation_succeeds` - requires executing validation
- `no_regressions` - requires full test suite run

**Expected Output Section**:
```markdown
**Runtime checks deferred**: tests_pass, validation_succeeds, no_regressions

These predicates will be verified during execution. Plan includes appropriate check steps.
```

---

## Verification Procedure

To verify constraint checking is working:

1. **Run hydrator** with each test case prompt
2. **Check output** for Constraint Verification section
3. **For valid plans**: Verify all constraints show ✅ Satisfied
4. **For flawed plans**: Verify violations are detected with correct remediation
5. **For conditionals**: Verify context-aware detection triggers appropriate rules

## Related Files

- `/home/nic/writing/aops/aops-core/agents/prompt-hydrator.md` - Agent definition with constraint checking
- `/home/nic/writing/aops/aops-core/specs/workflow-constraints.md` - Constraint format specification
- `/home/nic/writing/aops/aops-core/workflows/feature-dev.md` - Feature development workflow
- `/home/nic/writing/aops/aops-core/workflows/decompose.md` - Decomposition workflow
- `/home/nic/writing/aops/aops-core/workflows/tdd-cycle.md` - TDD cycle workflow
