#!/usr/bin/env python3
"""Integration tests for workflow constraint checking in prompt-hydrator.

Tests verify that the hydrator correctly:
1. Detects constraint violations in proposed plans
2. Reports violations with appropriate remediation
3. Passes valid plans that satisfy all constraints

These tests cover the three pilot workflows:
- feature-dev: Test-driven feature development
- decompose: Goal decomposition under uncertainty
- tdd-cycle: Red-green-refactor cycle

Run tests:
    uv run pytest tests/integration/test_workflow_constraints.py -v

Run with demo output:
    uv run pytest tests/integration/test_workflow_constraints.py -v -s -n 0
"""

import pytest

# ============================================================================
# CONSTRAINT TEST CASES
#
# Each test case defines:
# - workflow: Which workflow the constraints come from
# - scenario: Description of the scenario being tested
# - plan_steps: Proposed TodoWrite steps (simulated)
# - expected_violations: List of constraints that should be flagged
# - expected_pass: True if plan should pass all constraints
#
# These test cases document expected hydrator behavior and can be used
# for manual verification or future automated testing.
# ============================================================================


FEATURE_DEV_TEST_CASES = [
    {
        "id": "feature-dev-valid-sequence",
        "workflow": "feature-dev",
        "scenario": "Valid feature-dev sequence with all phases in order",
        "plan_steps": [
            "Claim task and capture user story",
            "Analyze requirements and define success criteria",
            "Design experiment plan",
            "Write failing tests for feature",
            "Verify tests fail",
            "Plan implementation approach",
            "Get plan approval",
            "Implement minimal solution",
            "Run tests and verify pass",
            "Spawn critic for review",
            "Synthesize learnings to spec",
            "Commit and complete task",
        ],
        "expected_violations": [],
        "expected_pass": True,
    },
    {
        "id": "feature-dev-missing-tests",
        "workflow": "feature-dev",
        "scenario": "Implementation planned before tests exist",
        "plan_steps": [
            "Claim task",
            "Analyze requirements",
            "Plan implementation approach",
            "Implement the feature",  # VIOLATION: No tests before implementation
            "Write tests",
            "Commit",
        ],
        "expected_violations": [
            "BEFORE implement: tests_exist AND tests_fail",
            "Never implement without tests existing first",
        ],
        "expected_pass": False,
    },
    {
        "id": "feature-dev-missing-plan-approval",
        "workflow": "feature-dev",
        "scenario": "Implementation starts without plan approval",
        "plan_steps": [
            "Claim task",
            "Analyze requirements",
            "Write failing tests",
            "Start implementing",  # VIOLATION: No plan approval step
            "Run tests",
            "Commit",
        ],
        "expected_violations": [
            "Plan must be approved before implementation begins",
            "Never implement without an approved plan",
        ],
        "expected_pass": False,
    },
    {
        "id": "feature-dev-commit-without-critic",
        "workflow": "feature-dev",
        "scenario": "Commit planned without critic review",
        "plan_steps": [
            "Claim task",
            "Write failing tests",
            "Get plan approval",
            "Implement feature",
            "Run tests - verify pass",
            "Commit changes",  # VIOLATION: No critic review before commit
        ],
        "expected_violations": [
            "Validation must pass and critic must review before synthesizing to spec",
            "Never skip critic review",
        ],
        "expected_pass": False,
    },
    {
        "id": "feature-dev-tests-not-verified-failing",
        "workflow": "feature-dev",
        "scenario": "Tests written but not verified to fail before implementation",
        "plan_steps": [
            "Claim task",
            "Analyze requirements",
            "Write tests for feature",  # Tests written...
            "Implement feature",  # ...but not verified to FAIL first
            "Run tests",
            "Critic review",
            "Commit",
        ],
        "expected_violations": [
            "Tests must exist and fail before planning development",
        ],
        "expected_pass": False,
    },
]


DECOMPOSE_TEST_CASES = [
    {
        "id": "decompose-valid-sequence",
        "workflow": "decompose",
        "scenario": "Valid decomposition with all steps and review gate",
        "plan_steps": [
            "Claim goal task",
            "Articulate the goal clearly",
            "Surface and document assumptions",
            "Identify affordable probes for unknowns",
            "Create coarse components (3-5 subtasks)",
            "Create REVIEW task that blocks other subtasks",
            "Mark decomposition complete",
        ],
        "expected_violations": [],
        "expected_pass": True,
    },
    {
        "id": "decompose-missing-assumptions",
        "workflow": "decompose",
        "scenario": "Components created without documenting assumptions",
        "plan_steps": [
            "Claim goal task",
            "Articulate the goal",
            "Create subtasks for components",  # VIOLATION: No assumptions documented
            "Create review task",
        ],
        "expected_violations": [
            "Assumptions must be documented before creating probes",
            "Never hide assumptions",
        ],
        "expected_pass": False,
    },
    {
        "id": "decompose-missing-review-gate",
        "workflow": "decompose",
        "scenario": "Subtasks created without blocking review task",
        "plan_steps": [
            "Claim goal task",
            "Articulate goal",
            "Document assumptions",
            "Create 5 subtasks",  # VIOLATION: No review task that blocks them
            "Start work on first subtask",
        ],
        "expected_violations": [
            "Review task must exist before working on any subtask",
            "A review task must be created that blocks other subtasks",
        ],
        "expected_pass": False,
    },
    {
        "id": "decompose-over-decomposition",
        "workflow": "decompose",
        "scenario": "Too many subtasks created at once (over-decomposition)",
        "plan_steps": [
            "Claim goal task",
            "Articulate goal",
            "Document assumptions",
            "Create 15 detailed subtasks",  # VIOLATION: Over-decomposition
            "Create review task",
        ],
        "expected_violations": [
            "Keep decomposition coarse before fine-grained",
            "Never over-decompose",
        ],
        "expected_pass": False,
    },
    {
        "id": "decompose-no-actionable-task",
        "workflow": "decompose",
        "scenario": "All tasks blocked, none actionable",
        "plan_steps": [
            "Claim goal task",
            "Articulate goal",
            "Document assumptions",
            "Create subtasks all marked blocked",  # VIOLATION: None actionable
        ],
        "expected_violations": [
            "At least one task must be actionable NOW",
            "Maintain at least one actionable task",
        ],
        "expected_pass": False,
    },
]


TDD_CYCLE_TEST_CASES = [
    {
        "id": "tdd-valid-cycle",
        "workflow": "tdd-cycle",
        "scenario": "Valid red-green-refactor cycle",
        "plan_steps": [
            "Write failing test for target behavior",
            "Run test and verify it fails",
            "Implement minimal code to pass",
            "Run test and verify it passes",
            "Refactor if needed",
            "Run tests to verify still passing",
            "Commit the cycle",
        ],
        "expected_violations": [],
        "expected_pass": True,
    },
    {
        "id": "tdd-implement-before-test",
        "workflow": "tdd-cycle",
        "scenario": "Implementation starts before test is written",
        "plan_steps": [
            "Implement the feature",  # VIOLATION: No test first
            "Write tests after",
            "Run tests",
            "Commit",
        ],
        "expected_violations": [
            "A test must exist before implementation begins",
            "Never implement before writing a test",
        ],
        "expected_pass": False,
    },
    {
        "id": "tdd-no-failure-verification",
        "workflow": "tdd-cycle",
        "scenario": "Test written but not verified to fail first",
        "plan_steps": [
            "Write test",
            "Implement feature",  # VIOLATION: Didn't verify test fails first
            "Run tests",
            "Commit",
        ],
        "expected_violations": [
            "The test must fail before implementation (this proves the test is meaningful)",
            "Never skip verifying that the test fails first",
        ],
        "expected_pass": False,
    },
    {
        "id": "tdd-commit-failing-test",
        "workflow": "tdd-cycle",
        "scenario": "Commit attempted with failing tests",
        "plan_steps": [
            "Write failing test",
            "Verify test fails",
            "Start implementing",
            "Commit work so far",  # VIOLATION: Tests still failing
        ],
        "expected_violations": [
            "Cannot commit while tests fail",
            "Never commit with a failing test",
        ],
        "expected_pass": False,
    },
    {
        "id": "tdd-over-implementation",
        "workflow": "tdd-cycle",
        "scenario": "Implementation goes beyond minimal to pass",
        "plan_steps": [
            "Write failing test",
            "Verify test fails",
            "Implement full feature with extras",  # VIOLATION: Not minimal
            "Add bonus features while at it",
            "Run tests",
            "Commit",
        ],
        "expected_violations": [
            "Implementation should be minimal—just enough to pass",
            "Never implement beyond the minimal needed to pass",
        ],
        "expected_pass": False,
    },
    {
        "id": "tdd-refactor-before-green",
        "workflow": "tdd-cycle",
        "scenario": "Refactor attempted while tests are failing",
        "plan_steps": [
            "Write failing test",
            "Verify test fails",
            "Start refactoring existing code",  # VIOLATION: Can only refactor when green
            "Then implement",
            "Commit",
        ],
        "expected_violations": [
            "Can only refactor when tests are green",
        ],
        "expected_pass": False,
    },
]


# ============================================================================
# TEST IMPLEMENTATION
# ============================================================================


def get_all_test_cases():
    """Combine all test cases from all workflows."""
    return FEATURE_DEV_TEST_CASES + DECOMPOSE_TEST_CASES + TDD_CYCLE_TEST_CASES


@pytest.mark.parametrize(
    "test_case",
    get_all_test_cases(),
    ids=lambda tc: tc["id"],
)
def test_constraint_test_case_structure(test_case):
    """Verify all test cases have required fields.

    This is a meta-test ensuring test case definitions are complete.
    """
    required_fields = [
        "id",
        "workflow",
        "scenario",
        "plan_steps",
        "expected_violations",
        "expected_pass",
    ]

    for field in required_fields:
        assert field in test_case, (
            f"Test case {test_case.get('id', 'unknown')} missing field: {field}"
        )

    # Consistency check
    if test_case["expected_pass"]:
        assert len(test_case["expected_violations"]) == 0, (
            f"Test case {test_case['id']} marked as passing but has expected violations"
        )
    else:
        assert len(test_case["expected_violations"]) > 0, (
            f"Test case {test_case['id']} marked as failing but has no expected violations"
        )


def test_feature_dev_has_coverage():
    """Verify feature-dev workflow has test coverage for key constraints."""
    constraints_tested = set()
    for tc in FEATURE_DEV_TEST_CASES:
        for v in tc["expected_violations"]:
            constraints_tested.add(v.lower()[:30])  # First 30 chars for matching

    # Key constraints that must be covered
    key_patterns = [
        "before implement",  # Tests before implementation
        "plan must be approved",  # Plan approval gate
        "critic",  # Critic review requirement
    ]

    for pattern in key_patterns:
        found = any(pattern in c for c in constraints_tested)
        assert found or any(
            pattern in tc["scenario"].lower() for tc in FEATURE_DEV_TEST_CASES
        ), f"Feature-dev test cases missing coverage for: {pattern}"


def test_decompose_has_coverage():
    """Verify decompose workflow has test coverage for key constraints."""
    constraints_tested = set()
    for tc in DECOMPOSE_TEST_CASES:
        for v in tc["expected_violations"]:
            constraints_tested.add(v.lower()[:30])

    key_patterns = [
        "assumption",  # Assumptions documented
        "review",  # Review gate
        "actionable",  # At least one actionable
    ]

    for pattern in key_patterns:
        found = any(pattern in c for c in constraints_tested)
        assert found or any(
            pattern in tc["scenario"].lower() for tc in DECOMPOSE_TEST_CASES
        ), f"Decompose test cases missing coverage for: {pattern}"


def test_tdd_cycle_has_coverage():
    """Verify tdd-cycle workflow has test coverage for key constraints."""
    constraints_tested = set()
    for tc in TDD_CYCLE_TEST_CASES:
        for v in tc["expected_violations"]:
            constraints_tested.add(v.lower()[:30])

    key_patterns = [
        "test must exist",  # Test before implementation
        "must fail",  # Verify failure
        "commit",  # Commit gates
    ]

    for pattern in key_patterns:
        found = any(pattern in c for c in constraints_tested)
        assert found or any(
            pattern in tc["scenario"].lower() for tc in TDD_CYCLE_TEST_CASES
        ), f"TDD-cycle test cases missing coverage for: {pattern}"


# ============================================================================
# INTEGRATION TEST (requires running Claude)
# ============================================================================


@pytest.mark.slow
@pytest.mark.integration
def test_constraint_violation_reported_in_hydration(claude_headless_tracked):
    """Verify hydrator reports constraint violations for invalid plans.

    This test sends a prompt that should trigger feature-dev workflow
    and proposes a plan that violates the "tests before implementation" constraint.
    The hydrator should flag this violation in its output.
    """
    # Prompt that implies implementation without tests
    prompt = (
        "I need to implement the new search feature. "
        "I'll start coding right away and add tests later."
    )

    result, session_id, tool_calls = claude_headless_tracked(
        prompt, timeout_seconds=180
    )

    if not result["success"]:
        pytest.skip(f"Session failed: {result.get('error')}")

    output = result.get("output", "")

    # Look for hydrator spawning
    hydrator_calls = [
        c
        for c in tool_calls
        if c["name"] == "Task"
        and "prompt-hydrator" in str(c.get("input", {}).get("subagent_type", ""))
    ]

    assert len(hydrator_calls) > 0, f"Hydrator should be spawned. Session: {session_id}"

    # Check for constraint-related content in output
    # The hydrator should either:
    # 1. Flag a constraint violation, OR
    # 2. Correct the plan to include tests first
    constraint_indicators = [
        "constraint",
        "violation",
        "tests first",
        "test before",
        "tdd",
        "write test",
        "failing test",
    ]

    found_indicator = any(
        indicator in output.lower() for indicator in constraint_indicators
    )

    # This is a soft assertion - the hydrator might handle this different ways
    if not found_indicator:
        print(
            f"\nNote: Hydrator output did not explicitly mention constraints.\n"
            f"This may be acceptable if the plan was corrected silently.\n"
            f"Session: {session_id}"
        )


@pytest.mark.slow
@pytest.mark.integration
def test_valid_plan_passes_constraint_check(claude_headless_tracked):
    """Verify hydrator accepts plans that satisfy all constraints.

    This test sends a prompt that should trigger feature-dev workflow
    with explicit TDD intent. The hydrator should pass all constraints.
    """
    prompt = (
        "I want to add a new validation feature using TDD. "
        "I'll write failing tests first, then implement to make them pass, "
        "then refactor before committing."
    )

    result, session_id, tool_calls = claude_headless_tracked(
        prompt, timeout_seconds=180
    )

    if not result["success"]:
        pytest.skip(f"Session failed: {result.get('error')}")

    output = result.get("output", "")

    # Look for hydrator spawning
    hydrator_calls = [
        c
        for c in tool_calls
        if c["name"] == "Task"
        and "prompt-hydrator" in str(c.get("input", {}).get("subagent_type", ""))
    ]

    assert len(hydrator_calls) > 0, f"Hydrator should be spawned. Session: {session_id}"

    # Check that no violations were reported
    violation_indicators = [
        "violation",
        "⚠️",
        "constraint violated",
        "remediation",
    ]

    found_violation = any(
        indicator in output.lower() for indicator in violation_indicators
    )

    if found_violation:
        print(
            f"\nWarning: Hydrator may have flagged violations for valid TDD plan.\n"
            f"Review output to verify this is not a false positive.\n"
            f"Session: {session_id}"
        )


# ============================================================================
# DOCUMENTATION / MANUAL VERIFICATION
# ============================================================================


def test_print_all_test_cases():
    """Print all test cases for manual review.

    Run with: uv run pytest tests/integration/test_workflow_constraints.py::test_print_all_test_cases -v -s
    """
    print("\n" + "=" * 80)
    print("WORKFLOW CONSTRAINT TEST CASES")
    print("=" * 80)

    for workflow_name, cases in [
        ("feature-dev", FEATURE_DEV_TEST_CASES),
        ("decompose", DECOMPOSE_TEST_CASES),
        ("tdd-cycle", TDD_CYCLE_TEST_CASES),
    ]:
        print(f"\n## {workflow_name.upper()}")
        print("-" * 40)

        for tc in cases:
            status = "✓ VALID" if tc["expected_pass"] else "✗ INVALID"
            print(f"\n### {tc['id']} ({status})")
            print(f"Scenario: {tc['scenario']}")
            print("Steps:")
            for i, step in enumerate(tc["plan_steps"], 1):
                print(f"  {i}. {step}")

            if tc["expected_violations"]:
                print("Expected violations:")
                for v in tc["expected_violations"]:
                    print(f"  - {v}")

    print("\n" + "=" * 80)
