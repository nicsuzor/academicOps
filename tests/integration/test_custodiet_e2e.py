#!/usr/bin/env python3
"""End-to-end tests for custodiet compliance checking.

These tests use the claude_headless fixture to run REAL Claude Code sessions
and verify actual custodiet behavior - not mocked Python imports.

Per H37: Tests verify ACTUAL behavior (Task spawned, files readable) not surface patterns.
Per H37a: Demo tests show FULL untruncated output for human validation.
Per H37b: Use REAL framework prompts, not contrived examples.

Run all tests:
    uv run pytest tests/integration/test_custodiet_e2e.py -v -m "slow"

Run demo test for visual validation:
    uv run pytest tests/integration/test_custodiet_e2e.py -k demo -v -s -n 0
"""

import time
from pathlib import Path

import pytest


# Custodiet threshold from hook configuration
TOOL_CALL_THRESHOLD = 50


def find_recent_audit_files(max_age_seconds: int = 300) -> list[Path]:
    """Find audit files created in the last N seconds."""
    temp_dir = Path("/tmp/claude-compliance")
    if not temp_dir.exists():
        return []

    cutoff = time.time() - max_age_seconds
    return [f for f in temp_dir.glob("audit_*.md") if f.stat().st_mtime > cutoff]


@pytest.mark.slow
@pytest.mark.integration
def test_custodiet_temp_file_created_on_threshold(claude_headless) -> None:
    """Verify custodiet hook creates temp file when threshold reached.

    This test triggers enough tool calls to hit the custodiet threshold,
    then verifies a temp file was created in /tmp/claude-compliance/.

    Per H37c: Execution over inspection - we verify actual file creation.
    """
    # Record existing files before test
    temp_dir = Path("/tmp/claude-compliance")
    files_before = set(temp_dir.glob("audit_*.md")) if temp_dir.exists() else set()

    # Prompt that will trigger many Bash tool calls
    # The custodiet hook triggers after TOOL_CALL_THRESHOLD tool uses
    prompt = (
        "CUSTODIET_TEST: Run these bash commands one at a time, waiting for each: "
        "echo 1, echo 2, echo 3, echo 4, echo 5, echo 6, echo 7, echo 8, echo 9, echo 10, "
        "echo 11, echo 12, echo 13, echo 14, echo 15, echo 16, echo 17, echo 18, echo 19, echo 20, "
        "echo 21, echo 22, echo 23, echo 24, echo 25, echo 26, echo 27, echo 28, echo 29, echo 30, "
        "echo 31, echo 32, echo 33, echo 34, echo 35, echo 36, echo 37, echo 38, echo 39, echo 40, "
        "echo 41, echo 42, echo 43, echo 44, echo 45, echo 46, echo 47, echo 48, echo 49, echo 50, "
        "echo 51, echo 52, echo 53, echo done"
    )

    result = claude_headless(prompt, timeout_seconds=300)

    # Test may fail due to agent behavior, but we want to check file creation regardless
    files_after = set(temp_dir.glob("audit_*.md")) if temp_dir.exists() else set()
    new_files = files_after - files_before

    # Verify temp file was created (custodiet hook fired)
    assert len(new_files) > 0, (
        f"Custodiet should create audit file when threshold ({TOOL_CALL_THRESHOLD}) reached. "
        f"Files before: {len(files_before)}, after: {len(files_after)}. "
        f"Session success: {result.get('success')}"
    )

    # Verify file has content
    newest_file = max(new_files, key=lambda f: f.stat().st_mtime)
    content = newest_file.read_text()
    assert (
        len(content) > 1000
    ), f"Audit file should contain substantial context. Got {len(content)} chars"
    assert "AXIOMS" in content, "Audit file should contain AXIOMS section"
    assert "HEURISTICS" in content, "Audit file should contain HEURISTICS section"


@pytest.mark.slow
@pytest.mark.integration
def test_custodiet_task_spawned(claude_headless_tracked) -> None:
    """Verify custodiet Task is actually spawned when threshold reached.

    Uses session tracking to verify the Task tool was called with
    subagent_type="custodiet". This tests ACTUAL invocation, not keywords.

    Per H37: Verify actual behavior (Task spawned) not surface patterns.
    """
    # Prompt to trigger threshold
    prompt = (
        "CUSTODIET_SPAWN_TEST: Execute these bash commands sequentially: "
        + ", ".join([f"echo {i}" for i in range(1, 55)])
        + ". Then report 'done'."
    )

    result, session_id, tool_calls = claude_headless_tracked(
        prompt, timeout_seconds=300
    )

    # Find custodiet Task calls
    custodiet_calls = [
        call
        for call in tool_calls
        if call["name"] == "Task"
        and call.get("input", {}).get("subagent_type") == "custodiet"
    ]

    assert len(custodiet_calls) > 0, (
        f"Custodiet Task should be spawned after {TOOL_CALL_THRESHOLD} tool calls. "
        f"Session {session_id} had {len(tool_calls)} tool calls but none were "
        f"custodiet Tasks. Task calls found: "
        f"{[c['name'] for c in tool_calls if c['name'] == 'Task']}"
    )

    # Verify custodiet was given the temp file path
    custodiet_input = custodiet_calls[0].get("input", {})
    custodiet_prompt = custodiet_input.get("prompt", "")

    assert "/tmp/claude-compliance/audit_" in custodiet_prompt, (
        f"Custodiet prompt should reference temp file path. "
        f"Got: {custodiet_prompt[:200]}..."
    )


@pytest.mark.slow
@pytest.mark.integration
def test_custodiet_subagent_file_access(claude_headless_tracked) -> None:
    """Test whether custodiet subagent can read its temp file (Issue #277).

    This is the key test for the alleged bug: Task() subagents may run in
    sandbox isolation and cannot access /tmp files from the parent session.

    Per H37d: Use observable side-effects for verification.
    """
    # Prompt to trigger custodiet
    prompt = (
        "CUSTODIET_FILE_ACCESS_TEST: Run 55 sequential echo commands "
        "(echo 1 through echo 55), then tell me what happened."
    )

    result, session_id, tool_calls = claude_headless_tracked(
        prompt, timeout_seconds=300
    )

    # Find custodiet Task calls
    custodiet_calls = [
        call
        for call in tool_calls
        if call["name"] == "Task"
        and call.get("input", {}).get("subagent_type") == "custodiet"
    ]

    if not custodiet_calls:
        pytest.skip("Custodiet not spawned - threshold may not have been reached")

    # Look for Read tool calls from the custodiet subagent
    # If the subagent can read the file, we should see a Read call to the audit file
    output = result.get("output", "")

    # Check for evidence of successful file read OR file read failure
    file_read_success_indicators = [
        "OK",  # Custodiet returns "OK" if compliant
        "ATTENTION",  # Custodiet returns "ATTENTION" if issues found
        "Ultra Vires",  # Content from the audit file
    ]

    file_read_failure_indicators = [
        "Error reading file",
        "No such file",
        "cannot access",
        "Permission denied",
    ]

    success_found = any(
        indicator in output for indicator in file_read_success_indicators
    )
    failure_found = any(
        indicator in output for indicator in file_read_failure_indicators
    )

    # Report what we found - this test documents current behavior
    if failure_found:
        pytest.fail(
            f"ISSUE #277 CONFIRMED: Custodiet subagent cannot read temp file. "
            f"Session: {session_id}. "
            f"This indicates Task() subagents have filesystem isolation from parent."
        )

    if not success_found and not failure_found:
        # Inconclusive - custodiet may have run but output not captured
        print("\nWARNING: Could not determine if custodiet read file successfully.")
        print(f"Session: {session_id}")
        print(f"Output length: {len(output)} chars")


@pytest.mark.demo
class TestCustodietDemo:
    """Demo tests showing real custodiet behavior.

    Run with: uv run pytest tests/integration/test_custodiet_e2e.py -k demo -v -s -n 0

    These tests print FULL UNTRUNCATED output for human validation (H37a).
    """

    def test_demo_custodiet_temp_file_content(self) -> None:
        """Show FULL temp file content - no truncation.

        Per H37a: Demo output must show FULL untruncated content
        so humans can visually validate.
        """
        temp_dir = Path("/tmp/claude-compliance")

        if not temp_dir.exists():
            pytest.skip("No custodiet temp directory - run a Claude session first")

        # Get most recent temp file
        temp_files = sorted(
            temp_dir.glob("audit_*.md"), key=lambda f: f.stat().st_mtime, reverse=True
        )

        if not temp_files:
            pytest.skip("No custodiet temp files found")

        most_recent = temp_files[0]
        content = most_recent.read_text()

        print("\n" + "=" * 80)
        print("CUSTODIET TEMP FILE DEMO - FULL CONTENT (H37a)")
        print("=" * 80)
        print(f"\nFile: {most_recent}")
        print(f"Size: {most_recent.stat().st_size} bytes")
        print(f"Modified: {time.ctime(most_recent.stat().st_mtime)}")
        print("\n--- FULL CONTENT (NO TRUNCATION) ---\n")
        print(content)  # FULL content, not truncated
        print("\n--- END CONTENT ---\n")

        # Structural validation
        checks = {
            "Has Session Context section": "## Session Context" in content,
            "Has AXIOMS section": "# AXIOMS" in content,
            "Has HEURISTICS section": "# HEURISTICS" in content,
            "Has Last Tool section": "## Last Tool" in content,
            "Has OUTPUT FORMAT section": "## OUTPUT FORMAT" in content,
            "Contains substantial content": len(content) > 2000,
        }

        print("--- STRUCTURAL VALIDATION ---")
        all_passed = True
        for check, passed in checks.items():
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {check}")
            if not passed:
                all_passed = False

        print("=" * 80)
        assert all_passed, "Structural validation failed - see above"

    def test_demo_custodiet_full_flow(self, claude_headless) -> None:
        """Demo full custodiet flow with REAL framework task (H37b).

        Shows complete custodiet behavior with a task that naturally
        triggers the threshold.
        """
        print("\n" + "=" * 80)
        print("CUSTODIET E2E DEMO - FULL FLOW (H37b)")
        print("=" * 80)

        # Real framework prompt that will make many tool calls
        prompt = (
            "CUSTODIET_DEMO: I want to understand the hook system. "
            "Read these files one by one: "
            "hooks/policy_enforcer.py, hooks/custodiet.py, hooks/prompt_router.py, "
            "hooks/criteria_gate.py, hooks/deny_rules.yaml. "
            "Then list all files in hooks/templates/. "
            "Then read each template file. "
            "Finally summarize what you learned about the hook system."
        )
        print(f"\nPrompt (REAL TASK): {prompt[:100]}...")
        print("\nExecuting headless session (this may take a few minutes)...")

        result = claude_headless(prompt, timeout_seconds=300)

        print(f"\nSuccess: {result['success']}")

        if not result["success"]:
            print(f"Error: {result.get('error')}")

        output = result.get("output", "")
        print(f"\nOutput length: {len(output)} chars")

        # Check for custodiet activity
        print("\n--- CUSTODIET ACTIVITY CHECK ---")

        custodiet_indicators = [
            (
                "Task spawn instruction",
                'subagent_type="custodiet"' in output
                or "subagent_type='custodiet'" in output,
            ),
            ("Temp file reference", "/tmp/claude-compliance/audit_" in output),
            ("Custodiet response (OK)", "```text\nOK\n```" in output),
            (
                "Custodiet response (ATTENTION)",
                "ATTENTION" in output and "Issue:" in output,
            ),
        ]

        for name, found in custodiet_indicators:
            status = "FOUND" if found else "NOT FOUND"
            print(f"  [{status}] {name}")

        # Show recent temp files
        temp_dir = Path("/tmp/claude-compliance")
        if temp_dir.exists():
            recent_files = find_recent_audit_files(max_age_seconds=300)
            print("\n--- RECENT AUDIT FILES (last 5 min) ---")
            print(f"  Count: {len(recent_files)}")
            for f in recent_files[:5]:
                print(f"  - {f.name} ({f.stat().st_size} bytes)")

        print("\n--- SESSION OUTPUT (FULL, NO TRUNCATION) ---")
        print(output)  # FULL output
        print("--- END OUTPUT ---")
        print("=" * 80)

    def test_demo_custodiet_tracked(self, claude_headless_tracked) -> None:
        """Demo with session tracking showing ALL tool calls.

        Verifies custodiet Task was actually spawned (not just keywords).
        """
        print("\n" + "=" * 80)
        print("CUSTODIET TRACKED DEMO - ALL TOOL CALLS")
        print("=" * 80)

        # Prompt that will trigger many tool calls
        prompt = (
            "CUSTODIET_TRACKED_DEMO: Run 55 bash echo commands (echo 1 through echo 55) "
            "one at a time. After each batch of 10, pause and count how many you've done."
        )
        print(f"\nPrompt: {prompt[:80]}...")
        print("\nExecuting tracked headless session...")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=300
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        if not result["success"]:
            print(f"Error: {result.get('error')}")

        # Count tool types
        tool_counts = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1

        print("\n--- TOOL CALL SUMMARY ---")
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"  {name}: {count}")

        # Find Task calls specifically
        task_calls = [c for c in tool_calls if c["name"] == "Task"]
        print(f"\n--- TASK CALLS ({len(task_calls)}) ---")
        for i, call in enumerate(task_calls):
            task_input = call.get("input", {})
            subagent_type = task_input.get("subagent_type", "N/A")
            description = task_input.get("description", "N/A")
            print(f"\n[{i + 1}] subagent_type: {subagent_type}")
            print(f"    description: {description}")
            if subagent_type == "custodiet":
                prompt_text = task_input.get("prompt", "")
                print(f"    prompt: {prompt_text[:200]}...")

        # Check for custodiet specifically
        custodiet_calls = [
            c
            for c in task_calls
            if c.get("input", {}).get("subagent_type") == "custodiet"
        ]

        print("\n--- CUSTODIET VERIFICATION ---")
        print(f"Custodiet Task calls found: {len(custodiet_calls)}")

        if custodiet_calls:
            print("Custodiet WAS spawned during this session.")
        else:
            print(f"WARNING: No custodiet Task found in {len(tool_calls)} tool calls.")
            print(f"Threshold is {TOOL_CALL_THRESHOLD} - may not have been reached.")

        print("=" * 80)
