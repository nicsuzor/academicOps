#!/usr/bin/env python3
"""Integration tests for prompt hydration system.

Consolidated from 9 slow tests to 2 essential tests.
Tests the UserPromptSubmit hook -> temp file -> hydrator subagent pipeline.
"""

import re

import pytest


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.requires_local_env
def test_hydrator_does_not_answer_user_questions(
    claude_headless_tracked,
) -> None:
    """Regression: Hydrator should SITUATE requests, not EXECUTE them.

    BUG (aops-gtn7): Hydrator searched filesystem and answered directly
    instead of just providing context and workflow selection.
    """
    prompt = "What is my shell PS1 prompt configured to?"

    result, session_id, tool_calls = claude_headless_tracked(prompt, timeout_seconds=180)

    assert result["success"], f"Execution failed: {result.get('error')}"

    output = result.get("output", "")

    # Check if hydrator used Read or Grep (which it shouldn't have access to)
    bug_indicators = [".zshrc", ".bashrc", ".config/", "PS1=", "Read(file_path=", "Grep(pattern="]

    if 'subagent_type":"aops-core:hydrator"' in output or 'subagent_type":"hydrator"' in output:
        hydrator_result_pattern = r'"type":"tool_result".*?"content":"(.*?)"'
        matches = re.findall(hydrator_result_pattern, output, re.DOTALL)
        for match in matches:
            for indicator in bug_indicators:
                if "HYDRATION RESULT" in match and indicator in match:
                    pytest.fail(
                        f"Hydrator scope violation: found '{indicator}' in hydrator output.\n"
                        f"Session: {session_id}"
                    )

    hydrator_calls = [
        c
        for c in tool_calls
        if c["name"] == "Task" and "hydrator" in str(c.get("input", {}).get("subagent_type", ""))
    ]

    assert len(hydrator_calls) > 0, f"hydrator should have been spawned. Session: {session_id}"


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.requires_local_env
def test_directive_disguised_as_question_routes_to_feature_dev(
    claude_headless_tracked,
) -> None:
    """Regression (aops-kyvu): Imperatives disguised as questions must route to feature-dev.

    BUG: "allow the agent to skip hydrator step..." was misclassified as simple question.
    Fix: Added guidance to detect imperatives ("allow", "add", "fix") vs. pure questions.
    """
    prompt = (
        "allow the agent to skip hydrator step if the prompt is JUST a question, "
        "in which case the workflow has to be: ANSWER and HALT"
    )

    result, session_id, tool_calls = claude_headless_tracked(prompt, timeout_seconds=180)

    assert result["success"], f"Execution failed: {result.get('error')}"

    output = result.get("output", "")

    hydrator_calls = [
        c
        for c in tool_calls
        if c["name"] == "Task" and "hydrator" in str(c.get("input", {}).get("subagent_type", ""))
    ]

    assert len(hydrator_calls) > 0, (
        f"hydrator should have been spawned for directive prompt. Session: {session_id}"
    )

    simple_question_selected = (
        'workflow": "simple-question"' in output.lower()
        or "**workflow**: simple-question" in output.lower()
        or "workflow: simple-question" in output.lower()
    )

    assert not simple_question_selected, (
        f"Hydrator incorrectly routed to simple-question workflow. "
        f"Imperative prompts are directives, not questions. "
        f"Session: {session_id}"
    )
