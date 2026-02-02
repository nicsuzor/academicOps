#!/usr/bin/env python3
"""Acceptance test runner for aops v1.1 release.

Parses markdown test definitions, executes tests via Claude Code headless mode,
evaluates results against pass criteria, and updates the results table.

Usage:
    uv run python tests/acceptance/run_acceptance_tests.py
    uv run python tests/acceptance/run_acceptance_tests.py --test TEST-001
    uv run python tests/acceptance/run_acceptance_tests.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

TESTS_DIR = Path(__file__).parent
ACCEPTANCE_FILE = TESTS_DIR / "v1.1-release.md"


@dataclass
class PassCriteria:
    """Structured pass criteria for a test."""

    criteria_type: str  # all_of, any_of
    checks: list[dict[str, Any]]


@dataclass
class TestCase:
    """A single acceptance test case."""

    test_id: str
    name: str
    description: str
    user_input: str
    expected_behavior: list[str]
    invocation_method: str  # hydrator-only, full-session, component
    pass_criteria: PassCriteria
    why_matters: str
    related: list[str]


@dataclass
class TestResult:
    """Result of running a test."""

    test_id: str
    status: str  # PASS, FAIL, ERROR, SKIP
    timestamp: str
    notes: str
    raw_output: str | None = None


def parse_test_file(filepath: Path) -> list[TestCase]:
    """Parse acceptance test markdown file into TestCase objects."""
    content = filepath.read_text()

    # Find all test sections (### TEST-NNN: ...)
    test_pattern = r"### (TEST-\d+): (.+?)(?=\n### TEST-|\n## Results|\Z)"
    matches = re.findall(test_pattern, content, re.DOTALL)

    tests = []
    for test_id, test_content in matches:
        test_content = f"### {test_id}: {test_content}"
        test = parse_single_test(test_id, test_content)
        if test:
            tests.append(test)

    return tests


def parse_single_test(test_id: str, content: str) -> TestCase | None:
    """Parse a single test section into a TestCase."""
    # Extract name from header
    name_match = re.search(r"### TEST-\d+: (.+)", content)
    name = name_match.group(1).strip() if name_match else test_id

    # Extract ID field
    id_match = re.search(r"\*\*ID\*\*: `([^`]+)`", content)
    full_id = id_match.group(1) if id_match else test_id

    # Extract description
    desc_match = re.search(r"\*\*Description\*\*: (.+?)(?=\n\n|\n\*\*)", content, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else ""

    # Extract user input (code block after **User Input**)
    input_match = re.search(r"\*\*User Input\*\*:\s*```\n?(.+?)```", content, re.DOTALL)
    user_input = input_match.group(1).strip() if input_match else ""

    # Extract expected behavior (numbered list)
    behavior_match = re.search(
        r"\*\*Expected Behavior\*\*:\s*\n((?:\d+\..+\n?)+)", content
    )
    expected_behavior = []
    if behavior_match:
        lines = behavior_match.group(1).strip().split("\n")
        expected_behavior = [re.sub(r"^\d+\.\s*", "", line).strip() for line in lines]

    # Extract invocation method
    method_match = re.search(r"\*\*Invocation Method\*\*: `([^`]+)`", content)
    invocation_method = method_match.group(1) if method_match else "hydrator-only"

    # Extract pass criteria (YAML block)
    criteria_match = re.search(
        r"\*\*Pass Criteria\*\*:\s*```yaml\n(.+?)```", content, re.DOTALL
    )
    pass_criteria = PassCriteria(criteria_type="all_of", checks=[])
    if criteria_match:
        try:
            criteria_yaml = yaml.safe_load(criteria_match.group(1))
            # Fail fast if required keys missing
            pass_criteria = PassCriteria(
                criteria_type=criteria_yaml["type"],
                checks=criteria_yaml["checks"],
            )
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in pass criteria: {e}") from e
        except KeyError as e:
            raise ValueError(f"Missing required key in pass criteria: {e}") from e

    # Extract why matters
    why_match = re.search(r"\*\*Why This Matters\*\*: (.+?)(?=\n\n|\n\*\*|\Z)", content)
    why_matters = why_match.group(1).strip() if why_match else ""

    # Extract related links
    related_match = re.search(r"\*\*Related\*\*:\s*\n((?:- .+\n?)+)", content)
    related = []
    if related_match:
        lines = related_match.group(1).strip().split("\n")
        related = [line.lstrip("- ").strip() for line in lines]

    if not user_input:
        return None

    return TestCase(
        test_id=full_id,
        name=name,
        description=description,
        user_input=user_input,
        expected_behavior=expected_behavior,
        invocation_method=invocation_method,
        pass_criteria=pass_criteria,
        why_matters=why_matters,
        related=related,
    )


def run_hydrator(user_input: str, timeout: int = 120) -> tuple[bool, str]:
    """Run the hydrator via Claude Code headless mode.

    Returns (success, output).
    """
    # Construct prompt that invokes hydrator
    prompt = f"""You are testing the hydrator. Invoke the prompt-hydrator agent with this exact input:

Task(subagent_type="aops-core:prompt-hydrator", prompt="{user_input}")

Return the hydrator's full output."""

    cmd = [
        "claude",
        "--print",
        "--output-format",
        "json",
        "--model",
        "claude-sonnet-4-5-20250929",
        "--permission-mode",
        "bypassPermissions",
        "-p",
        prompt,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent.parent,  # academicOps root
        )

        if result.returncode != 0:
            return False, f"Claude exited with code {result.returncode}: {result.stderr}"

        # Parse JSON output
        try:
            output = json.loads(result.stdout)
            response = output["result"]
            return True, response
        except json.JSONDecodeError:
            return True, result.stdout
        except KeyError:
            return True, result.stdout

    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s"
    except FileNotFoundError:
        return False, "Claude CLI not found"


def evaluate_criteria(output: str, criteria: PassCriteria) -> tuple[bool, str]:
    """Evaluate pass criteria against output.

    Returns (passed, explanation).
    """
    output_lower = output.lower()
    results = []

    for check in criteria.checks:
        check_type = check["type"]
        values = check["values"]

        if check_type == "contains":
            # All values must be present
            missing = [v for v in values if v.lower() not in output_lower]
            if missing:
                results.append((False, f"Missing required: {missing}"))
            else:
                results.append((True, f"Found all: {values}"))

        elif check_type == "contains_any":
            # At least one value must be present
            found = [v for v in values if v.lower() in output_lower]
            if found:
                results.append((True, f"Found: {found}"))
            else:
                results.append((False, f"Missing any of: {values}"))

        elif check_type == "calls_tool":
            # Check for tool invocation pattern
            tool_pattern = r"mcp__\w+__\w+"
            found_tools = re.findall(tool_pattern, output_lower)
            matching = [t for t in found_tools if any(v.lower() in t for v in values)]
            if matching:
                results.append((True, f"Found tool calls: {matching}"))
            else:
                results.append((False, f"No tool calls matching: {values}"))

        else:
            raise ValueError(f"Unknown check type: {check_type}")

    # Apply criteria type (all_of vs any_of)
    if criteria.criteria_type == "all_of":
        passed = all(r[0] for r in results)
    else:  # any_of
        passed = any(r[0] for r in results)

    explanation = "; ".join(r[1] for r in results)
    return passed, explanation


def run_test(test: TestCase, dry_run: bool = False) -> TestResult:
    """Execute a single test and return result."""
    timestamp = datetime.now(timezone.utc).isoformat()

    if dry_run:
        return TestResult(
            test_id=test.test_id,
            status="SKIP",
            timestamp=timestamp,
            notes="Dry run - not executed",
        )

    print(f"  Running {test.test_id}: {test.name}")
    print(f"    Input: {test.user_input!r}")
    print(f"    Method: {test.invocation_method}")

    if test.invocation_method == "hydrator-only":
        success, output = run_hydrator(test.user_input)
    else:
        # Full session - not yet implemented
        return TestResult(
            test_id=test.test_id,
            status="SKIP",
            timestamp=timestamp,
            notes=f"Invocation method '{test.invocation_method}' not yet implemented",
        )

    if not success:
        return TestResult(
            test_id=test.test_id,
            status="ERROR",
            timestamp=timestamp,
            notes=f"Execution failed: {output}",
            raw_output=output,
        )

    # Evaluate pass criteria
    passed, explanation = evaluate_criteria(output, test.pass_criteria)

    return TestResult(
        test_id=test.test_id,
        status="PASS" if passed else "FAIL",
        timestamp=timestamp,
        notes=explanation,
        raw_output=output,
    )


def update_results_table(filepath: Path, results: list[TestResult]) -> None:
    """Update the Results table in the markdown file."""
    content = filepath.read_text()

    # Build new results table
    table_lines = [
        "| Test ID | Status | Timestamp | Notes |",
        "|---------|--------|-----------|-------|",
    ]
    for r in results:
        # Truncate notes for table
        notes = r.notes[:80] + "..." if len(r.notes) > 80 else r.notes
        notes = notes.replace("|", "\\|")  # Escape pipes
        table_lines.append(f"| {r.test_id} | {r.status} | {r.timestamp[:19]} | {notes} |")

    new_table = "\n".join(table_lines)

    # Replace existing results table
    pattern = r"(## Results\s*\n\n_Results populated by test runner agent_\s*\n\n)\|.+?\|(?=\n\n---|\n\n##|\Z)"
    replacement = r"\1" + new_table
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    filepath.write_text(new_content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run aops acceptance tests")
    parser.add_argument(
        "--test",
        help="Run specific test by ID (e.g., TEST-001)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse tests but don't execute",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )
    args = parser.parse_args()

    print(f"Loading tests from: {ACCEPTANCE_FILE}")
    tests = parse_test_file(ACCEPTANCE_FILE)
    print(f"Found {len(tests)} test(s)")

    if args.test:
        tests = [t for t in tests if args.test in t.test_id]
        if not tests:
            print(f"No test matching '{args.test}'")
            return 1

    results = []
    for test in tests:
        result = run_test(test, dry_run=args.dry_run)
        results.append(result)

        if args.verbose and result.raw_output:
            print(f"\n--- Raw output for {test.test_id} ---")
            print(result.raw_output[:2000])
            print("---")

        print(f"  Result: {result.status}")
        if result.status != "PASS":
            print(f"  Notes: {result.notes}")

    # Update results in markdown file
    if not args.dry_run:
        update_results_table(ACCEPTANCE_FILE, results)
        print(f"\nResults updated in {ACCEPTANCE_FILE}")

    # Summary
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    errors = sum(1 for r in results if r.status == "ERROR")
    skipped = sum(1 for r in results if r.status == "SKIP")

    print(f"\nSummary: {passed} passed, {failed} failed, {errors} errors, {skipped} skipped")

    return 0 if failed == 0 and errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
