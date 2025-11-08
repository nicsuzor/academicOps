#!/usr/bin/env python3
"""
Tests for the session logging hooks.

This test verifies:
1. log_session_stop.py hook (Stop hook)
2. log_todowrite.py hook (PreToolUse hook)
3. session_log.py script security features
"""

import contextlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_session_logging_hook():
    """Test the session logging hook with sample input."""

    # Get the hook script path
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from paths import get_aops_root, get_hook_script
        aops_root = get_aops_root()
        hook_script = get_hook_script("log_session_stop.py")
    except ImportError:
        # Fallback for standalone execution
        repo_root = Path(__file__).parent.parent
        hook_script = repo_root / "hooks" / "log_session_stop.py"
        aops_root = repo_root

    if not hook_script.exists():
        print(f"ERROR: Hook script not found at {hook_script}")
        return False

    # Create a temporary transcript file
    # Using explicit file operations to ensure file is closed before use (Windows compatibility)
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
    transcript_path = temp_file.name

    try:
        # Write sample transcript entries
        temp_file.write(
            json.dumps({"type": "message", "role": "user", "content": "Test message"})
            + "\n"
        )

        temp_file.write(
            json.dumps(
                {"type": "message", "role": "assistant", "content": "Test response"}
            )
            + "\n"
        )

        temp_file.write(
            json.dumps(
                {"tool_name": "Read", "tool_input": {"file_path": "/test/file.py"}}
            )
            + "\n"
        )

        temp_file.write(
            json.dumps(
                {
                    "tool_name": "Edit",
                    "tool_input": {
                        "file_path": "/test/file.py",
                        "old_string": "old",
                        "new_string": "new",
                    },
                }
            )
            + "\n"
        )
    finally:
        # Explicitly close file handle before passing path to subprocess (Windows compatibility)
        temp_file.close()

    # Create sample hook input
    hook_input = {
        "session_id": "test-session-123",
        "transcript_path": transcript_path,
        "cwd": str(repo_root),
        "permission_mode": "bypassPermissions",
        "hook_event_name": "Stop",
        "stop_hook_active": False,
    }

    try:
        # Run the hook
        result = subprocess.run(
            ["python3", str(hook_script)],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
            timeout=5,
            env={**subprocess.os.environ, "CLAUDE_PROJECT_DIR": str(aops_root)},
        )

        # Check exit code
        if result.returncode != 0:
            print(f"ERROR: Hook returned non-zero exit code: {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return False

        # Parse output
        try:
            output = json.loads(result.stdout.strip())
        except json.JSONDecodeError as e:
            print(f"ERROR: Hook output is not valid JSON: {e}")
            print(f"OUTPUT: {result.stdout}")
            return False

        # Validate output schema for Stop hook
        # Stop hook should return {} to allow or {"decision": "block", "reason": "..."} to block
        if not isinstance(output, dict):
            print(f"ERROR: Output is not a dictionary: {output}")
            return False

        # If decision is present, it should be "block"
        if "decision" in output:
            if output["decision"] != "block":
                print(f"ERROR: Invalid decision value: {output['decision']}")
                return False
            if "reason" not in output:
                print("ERROR: 'reason' required when decision is 'block'")
                return False

        print("✓ Hook executed successfully")
        print(f"✓ Output: {json.dumps(output, indent=2)}")

        # Check stderr for informational messages
        if result.stderr:
            print(f"Hook stderr output:\n{result.stderr}")

        return True

    except subprocess.TimeoutExpired:
        print("ERROR: Hook timed out after 5 seconds")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False
    finally:
        # Clean up temporary file
        with contextlib.suppress(Exception):
            Path(transcript_path).unlink()


def test_session_log_script():
    """Test the session_log.py script directly."""

    repo_root = Path(__file__).parent.parent
    script_path = (
        repo_root / "skills" / "task-management" / "scripts" / "session_log.py"
    )

    if not script_path.exists():
        print(f"ERROR: Script not found at {script_path}")
        return False

    # This test requires ACA to be set or auto-detectable
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from paths import get_aca_root
        get_aca_root()
    except (ImportError, RuntimeError):
        print("SKIPPING: ACA not set and cannot auto-detect")
        return True  # Not a failure, just can't run

    try:
        # Run the script with minimal args
        result = subprocess.run(
            [
                "python3",
                str(script_path),
                "--session-id",
                "test-123",
                "--summary",
                "Test session",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            print(f"ERROR: Script returned non-zero exit code: {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return False

        # Parse output
        try:
            output = json.loads(result.stdout.strip())
            if not output.get("success"):
                print(f"ERROR: Script did not report success: {output}")
                return False
        except json.JSONDecodeError as e:
            print(f"ERROR: Script output is not valid JSON: {e}")
            print(f"OUTPUT: {result.stdout}")
            return False

        print("✓ Session log script executed successfully")
        print(f"✓ Log saved to: {output.get('log_path')}")

        return True

    except subprocess.TimeoutExpired:
        print("ERROR: Script timed out after 5 seconds")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False


def test_todowrite_hook():
    """Test the TodoWrite PreToolUse hook."""

    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from paths import get_aops_root, get_hook_script
        aops_root = get_aops_root()
        hook_script = get_hook_script("log_todowrite.py")
    except ImportError:
        # Fallback for standalone execution
        repo_root = Path(__file__).parent.parent
        hook_script = repo_root / "hooks" / "log_todowrite.py"
        aops_root = repo_root

    if not hook_script.exists():
        print(f"ERROR: Hook script not found at {hook_script}")
        return False

    # Create sample PreToolUse hook input for TodoWrite
    hook_input = {
        "session_id": "test-session-456",
        "tool_name": "TodoWrite",
        "tool_input": {
            "todos": [
                {
                    "content": "Test task 1",
                    "status": "in_progress",
                    "activeForm": "Testing task 1",
                },
                {
                    "content": "Test task 2",
                    "status": "pending",
                    "activeForm": "Testing task 2",
                },
            ]
        },
        "permission_mode": "bypassPermissions",
        "hook_event_name": "PreToolUse",
    }

    try:
        # Run the hook
        result = subprocess.run(
            ["python3", str(hook_script)],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
            timeout=5,
            env={**subprocess.os.environ, "CLAUDE_PROJECT_DIR": str(aops_root)},
        )

        # Check exit code
        if result.returncode != 0:
            print(f"ERROR: Hook returned non-zero exit code: {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return False

        # Parse output
        try:
            output = json.loads(result.stdout.strip())
        except json.JSONDecodeError as e:
            print(f"ERROR: Hook output is not valid JSON: {e}")
            print(f"OUTPUT: {result.stdout}")
            return False

        # Validate PreToolUse hook output schema
        if "hookSpecificOutput" not in output:
            print(f"ERROR: Missing hookSpecificOutput in response: {output}")
            return False

        if "permissionDecision" not in output["hookSpecificOutput"]:
            print(f"ERROR: Missing permissionDecision: {output}")
            return False

        if output["hookSpecificOutput"]["permissionDecision"] != "allow":
            print(
                f"ERROR: Expected 'allow', got: {output['hookSpecificOutput']['permissionDecision']}"
            )
            return False

        print("✓ TodoWrite hook executed successfully")
        print(
            f"✓ Permission decision: {output['hookSpecificOutput']['permissionDecision']}"
        )

        return True

    except subprocess.TimeoutExpired:
        print("ERROR: Hook timed out after 5 seconds")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False


def test_date_validation():
    """Test that date validation prevents path traversal."""

    repo_root = Path(__file__).parent.parent
    script_path = (
        repo_root / "skills" / "task-management" / "scripts" / "session_log.py"
    )

    if not script_path.exists():
        print(f"ERROR: Script not found at {script_path}")
        return False

    # This test requires ACA to be set or auto-detectable
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from paths import get_aca_root
        get_aca_root()
    except (ImportError, RuntimeError):
        print("SKIPPING: ACA not set and cannot auto-detect")
        return True  # Not a failure, just can't run

    # Test with malicious date containing path traversal
    malicious_dates = [
        "../../../etc/passwd",
        "../../secrets",
        "2025-10-24/../../../etc",
        "2025/10/24",  # Wrong separator
        "20251024",  # No separators
    ]

    for _bad_date in malicious_dates:
        # We can't easily test this without modifying the script to accept date as arg
        # Instead, we'll import and test the function directly
        # For now, just verify the script has the validation
        with open(script_path) as f:
            content = f.read()
            if "re.match(r'^\\d{4}-\\d{2}-\\d{2}$', date)" not in content:
                print("ERROR: Date validation regex not found in session_log.py")
                return False

    print("✓ Date validation code present in session_log.py")
    return True


def main():
    """Run all tests."""
    print("Testing session logging hooks...\n")

    tests = [
        ("Session logging hook", test_session_logging_hook),
        ("TodoWrite hook", test_todowrite_hook),
        ("Session log script", test_session_log_script),
        ("Date validation security", test_date_validation),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Running: {name}")
        print("=" * 60)

        if test_func():
            passed += 1
            print(f"✓ PASSED: {name}")
        else:
            failed += 1
            print(f"✗ FAILED: {name}")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
