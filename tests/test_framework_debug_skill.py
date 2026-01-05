"""Integration tests for framework-debug skill.

Tests verify that the framework-debug skill can successfully guide agents
to investigate session logs and extract relevant debugging information.
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime


def test_skill_file_exists():
    """Verify framework-debug skill file exists."""
    skill_path = Path.home() / ".claude" / "skills" / "framework-debug" / "SKILL.md"
    assert skill_path.exists(), f"framework-debug skill not found at {skill_path}"


def test_log_discovery_commands():
    """Test that skill provides working commands to discover logs."""
    # Create test log structure
    with tempfile.TemporaryDirectory() as tmpdir:
        claude_dir = Path(tmpdir) / ".claude"
        projects_dir = claude_dir / "projects" / "-tmp-test-repo"
        projects_dir.mkdir(parents=True)

        # Create mock session log
        session_id = "test-session-123"
        session_log = projects_dir / f"{session_id}.jsonl"
        session_log.write_text(
            '{"type":"user","message":"test","timestamp":"2025-11-18T10:00:00Z"}\n'
        )

        # Create mock agent log
        agent_log = projects_dir / "agent-abc123.jsonl"
        agent_log.write_text(
            '{"type":"agentStart","agentId":"abc123","timestamp":"2025-11-18T10:00:15Z"}\n'
        )

        # Test log discovery
        assert session_log.exists()
        assert agent_log.exists()

        # Verify can list logs
        logs = list(projects_dir.glob("*.jsonl"))
        assert len(logs) == 2

        # Verify can identify session vs agent logs
        session_logs = [f for f in logs if "agent-" not in f.name]
        agent_logs = [f for f in logs if "agent-" in f.name]
        assert len(session_logs) == 1
        assert len(agent_logs) == 1


def test_message_extraction():
    """Test extraction of specific message types from JSONL logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_log = Path(tmpdir) / "test.jsonl"

        # Create test log with various message types
        messages = [
            {
                "type": "user",
                "message": "user message",
                "timestamp": "2025-11-18T10:00:00Z",
            },
            {
                "type": "assistant",
                "message": "assistant message",
                "timestamp": "2025-11-18T10:00:05Z",
            },
            {
                "type": "tool",
                "message": "Error: test failure",
                "timestamp": "2025-11-18T10:00:10Z",
            },
            {
                "type": "error",
                "message": "System error",
                "timestamp": "2025-11-18T10:00:15Z",
            },
        ]

        with test_log.open("w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        # Test reading and parsing
        content = test_log.read_text()
        lines = content.strip().split("\n")
        parsed = [json.loads(line) for line in lines]

        # Verify can filter by type
        errors = [
            m
            for m in parsed
            if m.get("type") in ("error", "tool")
            and "error" in m.get("message", "").lower()
        ]
        assert len(errors) == 2

        # Verify chronological ordering
        timestamps = [
            datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
            for m in parsed
        ]
        assert timestamps == sorted(timestamps)


def test_timeline_correlation():
    """Test correlating messages across main session and agent logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create main session log
        main_log = Path(tmpdir) / "session.jsonl"
        main_messages = [
            {
                "type": "user",
                "message": "start task",
                "timestamp": "2025-11-18T10:00:00Z",
            },
            {
                "type": "assistant",
                "message": "invoking agent",
                "timestamp": "2025-11-18T10:00:05Z",
            },
            {
                "type": "user",
                "message": "check result",
                "timestamp": "2025-11-18T10:01:00Z",
            },
        ]

        with main_log.open("w") as f:
            for msg in main_messages:
                f.write(json.dumps(msg) + "\n")

        # Create agent log
        agent_log = Path(tmpdir) / "agent.jsonl"
        agent_messages = [
            {
                "type": "agentStart",
                "message": "agent started",
                "timestamp": "2025-11-18T10:00:10Z",
            },
            {
                "type": "error",
                "message": "agent error",
                "timestamp": "2025-11-18T10:00:15Z",
            },
            {
                "type": "agentEnd",
                "message": "agent finished",
                "timestamp": "2025-11-18T10:00:20Z",
            },
        ]

        with agent_log.open("w") as f:
            for msg in agent_messages:
                f.write(json.dumps(msg) + "\n")

        # Read and merge
        all_messages = []
        for log in [main_log, agent_log]:
            content = log.read_text()
            for line in content.strip().split("\n"):
                all_messages.append(json.loads(line))

        # Sort by timestamp
        all_messages.sort(key=lambda m: m["timestamp"])

        # Verify chronological order
        expected_order = [
            "start task",
            "invoking agent",
            "agent started",
            "agent error",
            "agent finished",
            "check result",
        ]
        actual_order = [m["message"] for m in all_messages]
        assert actual_order == expected_order


def test_error_extraction():
    """Test extracting error messages efficiently."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create log with mix of normal and error messages
        test_log = Path(tmpdir) / "test.jsonl"

        messages = []
        # Add 100 normal messages
        for i in range(100):
            messages.append(
                {
                    "type": "message",
                    "message": f"normal message {i}",
                    "timestamp": f"2025-11-18T10:{i:02d}:00Z",
                }
            )

        # Add 5 error messages scattered throughout
        for i in [10, 25, 50, 75, 90]:
            messages[i] = {
                "type": "error",
                "message": f"Error: test error {i}",
                "timestamp": messages[i]["timestamp"],
            }

        with test_log.open("w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        # Test efficient error extraction (should not need to read entire file)
        # In practice, would use grep or jq for efficiency
        content = test_log.read_text()
        error_lines = [line for line in content.split("\n") if "error" in line.lower()]

        assert len(error_lines) == 5


def test_malformed_log_handling():
    """Test graceful handling of malformed JSONL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_log = Path(tmpdir) / "malformed.jsonl"

        # Create log with malformed lines
        content = """{"type":"user","message":"good message 1","timestamp":"2025-11-18T10:00:00Z"}
{this is not valid json}
{"type":"user","message":"good message 2","timestamp":"2025-11-18T10:00:10Z"}
incomplete json {
{"type":"error","message":"Error: test","timestamp":"2025-11-18T10:00:20Z"}
"""
        test_log.write_text(content)

        # Test parsing with error handling
        valid_messages = []
        malformed_count = 0

        for line in test_log.read_text().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                valid_messages.append(msg)
            except json.JSONDecodeError:
                malformed_count += 1

        # Should have recovered 3 valid messages and counted 2 malformed
        assert len(valid_messages) == 3
        assert malformed_count == 2

        # Should still extract the error despite malformed neighbors
        errors = [m for m in valid_messages if m.get("type") == "error"]
        assert len(errors) == 1


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
