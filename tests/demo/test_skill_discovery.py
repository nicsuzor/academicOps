#!/usr/bin/env python3
"""Demo test for Skill Discovery & Loading (ns-k3f).

Demonstrates that skills are correctly discovered and loaded:
1. Skill exists in skills/ directory
2. SKILL.md is found and loaded
3. Instructions become available to agent
4. Referenced files (workflows, references) are accessible

Run with: uv run pytest tests/demo/test_skill_discovery.py -v -s -n 0 -m demo

Related:
- Epic ns-q5a: v1.0 Framework Audit - Demo Tests & Consolidation
- Task ns-k3f: Demo: Skill Discovery & Loading
"""

import pytest


@pytest.mark.demo
@pytest.mark.slow
class TestSkillDiscoveryDemo:
    """Demo test for skill discovery and loading."""

    def test_demo_skill_discovery_framework(self, claude_headless_tracked) -> None:
        """Demo: Skill invocation loads correct context.

        Strategy: Ask agent to invoke a specific skill and then
        demonstrate knowledge that can only come from that skill's content.
        We use the 'framework' skill since it has well-defined workflows.
        """
        print("\n" + "=" * 80)
        print("SKILL DISCOVERY DEMO: Framework Skill Loading")
        print("=" * 80)

        # Ask agent to invoke skill and report what it learned
        prompt = (
            "Invoke Skill(skill='framework') and then list the workflow files "
            "available in that skill. Just list the workflow names."
        )

        print(f"\n--- TASK ---\n{prompt}")
        print("\n--- EXECUTING HEADLESS SESSION ---")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=120, model="haiku"
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        # --- TEST EVALUATES ---
        print("\n" + "=" * 80)
        print("TEST EVALUATION: Skill Discovery Verification")
        print("=" * 80)

        # Check 1: Skill tool was called with 'framework'
        skill_calls = [c for c in tool_calls if c["name"] == "Skill"]
        print(f"\n--- Skill Tool Calls: {len(skill_calls)} ---")
        framework_invoked = False
        for call in skill_calls:
            skill_name = call.get("input", {}).get("skill", "")
            print(f"    - {skill_name}")
            if "framework" in skill_name.lower():
                framework_invoked = True
        print(f"    Framework skill invoked: {framework_invoked}")

        # Check 2: Agent response mentions workflow names
        # The framework skill has workflows like:
        # - 01-design-new-component.md
        # - 02-debug-framework-issue.md
        print("\n--- Agent Response Analysis ---")
        try:
            from tests.conftest import extract_response_text

            response_text = extract_response_text(result)
            response_lower = response_text.lower()

            # Check for evidence of workflow knowledge
            workflow_indicators = [
                "design",
                "debug",
                "component",
                "workflow",
                "01-",
                "02-",
            ]
            found_indicators = [
                ind for ind in workflow_indicators if ind in response_lower
            ]
            print(f"    Workflow indicators found: {found_indicators}")

            # Show response for human validation
            print("\n--- Response (first 800 chars) ---")
            print(response_text[:800] + ("..." if len(response_text) > 800 else ""))

            # Semantic check: response should mention workflows
            knows_workflows = len(found_indicators) >= 2
        except Exception as e:
            print(f"    Could not extract response: {e}")
            knows_workflows = False
            response_text = ""

        # --- CRITERIA ---
        print("\n" + "=" * 80)
        print("PASS/FAIL CRITERIA")
        print("=" * 80)

        criteria = [
            ("Session completed successfully", result["success"]),
            ("Skill tool was called", len(skill_calls) >= 1),
            ("Framework skill specifically invoked", framework_invoked),
            ("Agent demonstrates workflow knowledge", knows_workflows),
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
                f"Skill discovery validation FAILED. "
                f"Unmet criteria: {', '.join(failed)}. Session: {session_id}"
            )
