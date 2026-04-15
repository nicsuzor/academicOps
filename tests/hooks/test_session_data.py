import json
import os
import subprocess
import sys
from pathlib import Path

from hooks.router import get_parent_pid, get_session_data


def test_get_parent_pid():
    """Test that get_parent_pid works across platforms (including macOS fallback)."""

    # Test 1: Our own process should resolve to our parent's PID
    my_pid = os.getpid()
    parent_pid = os.getppid()

    assert get_parent_pid(my_pid) == parent_pid

    # Test 2: Spawn a subprocess and verify its parent is us
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1)"])
    try:
        assert get_parent_pid(process.pid) == my_pid
    finally:
        process.kill()
        process.wait()


def test_get_session_data_finds_file(monkeypatch, tmp_path):
    """Test that get_session_data climbs the process tree to find the JSON file."""

    # Write a mock session file for our own PID's parent (since get_session_data looks at parents)
    parent_pid = os.getppid()
    session_file = tmp_path / f"session-{parent_pid}.json"
    test_data = {"session_id": "test-session-123", "subagent_type": "aops-core:test"}
    session_file.write_text(json.dumps(test_data))

    # Patch get_pid_session_map_path to return our file so the fast path works
    monkeypatch.setattr("hooks.router.get_pid_session_map_path", lambda: session_file)

    # Test that it finds it
    data = get_session_data()
    assert data == test_data

    # Test fallback traversal
    # It should traverse up from 9999999 -> 8888888 -> parent_pid and find the file

    def mock_get_parent_pid(pid):
        if pid == 9999999:
            return 8888888
        if pid == 8888888:
            return parent_pid
        return None

    monkeypatch.setattr("os.getppid", lambda: 9999999)
    monkeypatch.setattr("hooks.router.get_parent_pid", mock_get_parent_pid)

    # We must patch Path inside hooks.router to redirect the fallback `/tmp` searches to tmp_path
    class MockPath:
        def __init__(self, *args):
            # If they ask for /tmp, redirect to tmp_path
            if str(args[0]) == "/tmp":
                self.base = tmp_path
            else:
                self.base = Path(*args)

        def __truediv__(self, other):
            return self.base / other

    monkeypatch.setattr("hooks.router.Path", MockPath)

    # also disable get_pid_session_map_path so it falls through to traversal
    monkeypatch.setattr(
        "hooks.router.get_pid_session_map_path", lambda: tmp_path / "nonexistent.json"
    )

    child_data = get_session_data()
    assert child_data == test_data
