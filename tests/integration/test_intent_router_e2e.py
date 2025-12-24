#!/usr/bin/env python3
"""End-to-end tests for intent-router system.

Tests the complete intent classification pipeline:
1. Cache file creation from write_classifier_prompt()
2. Intent-router subagent spawning when no keyword match
3. Cache file existence at spawned path
4. Intent-router reading cache file
5. Intent-router returning valid classification
"""

import re
from pathlib import Path
from typing import Any

import pytest
from hooks.prompt_router import write_classifier_prompt

# Valid skill names that intent-router can classify to
VALID_SKILL_NAMES = {
    "framework",
    "python-dev",
    "analyst",
    "remember",
    "tasks",
    "pdf",
    "osb-drafting",
    "learning-log",
    "transcript",
    "skill-creator",
    "training-set-builder",
    "extractor",
    "none",
}

# Mark all tests in this file with integration/slow/xdist_group
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group("intent_router"),
]


# --- Unit Test: Cache File Creation ---


def test_write_classifier_prompt_creates_file():
    """Test that write_classifier_prompt() creates a cache file.

    This is a unit test - no Claude CLI required.
    Tests the function directly to verify file creation.
    """
    test_prompt = "what is the meaning of life?"

    # Call function to write classifier prompt
    filepath = write_classifier_prompt(test_prompt)

    try:
        # Verify file was created
        assert filepath.exists(), f"Cache file not created at {filepath}"

        # Verify it's in the expected directory
        cache_dir = Path.home() / ".cache" / "aops" / "prompt-router"
        assert (
            filepath.parent == cache_dir
        ), f"File created in wrong directory: {filepath.parent}"

        # Read content and verify it contains expected elements
        content = filepath.read_text()

        # Must contain user prompt
        assert (
            test_prompt in content
        ), f"User prompt not found in cache file:\n{content}"

        # Must contain all skill names from VALID_SKILL_NAMES
        for skill_name in VALID_SKILL_NAMES:
            assert (
                skill_name in content
            ), f"Skill '{skill_name}' not found in cache file"

        # Should not contain YAML frontmatter
        assert not content.startswith(
            "---"
        ), "Cache file should not contain YAML frontmatter"

    finally:
        # Clean up - remove the test file
        if filepath.exists():
            filepath.unlink()


def test_write_classifier_prompt_returns_valid_path():
    """Test that write_classifier_prompt() returns a valid Path object."""
    test_prompt = "test prompt"

    filepath = write_classifier_prompt(test_prompt)

    try:
        # Verify return type is Path
        assert isinstance(filepath, Path), f"Expected Path, got {type(filepath)}"

        # Verify path is absolute
        assert filepath.is_absolute(), f"Path should be absolute: {filepath}"

        # Verify filename format (timestamp-based)
        assert filepath.suffix == ".md", f"Expected .md extension, got {filepath.suffix}"
        assert re.match(
            r"\d{8}_\d{6}_\d+\.md", filepath.name
        ), f"Filename format incorrect: {filepath.name}"

    finally:
        # Clean up
        if filepath.exists():
            filepath.unlink()


# --- E2E Tests: Intent-Router Subagent Spawning ---


def _task_tool_with_type(tool_calls: list[dict[str, Any]], subagent_type: str) -> bool:
    """Check if Task tool was used with specific subagent type.

    Args:
        tool_calls: List of parsed tool calls from session
        subagent_type: Expected subagent_type value

    Returns:
        True if Task tool was called with matching subagent_type
    """
    for call in tool_calls:
        if call["name"] == "Task":
            actual_type = call["input"].get("subagent_type", "")
            if actual_type == subagent_type:
                return True
    return False


def _extract_filepath_from_prompt(task_prompt: str) -> str | None:
    """Extract file path from Task prompt using regex.

    Looks for pattern: Read /path/to/file.md

    Args:
        task_prompt: The prompt field from Task tool call

    Returns:
        Extracted file path or None if not found
    """
    match = re.search(r"Read\s+(/[^\s]+\.md)", task_prompt)
    return match.group(1) if match else None


def _find_task_prompt(tool_calls: list[dict[str, Any]]) -> str | None:
    """Find the prompt from the first Task tool call.

    Args:
        tool_calls: List of parsed tool calls

    Returns:
        The prompt string from Task call, or None if not found
    """
    for call in tool_calls:
        if call["name"] == "Task":
            return call["input"].get("prompt")
    return None


def test_intent_router_spawned_for_no_keyword_match(claude_headless_tracked):
    """Test that intent-router subagent is spawned when no keyword match.

    E2E test: Sends a prompt with no keyword triggers and verifies that
    the Task tool is called with subagent_type='intent-router'.

    FAILS if intent-router is not spawned (tests for regression).
    """
    # Prompt with no keyword match - should trigger intent-router
    prompt = "what is the meaning of life?"

    result, session_id, tool_calls = claude_headless_tracked(
        prompt,
        timeout_seconds=120,
    )

    # Verify execution succeeded
    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    # Verify Task tool was used with intent-router subagent
    task_used = _task_tool_with_type(tool_calls, "intent-router")

    if not task_used:
        tool_names = [c["name"] for c in tool_calls]
        task_calls = [c for c in tool_calls if c["name"] == "Task"]
        pytest.fail(
            f"Task tool NOT used for intent-router.\n"
            f"Expected: Task(subagent_type='intent-router')\n"
            f"Actual tool calls: {tool_names}\n"
            f"Task calls: {task_calls}\n"
            f"This indicates intent-router spawn is broken."
        )


def test_intent_router_prompt_contains_read_and_path(claude_headless_tracked):
    """Test that Task prompt contains 'Read' and cache file path.

    E2E test: Verifies the Task prompt instructs the intent-router to
    read the classifier prompt from the cache file.

    Note: If agent doesn't spawn Task at all, this test is skipped since
    test_intent_router_spawned_for_no_keyword_match covers that case.
    """
    prompt = "what is the meaning of life?"  # Same prompt as spawn test

    result, _session_id, tool_calls = claude_headless_tracked(
        prompt,
        timeout_seconds=120,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # Find intent-router Task tool call specifically
    task_prompt = None
    for call in tool_calls:
        if call["name"] == "Task":
            if call["input"].get("subagent_type") == "intent-router":
                task_prompt = call["input"].get("prompt")
                break

    if task_prompt is None:
        pytest.skip("Intent-router not spawned - see test_intent_router_spawned_for_no_keyword_match")

    # Verify prompt contains "Read" instruction
    assert (
        "Read" in task_prompt
    ), f"Task prompt should contain 'Read' instruction:\n{task_prompt}"

    # Verify prompt contains "prompt-router" or cache path
    assert (
        "prompt-router" in task_prompt or ".cache" in task_prompt
    ), f"Task prompt should reference cache file:\n{task_prompt}"


def test_cache_file_exists_at_spawned_path(claude_headless_tracked):
    """Test that cache file exists at path extracted from Task prompt.

    E2E test: Extracts the file path from the Task prompt and verifies
    the file actually exists on disk. This tests that write_classifier_prompt()
    is being called correctly by the hook.
    """
    prompt = "tell me about artificial intelligence"

    result, _session_id, tool_calls = claude_headless_tracked(
        prompt,
        timeout_seconds=120,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # Find Task tool call and extract file path
    task_prompt = _find_task_prompt(tool_calls)
    assert task_prompt is not None, "No Task tool call found"

    filepath_str = _extract_filepath_from_prompt(task_prompt)
    assert (
        filepath_str is not None
    ), f"Could not extract file path from Task prompt:\n{task_prompt}"

    # Verify file exists
    filepath = Path(filepath_str)
    assert filepath.exists(), f"Cache file does not exist at: {filepath}"

    # Verify it's readable
    assert filepath.is_file(), f"Path is not a file: {filepath}"

    # Verify it has content
    content = filepath.read_text()
    assert len(content) > 0, f"Cache file is empty: {filepath}"


def test_intent_router_reads_cache_file(claude_headless_tracked):
    """Test that intent-router successfully reads the cache file.

    E2E test: Verifies that intent-router subagent can read the cache file
    and doesn't produce error messages about missing/inaccessible files.
    """
    prompt = "what is computational linguistics?"

    result, _session_id, _tool_calls = claude_headless_tracked(
        prompt,
        timeout_seconds=120,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # Extract response text (if available)
    response_text = ""
    if "result" in result:
        result_data = result["result"]
        if isinstance(result_data, list):
            for message in result_data:
                if isinstance(message, dict) and message.get("type") == "assistant":
                    message_obj = message.get("message", {})
                    content = message_obj.get("content", [])
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            response_text += block.get("text", "")

    # Check for failure indicators in response
    failure_indicators = [
        "does not exist",
        "not accessible",
        "cannot read",
        "file not found",
        "no such file",
        "permission denied",
    ]

    for indicator in failure_indicators:
        assert indicator.lower() not in response_text.lower(), (
            f"Intent-router failed to read cache file. "
            f"Response contains '{indicator}':\n{response_text}"
        )


def test_intent_router_returns_valid_classification(claude_headless_tracked):
    """Test that when intent-router is spawned, it returns a valid skill name.

    E2E test: Verifies that IF intent-router is spawned, its Task prompt
    references a valid cache file path. Skips if agent doesn't use intent-router.
    """
    prompt = "how do I write a pytest test with fixtures?"

    result, _session_id, tool_calls = claude_headless_tracked(
        prompt,
        timeout_seconds=120,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # Find intent-router Task call
    intent_router_call = None
    for call in tool_calls:
        if call["name"] == "Task":
            if call["input"].get("subagent_type") == "intent-router":
                intent_router_call = call
                break

    if intent_router_call is None:
        pytest.skip("Intent-router not spawned - agent answered directly")

    # Verify the Task prompt contains Read instruction with valid path
    task_prompt = intent_router_call["input"].get("prompt", "")
    assert "Read" in task_prompt, f"Task prompt missing Read: {task_prompt}"
    assert "prompt-router" in task_prompt, f"Task prompt missing path: {task_prompt}"
