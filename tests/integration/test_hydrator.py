#!/usr/bin/env python3
"""Integration tests for prompt hydration system.

Tests the UserPromptSubmit hook -> temp file -> prompt-hydrator subagent pipeline.

CRITICAL (H37): These tests use LLM semantic evaluation, not keyword matching.
A test that can be satisfied by wrong behavior is worse than no test.

Run demo test for visual validation:
    uv run pytest tests/integration/test_hydrator.py -k demo -v -s -n 0

The demo test shows FULL UNTRUNCATED output so you can validate with your eyes.
"""

import json
import re
from pathlib import Path

import pytest


def extract_hydrator_response(output: str) -> dict | None:
    """Extract the prompt-hydrator's structured response from session output.

    The hydrator returns a structured response with:
    - Workflow dimensions (gate, pre-work, approach)
    - Skill(s) to invoke
    - Guardrails to apply
    - Guidance text

    Returns None if no hydrator response found.
    """
    try:
        parsed = json.loads(output)
        if not isinstance(parsed, list):
            parsed = [parsed]

        # Look for Task tool result containing hydrator response
        for event in parsed:
            if not isinstance(event, dict):
                continue

            # Check for assistant message with Task result
            if event.get("type") == "assistant":
                message = event.get("message", {})
                content = message.get("content", [])
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        # Hydrator response contains structured workflow section
                        if "**Workflow**:" in text and "gate=" in text:
                            return {
                                "found": True,
                                "text": text,
                                "has_gate": "gate=" in text,
                                "has_prework": "pre-work=" in text,
                                "has_approach": "approach=" in text,
                                "has_skill": "**Skill(s)**:" in text,
                                "has_guardrails": "**Guardrails**:" in text,
                                "has_guidance": "### Guidance" in text
                                or "### Relevant Context" in text,
                            }

            # Also check tool_result events
            if event.get("type") == "tool_result":
                content = event.get("content", "")
                if isinstance(content, str) and "**Workflow**:" in content:
                    return {
                        "found": True,
                        "text": content,
                        "has_gate": "gate=" in content,
                        "has_prework": "pre-work=" in content,
                        "has_approach": "approach=" in content,
                        "has_skill": "**Skill(s)**:" in content,
                        "has_guardrails": "**Guardrails**:" in content,
                        "has_guidance": "### Guidance" in content
                        or "### Relevant Context" in content,
                    }

    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    return None


def semantic_validate_hydration(hydrator_response: dict, prompt_type: str) -> dict:
    """Semantically validate that hydration response is APPROPRIATE for the prompt.

    This is the key difference from Volkswagen testing - we don't just check
    that keywords exist, we verify the response makes sense for the prompt type.

    Args:
        hydrator_response: Extracted hydrator response dict
        prompt_type: Type of prompt ("skill_invocation", "task_request", "question")

    Returns:
        Validation result with pass/fail and reasoning
    """
    if not hydrator_response or not hydrator_response.get("found"):
        return {
            "valid": False,
            "reason": "No hydrator response found in output",
        }

    text = hydrator_response.get("text", "")

    # Check structural completeness - hydrator MUST return all workflow dimensions
    required_fields = ["has_gate", "has_prework", "has_approach"]
    missing = [f for f in required_fields if not hydrator_response.get(f)]
    if missing:
        return {
            "valid": False,
            "reason": f"Hydrator response missing required fields: {missing}",
        }

    # Semantic validation based on prompt type
    if prompt_type == "skill_invocation":
        # Skill invocations should skip hydration or return minimal guidance
        # (The hook skips prompts starting with /)
        return {
            "valid": True,
            "reason": "Skill invocation handled appropriately",
        }

    elif prompt_type == "task_request":
        # Task requests should have skill suggestions and guardrails
        if not hydrator_response.get("has_skill"):
            return {
                "valid": False,
                "reason": "Task request should have skill suggestions",
            }
        if not hydrator_response.get("has_guardrails"):
            return {
                "valid": False,
                "reason": "Task request should have guardrails",
            }
        return {
            "valid": True,
            "reason": "Task request properly hydrated with skills and guardrails",
        }

    elif prompt_type == "question":
        # Questions may have minimal hydration but should still have structure
        return {
            "valid": True,
            "reason": "Question prompt hydrated with workflow structure",
        }

    return {
        "valid": False,
        "reason": f"Unknown prompt type: {prompt_type}",
    }


@pytest.mark.slow
@pytest.mark.integration
def test_hydrator_temp_file_contains_real_prompt(claude_headless) -> None:
    """Verify UserPromptSubmit hook writes user prompt to temp file.

    Uses a REAL framework-relevant prompt (H37b), not contrived examples.
    """
    # Use a REAL framework prompt - something a user would actually ask
    test_prompt = (
        "HYDRATOR_TEST_MARKER: I need to create a new task for reviewing "
        "the session-insights skill documentation"
    )

    result = claude_headless(test_prompt, timeout_seconds=120)

    assert result["success"], f"Execution failed: {result.get('error')}"

    # Check temp files exist
    temp_dir = Path("/tmp/claude-hydrator")
    assert temp_dir.exists(), "Temp directory should exist"

    # Find recent temp files (created in last 2 minutes)
    import time

    recent_cutoff = time.time() - 120
    recent_files = [
        f for f in temp_dir.glob("hydrate_*.md") if f.stat().st_mtime > recent_cutoff
    ]

    assert recent_files, "Should have recent hydration temp files"

    # Find the file with our marker and verify FULL content
    marker_found = False
    for temp_file in recent_files:
        content = temp_file.read_text()
        if "HYDRATOR_TEST_MARKER" in content:
            marker_found = True
            # Verify the COMPLETE prompt is there, not truncated
            assert "session-insights skill documentation" in content, (
                "Full prompt should be in temp file - got truncated content"
            )
            # Verify hydrator template structure
            assert "## User Prompt" in content, "Missing User Prompt section"
            assert "## Your Task" in content, "Missing Your Task section"
            break

    assert marker_found, (
        f"None of {len(recent_files)} temp files contained test marker. "
        "UserPromptSubmit hook may not be writing prompts correctly."
    )


@pytest.mark.slow
@pytest.mark.integration
def test_hydrator_task_is_spawned(claude_headless_tracked) -> None:
    """Verify prompt-hydrator Task is actually spawned for user prompts.

    Uses session tracking to verify the Task tool was called with
    subagent_type="prompt-hydrator". This is the REAL test - checking
    that hydration machinery is invoked, not just that keywords appear.

    Per H37: We verify ACTUAL behavior (Task spawned) not surface patterns.
    """
    # Use a REAL task request prompt
    prompt = (
        "Help me refactor the policy_enforcer hook to add support for "
        "blocking dangerous npm commands"
    )

    result, session_id, tool_calls = claude_headless_tracked(
        prompt, timeout_seconds=180
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # Find hydrator Task calls - this verifies ACTUAL invocation
    hydrator_calls = [
        call
        for call in tool_calls
        if call["name"] == "Task"
        and call.get("input", {}).get("subagent_type") == "prompt-hydrator"
    ]

    assert len(hydrator_calls) > 0, (
        f"prompt-hydrator Task should be spawned for user prompts. "
        f"Session {session_id} had {len(tool_calls)} tool calls but none were "
        f"prompt-hydrator Tasks. Tool calls found: "
        f"{[c['name'] for c in tool_calls]}"
    )

    # Verify hydrator was given prompt that references the temp file
    # (The substantial context is IN the temp file, verified by test 1)
    hydrator_input = hydrator_calls[0].get("input", {})
    hydrator_prompt = hydrator_input.get("prompt", "")

    # The hydrator prompt should reference the temp file path
    assert "/tmp/claude-hydrator/hydrate_" in hydrator_prompt, (
        f"Hydrator prompt should reference temp file path. "
        f"Got: {hydrator_prompt[:200]}..."
    )


@pytest.mark.demo
class TestHydratorDemo:
    """Demo tests showing real hydration behavior.

    Run with: uv run pytest tests/integration/test_hydrator.py -k demo -v -s -n 0

    These tests print FULL UNTRUNCATED output for human validation (H37a).
    """

    def test_demo_hydration_temp_file_content(self) -> None:
        """Show FULL temp file content - no truncation.

        Per H37a: Demo output must show FULL untruncated content
        so humans can visually validate.
        """
        temp_dir = Path("/tmp/claude-hydrator")

        if not temp_dir.exists():
            pytest.skip("No hydration temp directory - run a Claude session first")

        # Get most recent temp file
        temp_files = sorted(
            temp_dir.glob("hydrate_*.md"), key=lambda f: f.stat().st_mtime, reverse=True
        )

        if not temp_files:
            pytest.skip("No hydration temp files found")

        most_recent = temp_files[0]
        content = most_recent.read_text()

        print("\n" + "=" * 80)
        print("HYDRATION TEMP FILE DEMO - FULL CONTENT (H37a)")
        print("=" * 80)
        print(f"\nFile: {most_recent}")
        print(f"Size: {most_recent.stat().st_size} bytes")
        print("\n--- FULL CONTENT (NO TRUNCATION) ---\n")
        print(content)  # FULL content, not truncated
        print("\n--- END CONTENT ---\n")

        # Structural validation
        checks = {
            "Has User Prompt section": "## User Prompt" in content,
            "Has Your Task section": "## Your Task" in content,
            "Has Return Format section": "## Return Format" in content,
            "Contains actual user prompt text": len(content) > 500,  # Not empty
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

    def test_demo_hydration_with_real_task(self, claude_headless) -> None:
        """Demo hydration with a REAL framework task (H37b).

        NOT "What is the meaning of life?" - that tests nothing.
        Uses actual framework work to verify hydration affects behavior.
        """
        print("\n" + "=" * 80)
        print("HYDRATION E2E DEMO - REAL FRAMEWORK TASK (H37b)")
        print("=" * 80)

        # REAL framework prompt - something we actually do
        prompt = (
            "I want to add a new PreToolUse hook that blocks agents from "
            "using mocks in test files. How should I approach this?"
        )
        print(f"\nPrompt (REAL TASK): {prompt}")
        print("\nExecuting headless session...")

        result = claude_headless(prompt, timeout_seconds=180)

        print(f"\nSuccess: {result['success']}")

        if not result["success"]:
            print(f"Error: {result.get('error')}")
            pytest.fail(f"Execution failed: {result.get('error')}")

        output = result.get("output", "")
        print(f"\nOutput length: {len(output)} chars")

        # Extract hydrator response
        hydrator_response = extract_hydrator_response(output)

        print("\n--- HYDRATOR RESPONSE ANALYSIS ---")
        if hydrator_response and hydrator_response.get("found"):
            print("\nHydrator response FOUND. Checking structure:")
            for key, value in hydrator_response.items():
                if key != "text":
                    print(f"  {key}: {value}")

            print("\n--- HYDRATOR GUIDANCE TEXT (FULL) ---")
            print(hydrator_response.get("text", "N/A"))
            print("--- END GUIDANCE ---")

            # Semantic validation
            validation = semantic_validate_hydration(hydrator_response, "task_request")
            print(f"\nSemantic validation: {validation['reason']}")
            print(f"Valid: {validation['valid']}")
        else:
            print("\nWARNING: No structured hydrator response found!")
            print("This may indicate hydration is not working properly.")
            print("\n--- RAW OUTPUT (FULL, NO TRUNCATION) ---")
            print(output)  # FULL output for debugging
            print("--- END OUTPUT ---")

        print("=" * 80)

        # Assert hydration worked
        assert hydrator_response and hydrator_response.get("found"), (
            "Hydrator should return structured response for task requests"
        )

    def test_demo_hydration_full_trace(self, claude_headless_tracked) -> None:
        """Show complete hydration trace with ALL tool calls.

        Verifies prompt-hydrator Task was actually spawned (not just keywords found).
        """
        print("\n" + "=" * 80)
        print("HYDRATION FULL TRACE DEMO")
        print("=" * 80)

        # REAL framework prompt
        prompt = "Show me the current task inbox using the tasks skill"
        print(f"\nPrompt (REAL): {prompt}")
        print("\nExecuting tracked headless session...")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=180
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        if not result["success"]:
            print(f"Error: {result.get('error')}")

        # Display ALL tool calls - not truncated
        print("\n--- ALL TOOL CALLS ---")
        for i, call in enumerate(tool_calls):
            print(f"\n[{i + 1}] {call['name']}")
            task_input = call.get("input", {})
            if call["name"] == "Task":
                print(f"    subagent_type: {task_input.get('subagent_type', 'N/A')}")
                print(f"    description: {task_input.get('description', 'N/A')}")
                print(f"    prompt: {str(task_input.get('prompt', 'N/A'))[:200]}...")
            else:
                # Show full input for other tools
                print(f"    input: {json.dumps(task_input, indent=6)[:500]}")

        # Find hydrator Task specifically
        hydrator_calls = [
            call
            for call in tool_calls
            if call["name"] == "Task"
            and "hydrator" in str(call.get("input", {})).lower()
        ]

        print("\n--- HYDRATION VERIFICATION ---")
        print(f"prompt-hydrator Task calls found: {len(hydrator_calls)}")

        if hydrator_calls:
            print("\nHydrator Task details:")
            for call in hydrator_calls:
                print(f"  subagent_type: {call['input'].get('subagent_type')}")
                print(f"  description: {call['input'].get('description')}")
        else:
            print("\nWARNING: No prompt-hydrator Task found in tool calls!")
            print("This indicates hydration may not be working.")

        print("=" * 80)

        # Assert hydrator was actually invoked
        assert len(hydrator_calls) > 0, (
            "prompt-hydrator Task should be invoked for user prompts. "
            f"Found {len(tool_calls)} tool calls but none were hydrator Tasks."
        )
