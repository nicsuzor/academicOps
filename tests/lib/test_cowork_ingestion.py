import importlib.util
import json
import sys
from pathlib import Path

from lib.session_reader import find_sessions
from lib.transcript_parser import SessionProcessor

_REPO_ROOT = Path(__file__).parent.parent.parent


def _import_transcript():
    spec = importlib.util.spec_from_file_location(
        "transcript", _REPO_ROOT / "aops-core" / "scripts" / "transcript.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def test_is_test_session_cowork_not_filtered():
    """Regression: Cowork audit.jsonl must not be filtered as a test session.

    Before the fix, paths containing 'local' were filtered out by _is_test_session,
    causing Cowork sessions (under local-agent-mode-sessions/) to be skipped.
    """
    transcript = _import_transcript()
    cowork_path = Path(
        "/Users/nic/Library/Application Support/Claude/"
        "local-agent-mode-sessions/user-uuid/org-uuid/local_abc123xyz/audit.jsonl"
    )
    assert not transcript._is_test_session(cowork_path)


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
