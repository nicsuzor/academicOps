#!/usr/bin/env python3
"""
Test script for validate_tool.py

Tests the warning and blocking functionality of the tool validation system.
"""

import json
import subprocess
import sys
from pathlib import Path


def test_validation(test_name: str, tool_name: str, tool_input: dict, expected_allowed: bool, expected_severity: str = "block"):
    """Run a single validation test."""
    input_data = {
        "tool_name": tool_name,
        "tool_input": tool_input
    }

    # Run the validation script
    script_path = Path("/home/nic/src/writing/bot/scripts/validate_tool.py")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    # Parse the JSON output to check permissionDecision
    try:
        output = json.loads(result.stderr.strip())
        permission_decision = output.get("hookSpecificOutput", {}).get("permissionDecision", "unknown")
    except:
        permission_decision = "unknown"

    # Check results
    actual_allowed = result.returncode == 0
    actual_has_message = bool(result.stderr.strip())

    # Determine expected behavior based on exit code mapping:
    # - "allow": exit 0
    # - "ask": exit 0
    # - "deny": exit 1
    if expected_allowed:
        expected_returncode = 0
        expected_permission = "allow"
        expected_has_message = True  # Even allow has JSON output
    else:
        if expected_severity == "warn":
            expected_returncode = 1  # Warnings use exit code 1
            expected_permission = "allow"  # Permission is "allow" with a warning message
            expected_has_message = True
        elif expected_severity == "force-ask":
            expected_returncode = 0  # "ask" exits with 0
            expected_permission = "ask"
            expected_has_message = True
        else:  # block
            expected_returncode = 2  # Blocks prevent the tool (exit code 2)
            expected_permission = "deny"
            expected_has_message = True

    # Report results
    status = "✅ PASS" if (result.returncode == expected_returncode) else "❌ FAIL"
    print(f"{status} {test_name}")
    print(f"   Expected: returncode={expected_returncode}, allowed={expected_allowed}, severity={expected_severity}, permission={expected_permission}")
    print(f"   Actual: returncode={result.returncode}, has_message={actual_has_message}, permission={permission_decision}")

    if result.stderr.strip():
        # Try to pretty print the message if it's JSON
        try:
            output = json.loads(result.stderr.strip())
            reason = output.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
            if reason:
                print(f"   Reason: {reason[:100]}...")
        except:
            print(f"   Message: {result.stderr.strip()[:100]}...")

    print()

    return result.returncode == expected_returncode


def main():
    """Run all validation tests."""
    print("=" * 80)
    print("Testing validate_tool.py")
    print("=" * 80)
    print()

    tests_passed = 0
    tests_total = 0

    # Test 1: Python without uv run (should warn)
    tests_total += 1
    if test_validation(
        "Python without uv run",
        "Bash",
        {"command": "python script.py", "subagent_type": "developer"},
        expected_allowed=False,
        expected_severity="warn"
    ):
        tests_passed += 1

    # Test 2: Python with uv run (should pass)
    tests_total += 1
    if test_validation(
        "Python with uv run",
        "Bash",
        {"command": "uv run python script.py", "subagent_type": "developer"},
        expected_allowed=True
    ):
        tests_passed += 1

    # Test 3: Pytest without uv run (should warn)
    tests_total += 1
    if test_validation(
        "Pytest without uv run",
        "Bash",
        {"command": "pytest tests/", "subagent_type": "developer"},
        expected_allowed=False,
        expected_severity="warn"
    ):
        tests_passed += 1

    # Test 4: Python3 without uv run (should warn)
    tests_total += 1
    if test_validation(
        "Python3 without uv run",
        "Bash",
        {"command": "python3 -m pytest", "subagent_type": "developer"},
        expected_allowed=False,
        expected_severity="warn"
    ):
        tests_passed += 1

    # Test 5: Chained command with python (should warn)
    tests_total += 1
    if test_validation(
        "Chained command with python",
        "Bash",
        {"command": "cd src && python test.py", "subagent_type": "developer"},
        expected_allowed=False,
        expected_severity="warn"
    ):
        tests_passed += 1

    # Test 6: Non-python command (should pass)
    tests_total += 1
    if test_validation(
        "Non-python command",
        "Bash",
        {"command": "ls -la", "subagent_type": "developer"},
        expected_allowed=True
    ):
        tests_passed += 1

    # Test 6.5: Timeout with uv run python (should pass)
    tests_total += 1
    if test_validation(
        "Timeout with uv run python",
        "Bash",
        {"command": "timeout 60 uv run python -m buttermilk.runner.cli", "subagent_type": "developer"},
        expected_allowed=True
    ):
        tests_passed += 1

    # Test 6.6: Timeout without uv run (should warn)
    tests_total += 1
    if test_validation(
        "Timeout without uv run",
        "Bash",
        {"command": "timeout 60 python test.py", "subagent_type": "developer"},
        expected_allowed=False,
        expected_severity="warn"
    ):
        tests_passed += 1

    # Test 7: Protected file edit by non-trainer (should block)
    tests_total += 1
    if test_validation(
        "Protected file edit by non-trainer",
        "Edit",
        {"file_path": ".claude/settings.json", "subagent_type": "developer"},
        expected_allowed=False,
        expected_severity="block"
    ):
        tests_passed += 1

    # Test 8: Protected file edit by trainer (should pass)
    tests_total += 1
    if test_validation(
        "Protected file edit by trainer",
        "Edit",
        {"file_path": ".gemini/config.json", "subagent_type": "trainer"},
        expected_allowed=True
    ):
        tests_passed += 1

    # Test 9: Git commit by non-code-review (should block with exit code 2)
    tests_total += 1
    if test_validation(
        "Git commit by non-code-review",
        "Bash",
        {"command": "git commit -m 'test'", "subagent_type": "developer"},
        expected_allowed=False,
        expected_severity="block"
    ):
        tests_passed += 1

    # Test 10: Fastmcp without uv run (should warn)
    tests_total += 1
    if test_validation(
        "Fastmcp without uv run",
        "Bash",
        {"command": "fastmcp dev server.py", "subagent_type": "developer"},
        expected_allowed=False,
        expected_severity="warn"
    ):
        tests_passed += 1

    # Test 11: Creating new markdown file in prohibited location (should block)
    tests_total += 1
    if test_validation(
        "Creating new markdown file in root",
        "Write",
        {"file_path": "README.md", "content": "# Test", "subagent_type": "developer"},
        expected_allowed=False,
        expected_severity="block"
    ):
        tests_passed += 1

    # Summary
    print("=" * 80)
    print(f"Results: {tests_passed}/{tests_total} tests passed")
    print("=" * 80)

    return 0 if tests_passed == tests_total else 1


if __name__ == "__main__":
    sys.exit(main())
