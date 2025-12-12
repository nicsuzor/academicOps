#!/usr/bin/env python3
"""End-to-end test for prompt router → Haiku classifier flow.

Tests that when prompt router has no keyword match, the agent spawns a Haiku
subagent for semantic classification as instructed.

This validates the two-tier routing:
1. Keyword match → MANDATORY skill invocation (tested elsewhere)
2. No match → Agent spawns Haiku classifier (tested HERE)
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group("prompt_router_haiku"),
]


def _spawned_haiku_subagent(tool_calls: list) -> bool:
    """Check if a Haiku subagent was spawned via Task tool.

    Args:
        tool_calls: List of parsed tool calls from session

    Returns:
        True if Task tool was called with model="haiku"
    """
    for call in tool_calls:
        if call["name"] == "Task":
            input_data = call.get("input", {})
            # Check for haiku model parameter
            if input_data.get("model") == "haiku":
                return True
            # Also check prompt content for haiku reference
            prompt = input_data.get("prompt", "")
            if "haiku" in prompt.lower():
                return True
    return False


def _read_temp_file(tool_calls: list) -> bool:
    """Check if agent attempted to read the prompt router temp file.

    The prompt router writes context to ~/.cache/aops/prompt-router/
    and instructs the agent to have the Haiku subagent read it.

    Args:
        tool_calls: List of parsed tool calls from session

    Returns:
        True if Read tool was called for prompt-router temp file
    """
    for call in tool_calls:
        if call["name"] == "Read":
            file_path = call.get("input", {}).get("file_path", "")
            if "prompt-router" in file_path:
                return True
        # Also check if Task tool prompt references reading the file
        if call["name"] == "Task":
            prompt = call.get("input", {}).get("prompt", "")
            if "prompt-router" in prompt and "Read" in prompt:
                return True
    return False


@pytest.mark.integration
@pytest.mark.slow
def test_no_keyword_match_triggers_classifier_instruction(
    claude_headless_tracked,
) -> None:
    """Test that prompts without keyword matches get classifier instruction.

    When prompt_router.py has no keyword match, it returns additionalContext
    with instructions to spawn a Haiku subagent. This test verifies the agent
    RECEIVES that instruction (hook output) and ACTS on it (spawns subagent).

    The prompt "please analyze this" has no keyword matches, so should trigger
    the classifier flow.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "please analyze this interesting situation",  # No skill keywords
        timeout_seconds=180,  # Allow time for subagent spawn
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    # Verify agent spawned Haiku subagent for classification
    # OR read the temp file to understand context
    spawned_haiku = _spawned_haiku_subagent(tool_calls)
    read_context = _read_temp_file(tool_calls)

    # Either behavior indicates the agent understood the classifier instruction
    instruction_followed = spawned_haiku or read_context

    if not instruction_followed:
        tool_names = [c["name"] for c in tool_calls]
        pytest.fail(
            f"Agent did NOT follow classifier instruction.\n"
            f"Expected: Task(model='haiku') spawn OR Read(prompt-router file)\n"
            f"Actual tool calls: {tool_names}\n"
            f"This suggests the prompt router → Haiku flow is broken."
        )


@pytest.mark.integration
@pytest.mark.slow
def test_ambiguous_prompt_uses_semantic_classification(
    claude_headless_tracked,
) -> None:
    """Test that ambiguous prompts trigger semantic classification.

    "help me with this" is ambiguous - could be framework, tasks, bmem, etc.
    The prompt router should provide classifier instruction, and the agent
    should use it to determine intent.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "help me with this complicated thing",  # Deliberately vague
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # For ambiguous prompts, we expect EITHER:
    # 1. Haiku classifier spawn (agent follows instruction)
    # 2. AskUserQuestion (agent asks for clarification - also valid!)
    # 3. Direct skill invocation (agent made a reasonable guess)

    spawned_haiku = _spawned_haiku_subagent(tool_calls)
    asked_user = any(c["name"] == "AskUserQuestion" for c in tool_calls)
    invoked_skill = any(c["name"] == "Skill" for c in tool_calls)

    handled_ambiguity = spawned_haiku or asked_user or invoked_skill

    if not handled_ambiguity:
        tool_names = [c["name"] for c in tool_calls]
        pytest.fail(
            f"Agent did not handle ambiguous prompt appropriately.\n"
            f"Expected one of: Task(haiku), AskUserQuestion, Skill\n"
            f"Actual tool calls: {tool_names}"
        )
