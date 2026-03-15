#!/usr/bin/env python3
"""End-to-end tests for custodiet compliance checking.

Consolidated from 6 slow tests to 2 essential tests.
Tests verify ACTUAL behavior (Task spawned, files created) not surface patterns.
"""

from pathlib import Path

import pytest
from lib import hook_utils

TOOL_CALL_THRESHOLD = 5
SKIP_TOOLS = {"Read", "Glob", "Grep", "mcp__memory__retrieve_memory"}


def get_audit_temp_dir() -> Path:
    """Get the audit temp directory using shared logic."""
    return hook_utils.get_hook_temp_dir("hydrator")


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.requires_local_env
def test_custodiet_temp_file_created_on_threshold(claude_headless) -> None:
    """Verify custodiet hook creates temp file when threshold reached.

    Triggers 7 Bash tool calls (above threshold of 5) to fire custodiet.
    """
    temp_dir = get_audit_temp_dir()
    files_before = set(temp_dir.glob("audit_*.md")) if temp_dir.exists() else set()

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

    files_after = set(temp_dir.glob("audit_*.md")) if temp_dir.exists() else set()
    new_files = files_after - files_before

    assert len(new_files) > 0, (
        f"Custodiet should create audit file when threshold ({TOOL_CALL_THRESHOLD}) reached. "
        f"Files before: {len(files_before)}, after: {len(files_after)}. "
        f"Session success: {result.get('success')}"
    )

    newest_file = max(new_files, key=lambda f: f.stat().st_mtime)
    content = newest_file.read_text()
    assert len(content) > 1000, (
        f"Audit file should contain substantial context. Got {len(content)} chars"
    )


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.requires_local_env
def test_custodiet_task_spawned(claude_headless_tracked) -> None:
    """Verify custodiet Task is actually spawned when threshold reached."""
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

    custodiet_calls = [
        call
        for call in tool_calls
        if call["name"] == "Task" and call.get("input", {}).get("subagent_type") == "custodiet"
    ]

    counted_tools = [c for c in tool_calls if c["name"] not in SKIP_TOOLS]

    assert len(custodiet_calls) > 0, (
        f"Custodiet Task should be spawned after {TOOL_CALL_THRESHOLD} counted tool calls. "
        f"Session {session_id} had {len(counted_tools)} counted calls (of {len(tool_calls)} total). "
        f"Task calls found: {[c.get('input', {}).get('subagent_type') for c in tool_calls if c['name'] == 'Task']}"
    )

    custodiet_prompt = custodiet_calls[0].get("input", {}).get("prompt", "")
    assert "/hydrator/audit_" in custodiet_prompt, (
        f"Custodiet prompt should reference temp file path. Got: {custodiet_prompt[:200]}..."
    )
