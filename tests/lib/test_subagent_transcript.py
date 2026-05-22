"""Tests for independent subagent transcripts + insights (task-b483e037).

End-to-end: synthesise a parent JSONL with two Task subagent invocations,
write the matching ``agent-*.jsonl`` sidecar files, run transcript.py, and
assert:

* parent ``-full.md`` lands under ``transcripts/YYYY-MM/``
* each subagent ``-full.md`` lands under ``subagent-transcripts/YYYY-MM/``
* parent transcript body contains a "Subagent Transcripts" footer linking
  to each subagent transcript
* per-subagent insights JSON exists under ``subagent-summaries/YYYY-MM/``
* parent insights JSON still exists under ``summaries/YYYY-MM/``

We also exercise the module-level helper :func:`write_subagent_transcripts`
in isolation to keep test feedback fast when the integration test slips.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

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


def _task_tool_use_entry(
    *,
    uuid: str,
    parent_uuid: str,
    session_id: str,
    tool_use_id: str,
    subagent_type: str,
    description: str,
    offset_min: int,
) -> dict:
    """Build an assistant entry whose content is a Task tool_use block.

    Mirrors the shape used by reviewer_verdicts._build_subagent_type_index
    so subagent_type can be resolved by the helper.
    """
    ts = datetime(2026, 5, 12, 9, 0, tzinfo=UTC) + timedelta(minutes=offset_min)
    return {
        "type": "assistant",
        "uuid": uuid,
        "parentUuid": parent_uuid,
        "sessionId": session_id,
        "timestamp": ts.isoformat(),
        "isSidechain": False,
        "message": {
            "role": "assistant",
            "model": "claude-opus-4-5",
            "usage": {
                "input_tokens": 5,
                "output_tokens": 5,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": "Task",
                    "input": {
                        "subagent_type": subagent_type,
                        "description": description,
                        "prompt": f"do {description}",
                    },
                }
            ],
        },
        "cwd": "/home/test/proj",
    }


def _task_tool_result_entry(
    *,
    uuid: str,
    parent_uuid: str,
    session_id: str,
    tool_use_id: str,
    agent_file_id: str,
    offset_min: int,
) -> dict:
    """Build a user entry whose content is a tool_result for a prior Task call.

    The ``tool_use_result.agentId`` field is the link the subagent type
    index uses to pair main-thread Task calls with the on-disk
    ``agent-<id>.jsonl`` file.
    """
    ts = datetime(2026, 5, 12, 9, 0, tzinfo=UTC) + timedelta(minutes=offset_min)
    return {
        "type": "user",
        "uuid": uuid,
        "parentUuid": parent_uuid,
        "sessionId": session_id,
        "timestamp": ts.isoformat(),
        "isSidechain": False,
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": [{"type": "text", "text": "subagent finished"}],
                }
            ],
        },
        "toolUseResult": {"agentId": agent_file_id},
        "cwd": "/home/test/proj",
    }


def _write_subagent_jsonl(
    path: Path,
    *,
    session_id: str,
    agent_id: str,
    user_text: str,
    assistant_text: str,
    offset_min: int,
) -> None:
    """Write a minimal ``agent-<id>.jsonl`` file the parser can load."""
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


def _build_parent_session(
    *,
    parent_path: Path,
    session_id: str,
    subagent_specs: list[dict],
) -> None:
    """Write the parent session jsonl with main-thread + Task tool calls.

    ``subagent_specs`` is a list of ``{"agent_id", "tool_use_id", "type"}``
    dicts. Each one drives one Task tool_use + tool_result pair, plus an
    ``agent-<id>.jsonl`` sidecar file under ``<session>/subagents/``.
    """
    entries: list[dict] = []
    entries.append(
        _entry(
            role="user",
            uuid="u1",
            parent_uuid="",
            session_id=session_id,
            text="kick off",
            offset_min=0,
        )
    )
    entries.append(
        _entry(
            role="assistant",
            uuid="a1",
            parent_uuid="u1",
            session_id=session_id,
            text="ok, dispatching subagents",
            offset_min=1,
        )
    )

    offset = 2
    for spec in subagent_specs:
        entries.append(
            _task_tool_use_entry(
                uuid=f"tu-{spec['tool_use_id']}",
                parent_uuid="a1",
                session_id=session_id,
                tool_use_id=spec["tool_use_id"],
                subagent_type=spec["type"],
                description=f"work-{spec['type']}",
                offset_min=offset,
            )
        )
        entries.append(
            _task_tool_result_entry(
                uuid=f"tr-{spec['tool_use_id']}",
                parent_uuid=f"tu-{spec['tool_use_id']}",
                session_id=session_id,
                tool_use_id=spec["tool_use_id"],
                agent_file_id=spec["agent_id"],
                offset_min=offset + 1,
            )
        )
        offset += 2

    entries.append(
        _entry(
            role="assistant",
            uuid="a-final",
            parent_uuid=entries[-1]["uuid"],
            session_id=session_id,
            text="all done",
            offset_min=offset + 1,
        )
    )

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

    subagent_specs = [
        {"agent_id": "ag00001", "tool_use_id": "tool_use_001", "type": "rbg"},
        {"agent_id": "ag00002", "tool_use_id": "tool_use_002", "type": "aops-core:pauli"},
    ]
    _build_parent_session(
        parent_path=parent_jsonl,
        session_id=session_uuid,
        subagent_specs=subagent_specs,
    )

    # Sidecar agent files live at <session_dir>/<session_uuid>/subagents/
    subagents_dir = project_dir / session_uuid / "subagents"
    for i, spec in enumerate(subagent_specs):
        _write_subagent_jsonl(
            subagents_dir / f"agent-{spec['agent_id']}.jsonl",
            session_id=session_uuid,
            agent_id=spec["agent_id"],
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

    # Each subagent insights JSON carries the parent linkage and type.
    seen_types: set[str] = set()
    for ins_path in sub_insights:
        ins = json.loads(ins_path.read_text())
        assert ins["artifact_type"] == "subagent"
        assert ins["parent_session_id"] == session_uuid[:8]
        assert ins["subagent_type"] in {"rbg", "aops-core:pauli"}
        assert ins["transcript_path"]  # non-empty
        seen_types.add(ins["subagent_type"])
    assert seen_types == {"rbg", "aops-core:pauli"}

    # Parent insights JSON still present under summaries/.
    parent_insights = list((sessions / "summaries" / "2026-05").glob("*.json"))
    assert parent_insights, "expected parent insights JSON"

    # Parent transcript has the subagent footer with both types and links.
    parent_text = parent_md.read_text(encoding="utf-8")
    assert "## Subagent Transcripts" in parent_text, "missing footer heading"
    assert "rbg" in parent_text
    assert "aops-core:pauli" in parent_text
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


def test_iter_subagent_invocations_resolves_type(tmp_path: Path):
    """Unit-level: subagent_type resolves via Task tool_use ↔ tool_result.

    Insulates the helper's resolution logic from the end-to-end harness so
    a regression here is identifiable without re-running the full pipeline.
    """
    # Late import: lib path is configured by tests/conftest.py.
    from lib.subagent_transcript import iter_subagent_invocations
    from lib.transcript_parser import Entry

    main_entries = [
        Entry(
            type="assistant",
            uuid="a1",
            message={
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool_use_001",
                        "name": "Task",
                        "input": {"subagent_type": "rbg"},
                    }
                ],
            },
        ),
        Entry(
            type="user",
            uuid="u2",
            message={
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_use_001",
                        "content": "",
                    }
                ],
            },
            tool_use_result={"agentId": "ag00001"},
        ),
    ]

    agent_entries = {
        "ag00001": [
            Entry(
                type="user",
                uuid="su1",
                message={"role": "user", "content": [{"type": "text", "text": "x"}]},
                is_sidechain=True,
                timestamp=datetime(2026, 5, 12, 9, 0, tzinfo=UTC),
            )
        ],
        "ag-orphan": [
            Entry(
                type="user",
                uuid="orph",
                message={"role": "user", "content": [{"type": "text", "text": "y"}]},
                is_sidechain=True,
            ),
        ],
    }

    invs = iter_subagent_invocations(main_entries, agent_entries)
    by_id = {inv["invocation_id"]: inv for inv in invs}
    assert by_id["ag00001"]["subagent_type"] == "rbg"
    # Orphan agent file (no matching Task tool_use) still surfaces with None.
    assert by_id["ag-orphan"]["subagent_type"] is None
