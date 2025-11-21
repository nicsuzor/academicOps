#!/usr/bin/env python3
"""
Tests for session logging functionality.

Verifies:
1. Session logger module functions correctly
2. Stop hook processes input and creates log files
3. Log files are created with correct naming format
4. Security: Date validation prevents path traversal
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_session_logger_module():
    """Test the session_logger module functions."""
    print("\n=== Testing session_logger module ===")

    # Add hooks directory to path
    repo_root = Path(__file__).parent.parent
    hooks_dir = repo_root / "hooks"
    sys.path.insert(0, str(hooks_dir))

    from session_logger import (
        create_session_note,
        extract_transcript_summary,
        get_log_path,
        get_session_short_hash,
        validate_date,
        write_session_log,
    )

    # Test 1: Short hash generation
    session_id = "test-session-123"
    short_hash = get_session_short_hash(session_id)
    assert len(short_hash) == 8, f"Expected 8 chars, got {len(short_hash)}"
    print(f"✓ Short hash generation: {short_hash}")

    # Test 2: Date validation
    assert validate_date("2025-11-09"), "Valid date should pass"
    assert not validate_date("../../../etc/passwd"), "Path traversal should fail"
    assert not validate_date("2025/11/09"), "Wrong separator should fail"
    assert not validate_date("20251109"), "No separators should fail"
    print("✓ Date validation working correctly")

    # Test 3: Log path generation
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        log_path = get_log_path(project_dir, session_id, "2025-11-09")
        expected_name = f"2025-11-09-{short_hash}.jsonl"
        assert log_path.name == expected_name, (
            f"Expected {expected_name}, got {log_path.name}"
        )
        assert log_path.parent == project_dir / "data" / "sessions"
        print(f"✓ Log path generation: {log_path.name}")

    # Test 4: Create session note
    summary = {
        "user_messages": 3,
        "assistant_messages": 5,
        "tools_used": ["Read", "Edit", "Bash"],
        "files_modified": ["/test/file.py"],
    }
    note = create_session_note(summary, session_id)
    assert "Short session" in note, f"Expected 'Short session' in note, got: {note}"
    assert "Read" in note or "Edit" in note, f"Expected tools in note, got: {note}"
    print(f"✓ Session note creation: {note}")

    # Test 5: Extract transcript summary
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        transcript_path = f.name
        f.write(
            json.dumps({"type": "message", "role": "user", "content": "Test"}) + "\n"
        )
        f.write(
            json.dumps({"type": "message", "role": "assistant", "content": "Response"})
            + "\n"
        )
        f.write(
            json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/test.py"}})
            + "\n"
        )

    try:
        summary = extract_transcript_summary(transcript_path)
        assert summary["user_messages"] == 1, (
            f"Expected 1 user message, got {summary['user_messages']}"
        )
        assert summary["assistant_messages"] == 1, (
            f"Expected 1 assistant message, got {summary['assistant_messages']}"
        )
        assert "Read" in summary["tools_used"], (
            f"Expected Read in tools_used, got {summary['tools_used']}"
        )
        print(f"✓ Transcript summary extraction: {summary}")
    finally:
        Path(transcript_path).unlink()

    # Test 6: Write session log
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        log_path = write_session_log(
            project_dir=project_dir,
            session_id=session_id,
            summary="Test session",
        )

        assert log_path.exists(), f"Log file not created at {log_path}"

        # Read and verify log content
        with log_path.open() as f:
            log_entry = json.loads(f.read())
            assert log_entry["session_id"] == session_id
            assert log_entry["summary"] == "Test session"
            assert "timestamp" in log_entry

        print(f"✓ Session log writing: {log_path.name}")

    print("✓ All session_logger module tests passed!")
    return True


def test_stop_hook():
    """Test the Stop hook script."""
    print("\n=== Testing Stop hook ===")

    repo_root = Path(__file__).parent.parent
    hook_script = repo_root / "hooks" / "log_session_stop.py"

    if not hook_script.exists():
        print(f"ERROR: Hook script not found at {hook_script}")
        return False

    # Create a temporary transcript
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        transcript_path = f.name
        f.write(
            json.dumps({"type": "message", "role": "user", "content": "Test"}) + "\n"
        )
        f.write(
            json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/test.py"}})
            + "\n"
        )

    try:
        # Create temporary project directory
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create hook input
            hook_input = {
                "session_id": "test-hook-session-456",
                "transcript_path": transcript_path,
                "cwd": str(project_dir),
                "hook_event_name": "Stop",
            }

            # Run the hook
            result = subprocess.run(
                ["python3", str(hook_script)],
                input=json.dumps(hook_input),
                capture_output=True,
                text=True,
                timeout=5,
                env={
                    **subprocess.os.environ,
                    "CLAUDE_PROJECT_DIR": str(project_dir),
                },
                check=False,
            )

            # Check exit code
            if result.returncode != 0:
                print(f"ERROR: Hook returned exit code {result.returncode}")
                print(f"STDERR: {result.stderr}")
                return False

            # Parse output (should be empty JSON for Stop hook)
            try:
                output = json.loads(result.stdout.strip())
                assert isinstance(output, dict), f"Expected dict, got {type(output)}"
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON output: {e}")
                print(f"OUTPUT: {result.stdout}")
                return False

            # Verify log file was created
            sessions_dir = project_dir / "data" / "sessions"
            log_files = list(sessions_dir.glob("*.jsonl"))

            if not log_files:
                print(f"ERROR: No log files created in {sessions_dir}")
                return False

            log_file = log_files[0]
            print(f"✓ Log file created: {log_file.name}")

            # Verify log content
            with log_file.open() as f:
                log_entry = json.loads(f.read())
                assert log_entry["session_id"] == "test-hook-session-456"
                assert "timestamp" in log_entry
                assert "summary" in log_entry

            print(f"✓ Log content valid: {log_entry['summary']}")

            print("✓ Stop hook test passed!")
            return True

    finally:
        Path(transcript_path).unlink()


def test_date_security():
    """Test that date validation prevents path traversal."""
    print("\n=== Testing date security ===")

    repo_root = Path(__file__).parent.parent
    hooks_dir = repo_root / "hooks"
    sys.path.insert(0, str(hooks_dir))

    from session_logger import get_log_path

    malicious_dates = [
        "../../../etc/passwd",
        "../../secrets",
        "2025-10-24/../../../etc",
        "2025/10/24",
        "20251024",
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        for bad_date in malicious_dates:
            try:
                get_log_path(project_dir, "test-session", bad_date)
                print(f"ERROR: Malicious date '{bad_date}' was not rejected!")
                return False
            except ValueError:
                # Expected - malicious date was rejected
                pass

    print("✓ All malicious dates were rejected")
    print("✓ Date security test passed!")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Session Logging")
    print("=" * 60)

    tests = [
        ("Session Logger Module", test_session_logger_module),
        ("Stop Hook", test_stop_hook),
        ("Date Security", test_date_security),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✓ {name} PASSED")
            else:
                failed += 1
                print(f"\n✗ {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n✗ {name} FAILED with exception: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
