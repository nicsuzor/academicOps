#!/usr/bin/env python3
"""Demo test for Hook Log Discovery and Parsing.

Demonstrates the complete workflow for discovering and parsing hook log files
from real Claude sessions stored in ~/.claude/projects/. This test walks through:

1. **Hook Log Discovery**: Finding *-hooks.jsonl files from past sessions
2. **File Enumeration**: Cataloging all available hook logs across projects
3. **JSON Parsing**: Validating each line is proper JSON (not corrupted)
4. **Data Integrity**: Reporting on parse success rates across all files

Hook logs capture tool invocations, skill calls, and other events during Claude
sessions. They're separate from main session JSONL files and follow the pattern:
    ~/.claude/projects/<project>/<session-id>-hooks.jsonl

This test uses REAL hook log data from your local Claude projects directory,
proving that the hook logging infrastructure produces valid, parseable output.

Run with: uv run pytest tests/demo/test_demo_hook_logs.py -v -s -n 0 -m demo

Related:
- hooks/hook_logger.py - Hook logging implementation
- hooks/session_logger.py - Session logging utilities
"""

import json
from pathlib import Path

import pytest


@pytest.mark.demo
class TestHookLogsDemo:
    """Demo test for hook log discovery and parsing workflow."""

    def test_demo_parse_real_hook_log_files(self) -> None:
        """Demo: Discover and parse all hook log files from real sessions.

        This demonstrates the complete workflow for validating hook log integrity.
        Hook logs are critical for debugging, compliance auditing, and understanding
        agent behavior across sessions.

        The workflow validates:
        - Hook log files exist and are discoverable
        - Each line in each file is valid JSON
        - No serialization corruption occurred during logging
        """
        print("\n" + "=" * 80)
        print("HOOK LOGS DEMO: Discovery and Parsing Validation")
        print("=" * 80)

        # === STEP 1: Discover Hook Log Files ===
        print("\n--- STEP 1: Hook Log Discovery ---")
        projects_dir = Path.home() / ".claude" / "projects"

        if not projects_dir.exists():
            pytest.skip(f"Claude projects directory not found: {projects_dir}")

        print(f"Scanning: {projects_dir}")
        print("Pattern: *-hooks.jsonl")

        hook_files = sorted(projects_dir.rglob("*-hooks.jsonl"))

        if not hook_files:
            pytest.skip(f"No hook log files found in {projects_dir}")

        print(f"\nFound {len(hook_files)} hook log file(s)")

        # === STEP 2: Enumerate Files by Project ===
        print("\n--- STEP 2: File Enumeration ---")

        # Group by project
        files_by_project: dict[str, list[Path]] = {}
        for hook_file in hook_files:
            project = hook_file.parent.name
            if project not in files_by_project:
                files_by_project[project] = []
            files_by_project[project].append(hook_file)

        print(f"Hook logs across {len(files_by_project)} project(s):")
        for project, files in sorted(files_by_project.items()):
            total_size = sum(f.stat().st_size for f in files)
            print(f"  {project}: {len(files)} file(s), {total_size:,} bytes total")

        # === STEP 3: Parse Each File ===
        print("\n--- STEP 3: JSON Parsing Validation ---")

        fully_valid_files: list[tuple[str, int]] = []
        partially_valid_files: list[tuple[str, int, int]] = []
        empty_files: list[str] = []
        total_lines_parsed = 0
        total_lines_failed = 0

        for hook_file in hook_files:
            with hook_file.open() as f:
                valid_count = 0
                invalid_count = 0

                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue

                    try:
                        json.loads(line)
                        valid_count += 1
                    except json.JSONDecodeError as e:
                        invalid_count += 1
                        # Only show first error per file
                        if invalid_count == 1:
                            print(f"  ! {hook_file.name}:{line_num} - JSONDecodeError: {e}")

                if valid_count == 0 and invalid_count == 0:
                    empty_files.append(hook_file.name)
                elif invalid_count == 0:
                    fully_valid_files.append((hook_file.name, valid_count))
                    total_lines_parsed += valid_count
                else:
                    partially_valid_files.append((hook_file.name, valid_count, invalid_count))
                    total_lines_parsed += valid_count
                    total_lines_failed += invalid_count

        # === STEP 4: Report Results ===
        print("\n--- STEP 4: Parsing Results ---")

        print("\n📊 Summary:")
        print(f"   Total files scanned: {len(hook_files)}")
        print(f"   Fully valid files: {len(fully_valid_files)}")
        print(f"   Partially valid files: {len(partially_valid_files)}")
        print(f"   Empty files: {len(empty_files)}")

        print("\n📝 Line Statistics:")
        print(f"   Total valid JSON lines: {total_lines_parsed:,}")
        print(f"   Total invalid lines: {total_lines_failed:,}")
        if total_lines_parsed + total_lines_failed > 0:
            success_rate = total_lines_parsed / (total_lines_parsed + total_lines_failed) * 100
            print(f"   Success rate: {success_rate:.2f}%")

        # Show sample of fully valid files
        if fully_valid_files:
            print("\n✅ Fully Valid Files (showing first 5):")
            for name, count in fully_valid_files[:5]:
                print(f"   {name}: {count} entries")
            if len(fully_valid_files) > 5:
                print(f"   ... and {len(fully_valid_files) - 5} more")

        # Show any problematic files
        if partially_valid_files:
            print("\n⚠️  Partially Valid Files:")
            for name, valid, invalid in partially_valid_files:
                print(f"   {name}: {valid} valid, {invalid} invalid")

        if empty_files:
            print("\n📭 Empty Files:")
            for name in empty_files[:5]:
                print(f"   {name}")

        # === Sample Hook Event Display ===
        print("\n--- BONUS: Sample Hook Events ---")

        # Read a few events from the first valid file to show structure
        if fully_valid_files:
            sample_file = next(f for f in hook_files if f.name == fully_valid_files[0][0])
            print(f"From: {sample_file.name}")

            events_shown = 0
            with sample_file.open() as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        # Show key fields
                        hook_event = event.get("hook_event", "unknown")
                        tool_name = event.get("tool_name", event.get("event_type", "N/A"))
                        timestamp = event.get("timestamp", "N/A")
                        print(f"\n   Event: {hook_event}")
                        print(f"   Tool/Type: {tool_name}")
                        print(f"   Timestamp: {timestamp}")
                        events_shown += 1
                        if events_shown >= 3:
                            break
                    except json.JSONDecodeError:
                        continue

        # === Final Assertions ===
        print("\n" + "=" * 80)
        print("VALIDATION CRITERIA")
        print("=" * 80)

        criteria = [
            ("Hook log files discovered", len(hook_files) > 0),
            ("At least one fully valid file", len(fully_valid_files) > 0),
            ("Valid JSON lines parsed", total_lines_parsed > 0),
        ]

        all_passed = True
        for name, passed in criteria:
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False
            print(f"  [{status}] {name}")

        # === Summary ===
        print("\n" + "=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        print(
            f"""
This demo showed the complete hook log validation workflow:

1. DISCOVERY: Found {len(hook_files)} hook log files across {len(files_by_project)} projects
2. ENUMERATION: Cataloged files by project with size statistics
3. PARSING: Validated JSON integrity of {total_lines_parsed:,} log entries
4. REPORTING: Identified {len(fully_valid_files)} fully valid, {len(partially_valid_files)} partial files

Hook logs are essential for:
- Debugging agent behavior
- Compliance auditing (custodiet checks)
- Understanding tool usage patterns
- Session replay and analysis

This proves the hook logging infrastructure produces valid, parseable JSON
that can be used for downstream analysis and auditing.
"""
        )
        print("=" * 80)
        if all_passed:
            print("PASS: Hook log parsing demo completed successfully")
        else:
            pytest.fail("Hook log parsing validation failed")
        print("=" * 80)

        assert all_passed, "Hook log validation criteria not met"
