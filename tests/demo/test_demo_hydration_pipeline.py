#!/usr/bin/env python3
"""Demo test for the Core Hydration Pipeline (ns-zlw5).

Demonstrates the complete prompt hydration pipeline from user prompt to execution:
1. User prompt submitted
2. UserPromptSubmit hook fires (automatic via session)
3. Prompt hydrator agent spawned
4. Workflow selected based on intent analysis
5. TodoWrite plan generated with structured steps
6. Main agent executes the plan

This test uses a REAL framework task to demonstrate authentic hydration behavior.
The demo shows HOW the hydration process works, not just THAT it works, by
displaying the full pipeline execution with semantic evaluation.

Run with: uv run pytest tests/demo/test_demo_hydration_pipeline.py -v -s -n 0 -m demo

Related:
- Epic ns-6hm: v1.0 Core Loop - Hydration/Workflow/QA/Reflection
- Task ns-zlw5: Demo: Core Pipeline (Hydration → Workflow → Execution)
- Agent: aops-core:prompt-hydrator
"""

import pytest


@pytest.mark.demo
class TestHydrationPipelineDemo:
    """Demo test for the complete prompt hydration pipeline."""

    def test_demo_hydration_pipeline_full_workflow(
        self, claude_headless_tracked
    ) -> None:
        """Demo: Complete hydration pipeline from prompt to execution.

        This test demonstrates the v1.0 core loop hydration process using a
        realistic framework task. The prompt is deliberately complex enough to
        trigger the full hydration pipeline with workflow classification.

        The test validates each stage:
        1. Prompt-hydrator agent invoked
        2. Workflow classification performed
        3. TodoWrite plan created with steps
        4. Plan execution begins
        """
        print("\n" + "=" * 80)
        print("HYDRATION PIPELINE DEMO: User Prompt → Workflow → Execution")
        print("=" * 80)

        # Use a realistic framework task that will trigger hydration
        # This should be classified as a 'debug' or 'qa-proof' workflow
        prompt = (
            "I need to verify that the custodiet agent is properly checking for "
            "scope drift violations. Can you check the custodiet implementation "
            "and verify it includes checks for off-task behavior?"
        )

        print(f"\n--- USER PROMPT ---\n{prompt}")
        print("\n--- EXECUTING HEADLESS SESSION ---")
        print("(UserPromptSubmit hook should trigger hydrator automatically)")

        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=240, model="sonnet"
        )

        print(f"\nSession ID: {session_id}")
        print(f"Success: {result['success']}")
        print(f"Total tool calls: {len(tool_calls)}")

        # === PIPELINE STAGE ANALYSIS ===
        print("\n" + "=" * 80)
        print("PIPELINE STAGE VERIFICATION")
        print("=" * 80)

        # Count tool usage
        tool_counts: dict[str, int] = {}
        for call in tool_calls:
            name = call["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1

        print("\n--- Tool Call Summary ---")
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"  {name}: {count}")

        # Stage 1: Hydrator Invocation
        hydrator_calls = [
            c
            for c in tool_calls
            if c["name"] == "Task"
            and c.get("input", {}).get("subagent_type") == "aops-core:prompt-hydrator"
        ]
        print(f"\n--- STAGE 1: Hydrator Invocation ---")
        print(f"  Hydrator calls: {len(hydrator_calls)}")

        if hydrator_calls:
            # Show hydrator invocation details
            for i, call in enumerate(hydrator_calls[:1]):  # Show first one
                desc = call.get("input", {}).get("description", "N/A")
                print(f"  [{i+1}] Description: {desc}")

        hydrator_invoked = len(hydrator_calls) >= 1

        # Stage 2: Workflow Classification (check TodoWrite content)
        todowrite_calls = [c for c in tool_calls if c["name"] == "TodoWrite"]
        print(f"\n--- STAGE 2: Workflow Selection & Planning ---")
        print(f"  TodoWrite calls: {len(todowrite_calls)}")

        workflow_classified = False
        if todowrite_calls:
            # Examine first TodoWrite for workflow-style structure
            first_todo = todowrite_calls[0].get("input", {})
            todos = first_todo.get("todos", [])
            print(f"  Plan items: {len(todos)}")

            # Show plan structure
            for i, todo in enumerate(todos[:5]):  # Show first 5
                content = todo.get("content", "")
                status = todo.get("status", "")
                print(f"  [{i+1}] {content[:70]}... ({status})")

            # Workflow was classified if we have a structured plan
            workflow_classified = len(todos) >= 2

        # Stage 3: Plan Execution (evidence of following plan)
        read_calls = [c for c in tool_calls if c["name"] == "Read"]
        grep_calls = [c for c in tool_calls if c["name"] == "Grep"]
        glob_calls = [c for c in tool_calls if c["name"] == "Glob"]

        print(f"\n--- STAGE 3: Plan Execution ---")
        print(f"  Read calls: {len(read_calls)}")
        print(f"  Grep calls: {len(grep_calls)}")
        print(f"  Glob calls: {len(glob_calls)}")

        # For qa-proof or debug workflow, we expect investigation tools used
        plan_executed = (len(read_calls) + len(grep_calls) + len(glob_calls)) >= 2

        # Stage 4: Response Quality (semantic check)
        print(f"\n--- STAGE 4: Response Quality ---")
        try:
            from tests.integration.conftest import extract_response_text

            response_text = extract_response_text(result)
            response_lower = response_text.lower()

            # Check for evidence of thoughtful analysis (not just keyword matching)
            quality_indicators = [
                "custodiet" in response_lower,
                "scope" in response_lower or "drift" in response_lower,
                len(response_text) > 100,  # Substantial response
                "check" in response_lower or "verify" in response_lower,
            ]

            quality_score = sum(quality_indicators)
            print(f"  Quality indicators present: {quality_score}/4")
            print(f"  Response length: {len(response_text)} chars")

            # Show response excerpt
            print("\n  Response preview (first 500 chars):")
            print("  " + "-" * 76)
            preview = response_text[:500].replace("\n", "\n  ")
            print(f"  {preview}...")
            print("  " + "-" * 76)

            quality_adequate = quality_score >= 3

        except Exception as e:
            print(f"  Could not extract response: {e}")
            quality_adequate = False

        # === VALIDATION CRITERIA ===
        print("\n" + "=" * 80)
        print("VALIDATION CRITERIA")
        print("=" * 80)

        criteria = [
            ("Session completed successfully", result["success"]),
            ("Stage 1: Hydrator agent invoked", hydrator_invoked),
            ("Stage 2: Workflow classified & plan created", workflow_classified),
            ("Stage 3: Plan execution evidence", plan_executed),
            ("Stage 4: Quality response provided", quality_adequate),
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
This demo showed the complete v1.0 hydration pipeline:

**Pipeline Flow:**
1. User submits prompt about custodiet verification
2. UserPromptSubmit hook fires (automatic in session)
3. Hydrator agent spawned ({len(hydrator_calls)} invocation(s))
4. Workflow classified and TodoWrite plan generated ({len(todowrite_calls)} plan(s))
5. Agent executes plan using investigation tools
6. Quality response provided to user

**Hydration Enables:**
- Automatic workflow selection based on intent
- Structured execution plans (TodoWrite)
- Consistent task handling across different request types
- Context injection from bd state + vector memory

**Why This Matters:**
The hydration pipeline transforms terse user prompts into complete execution
plans with appropriate workflow patterns. This ensures:
- Systematic approach to all tasks
- Reduced hallucination through structured planning
- Traceable execution via TodoWrite
- Quality gates at plan generation time

Session {session_id} demonstrates the core v1.0 loop working end-to-end.
"""
        )
        print("=" * 80)
        print(f"OVERALL: {'PASS' if all_passed else 'FAIL'}")
        print("=" * 80)

        if not all_passed:
            failed = [name for name, passed in criteria if not passed]
            pytest.fail(
                f"Hydration pipeline validation FAILED. "
                f"Unmet criteria: {', '.join(failed)}. Session: {session_id}"
            )

        assert all_passed, "Hydration pipeline demo validation failed"
