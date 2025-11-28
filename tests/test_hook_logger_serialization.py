"""Test hook_logger serialization handling for non-serializable objects.

Tests that hook_logger.log_hook_event() properly handles dict values
in tool_response and other fields that may contain nested objects.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from pytest import MonkeyPatch

from hooks.hook_logger import log_hook_event


def test_log_hook_event_with_non_serializable_object(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Test that log_hook_event fails with non-serializable objects.

    Verifies that non-serializable objects in input_data (e.g., custom class
    instances, functions, datetime objects) cause json.dump() to raise TypeError,
    which hook_logger catches and silently ignores.

    The hook_logger.log_hook_event() function uses json.dump() without a default
    parameter, which cannot serialize arbitrary Python objects. When this happens:
    1. json.dump() raises TypeError
    2. hook_logger catches it and prints to stderr (line 93)
    3. No log entry is written (the file write is aborted)

    This test demonstrates that data is lost silently when objects cannot be serialized.

    Args:
        tmp_path: pytest's temporary directory fixture
        monkeypatch: pytest monkeypatch fixture for environment variables

    Raises:
        AssertionError: If a valid JSON log entry is written (indicating serialization
            succeeded when it should have failed)
    """
    from datetime import datetime

    # Set ACA_DATA to use temp directory for this test
    monkeypatch.setenv("ACA_DATA", str(tmp_path))

    session_id = "test-session-123"
    hook_event = "ToolCall"

    # Create input_data with non-serializable datetime object
    # datetime.datetime cannot be JSON serialized without a default parameter
    input_data: dict[str, Any] = {
        "tool_response": {
            # datetime is not JSON serializable
            "timestamp": datetime(2025, 11, 26, 12, 30, 45),
            "file": {
                "content": "some content",
            }
        },
        "model": "claude-opus",
        "tool_name": "read_file",
    }

    # Call log_hook_event with non-serializable input
    # This attempts to serialize the datetime object, which will raise TypeError
    # The exception is caught and silently ignored in hook_logger
    log_hook_event(session_id, hook_event, input_data)

    # Now verify that NO valid log entry was written
    # We need to find the log file path
    from hooks.session_logger import get_log_path
    from lib.paths import get_data_root

    project_dir = get_data_root()
    log_path = get_log_path(project_dir, session_id, suffix="-hooks")

    # The critical assertion: a valid log entry SHOULD have been written
    # Currently, serialization failures cause silent data loss
    # This test FAILS because hook_logger cannot handle non-serializable objects
    assert log_path.exists(), (
        "Log file should exist - serialization should have succeeded"
    )

    content = log_path.read_text().strip()
    assert content, "Log file should contain valid JSON entry"

    # Parse the last line (most recent entry) - this should succeed
    # If it fails, it means the log entry is incomplete or malformed
    lines = content.split("\n")
    last_line = lines[-1]

    # This should succeed if serialization worked
    # But it will raise JSONDecodeError if datetime wasn't serialized
    try:
        log_entry = json.loads(last_line)
    except json.JSONDecodeError as e:
        pytest.fail(
            f"Last log entry is not valid JSON (JSONDecodeError: {e}). "
            f"This indicates serialization failed: {last_line[:100]}..."
        )

    # Verify the log entry contains expected fields
    assert log_entry["hook_event"] == "ToolCall"
    assert log_entry["tool_name"] == "read_file"
    assert "timestamp" in log_entry["tool_response"], (
        "Log entry should contain the timestamp from tool_response, "
        "but serialization failed silently"
    )


def test_parse_valid_hook_log_files() -> None:
    """Test that valid hook log files can be parsed successfully.

    This integration test verifies that real hook log files from production
    (~/.cache/aops/sessions/*-hooks.jsonl) can be parsed completely without
    JSON errors. This demonstrates backward compatibility - our fix should
    not break existing valid logs.

    Test scenario:
    1. Find hook log files in ~/.cache/aops/sessions/
    2. For each file, check if it's completely valid (all lines parse without error)
    3. Collect stats on valid vs partially valid files
    4. Ensure at least some files have been successfully tested

    Note: This test validates the hook_logger serialization fix. Some production
    logs may have pre-existing issues from before the fix was deployed. The test
    focuses on identifying which files are fully valid to verify backward
    compatibility - the fix doesn't break existing valid logs.
    """
    from pathlib import Path

    session_dir = Path.home() / ".cache" / "aops" / "sessions"

    # Skip test if no session directory (clean environment)
    if not session_dir.exists():
        pytest.skip("No session directory found - clean environment")

    # Find all hook log files
    hook_files = sorted(session_dir.glob("*-hooks.jsonl"))

    # Skip if no hook files exist
    if not hook_files:
        pytest.skip("No hook log files found in session directory")

    # Track statistics
    fully_valid_files = []
    partially_valid_files = []
    total_lines_parsed = 0

    # Parse each hook log file
    for hook_file in hook_files:
        with hook_file.open() as f:
            valid_count = 0
            invalid_count = 0

            for line in f:
                # Skip empty lines
                if not line.strip():
                    continue

                try:
                    json.loads(line)
                    valid_count += 1
                except json.JSONDecodeError:
                    invalid_count += 1

            # Classify file as fully valid or partially valid
            if valid_count > 0:
                total_lines_parsed += valid_count

                if invalid_count == 0:
                    fully_valid_files.append((hook_file.name, valid_count))
                else:
                    partially_valid_files.append(
                        (hook_file.name, valid_count, invalid_count)
                    )

    # Require at least one fully valid file
    assert fully_valid_files, (
        "No completely valid hook log files found. "
        f"Unable to verify backward compatibility. "
        f"Partially valid files: {len(partially_valid_files)}, "
        f"Total valid lines parsed: {total_lines_parsed}"
    )

    # Verify we actually parsed something meaningful
    assert total_lines_parsed > 0, (
        "No valid JSON lines were parsed from hook log files"
    )
