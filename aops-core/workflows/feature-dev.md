---
id: feature-dev
category: development
bases: [base-task-tracking, base-tdd, base-verification, base-commit]

# Workflow-specific gate constraints
# These extend the base gates defined in lib/gates/definitions.py
constraints:
  # Phase Sequencing - each phase must complete before the next
  phase_sequence:
    - id: user-story-before-requirements
      before: analyze_requirements
      requires: user_story_captured
      message: "User story must be captured before analyzing requirements"

    - id: requirements-before-experiment
      before: design_experiment
      requires: [requirements_documented, success_criteria_defined]
      message: "Requirements and success criteria must be defined before designing experiment"

    - id: experiment-before-tests
      before: write_tests
      requires: experiment_plan_exists
      message: "Experiment plan must exist before writing tests"

    - id: tests-before-plan
      before: plan_development
      requires: [tests_exist, tests_fail]
      message: "Tests must exist and fail before planning development"

    - id: plan-before-implement
      before: implement
      requires: plan_approved
      message: "Plan must be approved before implementation begins"

    - id: implement-before-validate
      before: validate
      requires: implementation_complete
      message: "Implementation must be complete before validation"

    - id: validate-before-synthesize
      before: synthesize_to_spec
      requires: [validation_passed, critic_reviewed]
      message: "Validation must pass and critic must review before synthesizing to spec"

  # Commit Gates - conditions that must hold before any commit
  commit_gates:
    - id: tests-pass-before-commit
      before: commit
      requires: all_tests_pass
      verdict: deny
      message: "All tests must pass before commit"

    - id: critic-before-commit
      before: commit
      requires: critic_reviewed
      verdict: deny
      message: "Critic must have reviewed before commit"

    - id: no-regressions-before-commit
      before: commit
      requires: no_regressions
      verdict: deny
      message: "No regressions in existing tests"

  # Post-step actions
  after_step:
    - trigger: implementation_step_complete
      action: [run_tests, update_todo_progress]

    - trigger: validation_succeeded
      action: commit_feature

    - trigger: validation_failed
      action: revert_feature

    - trigger: workflow_complete
      action: [update_spec, close_experiment_task]

  # Invariants - always true during this workflow
  invariants:
    - id: single-task-in-progress
      check: only_one_task_in_progress
      message: "Only one task should be in progress at a time"

    - id: changes-tracked
      check: all_changes_tracked_in_task
      message: "All changes must be tracked in a task"

    - id: doc-integrity
      check: documentation_integrity_maintained
      message: "Documentation integrity must be maintained"

    - id: ssot
      check: single_source_of_truth
      message: "Single source of truth principle applies"

  # Prohibitions - never do these
  never:
    - id: no-commit-failing-tests
      action: commit
      when: tests_failing
      verdict: deny
      message: "Never commit with failing tests"

    - id: no-implement-without-plan
      action: implement
      when: plan_not_approved
      verdict: deny
      message: "Never implement without an approved plan"

    - id: no-implement-without-tests
      action: implement
      when: tests_not_exist
      verdict: deny
      message: "Never implement without tests existing first"

    - id: no-skip-critic
      action: complete_phase
      when: critic_not_reviewed
      verdict: deny
      message: "Never skip critic review"

    - id: no-partial-success
      action: ship
      when: partial_success
      verdict: deny
      message: "Never ship partial success"

    - id: no-workaround-blockers
      action: proceed
      when: blocker_exists
      verdict: deny
      message: "Never work around blockers"

    - id: no-rationalize-failures
      action: proceed
      when: test_failure_rationalized
      verdict: deny
      message: "Never rationalize test failures"

    - id: no-duplicate-docs
      action: create_documentation
      when: documentation_exists
      verdict: deny
      message: "Never duplicate documentation"

  # Conditional rules
  conditionals:
    - id: halt-on-test-fail
      when: tests_fail
      action: [halt, fix_or_revert]
      message: "If tests fail: halt and fix, or revert"

    - id: halt-on-infra-block
      when: blocked_on_infrastructure
      action: [halt, report]
      message: "If blocked on infrastructure: halt and report"

    - id: return-to-analysis
      when: requirements_unclear
      action: return_to_analysis_phase
      message: "If requirements are unclear: return to analysis phase"

    - id: detailed-critic-for-framework
      when: is_framework_feature
      action: use_detailed_critic
      message: "If this is a framework feature: use detailed critic"

    - id: fast-critic-for-routine
      when: is_routine_feature
      action: use_fast_critic
      message: "If this is a routine feature: use fast critic"

    - id: revert-on-iteration-fail
      when: iteration_fails
      action: revert
      message: "If an iteration fails: revert"

# Predicate definitions for constraint checks
predicates:
  user_story_captured:
    check: "task body contains '## User Story' or file exists with user-story content"

  requirements_documented:
    check: "task body contains '## Requirements'"

  success_criteria_defined:
    check: "task body contains '## Success Criteria'"

  experiment_plan_exists:
    check: "task with tag 'experiment' exists for this feature"

  tests_exist:
    check: "grep finds 'def test_' or 'test(' in relevant test files"

  tests_fail:
    check: "pytest exit code is not 0 for feature tests"

  all_tests_pass:
    check: "pytest exit code is 0 for all tests"

  plan_approved:
    check: "task body contains '## Approved Plan' or user said 'approved' or 'lgtm'"

  implementation_complete:
    check: "all execution steps for implementation are done"

  critic_reviewed:
    check: "critic agent was spawned and returned a verdict"

  no_regressions:
    check: "full test suite passes (not just feature tests)"

  validation_passed:
    check: "all success criteria met, tests pass, and critic approved"

  is_framework_feature:
    check: "files touched include 'aops-core/' or tags include 'framework'"

  is_routine_feature:
    check: "not a framework feature"

  blocked_on_infrastructure:
    check: "error indicates missing tool/service/permission"

  requirements_unclear:
    check: "user asks clarifying question or requirements conflict"

  iteration_fails:
    check: "second validation attempt fails"
---

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
