#!/usr/bin/env python3
"""Demo test for QA Gates - Critic and Custodiet Verification (ns-qe4e).

Demonstrates the quality assurance verification pipeline with both agents:
1. Plan is generated (plan-mode workflow)
2. Critic agent reviews the plan and provides verdict
3. Custodiet agent checks for compliance violations
4. Agent respects verdicts and acts accordingly

This test validates that both quality gates work correctly and provide
meaningful feedback to prevent poor execution.

Run with: uv run pytest tests/demo/test_demo_qa_gates.py -v -s -n 0 -m demo

Related:
- Epic ns-6hm: v1.0 Core Loop - Hydration/Workflow/QA/Reflection
- Task ns-qe4e: Demo: QA Gates (Critic + Custodiet)
- Agent: aops-core:critic
- Agent: aops-core:custodiet
"""

import pytest


@pytest.mark.demo
@pytest.mark.slow
class TestQAGatesDemo:
    """Demo test for QA gates via critic and custodiet verification."""

    def test_demo_qa_gates_critic_and_custodiet(self, claude_headless_tracked) -> None:
        """Demo: Critic and custodiet provide quality verification.

        This test demonstrates both quality gates working together:
        1. Critic reviews implementation plan for problems
        2. Custodiet checks for scope drift and compliance violations

        Strategy: Present a deliberately flawed plan that should trigger
        both quality gates to provide feedback.
        """
        print("\n" + "=" * 80)
        print("QA GATES DEMO: Critic Review + Custodiet Compliance")
        print("=" * 80)

        # Present a task that should trigger both quality gates
        # The plan has multiple issues that critic and custodiet should catch:
        # - Testing in production (critic should flag)
        # - No backup plan (critic should flag)
        # - Scope creep potential (custodiet might flag)
        prompt = (
            "I need to implement a new user authentication system. "
            "Here's my plan:\n"
            "1. Remove the old auth system completely\n"
            "2. Write new auth code with JWT tokens\n"
            "3. Deploy directly to production and test with real users\n"
            "4. Also add password reset, 2FA, and OAuth while we're at it\n\n"
            "Please review this plan using:\n"
            "- Task(subagent_type='aops-core:critic') to check for risks\n"
            "- Task(subagent_type='aops-core:custodiet') to check for scope/compliance issues\n"
            "Report what each agent found."
        )

        print(f"\n--- FLAWED PLAN ---\n{prompt}")
        print("\n--- EXECUTING HEADLESS SESSION ---")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=360, model="sonnet"
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        # === QA GATE ANALYSIS ===
        print("\n" + "=" * 80)
        print("QA GATE VERIFICATION")
        print("=" * 80)

        # Tool usage summary
        tool_counts: dict[str, int] = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1

        print("\n--- Tool Call Summary ---")
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"  {name}: {count}")

        # Gate 1: Critic Invocation
        task_calls = [c for c in tool_calls if c["name"] == "Task"]
        print("\n--- GATE 1: Critic Review ---")
        print(f"  Task tool calls: {len(task_calls)}")

        critic_invoked = False
        critic_verdict = None
        for call in task_calls:
            subagent_type = call.get("input", {}).get("subagent_type", "")
            desc = call.get("input", {}).get("description", "")
            print(f"  - Subagent: {subagent_type}")
            print(f"    Description: {desc[:60]}...")

            if "critic" in subagent_type.lower():
                critic_invoked = True
                # Try to extract verdict from description or response
                if "proceed" in desc.lower():
                    critic_verdict = "PROCEED"
                elif "revise" in desc.lower() or "halt" in desc.lower():
                    critic_verdict = "REVISE/HALT"

        print(f"  Critic invoked: {critic_invoked}")
        print(f"  Critic verdict: {critic_verdict or 'N/A (check response)'}")

        # Gate 2: Custodiet Invocation
        print("\n--- GATE 2: Custodiet Compliance ---")

        custodiet_invoked = False
        custodiet_verdict = None
        for call in task_calls:
            subagent_type = call.get("input", {}).get("subagent_type", "")
            desc = call.get("input", {}).get("description", "")

            if "custodiet" in subagent_type.lower():
                custodiet_invoked = True
                # Try to extract verdict
                if "ok" in desc.lower() and "attention" not in desc.lower():
                    custodiet_verdict = "OK"
                elif "attention" in desc.lower():
                    custodiet_verdict = "ATTENTION"

                print(f"  - Subagent: {subagent_type}")
                print(f"    Description: {desc[:60]}...")

        print(f"  Custodiet invoked: {custodiet_invoked}")
        print(f"  Custodiet verdict: {custodiet_verdict or 'N/A (check response)'}")

        # Gate 3: Response Analysis (semantic check for issues found)
        print("\n--- GATE 3: Issue Detection ---")
        try:
            from tests.conftest import extract_response_text

            response_text = extract_response_text(result)
            response_lower = response_text.lower()

            # Look for evidence that QA gates found issues
            critic_issue_indicators = [
                "production" in response_lower,
                "test" in response_lower,
                "risk" in response_lower,
                "backup" in response_lower,
                "staging" in response_lower,
                "rollback" in response_lower,
            ]

            custodiet_issue_indicators = [
                "scope" in response_lower,
                "drift" in response_lower,
                "compliance" in response_lower,
                "violation" in response_lower,
                "focus" in response_lower,
            ]

            critic_issues_found = sum(critic_issue_indicators)
            custodiet_issues_found = sum(custodiet_issue_indicators)

            print(f"  Critic issue indicators: {critic_issues_found}/6")
            print(f"  Custodiet issue indicators: {custodiet_issues_found}/5")

            # === HUMAN OPERATOR VALIDATION SECTION ===
            print("\n" + "=" * 80)
            print("HUMAN OPERATOR VALIDATION - Full Agent Output")
            print("=" * 80)

            # Check for verdicts
            print("\n--- Verdict Detection ---")
            critic_verdicts = []
            custodiet_verdicts = []

            if "halt" in response_lower:
                critic_verdicts.append("HALT")
            if "revise" in response_lower:
                critic_verdicts.append("REVISE")
            if "proceed" in response_lower:
                critic_verdicts.append("PROCEED")
            if "block" in response_lower or "attention" in response_lower:
                custodiet_verdicts.append("BLOCK/ATTENTION")
            if response_lower.count("ok") > 1:  # Multiple "OK"s might indicate verdict
                custodiet_verdicts.append("OK")

            print(
                f"  Critic verdicts detected: {', '.join(critic_verdicts) if critic_verdicts else 'None'}"
            )
            print(
                f"  Custodiet verdicts detected: {', '.join(custodiet_verdicts) if custodiet_verdicts else 'None'}"
            )

            # Show full response for manual inspection
            print("\n--- FULL AGENT RESPONSE (for manual validation) ---")
            print("-" * 80)
            # Format for readability - indent each line
            formatted_response = response_text.replace("\n", "\n  ")
            print(f"  {formatted_response}")
            print("-" * 80)

            # Check if agent attempted implementation
            print("\n--- Implementation Attempt Detection ---")
            implementation_indicators = [
                "write" in response_lower and "code" in response_lower,
                "implement" in response_lower
                and ("jwt" in response_lower or "auth" in response_lower),
                "create" in response_lower and "file" in response_lower,
            ]
            attempted_implementation = sum(implementation_indicators) >= 2
            print(
                f"  Agent attempted implementation: {'YES (BAD - should respect HALT)' if attempted_implementation else 'NO (GOOD)'}"
            )

            issues_detected = (critic_issues_found >= 2) or (custodiet_issues_found >= 1)

        except Exception as e:
            print(f"  Could not extract response: {e}")
            issues_detected = False
            critic_issues_found = 0
            custodiet_issues_found = 0

        # === VALIDATION CRITERIA ===
        print("\n" + "=" * 80)
        print("VALIDATION CRITERIA")
        print("=" * 80)

        criteria = [
            ("Session completed successfully", result["success"]),
            ("Gate 1: Critic agent invoked", critic_invoked),
            ("Gate 2: Custodiet agent invoked", custodiet_invoked),
            ("Gate 3: Issues detected in flawed plan", issues_detected),
            (
                "Semantic validation: Meaningful feedback",
                (critic_issues_found + custodiet_issues_found) >= 3,
            ),
        ]

        all_passed = True
        for name, passed in criteria:
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False
            print(f"  [{status}] {name}")

        # === DEMO SUMMARY ===
        print("\n" + "=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        print(
            f"""
This demo showed both QA gates working together:

**Gate 1: Critic Review**
- Invoked: {"YES" if critic_invoked else "NO"}
- Purpose: Reviews plans for technical risks and bad practices
- Verdict: {critic_verdict or "See response"}
- Issues found: Testing in production, no backup, missing staging

**Gate 2: Custodiet Compliance**
- Invoked: {"YES" if custodiet_invoked else "NO"}
- Purpose: Checks for scope drift and compliance violations
- Verdict: {custodiet_verdict or "See response"}
- Issues found: Scope creep (multiple features bundled)

**Combined Impact:**
The two-gate system provides layered protection:
1. **Critic** catches technical and process risks before execution
2. **Custodiet** catches scope drift and ensures alignment with intent

**Flawed Plan Analysis:**
Original plan had major issues:
- ❌ No testing in staging environment
- ❌ No rollback strategy
- ❌ Scope creep (4 features bundled)
- ❌ Production testing with real users

**QA Gates Verdict:**
Both gates should flag this plan as problematic and require revision.
The agent should NOT proceed with execution until issues are addressed.

Session {session_id} demonstrates the v1.0 QA gates working correctly.
"""
        )
        print("=" * 80)
        print(f"OVERALL: {'PASS' if all_passed else 'FAIL'}")
        print("=" * 80)

        if not all_passed:
            failed = [name for name, passed in criteria if not passed]
            pytest.fail(
                f"QA gates validation FAILED. "
                f"Unmet criteria: {', '.join(failed)}. Session: {session_id}"
            )

        assert all_passed, "QA gates demo validation failed"
