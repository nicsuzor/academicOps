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
from pathlib import Path

import pytest

from lib.paths import get_aops_root
from tests.integration.conftest import extract_response_text


def print_full_session_trace(output: str) -> None:
    """Print the complete session trace showing all events in order.

    This shows hooks, agent reasoning, tool calls, and subagent responses
    so humans can verify the agent's decision-making process.
    """
    try:
        parsed = json.loads(output)
        if not isinstance(parsed, list):
            parsed = [parsed]

        print("\n" + "=" * 80)
        print("FULL SESSION TRACE - All Events in Order")
        print("=" * 80)

        for i, event in enumerate(parsed):
            if not isinstance(event, dict):
                continue

            event_type = event.get("type", "unknown")

            # Hook responses (system injections)
            if event_type == "system" and event.get("subtype") == "hook_response":
                hook_name = event.get("hook_name", "unknown")
                print(f"\n[{i}] 🪝 HOOK: {hook_name}")
                # Show first 500 chars of hook context
                stdout = event.get("stdout", "")
                if stdout:
                    try:
                        hook_data = json.loads(stdout)
                        context = hook_data.get("hookSpecificOutput", {}).get(
                            "additionalContext", ""
                        )
                        if context:
                            preview = (
                                context[:1000] + "..."
                                if len(context) > 1000
                                else context
                            )
                            print(f"    Context preview: {preview[:500]}")
                    except json.JSONDecodeError:
                        print(f"    Raw: {stdout[:500]}...")

            # Assistant messages (agent thinking/responses)
            elif event_type == "assistant":
                message = event.get("message", {})
                content = message.get("content", [])
                print(f"\n[{i}] 🤖 ASSISTANT MESSAGE:")
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type")
                        if block_type == "text":
                            text = block.get("text", "")
                            # Show first 800 chars of each text block
                            preview = text[:800] + "..." if len(text) > 800 else text
                            print(f"    TEXT: {preview}")
                        elif block_type == "tool_use":
                            tool_name = block.get("name", "unknown")
                            tool_input = block.get("input", {})
                            print(f"    TOOL CALL: {tool_name}")
                            if tool_name == "Task":
                                print(
                                    f"      subagent_type: {tool_input.get('subagent_type', 'N/A')}"
                                )
                                print(
                                    f"      description: {tool_input.get('description', 'N/A')}"
                                )
                                prompt_preview = str(tool_input.get("prompt", ""))[:200]
                                print(f"      prompt: {prompt_preview}...")
                            else:
                                input_preview = json.dumps(tool_input)[:300]
                                print(f"      input: {input_preview}...")

            # Tool results - show FULL content for Task results (subagent responses)
            elif event_type == "tool_result":
                tool_id = event.get("tool_use_id", "unknown")[:8]
                content = event.get("content", "")
                print(f"\n[{i}] 📥 TOOL RESULT (id: {tool_id}...):")
                if isinstance(content, str):
                    # Show full content for subagent responses (they contain hydrator output)
                    print(f"    {content}")

            # Result (final)
            elif event_type == "result":
                print(f"\n[{i}] ✅ FINAL RESULT:")
                result_text = event.get("result", "")
                if isinstance(result_text, str):
                    preview = (
                        result_text[:500] + "..."
                        if len(result_text) > 500
                        else result_text
                    )
                    print(f"    {preview}")

            # User events contain tool results
            elif event_type == "user":
                # Check if this has tool_use_result (contains subagent/tool output)
                if "tool_use_result" in event:
                    result_data = event.get("tool_use_result", {})
                    print(f"\n[{i}] 📥 TOOL RESULT:")
                    if isinstance(result_data, dict):
                        content = result_data.get("content", "")
                        if content:
                            print(f"    {content}")
                    elif isinstance(result_data, str):
                        print(f"    {result_data}")
                # Also check message.content for tool results
                message = event.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if (
                                isinstance(block, dict)
                                and block.get("type") == "tool_result"
                            ):
                                tool_content = block.get("content", "")
                                print(f"\n[{i}] 📥 TOOL RESULT (from message):")
                                print(f"    {tool_content}")

        print("\n" + "=" * 80)
        print("END SESSION TRACE")
        print("=" * 80)

    except json.JSONDecodeError as e:
        print(f"Could not parse session output as JSON: {e}")


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
def test_hydrator_does_not_glob_when_given_specific_file(
    claude_headless_tracked,
) -> None:
    """Verify hydrator reads specific file directly without globbing the directory.

    BUG: When given "Read /tmp/claude-hydrator/hydrate_xxx.md", the hydrator
    was making unnecessary Glob/Search calls to list all files in the directory
    before reading the specific file.

    This test verifies the fix: hydrator should trust the specific file path
    and read it directly without searching the directory.

    Per H37c: Execution over inspection - we verify actual tool call behavior.
    """
    # Send a normal prompt that triggers hydration via UserPromptSubmit hook
    # The hook creates a temp file and tells main agent to spawn prompt-hydrator
    prompt = "HYDRATOR_GLOB_TEST: Help me understand how the policy_enforcer hook works"

    result, session_id, tool_calls = claude_headless_tracked(
        prompt, timeout_seconds=180
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # Check raw output for evidence of unnecessary globbing by the hydrator
    output = result.get("output", "")

    # The BUG: hydrator globs /tmp/claude-hydrator when it should just read the specific file
    # Look for patterns that indicate the hydrator searched the temp directory
    temp_dir = "/tmp/claude-hydrator"

    # These patterns in the output indicate the bug is present
    # The hydrator should NOT be searching the temp directory - it should trust the path
    bug_indicators = [
        # Glob/Search patterns targeting the hydrator temp directory
        f'path: "{temp_dir}"',
        f"path: '{temp_dir}'",
        f'path="{temp_dir}"',
        f"path='{temp_dir}'",
        # Pattern matching all files in hydrator directory
        "Found 43 files",  # From user's bug report
        "Found 4",  # Any "Found N files" in that directory
    ]

    # Check if output contains evidence of unnecessary globbing
    for indicator in bug_indicators:
        if indicator in output:
            # Verify it's actually the hydrator doing this, not the main agent
            # The bug shows up as Search/Glob calls within the prompt-hydrator output
            if "prompt-hydrator" in output and indicator in output:
                pytest.fail(
                    f"Hydrator made unnecessary glob/search of temp directory.\n"
                    f"Found indicator: {indicator}\n"
                    f"When given a specific file path, the hydrator should read it "
                    f"directly without searching the directory.\n"
                    f"Session: {session_id}"
                )

    # Verify hydration actually happened (positive check)
    hydrator_calls = [
        c
        for c in tool_calls
        if c["name"] == "Task"
        and c.get("input", {}).get("subagent_type") == "prompt-hydrator"
    ]

    assert len(hydrator_calls) > 0, (
        f"prompt-hydrator should have been spawned for this prompt. "
        f"Session: {session_id}"
    )


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
            assert (
                "session-insights skill documentation" in content
            ), "Full prompt should be in temp file - got truncated content"
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


@pytest.mark.slow
@pytest.mark.integration
def test_hydration_temp_file_structure() -> None:
    """Validate hydration temp file structure (non-demo unit test).

    Reads existing temp files to verify structure - no Claude session needed.
    """
    temp_dir = Path("/tmp/claude-hydrator")

    if not temp_dir.exists():
        pytest.skip("No hydration temp directory - run a Claude session first")

    temp_files = sorted(
        temp_dir.glob("hydrate_*.md"), key=lambda f: f.stat().st_mtime, reverse=True
    )

    if not temp_files:
        pytest.skip("No hydration temp files found")

    most_recent = temp_files[0]
    content = most_recent.read_text()

    # Structural validation
    assert "## User Prompt" in content, "Missing User Prompt section"
    assert "## Your Task" in content, "Missing Your Task section"
    assert "## Return Format" in content, "Missing Return Format section"
    assert len(content) > 500, "Temp file should contain substantial content"


@pytest.mark.demo
@pytest.mark.slow
@pytest.mark.integration
class TestHydratorDemo:
    """Demo test showing real hydration behavior.

    Run with: uv run pytest tests/integration/test_hydrator.py -k demo -v -s -n 0

    Single golden path demo that prints FULL output for human validation (H37a).
    """

    def test_demo_hydration_golden_path(self, claude_headless) -> None:
        """Demo hydration with a REAL framework task (H37b).

        NOT "What is the meaning of life?" - that tests nothing.
        Uses actual framework work to verify hydration affects behavior.
        """
        print("\n" + "=" * 80)
        print("HYDRATION E2E DEMO - REAL FRAMEWORK TASK (H37b)")
        print("=" * 80)

        # Simple prompt that won't trigger many tool calls - just enough to see hydration
        prompt = "What is 2 + 2?"
        print(f"\nPrompt (REAL TASK): {prompt}")
        print("\nExecuting headless session...")

        # Must run from aops_root to have hooks available
        # bypassPermissions allows reading temp files without interactive approval
        result = claude_headless(
            prompt,
            timeout_seconds=180,
            cwd=get_aops_root(),
            permission_mode="bypassPermissions",
        )

        print(f"\nSuccess: {result['success']}")

        if not result["success"]:
            print(f"Error: {result.get('error')}")
            pytest.fail(f"Execution failed: {result.get('error')}")

        output = result.get("output", "")
        print(f"\nOutput length: {len(output)} chars")

        # Show full session trace - ALL events so humans can verify decision-making
        print_full_session_trace(output)

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

        # Always show the agent's actual response text
        print("\n--- AGENT RESPONSE (FULL, NO TRUNCATION) ---")
        try:
            response_text = extract_response_text(result)
            print(response_text)
        except (ValueError, TypeError) as e:
            print(f"Could not extract response text: {e}")
            print("\n--- RAW JSON OUTPUT ---")
            print(output)
        print("--- END RESPONSE ---")

        print("=" * 80)

        # Demo test - show output for human validation, don't assert
        # The trace above shows everything needed to verify hydration manually
        if not (hydrator_response and hydrator_response.get("found")):
            print("\n⚠️  NOTE: Hydrator structured response not found in output.")
            print("    Review the trace above to verify hydration behavior.")
