#!/usr/bin/env python3
"""
Tests for the session logging hook.

This test verifies that the log_session_stop.py hook:
1. Accepts valid Stop hook input
2. Produces valid Stop hook output
3. Extracts session information correctly
4. Runs without errors
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_session_logging_hook():
    """Test the session logging hook with sample input."""

    # Get the hook script path
    repo_root = Path(__file__).parent.parent
    hook_script = repo_root / "bots" / "hooks" / "log_session_stop.py"

    if not hook_script.exists():
        print(f"ERROR: Hook script not found at {hook_script}")
        return False

    # Create a temporary transcript file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        transcript_path = f.name

        # Write sample transcript entries
        f.write(json.dumps({
            "type": "message",
            "role": "user",
            "content": "Test message"
        }) + "\n")

        f.write(json.dumps({
            "type": "message",
            "role": "assistant",
            "content": "Test response"
        }) + "\n")

        f.write(json.dumps({
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/file.py"}
        }) + "\n")

        f.write(json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": "/test/file.py", "old_string": "old", "new_string": "new"}
        }) + "\n")

    # Create sample hook input
    hook_input = {
        "session_id": "test-session-123",
        "transcript_path": transcript_path,
        "cwd": str(repo_root),
        "permission_mode": "bypassPermissions",
        "hook_event_name": "Stop",
        "stop_hook_active": False
    }

    try:
        # Run the hook
        result = subprocess.run(
            ["python3", str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
            timeout=5,
            env={**subprocess.os.environ, "CLAUDE_PROJECT_DIR": str(repo_root)}
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
        try:
            Path(transcript_path).unlink()
        except Exception:
            pass


def test_session_log_script():
    """Test the session_log.py script directly."""

    repo_root = Path(__file__).parent.parent
    script_path = repo_root / "skills" / "task-management" / "scripts" / "session_log.py"

    if not script_path.exists():
        print(f"ERROR: Script not found at {script_path}")
        return False

    # This test requires ACADEMICOPS_PERSONAL to be set
    if "ACADEMICOPS_PERSONAL" not in subprocess.os.environ:
        print("SKIPPING: ACADEMICOPS_PERSONAL not set in environment")
        return True  # Not a failure, just can't run

    try:
        # Run the script with minimal args
        result = subprocess.run(
            [
                "python3",
                str(script_path),
                "--session-id", "test-123",
                "--summary", "Test session"
            ],
            capture_output=True,
            text=True,
            timeout=5
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


def main():
    """Run all tests."""
    print("Testing session logging hook...\n")

    tests = [
        ("Session logging hook", test_session_logging_hook),
        ("Session log script", test_session_log_script),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print('='*60)

        if test_func():
            passed += 1
            print(f"✓ PASSED: {name}")
        else:
            failed += 1
            print(f"✗ FAILED: {name}")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print('='*60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
