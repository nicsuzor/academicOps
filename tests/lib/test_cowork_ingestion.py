import json

from lib.session_reader import find_sessions
from lib.transcript_parser import SessionProcessor


def test_cowork_audit_parsing(tmp_path):
    """Verify Cowork audit.jsonl parsing and turn grouping."""
    audit_file = tmp_path / "audit.jsonl"
    entries = [
        {"type": "init", "tools": ["Bash"], "_audit_timestamp": "2026-04-28T10:00:00Z"},
        {
            "type": "message",
            "role": "user",
            "content": "Help me",
            "_audit_timestamp": "2026-04-28T10:00:01Z",
        },
        {
            "type": "message",
            "role": "assistant",
            "content": "Sure",
            "_audit_timestamp": "2026-04-28T10:00:02Z",
        },
        {
            "type": "tool_call",
            "name": "Bash",
            "args": {"command": "ls"},
            "id": "call_123",
            "_audit_timestamp": "2026-04-28T10:00:03Z",
        },
        {
            "type": "tool_result",
            "output": "file1.txt",
            "is_error": False,
            "tool_use_id": "call_123",
            "_audit_timestamp": "2026-04-28T10:00:04Z",
        },
    ]
    with open(audit_file, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    processor = SessionProcessor()
    summary, parsed_entries, _ = processor.parse_session_file(audit_file)

    # Check entry types were normalized
    assert any(e.type == "user" for e in parsed_entries)
    assert any(e.type == "assistant" for e in parsed_entries)

    turns = processor.group_entries_into_turns(parsed_entries)
    assert len(turns) == 1
    assert turns[0].user_message == "Help me"
    # Assistant sequence should include text and tool use
    assert len(turns[0].assistant_sequence) == 2
    assert any("Bash" in str(s) for s in turns[0].assistant_sequence)


def test_cowork_ingested_discovery(tmp_path, monkeypatch):
    """Verify discovery of ingested Cowork sessions."""
    # Setup mock sessions repo
    sessions_repo = tmp_path / "sessions"
    cowork_logs = sessions_repo / "cowork-logs"
    session_id = "abc12345"
    target_dir = cowork_logs / session_id
    target_dir.mkdir(parents=True)
    (target_dir / "session.jsonl").write_text('{"type": "user", "message": {"content": "test"}}\n')

    import lib.paths

    monkeypatch.setattr(lib.paths, "get_sessions_repo", lambda: sessions_repo)

    sessions = find_sessions(include_cowork=False)

    found = [s for s in sessions if s.session_id == session_id]
    assert len(found) == 1
    assert found[0].project == session_id
