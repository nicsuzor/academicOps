#!/usr/bin/env python3
"""Demo test for Quality Gates - Critic Review (ns-m26).

Demonstrates that critic agent catches issues and provides feedback:
1. Plan submitted to critic for review
2. Critic identifies problems
3. Agent addresses feedback

Run with: uv run pytest tests/demo/test_quality_gates.py -v -s -n 0 -m demo

Related:
- Epic ns-q5a: v1.0 Framework Audit - Demo Tests & Consolidation
- Task ns-m26: Demo: Quality Gates (Critic Review)
"""

import pytest


@pytest.mark.demo
@pytest.mark.slow
class TestQualityGatesDemo:
    """Demo test for quality gates via critic review."""

    def test_demo_quality_gate_critic_review(self, claude_headless_tracked) -> None:
        """Demo: Critic review catches issues and provides feedback.

        Strategy: Present a deliberately flawed plan to the critic and verify
        that the critic identifies problems. The test checks that:
        1. Critic agent was invoked
        2. Critic identified issues in the plan
        3. Agent processed and reported the feedback
        """
        print("\n" + "=" * 80)
        print("QUALITY GATES DEMO: Critic Catches Issues")
        print("=" * 80)

        # Present a flawed plan that critic should catch issues with
        # NOTE: Must explicitly specify Task(subagent_type='critic') because
        # "critic agent" alone is ambiguous - models may look for a skill instead
        prompt = (
            "I have this plan for implementing a new database migration: "
            "'1. Write migration script, 2. Run on production, 3. Test if it worked'. "
            "Use Task(subagent_type='critic') to review this plan and report any concerns."
        )

        print(f"\n--- TASK ---\n{prompt}")
        print("\n--- EXECUTING HEADLESS SESSION ---")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=360, model="haiku"
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        # --- TEST EVALUATES ---
        print("\n" + "=" * 80)
        print("TEST EVALUATION: Quality Gate Verification")
        print("=" * 80)

        # Check 1: Task tool was called with critic subagent
        task_calls = [c for c in tool_calls if c["name"] == "Task"]
        print(f"\n--- Task Tool Calls: {len(task_calls)} ---")
        critic_invoked = False
        for call in task_calls:
            subagent_type = call.get("input", {}).get("subagent_type", "")
            print(f"    - subagent_type: {subagent_type}")
            if "critic" in subagent_type.lower():
                critic_invoked = True
        print(f"    Critic invoked: {critic_invoked}")

        # Check 2: Response contains critic feedback with concerns
        print("\n--- Response Analysis ---")
        try:
            from tests.conftest import extract_response_text

            response_text = extract_response_text(result)
            response_lower = response_text.lower()

            # Look for evidence that critic found issues
            concern_indicators = [
                "concern",
                "issue",
                "problem",
                "risk",
                "violat",
                "test",
                "backup",
                "staging",
                "rollback",
            ]
            found_concerns = [
                ind for ind in concern_indicators if ind in response_lower
            ]
            print(f"    Concern indicators found: {found_concerns}")

            # Critic should identify testing/staging issues with the flawed plan
            critic_found_issues = len(found_concerns) >= 2

            # Show response for human validation
            print("\n--- Response (first 1000 chars) ---")
            print(response_text[:1000] + ("..." if len(response_text) > 1000 else ""))

        except Exception as e:
            print(f"    Could not extract response: {e}")
            critic_found_issues = False
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
            ("Critic agent invoked", critic_invoked),
            ("Critic identified issues in plan", critic_found_issues),
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
                f"Quality gate validation FAILED. "
                f"Unmet criteria: {', '.join(failed)}. Session: {session_id}"
            )
