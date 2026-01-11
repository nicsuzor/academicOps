#!/usr/bin/env python3
"""Demo test for the Core Pipeline (ns-t15).

Demonstrates that the full prompt hydration pipeline works end-to-end:
1. User prompt submitted
2. Hydrator agent invoked with context
3. Workflow selected based on intent
4. TodoWrite plan created with skill assignments
5. Execution follows plan

Run with: uv run pytest tests/demo/test_core_pipeline.py -v -s -n 0 -m demo

Related:
- Epic ns-q5a: v1.0 Framework Audit - Demo Tests & Consolidation
- Task ns-t15: Demo: Core Pipeline (Hydration → Workflow → Execution)
"""

import uuid

import pytest


@pytest.mark.demo
class TestCorePipelineDemo:
    """Demo test for the core prompt hydration pipeline."""

    def test_demo_core_pipeline_hydration_to_execution(
        self, claude_headless_tracked
    ) -> None:
        """Demo: Prompt hydration produces executable plan that completes.

        Strategy: Give agent a straightforward Python task that should trigger:
        1. Prompt hydrator (Task with subagent_type=prompt-hydrator)
        2. TodoWrite with structured plan
        3. python-dev skill invocation
        4. Code written to a file

        The test verifies each stage of the pipeline fired.
        """
        print("\n" + "=" * 80)
        print("CORE PIPELINE DEMO: Hydration → Workflow → Execution")
        print("=" * 80)

        # Generate unique file path to avoid conflicts between parallel test runs
        test_id = uuid.uuid4().hex[:8]
        output_file = f"/tmp/claude-test/math_utils_{test_id}.py"

        # Task that should trigger the full pipeline:
        # - Hydrator classifies as "implementation" workflow
        # - TodoWrite plan created
        # - python-dev skill invoked (or appropriate skill)
        # - Code actually written
        prompt = (
            "Create a simple Python function called 'add_numbers' that takes two "
            f"integers and returns their sum. Save it to {output_file}"
        )

        print(f"\n--- TASK ---\n{prompt}")
        print(f"--- Output file: {output_file} ---")
        print("\n--- EXECUTING HEADLESS SESSION ---")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=180, model="haiku"
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        # --- TEST EVALUATES (not the agent) ---
        print("\n" + "=" * 80)
        print("TEST EVALUATION: Pipeline Stage Verification")
        print("=" * 80)

        # Count tool types
        tool_counts: dict[str, int] = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1

        print("\n--- Tool Calls Summary ---")
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"  {name}: {count}")

        # Stage 1: Hydrator invocation
        hydrator_calls = [
            c
            for c in tool_calls
            if c["name"] == "Task"
            and c.get("input", {}).get("subagent_type") == "prompt-hydrator"
        ]
        print(f"\n--- Stage 1: Hydrator Invocations: {len(hydrator_calls)} ---")
        hydrator_invoked = len(hydrator_calls) >= 1

        # Stage 2: TodoWrite plan created
        todowrite_calls = [c for c in tool_calls if c["name"] == "TodoWrite"]
        print(f"--- Stage 2: TodoWrite Calls: {len(todowrite_calls)} ---")
        if todowrite_calls:
            # Show first TodoWrite content (truncated)
            first_todo = todowrite_calls[0].get("input", {})
            todos = first_todo.get("todos", [])
            print(f"    Plan items: {len(todos)}")
            for i, todo in enumerate(todos[:3]):  # Show first 3
                content = todo.get("content", "")[:60]
                print(f"    [{i+1}] {content}...")
        todowrite_used = len(todowrite_calls) >= 1

        # Stage 3: Skill invocation (python-dev or framework)
        skill_calls = [c for c in tool_calls if c["name"] == "Skill"]
        print(f"--- Stage 3: Skill Invocations: {len(skill_calls)} ---")
        for call in skill_calls:
            skill_name = call.get("input", {}).get("skill", "unknown")
            print(f"    - {skill_name}")
        # For this task, python-dev should be invoked
        python_dev_invoked = any(
            "python" in call.get("input", {}).get("skill", "").lower()
            for call in skill_calls
        )

        # Stage 4: Code written (Write tool used)
        write_calls = [c for c in tool_calls if c["name"] == "Write"]
        print(f"--- Stage 4: Write Calls: {len(write_calls)} ---")
        for call in write_calls:
            path = call.get("input", {}).get("file_path", "unknown")
            print(f"    - {path}")
        code_written = len(write_calls) >= 1

        # --- CRITERIA ---
        print("\n" + "=" * 80)
        print("PASS/FAIL CRITERIA")
        print("=" * 80)

        criteria = [
            ("Session completed successfully", result["success"]),
            ("Stage 1: Hydrator agent invoked", hydrator_invoked),
            ("Stage 2: TodoWrite plan created", todowrite_used),
            ("Stage 3: python-dev skill invoked", python_dev_invoked),
            ("Stage 4: Code written via Write tool", code_written),
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

        # Show response excerpt for human validation
        print("\n--- Agent Response (first 500 chars) ---")
        try:
            from tests.integration.conftest import extract_response_text

            response_text = extract_response_text(result)
            print(response_text[:500] + ("..." if len(response_text) > 500 else ""))
        except Exception as e:
            print(f"Could not extract: {e}")

        if not all_passed:
            failed = [name for name, passed in criteria if not passed]
            pytest.fail(
                f"Core pipeline validation FAILED. "
                f"Unmet criteria: {', '.join(failed)}. Session: {session_id}"
            )
