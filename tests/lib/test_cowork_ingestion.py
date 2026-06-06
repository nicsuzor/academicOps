import importlib.util
import json
from pathlib import Path

from lib.session_reader import find_sessions
from lib.transcript_parser import Entry, SessionProcessor

_REPO_ROOT = Path(__file__).parent.parent.parent


def _import_transcript():
    spec = importlib.util.spec_from_file_location(
        "transcript", _REPO_ROOT / "aops-core" / "scripts" / "transcript.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _import_ingest():
    spec = importlib.util.spec_from_file_location(
        "ingest_cowork", _REPO_ROOT / "aops-core" / "scripts" / "ingest_cowork.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ingest_preserves_native_message_envelope():
    """Current Cowork audit logs emit native Claude Code records (type=user/
    assistant + top-level `message`). Ingest must pass `message` through, not
    bury it under `content` — otherwise the transcript parser reads no content
    and emits an empty transcript (regression: 875KB session → 429 bytes).
    """
    ingest = _import_ingest()

    native = {
        "type": "assistant",
        "uuid": "abc",
        "_audit_timestamp": "2026-06-05T13:03:46.922Z",
        "_audit_hmac": "deadbeef",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "hello"}],
        },
    }
    out = ingest.normalize_cowork_entry(native)

    # Envelope preserved at top level for Entry.from_dict
    assert out["type"] == "assistant"
    assert out["message"]["content"][0]["text"] == "hello"
    assert "content" not in out  # not double-wrapped
    # Audit bookkeeping normalized away
    assert out["timestamp"] == "2026-06-05T13:03:46.922Z"
    assert "_audit_hmac" not in out

    # And the parser actually renders it
    entry = Entry.from_dict(out)
    assert entry.type == "assistant"
    assert entry.message["content"][0]["text"] == "hello"


def test_ingest_legacy_schema_still_normalized():
    """Legacy flat audit events (type=message) must still get a synthesized
    Claude Code message envelope."""
    ingest = _import_ingest()
    legacy = {
        "type": "message",
        "role": "user",
        "content": "Help me",
        "_audit_timestamp": "2026-04-28T10:00:01Z",
    }
    out = ingest.normalize_cowork_entry(legacy)
    assert out["type"] == "user"
    assert out["message"]["content"][0]["text"] == "Help me"


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

    # include_cowork=True: ingested session must be discovered
    sessions = find_sessions(include_cowork=True, claude_projects_dir=tmp_path / "no-claude")
    found = [s for s in sessions if s.session_id == session_id]
    assert len(found) == 1
    assert found[0].project == session_id

    # include_cowork=False: ingested session must NOT be discovered
    sessions_no_cowork = find_sessions(
        include_cowork=False, claude_projects_dir=tmp_path / "no-claude"
    )
    assert not any(s.session_id == session_id for s in sessions_no_cowork)
