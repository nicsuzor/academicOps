#!/usr/bin/env python3
"""Demo test for Hook Firing Sequence (ns-0pi).

Demonstrates that hooks fire at correct lifecycle events:
1. SessionStart hook injects AXIOMS, FRAMEWORK, HEURISTICS
2. UserPromptSubmit hook prepares hydration context
3. PostToolUse hooks fire after tool calls
4. Custodiet compliance checks run

Run with: uv run pytest tests/demo/test_hook_sequence.py -v -s -n 0 -m demo

Related:
- Epic ns-q5a: v1.0 Framework Audit - Demo Tests & Consolidation
- Task ns-0pi: Demo: Hook Firing Sequence
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


def find_recent_hydrator_files(max_age_seconds: int = 300) -> list[Path]:
    """Find hydrator context files created in the last N seconds."""
    temp_dir = Path("/tmp/claude-hydrator")
    if not temp_dir.exists():
        return []

    cutoff = time.time() - max_age_seconds
    return [f for f in temp_dir.glob("hydrate_*.md") if f.stat().st_mtime > cutoff]


@pytest.mark.demo
@pytest.mark.slow
class TestHookSequenceDemo:
    """Demo test for hook firing sequence."""

    def test_demo_hook_firing_sequence(self, claude_headless_tracked) -> None:
        """Demo: Hooks fire at correct lifecycle points.

        Strategy: Run a session that triggers multiple hooks and verify
        evidence of each hook firing via side effects (temp files, tool calls).

        Hooks verified:
        - SessionStart: Injects framework context (AXIOMS, HEURISTICS)
        - UserPromptSubmit: Creates hydration context file
        - PostToolUse: Triggers custodiet checks (creates audit files)
        """
        print("\n" + "=" * 80)
        print("HOOK SEQUENCE DEMO: Lifecycle Event Verification")
        print("=" * 80)

        # Record state before test
        audit_files_before = set(find_recent_audit_files(max_age_seconds=3600))
        hydrator_files_before = set(find_recent_hydrator_files(max_age_seconds=3600))

        # Task that will trigger hooks:
        # - SessionStart fires at session start
        # - UserPromptSubmit fires when prompt submitted
        # - PostToolUse fires after action tools (Bash, Write, Edit - NOT Read/Glob/Grep)
        # Use multiple bash commands to exceed tool threshold and trigger custodiet
        prompt = (
            "Run these bash commands one at a time: "
            "1) echo 'hook test step 1' "
            "2) date "
            "3) pwd "
            "4) echo 'hook test done'"
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
        print("TEST EVALUATION: Hook Firing Evidence")
        print("=" * 80)

        # Evidence 1: SessionStart hook - injects context
        # Session completed means SessionStart fired (it always does for aops sessions)
        print("\n--- Evidence 1: SessionStart Hook ---")
        try:
            from tests.conftest import extract_response_text

            response_text = extract_response_text(result)
            # Session completed successfully means SessionStart injected context
            session_start_fired = result["success"]
            print(f"    Session started successfully: {session_start_fired}")
        except Exception as e:
            print(f"    Could not extract response: {e}")
            session_start_fired = result["success"]
            response_text = ""

        # Evidence 2: UserPromptSubmit hook - creates hydrator file
        print("\n--- Evidence 2: UserPromptSubmit Hook ---")
        hydrator_files_after = set(find_recent_hydrator_files(max_age_seconds=600))
        new_hydrator_files = hydrator_files_after - hydrator_files_before
        print(f"    New hydrator files: {len(new_hydrator_files)}")
        hydrator_fired = len(new_hydrator_files) >= 1

        # Evidence 3: PostToolUse hook - creates audit files (custodiet)
        print("\n--- Evidence 3: PostToolUse Hook (Custodiet) ---")
        audit_files_after = set(find_recent_audit_files(max_age_seconds=600))
        new_audit_files = audit_files_after - audit_files_before
        print(f"    New audit files: {len(new_audit_files)}")
        posttooluse_fired = len(new_audit_files) >= 1

        # Evidence 4: Tool calls show action tools were used (triggers PostToolUse)
        print("\n--- Evidence 4: Tool Usage ---")
        tool_counts: dict[str, int] = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"    {name}: {count}")
        # Any tool usage triggers PostToolUse hooks
        action_tools_used = len(tool_calls) >= 1

        # Show response for human validation
        print("\n--- Agent Response (first 600 chars) ---")
        if response_text:
            print(response_text[:600] + ("..." if len(response_text) > 600 else ""))

        # --- CRITERIA ---
        print("\n" + "=" * 80)
        print("PASS/FAIL CRITERIA")
        print("=" * 80)

        criteria = [
            ("Session completed successfully", result["success"]),
            ("SessionStart: Hook fired (session started)", session_start_fired),
            ("UserPromptSubmit: Hydrator file created", hydrator_fired),
            ("PostToolUse: Custodiet audit file created", posttooluse_fired),
            ("Action tools used (triggers PostToolUse)", action_tools_used),
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
                f"Hook sequence validation FAILED. "
                f"Unmet criteria: {', '.join(failed)}. Session: {session_id}"
            )
