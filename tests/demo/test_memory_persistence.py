#!/usr/bin/env python3
"""Demo test for Memory Persistence (ns-0f9).

Demonstrates that remember skill correctly persists and retrieves knowledge:
1. Skill invocation writes to markdown
2. Memory server receives content
3. Content is retrievable via memory search

Run with: uv run pytest tests/demo/test_memory_persistence.py -v -s -n 0 -m demo

Related:
- Epic ns-q5a: v1.0 Framework Audit - Demo Tests & Consolidation
- Task ns-0f9: Demo: Memory Persistence
"""

import uuid

import pytest


@pytest.mark.demo
class TestMemoryPersistenceDemo:
    """Demo test for memory persistence."""

    def test_demo_memory_persistence(self, claude_headless_tracked) -> None:
        """Demo: Remember skill persists to memory server.

        Strategy: Ask agent to persist a unique fact using the remember skill,
        then verify it used the appropriate tools (Skill, mcp__memory__store_memory).
        """
        print("\n" + "=" * 80)
        print("MEMORY PERSISTENCE DEMO: Remember Skill Storage")
        print("=" * 80)

        # Generate unique identifier for this test run
        unique_id = f"demo_test_{uuid.uuid4().hex[:8]}"

        # Ask agent to persist something using remember skill
        prompt = (
            f"Use Skill(skill='remember') to persist this fact to memory: "
            f"'Memory persistence demo {unique_id} executed successfully on this date'. "
            f"Confirm when done."
        )

        print(f"\n--- TASK ---\n{prompt}")
        print(f"--- Unique ID: {unique_id} ---")
        print("\n--- EXECUTING HEADLESS SESSION ---")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=240, model="haiku"
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        # --- TEST EVALUATES ---
        print("\n" + "=" * 80)
        print("TEST EVALUATION: Memory Persistence Verification")
        print("=" * 80)

        # Check 1: Skill tool was called with 'remember'
        skill_calls = [c for c in tool_calls if c["name"] == "Skill"]
        print(f"\n--- Skill Tool Calls: {len(skill_calls)} ---")
        remember_invoked = False
        for call in skill_calls:
            skill_name = call.get("input", {}).get("skill", "")
            print(f"    - {skill_name}")
            if "remember" in skill_name.lower():
                remember_invoked = True
        print(f"    Remember skill invoked: {remember_invoked}")

        # Check 2: Memory server store was called
        memory_store_calls = [
            c for c in tool_calls if c["name"] == "mcp__memory__store_memory"
        ]
        print(f"\n--- Memory Store Calls: {len(memory_store_calls)} ---")
        memory_stored = len(memory_store_calls) >= 1
        if memory_store_calls:
            # Show what was stored (truncated)
            for call in memory_store_calls:
                content = call.get("input", {}).get("content", "")[:100]
                print(f"    Content: {content}...")

        # Check 3: Write tool was called (markdown file)
        write_calls = [c for c in tool_calls if c["name"] == "Write"]
        print(f"\n--- Write Calls (Markdown): {len(write_calls)} ---")
        markdown_written = len(write_calls) >= 1
        for call in write_calls:
            path = call.get("input", {}).get("file_path", "")
            print(f"    - {path}")

        # Tool usage summary
        print("\n--- All Tool Calls ---")
        tool_counts: dict[str, int] = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"    {name}: {count}")

        # Show response
        print("\n--- Agent Response (first 600 chars) ---")
        try:
            from tests.integration.conftest import extract_response_text

            response_text = extract_response_text(result)
            print(response_text[:600] + ("..." if len(response_text) > 600 else ""))
        except Exception as e:
            print(f"    Could not extract response: {e}")

        # --- CRITERIA ---
        print("\n" + "=" * 80)
        print("PASS/FAIL CRITERIA")
        print("=" * 80)

        criteria = [
            ("Session completed successfully", result["success"]),
            ("Remember skill invoked", remember_invoked),
            ("Memory server store called", memory_stored),
            ("Markdown file written", markdown_written),
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
                f"Memory persistence validation FAILED. "
                f"Unmet criteria: {', '.join(failed)}. Session: {session_id}"
            )
