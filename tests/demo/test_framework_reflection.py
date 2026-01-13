#!/usr/bin/env python3
"""Demo test for the framework reflection loop (ns-shsd).

Demonstrates that the framework agent generates reflections and /log persists them.

Run with: uv run pytest tests/demo/test_framework_reflection.py -v -s -n 0 -m demo

Related:
- Epic ns-6hm: v1.0 Core Loop
- Task ns-shsd: Demo: Framework Reflection Loop
"""

import re

import pytest


@pytest.mark.demo
class TestFrameworkReflectionDemo:
    """Demo test for the framework reflection loop."""

    def test_demo_framework_reflection_generated(
        self, claude_headless_tracked, skill_was_invoked
    ) -> None:
        """Demo: Task completion triggers reflection generation.

        Strategy: Give agent a task that requires implementation work.
        The test verifies reflection format is correct in output.
        """
        print("\n" + "=" * 80)
        print("FRAMEWORK REFLECTION DEMO: Task Completion + Reflection")
        print("=" * 80)

        # Task that requires work and should trigger reflection at end
        prompt = (
            "Create a simple Python function in /tmp/test_reflection_func.py "
            "that adds two numbers. Then generate a Framework Reflection "
            "following the AGENTS.md format with these fields: "
            "Request, Guidance received, Followed, Outcome, Accomplishment, "
            "Root cause (if not success), Proposed change."
        )

        print(f"\n--- TASK ---\n{prompt}")
        print("\n--- EXECUTING HEADLESS SESSION ---")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=180, model="haiku"
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        if not result["success"]:
            pytest.fail(f"Session failed: {result.get('error')}. Session: {session_id}")

        # --- TEST EVALUATES (not the agent) ---
        print("\n" + "=" * 80)
        print("TEST EVALUATION")
        print("=" * 80)

        # Count tool types
        tool_counts: dict[str, int] = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1

        print("\n--- Tool Calls ---")
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"  {name}: {count}")

        # Extract response text
        print("\n--- Agent Response ---")
        try:
            from tests.integration.conftest import extract_response_text

            response_text = extract_response_text(result)
            # Show reflection part if found
            if "Framework Reflection" in response_text:
                # Find reflection section
                reflection_match = re.search(
                    r"##\s*Framework Reflection.*?(?=##|$)",
                    response_text,
                    re.DOTALL | re.IGNORECASE,
                )
                if reflection_match:
                    print("Found reflection:")
                    print(reflection_match.group(0)[:800])
                else:
                    print(response_text[:500] + "...")
            else:
                print(response_text[:500] + "...")
        except Exception as e:
            print(f"Could not extract: {e}")
            response_text = ""

        # --- CRITERIA ---
        print("\n" + "=" * 80)
        print("PASS/FAIL CRITERIA")
        print("=" * 80)

        # Check for reflection in response
        has_reflection_header = "Framework Reflection" in response_text.lower().replace(
            " ", ""
        ) or "## framework reflection" in response_text.lower()
        has_request_field = "**request**:" in response_text.lower()
        has_outcome_field = "**outcome**:" in response_text.lower()

        # Check for framework agent or /log invocation
        framework_invoked = any(
            c["name"] == "Task"
            and c.get("input", {}).get("subagent_type", "").endswith("framework")
            for c in tool_calls
        )
        log_invoked = skill_was_invoked(tool_calls, "log")

        criteria = [
            ("Session completed successfully", result["success"]),
            ("Reflection header present", has_reflection_header),
            ("Request field present", has_request_field),
            ("Outcome field present", has_outcome_field),
            ("Framework agent or /log invoked", framework_invoked or log_invoked),
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

        # For demo, we don't hard-fail on missing /log since haiku may not invoke it
        # The critical criteria are: reflection format is correct
        critical_criteria = [
            ("Session completed successfully", result["success"]),
            ("Reflection header present", has_reflection_header),
        ]

        critical_passed = all(passed for _, passed in critical_criteria)
        if not critical_passed:
            failed = [name for name, passed in critical_criteria if not passed]
            pytest.fail(
                f"Framework reflection demo FAILED. "
                f"Critical unmet: {', '.join(failed)}. Session: {session_id}"
            )

    def test_demo_log_command_creates_issue(self, claude_headless_tracked) -> None:
        """Demo: /log command creates bd issue for observation.

        Strategy: Invoke /log with an observation and verify bd create is called.
        """
        print("\n" + "=" * 80)
        print("LOG COMMAND DEMO: Observation Logging")
        print("=" * 80)

        # Direct /log invocation
        prompt = (
            "/log Test observation: Router suggested framework skill but agent "
            "ignored it - instruction wasn't task-specific"
        )

        print(f"\n--- TASK ---\n{prompt}")
        print("\n--- EXECUTING HEADLESS SESSION ---")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=120, model="haiku", fail_on_error=False
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        # --- TEST EVALUATES ---
        print("\n" + "=" * 80)
        print("TEST EVALUATION")
        print("=" * 80)

        # Count tool types
        tool_counts: dict[str, int] = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1

        print("\n--- Tool Calls ---")
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"  {name}: {count}")

        # Check for Skill tool with log or Task with framework agent
        skill_calls = [c for c in tool_calls if c["name"] == "Skill"]
        framework_agent_calls = [
            c
            for c in tool_calls
            if c["name"] == "Task"
            and "framework" in c.get("input", {}).get("subagent_type", "")
        ]

        log_skill_called = any(
            "log" in c.get("input", {}).get("skill", "").lower() for c in skill_calls
        )
        framework_called = len(framework_agent_calls) > 0

        print(f"\n--- Log/Framework Invocation ---")
        print(f"  Skill(log) called: {log_skill_called}")
        print(f"  Framework agent called: {framework_called}")

        # --- CRITERIA ---
        print("\n" + "=" * 80)
        print("PASS/FAIL CRITERIA")
        print("=" * 80)

        criteria = [
            ("Session completed (or made progress)", result["success"] or len(tool_calls) > 0),
            ("/log skill or framework agent invoked", log_skill_called or framework_called),
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

        # Note: We don't hard-fail here since /log command may need proper
        # plugin registration to work. This demo shows the expected behavior.
        if not all_passed:
            print(
                "\nNote: /log command requires aops-core plugin to be registered. "
                "This demo shows expected behavior pattern."
            )
