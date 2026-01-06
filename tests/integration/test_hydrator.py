#!/usr/bin/env python3
"""Integration tests for prompt hydration system.

Tests the UserPromptSubmit hook -> temp file -> prompt-hydrator subagent pipeline.

Run demo test for visual validation:
    uv run pytest tests/integration/test_hydrator.py -k demo -v -s

The demo test shows actual hydration output so you can validate with your eyes.
"""

import json
import re
from pathlib import Path

import pytest


@pytest.mark.slow
@pytest.mark.integration
def test_hydrator_temp_file_contains_prompt(claude_headless) -> None:
    """Verify UserPromptSubmit hook writes user prompt to temp file.

    This tests the FIRST half of hydration:
    - Hook receives user prompt
    - Hook writes to /tmp/claude-hydrator/hydrate_*.md
    - Temp file contains the actual prompt text
    """
    # Use distinctive prompt we can search for
    test_prompt = "HYDRATOR_TEST_MARKER: What is the capital of France?"

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

    # At least one should contain our marker
    marker_found = False
    for temp_file in recent_files:
        content = temp_file.read_text()
        if "HYDRATOR_TEST_MARKER" in content:
            marker_found = True
            # Verify full prompt is there
            assert "capital of France" in content, "Full prompt should be in temp file"
            break

    assert marker_found, (
        f"None of {len(recent_files)} temp files contained test marker. "
        "UserPromptSubmit hook may not be writing prompts correctly."
    )


@pytest.mark.slow
@pytest.mark.integration
def test_hydrator_invoked_in_session(claude_headless) -> None:
    """Verify prompt-hydrator subagent is actually invoked.

    This tests the SECOND half of hydration:
    - Main agent receives hook instruction
    - Main agent spawns prompt-hydrator Task
    - Hydrator returns workflow guidance
    """
    result = claude_headless(
        "What is 2+2? Just answer with the number.", timeout_seconds=120
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # The output should show evidence of hydration
    output_str = str(result.get("output", "")).lower()

    hydrator_indicators = [
        "prompt-hydrator",
        "workflow guidance",
        "hydrate:",
        "prompt hydration",
        "hydration",
    ]

    has_hydration = any(ind.lower() in output_str for ind in hydrator_indicators)
    assert has_hydration, (
        f"Hydration should occur. Expected one of {hydrator_indicators} in output. "
        f"Got (first 1000 chars): {output_str[:1000]}"
    )


@pytest.mark.demo
class TestHydratorDemo:
    """Demo tests showing real hydration behavior.

    Run with: uv run pytest tests/integration/test_hydrator.py -k demo -v -s

    These tests print actual hydration output for visual validation.
    """

    def test_demo_hydration_temp_file_content(self) -> None:
        """Show what the UserPromptSubmit hook writes to temp files.

        This reveals:
        - Actual temp file structure
        - How user prompts are embedded
        - Session context included
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

        print("\n" + "=" * 80)
        print("HYDRATION TEMP FILE DEMO")
        print("=" * 80)
        print(f"\nFile: {most_recent}")
        print(f"Size: {most_recent.stat().st_size} bytes")
        print(f"Modified: {most_recent.stat().st_mtime}")
        print("\n--- CONTENT START ---\n")
        print(most_recent.read_text())
        print("\n--- CONTENT END ---\n")

        # Verify structure
        content = most_recent.read_text()
        assert "## User Prompt" in content, "Should have User Prompt section"
        assert "## Your Task" in content, "Should have Your Task section"

        print("STRUCTURE VALIDATION: PASSED")
        print("=" * 80)

    def test_demo_hydration_in_headless_session(self, claude_headless) -> None:
        """Show actual hydration happening in a headless session.

        This reveals:
        - Hook instruction injected
        - Hydrator subagent spawned
        - Workflow guidance returned
        """
        print("\n" + "=" * 80)
        print("HYDRATION E2E DEMO")
        print("=" * 80)

        prompt = "What is the meaning of life? Answer briefly."
        print(f"\nPrompt: {prompt}")
        print("\nExecuting headless session...")

        result = claude_headless(prompt, timeout_seconds=180)

        print(f"\nSuccess: {result['success']}")

        if not result["success"]:
            print(f"Error: {result.get('error')}")
            pytest.fail(f"Execution failed: {result.get('error')}")

        # Parse and display output
        output = result.get("output", "")
        print(f"\nRaw output length: {len(output)} chars")

        # Try to parse as JSON for prettier display
        try:
            parsed = json.loads(output)
            print("\n--- PARSED OUTPUT ---")
            print(json.dumps(parsed, indent=2)[:3000])
            if len(json.dumps(parsed)) > 3000:
                print("... (truncated)")
        except json.JSONDecodeError:
            print("\n--- RAW OUTPUT (first 2000 chars) ---")
            print(output[:2000])

        # Check for hydration evidence
        output_lower = output.lower()
        hydration_evidence = {
            "prompt-hydrator": "prompt-hydrator" in output_lower,
            "workflow": "workflow" in output_lower,
            "hydrate": "hydrate" in output_lower,
            "guidance": "guidance" in output_lower,
        }

        print("\n--- HYDRATION EVIDENCE ---")
        for indicator, found in hydration_evidence.items():
            status = "FOUND" if found else "NOT FOUND"
            print(f"  {indicator}: {status}")

        any_found = any(hydration_evidence.values())
        print(f"\nHydration occurred: {any_found}")
        print("=" * 80)

        assert any_found, "Should find hydration evidence in output"

    def test_demo_hydration_full_trace(self, claude_headless_tracked) -> None:
        """Show complete hydration trace with tool calls.

        This reveals:
        - Exact sequence of tool invocations
        - Whether Task tool spawned prompt-hydrator
        - Full session audit trail
        """
        print("\n" + "=" * 80)
        print("HYDRATION FULL TRACE DEMO")
        print("=" * 80)

        prompt = "List three primary colors."
        print(f"\nPrompt: {prompt}")
        print("\nExecuting tracked headless session...")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=180
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Tool calls captured: {len(tool_calls)}")

        if not result["success"]:
            print(f"Error: {result.get('error')}")

        # Display tool calls
        print("\n--- TOOL CALLS ---")
        for i, call in enumerate(tool_calls):
            print(f"\n[{i + 1}] {call['name']}")
            # Show relevant input for Task calls
            if call["name"] == "Task":
                task_input = call.get("input", {})
                print(f"    subagent_type: {task_input.get('subagent_type', 'N/A')}")
                print(f"    description: {task_input.get('description', 'N/A')[:60]}")
            elif call["name"] in ("Read", "Grep", "Glob"):
                print(f"    input: {str(call.get('input', {}))[:80]}")

        # Check for hydrator Task
        hydrator_invoked = any(
            call["name"] == "Task"
            and "hydrator" in str(call.get("input", {})).lower()
            for call in tool_calls
        )

        print("\n--- HYDRATION VERIFICATION ---")
        print(f"prompt-hydrator Task invoked: {hydrator_invoked}")

        # Also check output for hydration content
        output = result.get("output", "")
        has_hydration_output = any(
            ind in output.lower()
            for ind in ["prompt hydration", "workflow", "hydrate:"]
        )
        print(f"Hydration content in output: {has_hydration_output}")
        print("=" * 80)

        # This is a demo - we report rather than assert
        # In real tests we'd assert hydrator_invoked is True
