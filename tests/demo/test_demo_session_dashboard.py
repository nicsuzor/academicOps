#!/usr/bin/env python3
"""Demo test for Session Dashboard State Extraction.

Demonstrates the complete workflow for extracting dashboard state from real
Claude session files stored in ~/.claude/projects/. This test walks through:

1. **Session Discovery**: Finding real session JSONL files from past Claude interactions
2. **Session Selection**: Choosing the most recent session for analysis
3. **State Extraction**: Using SessionAnalyzer to extract dashboard-relevant data
4. **Data Validation**: Verifying the extracted state has all required fields

This test uses REAL session data from your local Claude projects directory,
proving that the session analysis infrastructure works on actual production data
rather than synthetic fixtures.

Run with: uv run pytest tests/demo/test_demo_session_dashboard.py -v -s -n 0 -m demo

Related:
- SessionAnalyzer class in lib/session_analyzer.py
- Dashboard Streamlit app that consumes this data
"""

from pathlib import Path

import pytest
from lib.session_analyzer import SessionAnalyzer


@pytest.mark.demo
class TestSessionDashboardDemo:
    """Demo test for session dashboard state extraction workflow."""

    def test_demo_extract_dashboard_state_from_real_session(self) -> None:
        """Demo: Extract dashboard state from a real Claude session file.

        This demonstrates the complete workflow that the live dashboard uses
        to display session information. The test walks through each step with
        detailed output showing what's happening and what data is extracted.

        The dashboard state includes:
        - first_prompt: Truncated first user prompt (for display)
        - first_prompt_full: Complete first user prompt
        - last_prompt: Most recent user prompt
        - todos: Current todo list (if any)
        - memory_notes: Memory operations performed
        - in_progress_count: Number of in-progress todo items
        """
        print("\n" + "=" * 80)
        print("SESSION DASHBOARD DEMO: Real Session State Extraction")
        print("=" * 80)

        # === STEP 1: Discover Session Files ===
        print("\n--- STEP 1: Session Discovery ---")
        projects_dir = Path.home() / ".claude" / "projects"

        if not projects_dir.exists():
            pytest.skip(f"Claude projects directory not found: {projects_dir}")

        print(f"Scanning: {projects_dir}")
        session_files = list(projects_dir.rglob("*.jsonl"))

        # Filter out hook files (they have different format)
        session_files = [f for f in session_files if not f.name.endswith("-hooks.jsonl")]

        if not session_files:
            pytest.skip(f"No session files found in {projects_dir}")

        print(f"Found {len(session_files)} session file(s)")

        # === STEP 2: Select Most Recent Session ===
        print("\n--- STEP 2: Session Selection ---")
        session_path = max(session_files, key=lambda f: f.stat().st_mtime)

        # Show session metadata
        file_size = session_path.stat().st_size
        project_name = session_path.parent.name
        session_id = session_path.stem

        print(f"Selected: {session_path.name}")
        print(f"  Project: {project_name}")
        print(f"  Session ID: {session_id}")
        print(f"  Size: {file_size:,} bytes")

        # === STEP 3: Extract Dashboard State ===
        print("\n--- STEP 3: Dashboard State Extraction ---")
        print("Creating SessionAnalyzer instance...")
        analyzer = SessionAnalyzer()

        print(f"Extracting state from: {session_path}")
        result = analyzer.extract_dashboard_state(session_path)

        print("Extraction complete!")

        # === STEP 4: Validate and Display Results ===
        print("\n--- STEP 4: Results Validation ---")

        # Check return type
        assert isinstance(result, dict), "extract_dashboard_state() should return dict"
        print(f"Result type: {type(result).__name__} (OK)")

        # Validate all required keys are present
        required_keys = [
            "first_prompt",
            "first_prompt_full",
            "last_prompt",
            "todos",
            "memory_notes",
            "in_progress_count",
        ]

        print("\nRequired fields:")
        all_present = True
        for key in required_keys:
            present = key in result
            status = "PRESENT" if present else "MISSING"
            if not present:
                all_present = False
            print(f"  [{status}] {key}")

        assert all_present, "Missing required keys in result"

        # Validate types
        print("\nType validation:")
        type_checks = [
            ("first_prompt", str, result["first_prompt"]),
            ("first_prompt_full", str, result["first_prompt_full"]),
            ("last_prompt", str, result["last_prompt"]),
            ("memory_notes", list, result["memory_notes"]),
            ("in_progress_count", int, result["in_progress_count"]),
        ]

        for field, expected_type, value in type_checks:
            actual_type = type(value).__name__
            matches = isinstance(value, expected_type)
            status = "OK" if matches else "FAIL"
            print(f"  [{status}] {field}: {actual_type} (expected {expected_type.__name__})")
            assert matches, f"{field} has wrong type: {actual_type}"

        # todos can be None or list
        todos = result["todos"]
        todos_ok = todos is None or isinstance(todos, list)
        status = "OK" if todos_ok else "FAIL"
        print(f"  [{status}] todos: {type(todos).__name__} (expected None or list)")
        assert todos_ok, f"todos has wrong type: {type(todos)}"

        # === Display Extracted Content ===
        print("\n" + "=" * 80)
        print("EXTRACTED DASHBOARD STATE")
        print("=" * 80)

        # First prompt (truncated for display)
        print("\n📝 First Prompt (truncated):")
        print(
            f"   {result['first_prompt'][:100]}..."
            if len(result["first_prompt"]) > 100
            else f"   {result['first_prompt']}"
        )

        # Last prompt
        print("\n📝 Last Prompt:")
        last = result["last_prompt"]
        print(f"   {last[:100]}..." if len(last) > 100 else f"   {last}")

        # Todos
        print("\n📋 Todos:")
        if result["todos"]:
            for i, todo in enumerate(result["todos"][:5]):  # Show first 5
                status = todo.get("status", "unknown")
                content = todo.get("content", "")[:50]
                print(f"   [{status}] {content}...")
            if len(result["todos"]) > 5:
                print(f"   ... and {len(result['todos']) - 5} more")
        else:
            print("   (none)")

        print(f"\n📊 In-Progress Count: {result['in_progress_count']}")

        print(f"\n🧠 Memory Notes: {len(result['memory_notes'])} operation(s)")
        for note in result["memory_notes"][:3]:  # Show first 3
            print(f"   - {str(note)[:60]}...")

        # === Summary ===
        print("\n" + "=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        print(
            f"""
This demo showed the complete dashboard state extraction workflow:

1. DISCOVERY: Found {len(session_files)} session files in {projects_dir}
2. SELECTION: Chose most recent session from project '{project_name}'
3. EXTRACTION: SessionAnalyzer.extract_dashboard_state() parsed the JSONL
4. VALIDATION: All {len(required_keys)} required fields present with correct types

The extracted state is used by the Streamlit dashboard to display:
- Session overview (first/last prompts)
- Active todo items and progress
- Memory operations performed

This proves the session analysis pipeline works on REAL production data.
"""
        )
        print("=" * 80)
        print("PASS: Dashboard state extraction demo completed successfully")
        print("=" * 80)
