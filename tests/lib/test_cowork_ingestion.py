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


def test_ingest_subagent_bundles_native_layout(tmp_path):
    """Cowork nests delegated work as native Claude Code bundles under
    `<conv>/.claude/projects/<encoded>/<task>.jsonl` + `<task>/subagents/`.
    The old ingest globbed audit.jsonl only and dropped this whole tree
    (GH #1621). `ingest_subagent_bundles` must copy each bundle into its own
    top-level `cowork-logs/<conv8>-<task8>/` dir in native layout so the
    existing discovery + subagent-linking machinery picks it up unchanged.
    """
    ingest = _import_ingest()

    conv_dir = tmp_path / "local_abc12345-aaaa-bbbb-cccc-dddddddddddd"
    task_uuid = "da55dfd3-2e6f-463f-8380-225f96b2030d"
    proj = conv_dir / ".claude" / "projects" / "encoded-cwd-outputs"
    subagents = proj / task_uuid / "subagents"
    subagents.mkdir(parents=True)

    # Native main task thread + one subagent (sessionId == main stem).
    (proj / f"{task_uuid}.jsonl").write_text(
        json.dumps({"type": "user", "sessionId": task_uuid, "message": {"content": "do it"}}) + "\n"
    )
    (subagents / "agent-a080f46fff3908fee.jsonl").write_text(
        json.dumps(
            {
                "type": "assistant",
                "sessionId": task_uuid,
                "isSidechain": True,
                "message": {"content": [{"type": "text", "text": "verified"}]},
            }
        )
        + "\n"
    )
    (subagents / "agent-a080f46fff3908fee.meta.json").write_text("{}")

    target_base = tmp_path / "sessions" / "cowork-logs"
    target_base.mkdir(parents=True)

    n = ingest.ingest_subagent_bundles(conv_dir, "abc12345", target_base)
    assert n == 1

    bundle = target_base / f"abc12345-{task_uuid[:8]}"
    assert (bundle / f"{task_uuid}.jsonl").exists()  # main thread, native layout
    assert (bundle / task_uuid / "subagents" / "agent-a080f46fff3908fee.jsonl").exists()

    # Idempotent: a second pass with unchanged source copies nothing.
    assert ingest.ingest_subagent_bundles(conv_dir, "abc12345", target_base) == 0


def test_cowork_bundle_files_under_cowork_title(tmp_path):
    """A recovered subagent bundle (`<task>.jsonl` under cowork-logs/) must file
    under the SAME `cowork-<title>` repo as its parent — driving both the
    filename slug and the frontmatter `repo:` field — so it's findable when
    browsing cowork transcripts instead of surfacing as anonymous `claude`
    (GH #1621). Before the fix only `session.jsonl` got the cowork title.
    """
    transcript = _import_transcript()

    bundle = tmp_path / "cowork-logs" / "6b32f9e0-da55dfd3"
    bundle.mkdir(parents=True)
    (bundle / "metadata.json").write_text(json.dumps({"title": "ARC Review Workflow"}))
    main = bundle / "da55dfd3-2e6f-463f-8380-225f96b2030d.jsonl"
    main.write_text('{"type":"user","sessionId":"da55dfd3","message":{"content":"x"}}\n')

    assert transcript._infer_project(main) == "cowork-arc-review-workflow"

    # No metadata → still tagged cowork, never anonymous.
    bare = tmp_path / "cowork-logs" / "abcd1234-eeee5678"
    bare.mkdir(parents=True)
    bare_main = bare / "eeee5678-0000-0000-0000-000000000000.jsonl"
    bare_main.write_text('{"type":"user","message":{"content":"x"}}\n')
    assert transcript._infer_project(bare_main) == "cowork"


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
    # Ingested Cowork sessions must be labelled source="cowork", not "claude"
    # (they share the discovery loop with ~/.claude/projects/ but originate in Cowork).
    assert found[0].source == "cowork"

    # include_cowork=False: ingested session must NOT be discovered
    sessions_no_cowork = find_sessions(
        include_cowork=False, claude_projects_dir=tmp_path / "no-claude"
    )
    assert not any(s.session_id == session_id for s in sessions_no_cowork)
