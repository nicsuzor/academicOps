#!/usr/bin/env python3
"""Demo test for Multi-Agent Workflows (ns-ktp).

Demonstrates that subagents spawn correctly and return results:
1. Task tool invoked with subagent_type
2. Subagent executes independently
3. Results returned to main agent
4. Main agent processes subagent output

Run with: uv run pytest tests/demo/test_multi_agent.py -v -s -n 0 -m demo

Related:
- Epic ns-q5a: v1.0 Framework Audit - Demo Tests & Consolidation
- Task ns-ktp: Demo: Multi-Agent Workflows
"""

import pytest


@pytest.mark.demo
@pytest.mark.slow
class TestMultiAgentDemo:
    """Demo test for multi-agent workflows."""

    def test_demo_multi_agent_critic(self, claude_headless_tracked) -> None:
        """Demo: Subagents spawn and return results.

        Strategy: Ask the main agent to use a subagent (critic) to review
        a statement. The test verifies the Task tool was called with the
        correct subagent_type and that the main agent processed the result.
        """
        print("\n" + "=" * 80)
        print("MULTI-AGENT DEMO: Critic Subagent Invocation")
        print("=" * 80)

        # Ask agent to use a specific subagent
        prompt = (
            "Use the critic agent (Task tool with subagent_type='critic') to review "
            "this plan: 'Add a new feature without writing any tests first'. "
            "Report what the critic says."
        )

        print(f"\n--- TASK ---\n{prompt}")
        print("\n--- EXECUTING HEADLESS SESSION ---")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=180, model="haiku"
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        # --- TEST EVALUATES ---
        print("\n" + "=" * 80)
        print("TEST EVALUATION: Multi-Agent Verification")
        print("=" * 80)

        # Check 1: Task tool was called
        task_calls = [c for c in tool_calls if c["name"] == "Task"]
        print(f"\n--- Task Tool Calls: {len(task_calls)} ---")

        # Check 2: Subagent type was specified
        critic_invoked = False
        for call in task_calls:
            subagent_type = call.get("input", {}).get("subagent_type", "")
            print(f"    - subagent_type: {subagent_type}")
            if "critic" in subagent_type.lower():
                critic_invoked = True
        print(f"    Critic subagent invoked: {critic_invoked}")

        # Check 3: Main agent processed critic output
        print("\n--- Response Analysis ---")
        try:
            from tests.conftest import extract_response_text

            response_text = extract_response_text(result)
            response_lower = response_text.lower()

            # Look for evidence that critic feedback was processed
            critic_indicators = ["critic", "review", "concern", "issue", "test", "risk"]
            found_indicators = [ind for ind in critic_indicators if ind in response_lower]
            print(f"    Critic-related terms found: {found_indicators}")

            # Show response for human validation
            print("\n--- Response (first 800 chars) ---")
            print(response_text[:800] + ("..." if len(response_text) > 800 else ""))

            processed_critic_output = len(found_indicators) >= 2
        except Exception as e:
            print(f"    Could not extract response: {e}")
            processed_critic_output = False
            response_text = ""

        # Tool usage summary
        print("\n--- All Tool Calls ---")
        tool_counts: dict[str, int] = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"    {name}: {count}")

        # --- CRITERIA ---
        print("\n" + "=" * 80)
        print("PASS/FAIL CRITERIA")
        print("=" * 80)

        criteria = [
            ("Session completed successfully", result["success"]),
            ("Task tool was called", len(task_calls) >= 1),
            ("Critic subagent invoked", critic_invoked),
            ("Main agent processed critic output", processed_critic_output),
        ]

        all_passed = True
        for name, passed in criteria:
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False
            print(f"  [{status}] {name}")

        print("\n" + "=" * 80)
        print(f"OVERALL: {'PASS' if all_passed else 'FAIL'}")
        print("=" * 80)

        if not all_passed:
            failed = [name for name, passed in criteria if not passed]
            pytest.fail(
                f"Multi-agent validation FAILED. "
                f"Unmet criteria: {', '.join(failed)}. Session: {session_id}"
            )
