#!/usr/bin/env python3
"""Demo test for the self-reflexive loop validation (ns-rad).

Demonstrates that custodiet fires during normal agent operation.
The agent does a simple task; the TEST proves custodiet worked.

Run with: uv run pytest tests/demo/test_reflexive_loop.py -v -s -n 0 -m demo

Related:
- Epic ns-6fq: Self-Reflexive Loop Architecture
- Task ns-rad: Demo: Reflexive Loop Validation Test
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
class TestReflexiveLoopDemo:
    """Demo test for the self-reflexive loop validation."""

    def test_demo_reflexive_loop_validation(self, claude_headless_tracked) -> None:
        """Demo: Simple task triggers custodiet, test evaluates.

        Strategy: Give agent a straightforward task that requires
        multiple action tools. The test then verifies custodiet fired.
        """
        print("\n" + "=" * 80)
        print("REFLEXIVE LOOP DEMO: Simple Task + Custodiet Verification")
        print("=" * 80)

        # Simple task requiring multiple bash calls (action tools trigger custodiet)
        prompt = (
            "Run these commands one at a time and report the results: "
            "1) echo 'step one' "
            "2) date "
            "3) whoami "
            "4) pwd "
            "5) echo 'step five' "
            "6) echo 'done'"
        )

        print(f"\n--- TASK ---\n{prompt}")
        print("\n--- EXECUTING HEADLESS SESSION ---")

        # Record audit files before test
        audit_files_before = set(find_recent_audit_files(max_age_seconds=3600))

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=120, model="haiku"
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

        # Find custodiet invocations
        custodiet_calls = [
            c
            for c in tool_calls
            if c["name"] == "Task"
            and c.get("input", {}).get("subagent_type") == "custodiet"
        ]
        print(f"\n--- Custodiet Invocations: {len(custodiet_calls)} ---")

        # Check for new audit files
        audit_files_after = set(find_recent_audit_files(max_age_seconds=600))
        new_audit_files = audit_files_after - audit_files_before
        print(f"--- New Audit Files: {len(new_audit_files)} ---")

        # Extract response
        print("\n--- Agent Response ---")
        try:
            from tests.integration.conftest import extract_response_text

            response_text = extract_response_text(result)
            # Show first 500 chars
            print(response_text[:500] + ("..." if len(response_text) > 500 else ""))
        except Exception as e:
            print(f"Could not extract: {e}")

        # --- CRITERIA ---
        print("\n" + "=" * 80)
        print("PASS/FAIL CRITERIA")
        print("=" * 80)

        bash_count = tool_counts.get("Bash", 0)
        # Note: Custodiet runs as background subagent via PostToolUse hook.
        # It's not in tool_calls, but creates audit files.
        criteria = [
            ("Session completed successfully", result["success"]),
            ("Bash tools used (>= 3)", bash_count >= 3),
            ("Custodiet audit file created", len(new_audit_files) >= 1),
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
                f"Reflexive loop validation FAILED. "
                f"Unmet: {', '.join(failed)}. Session: {session_id}"
            )
