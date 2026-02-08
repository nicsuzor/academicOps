# Feature Development Workflow

Test-first feature development from idea to validated implementation.

## When to Use

Use this workflow when:

- Adding new features
- Building significant functionality
- Implementing user-requested capabilities

Do NOT use for:

- Bug fixes (unless requiring new functionality)
- Simple refactoring
- Documentation-only changes

## Constraints

### Phase Sequencing

Each phase must complete before the next can begin:

1. **User story** must be captured before analyzing requirements
2. **Requirements** must be documented and **success criteria** defined before designing the experiment
3. **Experiment plan** must exist before writing tests
4. **Tests must exist and fail** before planning development
5. **Plan must be approved** before implementation begins
6. **Implementation must be complete** before validation
7. **Validation must pass** and **critic must review** before synthesizing to spec

### Commit Gates

Before any commit:

- All tests must pass
- Critic must have reviewed
- No regressions in existing tests

### After Each Step

- After implementing any step: run tests and update todo progress
- After validation succeeds: commit the feature
- After validation fails: revert the feature
- After completion: update the spec and close the experiment task

### Always True

- Only one task should be in progress at a time
- All changes must be tracked in a task
- Documentation integrity must be maintained
- Single source of truth principle applies

### Never Do

- Never commit with failing tests
- Never implement without an approved plan
- Never implement without tests existing first
- Never skip critic review
- Never ship partial success
- Never work around blockers
- Never rationalize test failures
- Never duplicate documentation

### Conditional Rules

- If tests fail: halt and fix, or revert
- If blocked on infrastructure: halt and report
- If requirements are unclear: return to analysis phase
- If this is a framework feature: use detailed critic
- If this is a routine feature: use fast critic
- If an iteration fails: revert

## Triggers

Phase transitions happen automatically:

- When user story is captured → analyze requirements
- When requirements are documented → design experiment
- When experiment plan exists → write tests
- When tests fail → plan development
- When plan is approved → implement
- When implementation is complete → validate
- When validation passes → synthesize to spec

Review gates:

- When plan is ready → invoke plan-agent
- When review is needed → invoke critic
- If critic escalates → invoke detailed critic

Error handling:

- On unexpected test failure → halt
- On blocker → halt and report
- On validation failure → revert or iterate

## How to Check

**Phase completion checks:**

- User story captured: task body contains "## User Story" or file exists with user-story content
- Requirements documented: task body contains "## Requirements"
- Success criteria defined: task body contains "## Success Criteria"
- Experiment plan exists: task with tag "experiment" exists for this feature
- Tests exist: grep finds "def test_" or "test(" in relevant test files
- Tests fail: pytest exit code is not 0 for feature tests
- Tests pass: pytest exit code is 0 for all tests
- Plan approved: task body contains "## Approved Plan" or user said "approved" or "lgtm"
- Implementation complete: all execution steps for implementation are done
- Critic reviewed: critic agent was spawned and returned a verdict
- No regressions: full test suite passes (not just feature tests)
- Validation passed: all success criteria met, tests pass, and critic approved

**Condition checks:**

- Framework feature: files touched include "aops-core/" or tags include "framework"
- Routine feature: not a framework feature
- Blocked on infrastructure: error indicates missing tool/service/permission
- Requirements unclear: user asks clarifying question or requirements conflict
- Iteration fails: second validation attempt fails
