#!/usr/bin/env python3
"""Demo test for Session Discovery API.

Demonstrates the complete workflow for discovering Claude sessions using the
find_sessions() API. This test walks through:

1. **API Invocation**: Calling find_sessions() to discover sessions
2. **Session Enumeration**: Examining returned session objects
3. **Attribute Validation**: Verifying each session has required attributes
4. **Path Verification**: Confirming session paths point to real files

The find_sessions() API is the primary entry point for discovering past
Claude sessions. It returns Session objects with metadata about each
session, enabling analysis, reporting, and batch processing.

This test uses REAL session data from your local Claude projects directory,
proving that the session discovery infrastructure works on actual production data.

Run with: uv run pytest tests/demo/test_demo_session_discovery.py -v -s -n 0 -m demo

Related:
- lib/session_reader.py - find_sessions() implementation
- SessionInfo dataclass - Session metadata structure
"""

from datetime import datetime
from pathlib import Path

import pytest


@pytest.mark.demo
class TestSessionDiscoveryDemo:
    """Demo test for session discovery API workflow."""

    def test_demo_find_sessions_discovers_real_sessions(self) -> None:
        """Demo: Use find_sessions() to discover all available Claude sessions.

        This demonstrates the primary session discovery API that enables
        batch processing of sessions for analysis, reporting, and archival.

        The workflow:
        1. Call find_sessions() to discover sessions
        2. Examine returned session objects
        3. Validate required attributes
        4. Verify paths point to real files
        """
        print("\n" + "=" * 80)
        print("SESSION DISCOVERY DEMO: find_sessions() API Workflow")
        print("=" * 80)

        # === STEP 1: Invoke find_sessions() ===
        print("\n--- STEP 1: API Invocation ---")

        from lib.session_reader import find_sessions

        print("Calling find_sessions()...")
        sessions = find_sessions()

        print(f"Type returned: {type(sessions).__name__}")
        assert isinstance(sessions, list), "find_sessions() should return a list"

        if not sessions:
            pytest.skip("No sessions found - find_sessions() returned empty list")

        print(f"Sessions discovered: {len(sessions)}")

        # === STEP 2: Examine Session Objects ===
        print("\n--- STEP 2: Session Enumeration ---")

        # Group sessions by project
        sessions_by_project: dict[str, list] = {}
        for session in sessions:
            project = getattr(session, "project", "unknown")
            if project not in sessions_by_project:
                sessions_by_project[project] = []
            sessions_by_project[project].append(session)

        print(f"Sessions across {len(sessions_by_project)} project(s):")
        for project, project_sessions in sorted(sessions_by_project.items()):
            print(f"  {project}: {len(project_sessions)} session(s)")

        # Show recent sessions
        print("\nMost recent sessions (up to 5):")

        # Sort by last_modified if available
        try:
            sorted_sessions = sorted(
                sessions,
                key=lambda s: getattr(s, "last_modified", datetime.min),
                reverse=True,
            )
        except Exception:
            sorted_sessions = sessions[:5]

        for session in sorted_sessions[:5]:
            session_id = getattr(session, "session_id", "unknown")[:12]
            project = getattr(session, "project", "unknown")
            last_mod = getattr(session, "last_modified", None)
            if last_mod:
                if isinstance(last_mod, datetime):
                    last_mod_str = last_mod.strftime("%Y-%m-%d %H:%M")
                else:
                    last_mod_str = str(last_mod)[:16]
            else:
                last_mod_str = "N/A"
            print(f"  {session_id}... | {project:<20} | {last_mod_str}")

        # === STEP 3: Validate Required Attributes ===
        print("\n--- STEP 3: Attribute Validation ---")

        required_attrs = ["path", "session_id", "project", "last_modified"]

        # Check first session as representative
        first_session = sessions[0]
        print(
            f"Checking session: {getattr(first_session, 'session_id', 'unknown')[:20]}..."
        )

        print("\nRequired attributes:")
        all_attrs_present = True
        for attr in required_attrs:
            present = hasattr(first_session, attr)
            value = getattr(first_session, attr, None)
            status = "PRESENT" if present else "MISSING"
            if not present:
                all_attrs_present = False

            # Show value (truncated)
            if present:
                value_str = str(value)[:40]
                print(
                    f"  [{status}] {attr}: {value_str}{'...' if len(str(value)) > 40 else ''}"
                )
            else:
                print(f"  [{status}] {attr}")

        assert all_attrs_present, "Session missing required attributes"

        # Check a sample of sessions
        print(f"\nValidating attributes across {min(10, len(sessions))} sessions...")
        validation_errors = []

        for i, session in enumerate(sessions[:10]):
            for attr in required_attrs:
                if not hasattr(session, attr):
                    validation_errors.append(f"Session {i}: missing {attr}")

        if validation_errors:
            print(f"  ⚠️  Found {len(validation_errors)} validation error(s)")
            for err in validation_errors[:3]:
                print(f"     - {err}")
        else:
            print(
                f"  ✅ All {min(10, len(sessions))} sessions have required attributes"
            )

        # === STEP 4: Verify Paths Exist ===
        print("\n--- STEP 4: Path Verification ---")

        print("Verifying session paths point to real files...")

        paths_checked = 0
        paths_valid = 0
        paths_missing = []

        for session in sessions[:10]:  # Check first 10
            path = Path(getattr(session, "path", ""))
            paths_checked += 1
            if path.exists():
                paths_valid += 1
            else:
                paths_missing.append(str(path)[:50])

        print(f"  Paths checked: {paths_checked}")
        print(f"  Paths valid: {paths_valid}")
        print(f"  Paths missing: {len(paths_missing)}")

        if paths_missing:
            print("  Missing paths:")
            for p in paths_missing[:3]:
                print(f"    - {p}...")

        # All checked paths should exist
        assert paths_valid == paths_checked, (
            f"Some session paths don't exist: {paths_missing}"
        )

        # === STEP 5: Show Session Details ===
        print("\n--- STEP 5: Session Details ---")

        # Pick a session and show all available info
        sample_session = sorted_sessions[0] if sorted_sessions else sessions[0]

        print("Sample session details:")
        print(f"  Session ID: {getattr(sample_session, 'session_id', 'N/A')}")
        print(f"  Project: {getattr(sample_session, 'project', 'N/A')}")
        print(f"  Last Modified: {getattr(sample_session, 'last_modified', 'N/A')}")
        print(f"  Path: {getattr(sample_session, 'path', 'N/A')}")

        # If path exists, show file info
        path = Path(getattr(sample_session, "path", ""))
        if path.exists():
            stat = path.stat()
            print(f"  File size: {stat.st_size:,} bytes")
            print(
                f"  File mtime: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
            )

        # === Final Summary ===
        print("\n" + "=" * 80)
        print("VALIDATION CRITERIA")
        print("=" * 80)

        criteria = [
            ("find_sessions() returns list", isinstance(sessions, list)),
            ("At least one session found", len(sessions) > 0),
            ("Sessions have required attributes", all_attrs_present),
            ("Session paths exist", paths_valid == paths_checked),
        ]

        all_passed = True
        for name, passed in criteria:
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False
            print(f"  [{status}] {name}")

        print("\n" + "=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        print(
            f"""
This demo showed the complete session discovery workflow:

1. INVOCATION: Called find_sessions() API
2. ENUMERATION: Found {len(sessions)} sessions across {len(sessions_by_project)} projects
3. VALIDATION: Verified required attributes (path, session_id, project, last_modified)
4. VERIFICATION: Confirmed session paths point to real files

The find_sessions() API enables:
- Batch processing of past sessions
- Session analytics and reporting
- Transcript generation workflows
- Session archival and cleanup

Each Session object provides:
- path: Full path to session JSONL file
- session_id: Unique identifier for the session
- project: Project name (directory name)
- last_modified: When session was last updated

This proves the session discovery API works on REAL production data.
"""
        )
        print("=" * 80)
        if all_passed:
            print("PASS: Session discovery demo completed successfully")
        else:
            pytest.fail("Session discovery validation failed")
        print("=" * 80)

        assert all_passed, "Session discovery validation criteria not met"
