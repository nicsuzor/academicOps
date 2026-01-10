#!/usr/bin/env python3
"""Demo test for the self-reflexive loop validation (ns-rad).

Tests that agents can demonstrate their own verification capabilities
with full transparency. This is the core of academicOps: an agent that
knows where we want to go (VISION), knows where we ARE (bd), and can
reliably evaluate performance.

Run with: uv run pytest tests/demo/test_reflexive_loop.py -v -s -n 0 -m demo

Related:
- Epic ns-6fq: Self-Reflexive Loop Architecture
- Task ns-rad: Demo: Reflexive Loop Validation Test
- Issue aops-317: Transcript efficiency for reflexive debugging

Per H37a: Shows FULL untruncated output for human validation.
Per H37b: Uses REAL framework prompts, not contrived examples.
"""

import time
from pathlib import Path

import pytest


def find_recent_audit_files(max_age_seconds: int = 300) -> list[Path]:
    """Find audit files created in the last N seconds."""
    temp_dir = Path("/tmp/claude-compliance")
    if not temp_dir.exists():
        return []

    cutoff = time.time() - max_age_seconds
    return [f for f in temp_dir.glob("audit_*.md") if f.stat().st_mtime > cutoff]


@pytest.mark.demo
@pytest.mark.slow
@pytest.mark.integration
class TestReflexiveLoopDemo:
    """Demo test for the self-reflexive loop validation."""

    def test_demo_reflexive_loop_validation(self, claude_headless_tracked) -> None:
        """Demo: Prove the reflexive loop works with transparent evidence.

        Challenge: "Prove to me that the custodiet agent works as expected"

        Evaluation criteria (shown in output for human validation):
        1. Did the agent invoke custodiet?
        2. Did custodiet check relevant axioms/heuristics?
        3. Were claims supported by evidence?
        4. Were any steps skipped?
        5. Did the agent follow the reflexive process?
        """
        print("\n" + "=" * 80)
        print("REFLEXIVE LOOP VALIDATION DEMO")
        print("Epic: ns-6fq | Task: ns-rad")
        print("=" * 80)

        # The meta-challenge: prove custodiet works
        prompt = (
            "Prove to me that the custodiet agent works as expected. "
            "Show me evidence that: "
            "1) custodiet is invoked during normal operation, "
            "2) it checks axioms and heuristics, "
            "3) it can detect compliance issues. "
            "Use the framework's actual mechanisms - don't just describe them."
        )

        print("\n--- CHALLENGE ---")
        print(prompt)
        print("\n--- EXECUTING HEADLESS SESSION ---")

        # Use haiku for faster execution (sonnet times out on complex prompts)
        # 300s timeout - complex meta-prompts need time (session made 19 calls in 180s)
        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=300, model="haiku"
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        if not result["success"]:
            print(f"\nERROR: {result.get('error')}")
            print("\n--- EVALUATION: FAILED ---")
            print("Session did not complete successfully.")
            pytest.fail(
                f"Headless session failed: {result.get('error')}. "
                f"Session ID: {session_id}. Tool calls: {len(tool_calls)}"
            )

        # --- EVIDENCE COLLECTION ---
        print("\n" + "=" * 80)
        print("EVIDENCE COLLECTION")
        print("=" * 80)

        # 1. Tool call analysis
        tool_counts: dict[str, int] = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1

        print("\n--- TOOL CALLS ---")
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"  {name}: {count}")

        # 2. Find custodiet invocations
        custodiet_calls = [
            c
            for c in tool_calls
            if c["name"] == "Task"
            and c.get("input", {}).get("subagent_type") == "custodiet"
        ]

        print(f"\n--- CUSTODIET INVOCATIONS: {len(custodiet_calls)} ---")
        for i, call in enumerate(custodiet_calls):
            task_input = call.get("input", {})
            print(f"\n[{i + 1}] Custodiet Task:")
            print(f"    Description: {task_input.get('description', 'N/A')}")
            prompt_text = task_input.get("prompt", "")
            print(f"    Prompt: {prompt_text[:300]}...")

        # 3. Find compliance temp files created
        temp_dir = Path("/tmp/claude-compliance")
        if temp_dir.exists():
            recent_files = find_recent_audit_files(max_age_seconds=600)
            print(f"\n--- AUDIT FILES CREATED: {len(recent_files)} ---")
            for f in recent_files[-3:]:  # Show last 3
                print(f"    {f.name} ({f.stat().st_size} bytes)")
        else:
            print("\n--- AUDIT FILES: None found ---")

        # 4. Extract response text
        print("\n" + "=" * 80)
        print("AGENT RESPONSE (FULL)")
        print("=" * 80)

        try:
            from tests.integration.conftest import extract_response_text

            response_text = extract_response_text(result)
            print(response_text)
        except Exception as e:
            print(f"Could not extract response: {e}")
            print(f"Raw output length: {len(result.get('output', ''))} chars")

        # --- EVALUATION CRITERIA ---
        print("\n" + "=" * 80)
        print("EVALUATION CRITERIA")
        print("=" * 80)

        criteria = [
            ("Custodiet invoked?", len(custodiet_calls) > 0),
            ("Multiple tool types used?", len(tool_counts) >= 3),
            ("Bash tools used (triggers custodiet)?", tool_counts.get("Bash", 0) >= 1),
            ("Read tools used (evidence gathering)?", tool_counts.get("Read", 0) >= 1),
            (
                "Audit files created?",
                temp_dir.exists() and len(list(temp_dir.glob("audit_*.md"))) > 0,
            ),
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

        print("\n--- HUMAN VALIDATION REQUIRED ---")
        print("Review the agent response above to verify:")
        print("  1. Claims are supported by evidence (not just assertions)")
        print("  2. The agent demonstrated actual custodiet execution")
        print("  3. No steps were skipped or glossed over")
        print("  4. The reflexive process was followed (observe -> diagnose -> report)")
        print("=" * 80)

        # H37 FIX (ns-een): Test MUST fail if criteria not met
        # Previous version printed "NEEDS REVIEW" but passed - a Volkswagen test
        if not all_passed:
            failed_criteria = [name for name, passed in criteria if not passed]
            pytest.fail(
                f"Reflexive loop validation FAILED. "
                f"Unmet criteria: {', '.join(failed_criteria)}. "
                f"Session ID: {session_id}. "
                f"See full output above for evidence."
            )
