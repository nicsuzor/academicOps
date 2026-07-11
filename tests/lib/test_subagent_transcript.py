"""Tests for independent subagent transcripts + insights (task-b483e037).

End-to-end: synthesise a parent JSONL with two subagent invocations, write
the matching ``agent-*.jsonl`` + ``agent-*.meta.json`` sidecar files, run
transcript.py, and assert:

* parent ``-full.md`` lands under ``transcripts/YYYY-MM/``
* each subagent ``-full.md`` lands under ``subagent-transcripts/YYYY-MM/``
* parent transcript body contains a "Subagent Transcripts" footer linking
  to each subagent transcript
* per-subagent insights JSON exists under ``subagent-summaries/YYYY-MM/``
* parent insights JSON still exists under ``summaries/YYYY-MM/``

We also exercise the module-level helper :func:`write_subagent_transcripts`
in isolation to keep test feedback fast when the integration test slips.

``agent-<id>.meta.json`` is the sole, required source of subagent identity
(``iter_subagent_invocations``/``_load_agent_meta``) — there is no
tool_use/tool_result pairing fallback, so every fixture here writes the
sidecar alongside the subagent jsonl.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _entry(
    *,
    role: str,
    uuid: str,
    parent_uuid: str,
    session_id: str,
    text: str,
    offset_min: int,
    is_sidechain: bool = False,
    extra: dict | None = None,
) -> dict:
    ts = datetime(2026, 5, 12, 9, 0, tzinfo=UTC) + timedelta(minutes=offset_min)
    msg: dict = {
        "role": role,
        "content": [{"type": "text", "text": text}],
    }
    if role == "assistant":
        msg["model"] = "claude-opus-4-5"
        msg["usage"] = {
            "input_tokens": 10,
            "output_tokens": 10,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
    base = {
        "type": role,
        "uuid": uuid,
        "parentUuid": parent_uuid,
        "sessionId": session_id,
        "timestamp": ts.isoformat(),
        "isSidechain": is_sidechain,
        "message": msg,
        "cwd": "/home/test/proj",
    }
    if extra:
        base.update(extra)
    return base


def _write_subagent_jsonl(
    path: Path,
    *,
    session_id: str,
    agent_id: str,
    subagent_type: str,
    user_text: str,
    assistant_text: str,
    offset_min: int,
    meta_extra: dict | None = None,
) -> None:
    """Write a minimal ``agent-<id>.jsonl`` plus its required ``.meta.json`` sidecar."""
    path.parent.mkdir(parents=True, exist_ok=True)
    base_extra = {"agentId": agent_id}
    with path.open("w") as f:
        f.write(
            json.dumps(
                _entry(
                    role="user",
                    uuid=f"{agent_id}-u1",
                    parent_uuid="",
                    session_id=session_id,
                    text=user_text,
                    offset_min=offset_min,
                    is_sidechain=True,
                    extra=base_extra,
                )
            )
            + "\n"
        )
        f.write(
            json.dumps(
                _entry(
                    role="assistant",
                    uuid=f"{agent_id}-a1",
                    parent_uuid=f"{agent_id}-u1",
                    session_id=session_id,
                    text=assistant_text,
                    offset_min=offset_min + 1,
                    is_sidechain=True,
                    extra=base_extra,
                )
            )
            + "\n"
        )

    meta = {"agentType": subagent_type, "description": f"work-{subagent_type}"}
    if meta_extra:
        meta.update(meta_extra)
    path.with_name(f"{path.stem}.meta.json").write_text(json.dumps(meta))


def _build_parent_session(
    *,
    parent_path: Path,
    session_id: str,
) -> None:
    """Write a plain parent session jsonl (no Task tool_use required — subagent
    identity comes entirely from the ``.meta.json`` sidecars)."""
    entries = [
        _entry(
            role="user",
            uuid="u1",
            parent_uuid="",
            session_id=session_id,
            text="kick off",
            offset_min=0,
        ),
        _entry(
            role="assistant",
            uuid="a1",
            parent_uuid="u1",
            session_id=session_id,
            text="ok, dispatching subagents",
            offset_min=1,
        ),
        _entry(
            role="assistant",
            uuid="a-final",
            parent_uuid="a1",
            session_id=session_id,
            text="all done",
            offset_min=2,
        ),
    ]
    with parent_path.open("w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


def test_subagent_transcripts_emitted_end_to_end(tmp_path: Path, monkeypatch):
    """Parent + 2 subagents → 3 transcripts, 3 insights, parent footer links."""
    sessions = tmp_path / "sessions"
    for sub in ("transcripts", "summaries", "subagent-transcripts", "subagent-summaries"):
        (sessions / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions))
    monkeypatch.setenv("AOPS_MACHINE", "testmachine")
    monkeypatch.delenv("AOPS_TASK_ID", raising=False)

    session_uuid = "b483e037-1234-5678-9abc-def012345678"
    project_dir = tmp_path / "proj"
    project_dir.mkdir(parents=True, exist_ok=True)
    parent_jsonl = project_dir / f"{session_uuid}.jsonl"

    _build_parent_session(parent_path=parent_jsonl, session_id=session_uuid)

    # Sidecar agent files live at <session_dir>/<session_uuid>/subagents/
    subagents_dir = project_dir / session_uuid / "subagents"
    subagent_specs = [
        {"agent_id": "ag00001", "type": "rbg"},
        {"agent_id": "ag00002", "type": "aops-pkb:pauli"},
    ]
    for i, spec in enumerate(subagent_specs):
        _write_subagent_jsonl(
            subagents_dir / f"agent-{spec['agent_id']}.jsonl",
            session_id=session_uuid,
            agent_id=spec["agent_id"],
            subagent_type=spec["type"],
            user_text=f"subagent {spec['type']} prompt",
            assistant_text=f"subagent {spec['type']} response with output",
            offset_min=2 + (i * 2),
        )

    # Run the transcript script.
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "aops-core" / "scripts" / "transcript.py"),
            str(parent_jsonl),
            "--no-sync",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"transcript.py failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )

    # Parent transcript present and rotated.
    parent_full = list((sessions / "transcripts" / "2026-05").glob("*-full.md"))
    assert parent_full, (
        f"no rotated parent transcript produced. stdout={result.stdout!r}\n"
        f"flat files: {list((sessions / 'transcripts').glob('*-full.md'))}"
    )
    parent_md = parent_full[0]
    assert parent_md.name.startswith("20260512-"), parent_md.name

    # Subagent transcripts present and rotated.
    sub_transcripts = list((sessions / "subagent-transcripts" / "2026-05").glob("*-full.md"))
    assert len(sub_transcripts) == 2, (
        f"expected 2 subagent transcripts, got {len(sub_transcripts)}: "
        f"{[p.name for p in sub_transcripts]}\nstdout={result.stdout}"
    )

    # Subagent insights present.
    sub_insights = list((sessions / "subagent-summaries" / "2026-05").glob("*.json"))
    assert len(sub_insights) == 2, (
        f"expected 2 subagent insight files, got {len(sub_insights)}: "
        f"{[p.name for p in sub_insights]}"
    )

    # Parent insights JSON still present under summaries/.
    parent_insights = list((sessions / "summaries" / "2026-05").glob("*.json"))
    assert parent_insights, "expected parent insights JSON"
    parent_ins = json.loads(parent_insights[0].read_text())
    parent_surface = parent_ins.get("surface")
    parent_client = parent_ins.get("client")
    assert parent_surface, "parent insights missing surface"

    # Each subagent insights JSON carries the parent linkage and type, and
    # inherits the parent's launch surface/client (aops-29... surface accuracy:
    # the JSON previously dropped surface/client, leaving subagents
    # unclassifiable by surface even though the .md frontmatter carried them).
    seen_types: set[str] = set()
    for ins_path in sub_insights:
        ins = json.loads(ins_path.read_text())
        assert ins["artifact_type"] == "subagent"
        assert ins["parent_session_id"] == session_uuid[:8]
        assert ins["subagent_type"] in {"rbg", "aops-pkb:pauli"}
        assert ins["transcript_path"]  # non-empty
        assert ins["surface"] == parent_surface, (
            f"subagent surface {ins.get('surface')!r} != parent {parent_surface!r}"
        )
        assert ins["client"] == parent_client, (
            f"subagent client {ins.get('client')!r} != parent {parent_client!r}"
        )
        seen_types.add(ins["subagent_type"])
    assert seen_types == {"rbg", "aops-pkb:pauli"}

    # Parent transcript has the subagent footer with both types and links.
    parent_text = parent_md.read_text(encoding="utf-8")
    assert "## Subagent Transcripts" in parent_text, "missing footer heading"
    assert "rbg" in parent_text
    assert "aops-pkb:pauli" in parent_text
    # The footer must reference each subagent transcript filename.
    for sub_path in sub_transcripts:
        assert sub_path.name in parent_text, (
            f"parent transcript missing link to {sub_path.name}.\nFooter section:\n"
            f"{parent_text[parent_text.find('## Subagent Transcripts') :]}"
        )

    # Subagent transcripts carry the parent linkage in their frontmatter.
    for sub_path in sub_transcripts:
        text = sub_path.read_text(encoding="utf-8")
        assert "artifact_type: subagent" in text, (
            f"missing artifact_type frontmatter in {sub_path.name}"
        )
        assert f"parent_session_id: {session_uuid[:8]}" in text, (
            f"missing parent_session_id frontmatter in {sub_path.name}"
        )


def test_iter_subagent_invocations_resolves_type_from_meta_json(tmp_path: Path):
    """Unit-level: subagent_type resolves from the ``.meta.json`` sidecar.

    Insulates the helper's resolution logic from the end-to-end harness so
    a regression here is identifiable without re-running the full pipeline.
    Also covers a nested/background-teammate spawn (no Task tool_use in the
    main thread at all) — the sidecar is the only source, so this resolves
    identically regardless of how the subagent was launched.
    """
    from lib.subagent_transcript import iter_subagent_invocations
    from lib.transcript_parser import Entry

    agent_entries = {
        "asupervisor-abc123": [
            Entry(
                type="user",
                uuid="su1",
                message={"role": "user", "content": [{"type": "text", "text": "x"}]},
                is_sidechain=True,
                timestamp=datetime(2026, 5, 12, 9, 0, tzinfo=UTC),
            )
        ],
    }

    session_dir = tmp_path / "proj"
    session_uuid = "parent-session-uuid"
    subagents_dir = session_dir / session_uuid / "subagents"
    subagents_dir.mkdir(parents=True)
    (subagents_dir / "agent-asupervisor-abc123.meta.json").write_text(
        json.dumps(
            {
                "agentType": "general-purpose",
                "description": "Supervise plugin-fix loop",
                "name": "supervisor-abc123",
                "spawnDepth": 0,
                "teamName": "session-parent",
                "model": "sonnet",
                "permissionMode": "auto",
            }
        )
    )

    parent_session_path = session_dir / f"{session_uuid}.jsonl"

    invs = iter_subagent_invocations(agent_entries, parent_session_path)
    assert len(invs) == 1
    inv = invs[0]
    assert inv["subagent_type"] == "general-purpose"
    assert inv["meta"]["description"] == "Supervise plugin-fix loop"
    assert inv["meta"]["name"] == "supervisor-abc123"


def test_iter_subagent_invocations_raises_on_missing_meta_json(tmp_path: Path):
    """Golden path only: a subagent with no ``.meta.json`` sidecar is a hard error,
    not a degraded "unknown" placeholder."""
    from lib.subagent_transcript import iter_subagent_invocations
    from lib.transcript_parser import Entry

    agent_entries = {
        "ag-orphan": [
            Entry(
                type="user",
                uuid="orph",
                message={"role": "user", "content": [{"type": "text", "text": "y"}]},
                is_sidechain=True,
            ),
        ],
    }
    session_dir = tmp_path / "proj"
    session_uuid = "parent-session-uuid"
    (session_dir / session_uuid / "subagents").mkdir(parents=True)
    parent_session_path = session_dir / f"{session_uuid}.jsonl"

    with pytest.raises(FileNotFoundError):
        iter_subagent_invocations(agent_entries, parent_session_path)


def test_subagent_transcript_frontmatter_carries_meta_fields(tmp_path: Path, monkeypatch):
    """write_subagent_transcripts splices meta.json fields into frontmatter.

    Covers the "not milking all available info" gap: description, name,
    spawn depth, team, and model were sitting in the sidecar unused.
    """
    from lib.subagent_transcript import write_subagent_transcripts
    from lib.transcript_parser import Entry, ParsedSession, SessionProcessor

    sessions = tmp_path / "sessions"
    for sub in ("subagent-transcripts", "subagent-summaries"):
        (sessions / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions))
    monkeypatch.delenv("AOPS_TASK_ID", raising=False)

    session_dir = tmp_path / "proj"
    session_uuid = "parent-session-uuid"
    subagents_dir = session_dir / session_uuid / "subagents"
    subagents_dir.mkdir(parents=True)
    (subagents_dir / "agent-asupervisor-abc123.meta.json").write_text(
        json.dumps(
            {
                "agentType": "general-purpose",
                "description": "Supervise plugin-fix loop",
                "name": "supervisor-abc123",
                "parentAgentId": "asupervisor-abc123",
                "spawnDepth": 1,
                "teamName": "session-parent",
                "model": "sonnet",
                "permissionMode": "auto",
                "taskKind": "in_process_teammate",
            }
        )
    )
    parent_session_path = session_dir / f"{session_uuid}.jsonl"
    parent_session_path.write_text("")

    entries = [
        Entry(
            type="user",
            uuid="su1",
            message={"role": "user", "content": [{"type": "text", "text": "hello"}]},
            is_sidechain=True,
            timestamp=datetime(2026, 5, 12, 9, 0, tzinfo=UTC),
        ),
        Entry(
            type="assistant",
            uuid="sa1",
            parent_uuid="su1",
            message={
                "role": "assistant",
                "model": "claude-opus-4-5",
                "usage": {
                    "input_tokens": 5,
                    "output_tokens": 5,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
                "content": [{"type": "text", "text": "done"}],
            },
            is_sidechain=True,
            timestamp=datetime(2026, 5, 12, 9, 1, tzinfo=UTC),
        ),
    ]
    agent_entries = {"asupervisor-abc123": entries}

    parent_summary = ParsedSession(uuid=session_uuid, repo="aops", task_id=None)
    processor = SessionProcessor()

    artifacts = write_subagent_transcripts(
        parent_session_path=parent_session_path,
        parent_session_id=session_uuid[:8],
        parent_summary=parent_summary,
        agent_entries=agent_entries,
        processor=processor,
    )

    assert len(artifacts) == 1
    art = artifacts[0]
    assert art.subagent_type == "general-purpose"
    text = art.transcript_path.read_text(encoding="utf-8")
    assert 'subagent_type: "general-purpose"' in text
    assert 'agent_name: "supervisor-abc123"' in text
    assert 'agent_description: "Supervise plugin-fix loop"' in text
    assert 'parent_agent_id: "asupervisor-abc123"' in text
    assert "spawn_depth: 1" in text
    assert 'team_name: "session-parent"' in text
    assert 'agent_model: "sonnet"' in text
    assert 'task_kind: "in_process_teammate"' in text
    # Description folded into the title so a reader isn't stuck with a bare
    # "Subagent: <type>" heading when richer context was available.
    assert "Supervise plugin-fix loop" in text
