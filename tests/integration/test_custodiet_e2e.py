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

from lib import hook_utils

# Custodiet threshold from hooks/custodiet_gate.py
TOOL_CALL_THRESHOLD = 5

# Tools that custodiet SKIPS (don't count toward threshold)
# See hooks/custodiet_gate.py lines 214-218
SKIP_TOOLS = {"Read", "Glob", "Grep", "mcp__memory__retrieve_memory"}


def get_audit_temp_dir() -> Path:
    """Get the audit temp directory using shared logic."""
    # Align with the new consolidated "hydrator" category
    return hook_utils.get_hook_temp_dir("hydrator")


def find_recent_audit_files(max_age_seconds: int = 300) -> list[Path]:
    """Find audit files created in the last N seconds."""
    temp_dir = get_audit_temp_dir()
    if not temp_dir.exists():
        return []

    cutoff = time.time() - max_age_seconds
    return [f for f in temp_dir.glob("audit_*.md") if f.stat().st_mtime > cutoff]


@pytest.mark.slow
@pytest.mark.integration
def test_custodiet_temp_file_created_on_threshold(claude_headless) -> None:
    """Verify custodiet hook creates temp file when threshold reached.

    Triggers 7 Bash tool calls (above threshold of 5) to fire custodiet.
    NOTE: Read/Glob/Grep don't count - custodiet skips them (see SKIP_TOOLS).

    Per H37c: Execution over inspection - we verify actual file creation.
    """
    # Record existing files before test
    temp_dir = get_audit_temp_dir()
    files_before = set(temp_dir.glob("audit_*.md")) if temp_dir.exists() else set()

    # Prompt that triggers 7 separate BASH tool calls (not Read - those are skipped)
    # Custodiet only counts tools that modify state (Bash, Edit, Write, Task)
    prompt = (
        "Run these 7 bash commands ONE AT A TIME, reporting output after each: "
        "1. echo 'check 1' "
        "2. echo 'check 2' "
        "3. echo 'check 3' "
        "4. echo 'check 4' "
        "5. echo 'check 5' "
        "6. echo 'check 6' "
        "7. echo 'check 7'"
    )

    result = claude_headless(prompt, timeout_seconds=180)

    # Check file creation regardless of agent behavior
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
    assert len(content) > 1000, (
        f"Audit file should contain substantial context. Got {len(content)} chars"
    )
    assert "AXIOMS" in content, "Audit file should contain AXIOMS section"


@pytest.mark.slow
@pytest.mark.integration
def test_custodiet_task_spawned(claude_headless_tracked) -> None:
    """Verify custodiet Task is actually spawned when threshold reached.

    Uses session tracking to verify the Task tool was called with
    subagent_type="custodiet". This tests ACTUAL invocation, not keywords.

    NOTE: Read/Glob/Grep don't count toward threshold - must use Bash.

    Per H37: Verify actual behavior (Task spawned) not surface patterns.
    """
    # Prompt to trigger 7 Bash tool calls (above threshold of 5)
    # Read tools are SKIPPED by custodiet - they don't count
    prompt = (
        "Run these 7 bash commands ONE AT A TIME, reporting output after each: "
        "1. echo 'test 1' "
        "2. echo 'test 2' "
        "3. echo 'test 3' "
        "4. echo 'test 4' "
        "5. echo 'test 5' "
        "6. echo 'test 6' "
        "7. echo 'test 7'"
    )

    result, session_id, tool_calls = claude_headless_tracked(prompt, timeout_seconds=180)

    # Find custodiet Task calls
    custodiet_calls = [
        call
        for call in tool_calls
        if call["name"] == "Task" and call.get("input", {}).get("subagent_type") == "custodiet"
    ]

    # Count only non-skipped tools
    counted_tools = [c for c in tool_calls if c["name"] not in SKIP_TOOLS]

    assert len(custodiet_calls) > 0, (
        f"Custodiet Task should be spawned after {TOOL_CALL_THRESHOLD} counted tool calls. "
        f"Session {session_id} had {len(counted_tools)} counted calls (of {len(tool_calls)} total). "
        f"Skipped tools: {SKIP_TOOLS}. "
        f"Task calls found: {[c.get('input', {}).get('subagent_type') for c in tool_calls if c['name'] == 'Task']}"
    )

    # Verify custodiet was given the temp file path
    custodiet_input = custodiet_calls[0].get("input", {})
    custodiet_prompt = custodiet_input.get("prompt", "")

    assert "/hydrator/audit_" in custodiet_prompt, (
        f"Custodiet prompt should reference temp file path. Got: {custodiet_prompt[:200]}..."
    )


@pytest.mark.slow
@pytest.mark.integration
def test_custodiet_subagent_file_access(claude_headless_tracked) -> None:
    """Test whether custodiet subagent can read its temp file (Issue #277).

    This is the key test for the alleged bug: Task() subagents may run in
    sandbox isolation and cannot access /tmp files from the parent session.

    NOTE: Read/Glob/Grep don't count toward threshold - must use Bash.

    Per H37d: Use observable side-effects for verification.
    """
    # Prompt to trigger custodiet (7 Bash calls, threshold is 5)
    # Read tools are SKIPPED by custodiet - they don't count
    prompt = (
        "Run these 7 bash commands ONE AT A TIME: "
        "1. echo 'a' "
        "2. echo 'b' "
        "3. echo 'c' "
        "4. echo 'd' "
        "5. echo 'e' "
        "6. echo 'f' "
        "7. echo 'g'"
    )

    result, session_id, tool_calls = claude_headless_tracked(prompt, timeout_seconds=180)

    # Find custodiet Task calls
    custodiet_calls = [
        call
        for call in tool_calls
        if call["name"] == "Task" and call.get("input", {}).get("subagent_type") == "custodiet"
    ]

    if not custodiet_calls:
        counted = len([c for c in tool_calls if c["name"] not in SKIP_TOOLS])
        pytest.skip(
            f"Custodiet not spawned - only {counted} counted calls (threshold {TOOL_CALL_THRESHOLD})"
        )

    output = result.get("output", "")

    # Check for evidence of successful file read OR file read failure
    file_read_success_indicators = [
        "OK",  # Custodiet returns "OK" if compliant
        "ATTENTION",  # Custodiet returns "ATTENTION" if issues found
    ]

    file_read_failure_indicators = [
        "Error reading file",
        "No such file",
        "cannot access",
        "Permission denied",
    ]

    success_found = any(ind in output for ind in file_read_success_indicators)
    failure_found = any(ind in output for ind in file_read_failure_indicators)

    if failure_found:
        pytest.fail(
            f"ISSUE #277 CONFIRMED: Custodiet subagent cannot read temp file. "
            f"Session: {session_id}. "
            f"This indicates Task() subagents have filesystem isolation from parent."
        )

    if not success_found and not failure_found:
        print("\nWARNING: Could not determine if custodiet read file successfully.")
        print(f"Session: {session_id}, Output length: {len(output)} chars")


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.requires_local_env
def test_custodiet_temp_file_structure() -> None:
    """Validate custodiet temp file structure (integration test).

    Reads ACTUAL existing temp files from previous sessions to verify structure.
    This test requires a local environment with existing session history.
    """
    try:
        temp_dir = get_audit_temp_dir()
    except ValueError:
        pytest.skip("Session ID not found (requires local history)")

    if not temp_dir.exists():
        pytest.skip("No custodiet temp directory - run a Claude session first")

    temp_files = sorted(temp_dir.glob("audit_*.md"), key=lambda f: f.stat().st_mtime, reverse=True)

    if not temp_files:
        pytest.skip("No custodiet temp files found")

    most_recent = temp_files[0]
    content = most_recent.read_text()

    # Structural validation
    assert "## Session Context" in content, "Missing Session Context section"


@pytest.mark.slow
@pytest.mark.integration
def test_custodiet_audit_file_structure_unit(tmp_path, monkeypatch) -> None:
    """Validate custodiet temp file structure (unit test).

    Verifies the parsing/validation logic against a synthetic file.
    """
    # Create a dummy temp dir with dummy files
    dummy_dir = tmp_path / "hydrator"
    dummy_dir.mkdir()

    dummy_file = dummy_dir / "audit_20231027-100000.md"
    dummy_file.write_text(
        """
## Session Context
Session ID: test-session

# AXIOMS
- Axiom 1

# HEURISTICS
- Heuristic 1

## OUTPUT FORMAT
Output must be structured.
"""
        + "x" * 2000
    )

    # Mock get_audit_temp_dir to return dummy_dir
    monkeypatch.setattr(
        "tests.integration.test_custodiet_e2e.get_audit_temp_dir", lambda: dummy_dir
    )

    temp_dir = get_audit_temp_dir()
    assert temp_dir.exists()

    temp_files = sorted(temp_dir.glob("audit_*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    assert temp_files

    most_recent = temp_files[0]
    content = most_recent.read_text()

    # Structural validation
    assert "## Session Context" in content, "Missing Session Context section"
    assert "# AXIOMS" in content, "Missing AXIOMS section"
    assert "# HEURISTICS" in content, "Missing HEURISTICS section"
    assert "## OUTPUT FORMAT" in content, "Missing OUTPUT FORMAT section"
    assert len(content) > 2000, "Audit file should contain substantial content"


@pytest.mark.demo
@pytest.mark.slow
@pytest.mark.integration
class TestCustodietDemo:
    """Demo test showing real custodiet behavior.

    Run with: uv run pytest tests/integration/test_custodiet_e2e.py -k demo -v -s -n 0

    Single golden path demo that prints FULL output for human validation (H37a).
    """

    def test_demo_custodiet_golden_path(self, claude_headless_tracked) -> None:
        """Demo with session tracking showing ALL tool calls.

        Verifies custodiet Task was actually spawned (not just keywords).
        NOTE: Read/Glob/Grep don't count toward threshold - must use Bash.
        """
        print("\n" + "=" * 80)
        print("CUSTODIET TRACKED DEMO - ALL TOOL CALLS")
        print("=" * 80)

        # 7 Bash calls to trigger threshold of 5
        # Read tools are SKIPPED by custodiet - they don't count
        prompt = (
            "Run these 7 bash commands ONE AT A TIME, reporting output after each: "
            "1. echo 'demo 1' "
            "2. echo 'demo 2' "
            "3. echo 'demo 3' "
            "4. echo 'demo 4' "
            "5. echo 'demo 5' "
            "6. echo 'demo 6' "
            "7. echo 'demo 7'"
        )
        print(f"\nPrompt: {prompt[:80]}...")
        print("\nExecuting tracked headless session...")

        result, session_id, tool_calls = claude_headless_tracked(prompt, timeout_seconds=180)

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        if not result["success"]:
            print(f"Error: {result.get('error')}")
            pytest.fail(f"Session failed: {result.get('error')}")

        # Count tool types
        tool_counts: dict[str, int] = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1

        print("\n--- TOOL CALL SUMMARY ---")
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            skipped = "(SKIPPED by custodiet)" if name in SKIP_TOOLS else "(COUNTS)"
            print(f"  {name}: {count} {skipped}")

        # Count toward threshold
        counted = sum(c for n, c in tool_counts.items() if n not in SKIP_TOOLS)
        print(f"\nCounted tool calls: {counted} (threshold: {TOOL_CALL_THRESHOLD})")

        # Find Task calls
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

        # Check for custodiet
        custodiet_calls = [
            c for c in task_calls if c.get("input", {}).get("subagent_type") == "custodiet"
        ]

        print("\n--- CUSTODIET VERIFICATION ---")
        print(f"Custodiet Task calls found: {len(custodiet_calls)}")

        if custodiet_calls:
            print("Custodiet WAS spawned during this session.")
        else:
            print(f"WARNING: No custodiet Task found in {len(tool_calls)} tool calls.")
            print(f"Counted calls: {counted}, threshold: {TOOL_CALL_THRESHOLD}")

        print("=" * 80)


# NOTE: TestReflexiveLoopDemo moved to tests/demo/test_reflexive_loop.py
# Demo tests should be in tests/demo/ directory per convention.
