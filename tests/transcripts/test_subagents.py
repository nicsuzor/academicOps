"""Tests for subagent (sidechain) handling in the transcript pipeline.

A Claude Code subagent writes its conversation to a separate log under
`<session-id>/subagents/`, but every record in it carries the *parent's*
`sessionId`. Treating one as a session in its own right therefore produces the
parent's stable slug, the parent's output filename, and — whichever file the
batch run reached last — the parent's published transcript replaced by a
subagent's. These tests pin the two halves of the fix: subagent logs are never
discovered or loaded as sessions, and their content is carried inside the
parent's record instead of being lost.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from transcripts.adapters.claude import (
    ClaudeTranscript,
    find_subagent_files,
    is_sidechain_file,
    load_claude_session,
    load_claude_transcript,
    load_subagent_transcripts,
    normalize_claude_transcript,
)
from transcripts.domain.renderer import (
    MAX_SUBAGENT_FULL_MD_CHARS,
    render_to_full_markdown,
    render_to_json,
    render_to_markdown,
)
from transcripts.model import (
    NormalizedEvent,
    NormalizedSession,
    NormalizedToolCall,
    SubagentTranscript,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
CLAUDE_FIXTURE = FIXTURES_DIR / "claude_session.jsonl"
SUBAGENT_FIXTURE = FIXTURES_DIR / "claude_subagent.jsonl"
SUBAGENT_META_FIXTURE = FIXTURES_DIR / "claude_subagent.meta.json"

PARENT_SESSION_ID = "19cb8a50-7d62-4936-aef9-6861ad8967a4"
SUBAGENT_AGENT_ID = "a270f5ac9ef8b3a95"
CORRELATION: dict[str, str | None] = {"project": "aops", "task_id": None, "pr_number": None}


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """A Claude Code project directory laid out the way the client writes it.

    `<project>/<session-id>.jsonl` for the trunk, and the subagent's sidechain
    plus its metadata sidecar under `<project>/<session-id>/subagents/`.
    """
    project = tmp_path / "-home-user-src-aops"
    subagents = project / PARENT_SESSION_ID / "subagents"
    subagents.mkdir(parents=True)

    shutil.copy(CLAUDE_FIXTURE, project / f"{PARENT_SESSION_ID}.jsonl")
    shutil.copy(SUBAGENT_FIXTURE, subagents / f"agent-{SUBAGENT_AGENT_ID}.jsonl")
    shutil.copy(SUBAGENT_META_FIXTURE, subagents / f"agent-{SUBAGENT_AGENT_ID}.meta.json")
    return project


def _trunk(project_dir: Path) -> Path:
    return project_dir / f"{PARENT_SESSION_ID}.jsonl"


# --- The shared session id: why a subagent log used to clobber the trunk ------


def test_subagent_log_carries_the_parents_session_id(project_dir: Path) -> None:
    """The precondition for the bug — assert it, so the rest of the file means something."""
    subagent_file = find_subagent_files(_trunk(project_dir))[0]
    transcript = load_claude_transcript(subagent_file)

    assert transcript.entries
    assert all(entry.sessionId == PARENT_SESSION_ID for entry in transcript.entries)
    assert is_sidechain_file(subagent_file)


def test_trunk_file_is_not_classified_as_a_sidechain(project_dir: Path) -> None:
    assert not is_sidechain_file(_trunk(project_dir))


def test_a_trunk_holding_inlined_sidechain_records_is_still_a_trunk(tmp_path: Path) -> None:
    """claude-code-log inlines linked subagents, so entry contents cannot classify a file.

    A trunk whose loaded entries include sidechain records must still be
    recognised as a trunk, or the session is dropped instead of published.
    """
    trunk = tmp_path / f"{PARENT_SESSION_ID}.jsonl"
    trunk.write_text(
        CLAUDE_FIXTURE.read_text(encoding="utf-8") + SUBAGENT_FIXTURE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert not is_sidechain_file(trunk)
    assert load_claude_session(trunk) is not None


# --- Discovery: subagent logs are not sessions --------------------------------


def test_discovery_yields_the_trunk_only(project_dir: Path, monkeypatch) -> None:
    """`find_session_files` must not descend into `subagents/`."""
    from transcripts import runner

    home = project_dir.parent.parent
    claude_projects = home / ".claude" / "projects"
    claude_projects.mkdir(parents=True)
    shutil.copytree(project_dir, claude_projects / project_dir.name)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    found = runner.find_session_files()

    assert [p.name for p in found] == [f"{PARENT_SESSION_ID}.jsonl"]
    assert not any("subagents" in p.parts for p in found)


def test_loading_a_subagent_log_directly_is_refused(project_dir: Path) -> None:
    """Second guard: even handed the path, the loader will not make a session of it."""
    subagent_file = find_subagent_files(_trunk(project_dir))[0]

    assert load_claude_session(subagent_file) is None


def test_session_source_files_covers_trunk_and_subagents(project_dir: Path) -> None:
    from transcripts import runner

    sources = runner.session_source_files(_trunk(project_dir))

    assert sources[0] == _trunk(project_dir)
    assert [p.name for p in sources[1:]] == [f"agent-{SUBAGENT_AGENT_ID}.jsonl"]


# --- Incorporation: the parent's record carries the delegated work ------------


def test_subagent_is_attached_to_the_parent_session(project_dir: Path) -> None:
    session = load_claude_session(_trunk(project_dir))

    assert session is not None
    assert session.session_id == PARENT_SESSION_ID
    assert len(session.subagents) == 1

    subagent = session.subagents[0]
    assert subagent.agent_id == SUBAGENT_AGENT_ID
    assert subagent.agent_type == "aops:pauli"
    assert subagent.description == "Retro: agent unaware of md transcripts"
    assert subagent.parent_tool_use_id == "toolu_01Me46HjJa47GxqUEh193Rfs"
    assert subagent.events, "subagent conversation was attached but empty"
    # claude_subagent.meta.json carries spawnDepth: 1 and no isFork key.
    assert subagent.spawn_depth == 1
    assert subagent.is_fork is False


def test_trunk_events_are_not_replaced_by_subagent_events(project_dir: Path) -> None:
    """The actual regression: the published record must be the trunk's."""
    trunk_only = load_claude_session(_trunk(project_dir))
    assert trunk_only is not None
    trunk_event_ids = {event.event_id for event in trunk_only.events}

    subagent_event_ids = {event.event_id for sub in trunk_only.subagents for event in sub.events}

    assert trunk_event_ids
    assert subagent_event_ids
    assert not trunk_event_ids & subagent_event_ids
    assert trunk_only.total_event_count == len(trunk_only.events) + len(subagent_event_ids)


def test_subagent_usage_counts_towards_the_session_total(project_dir: Path) -> None:
    session = load_claude_session(_trunk(project_dir))
    assert session is not None

    subagent = session.subagents[0]
    # 7064 input + 1898 cache_creation + 23474 cache_read + 2 output
    assert subagent.tokens_used == 32438
    assert session.total_tokens_used == session.tokens_used + subagent.tokens_used
    assert session.total_cost_usd > session.cost_usd


def test_session_without_subagents_is_unchanged(tmp_path: Path) -> None:
    """A single-thread session must render exactly as before, with no empty scaffolding."""
    trunk = tmp_path / f"{PARENT_SESSION_ID}.jsonl"
    shutil.copy(CLAUDE_FIXTURE, trunk)

    session = load_claude_session(trunk)

    assert session is not None
    assert session.subagents == []
    assert session.total_event_count == len(session.events)
    assert session.total_tokens_used == session.tokens_used

    md = render_to_markdown(session, "19cb8a50", "", "", "", True, CORRELATION, None)
    full_md = render_to_full_markdown(session, "19cb8a50", "", "", "", True, CORRELATION, None)
    assert "Subagents" not in md
    assert "Subagent Transcripts" not in full_md


# --- Inlined subagents: claude-code-log merges the ones it can link ----------


def _merged_transcript(project_dir: Path) -> ClaudeTranscript:
    """A trunk transcript with its subagent's records inlined, as upstream produces."""
    trunk = load_claude_transcript(_trunk(project_dir))
    sidechain = load_claude_transcript(find_subagent_files(_trunk(project_dir))[0])
    return ClaudeTranscript(
        source=_trunk(project_dir),
        entries=trunk.entries + sidechain.entries,
        raw_entries=trunk.raw_entries,
    )


def test_inlined_sidechain_records_are_not_counted_as_trunk_events(project_dir: Path) -> None:
    """Upstream inlining must not inflate the main thread or its cost."""
    trunk_only = normalize_claude_transcript(load_claude_transcript(_trunk(project_dir)))
    merged = normalize_claude_transcript(_merged_transcript(project_dir))

    assert len(merged.events) == len(trunk_only.events)
    assert merged.tokens_used == trunk_only.tokens_used


def test_an_inlined_subagent_is_regrouped_and_not_duplicated(project_dir: Path) -> None:
    """Found inline and on disk, an agent must still appear exactly once."""
    merged = _merged_transcript(project_dir)
    inlined = [entry for entry in merged.entries if getattr(entry, "isSidechain", False)]
    assert inlined, "fixture did not produce any sidechain entries to regroup"

    subagents = load_subagent_transcripts(_trunk(project_dir), [], inlined)

    assert [sub.agent_id for sub in subagents] == [SUBAGENT_AGENT_ID]
    assert subagents[0].agent_type == "aops:pauli"
    assert subagents[0].tokens_used == 32438


# --- Rendering: summary names them, `.full.md` carries them -------------------


def _rendered(project_dir: Path) -> tuple[NormalizedSession, str, str, str]:
    session = load_claude_session(_trunk(project_dir))
    assert session is not None
    args = ("19cb8a50", "2026-07-05T06:45:18Z", "", "", True, CORRELATION, None)
    return (
        session,
        render_to_markdown(session, *args),
        render_to_full_markdown(session, *args),
        render_to_json(session, *args),
    )


def test_summary_markdown_indexes_subagents_without_inlining_them(project_dir: Path) -> None:
    session, md, _, _ = _rendered(project_dir)
    reply = session.subagents[0].events[-1].content

    assert "## 🧵 Subagents" in md
    assert "aops:pauli" in md
    assert "Retro: agent unaware of md transcripts" in md
    # The summary stays a summary: the conversation itself is not inlined.
    assert reply not in md
    assert ".full.md" in md


def test_full_markdown_carries_the_whole_subagent_conversation(project_dir: Path) -> None:
    session, _, full_md, _ = _rendered(project_dir)
    subagent = session.subagents[0]

    assert "## 🧵 Subagent Transcripts" in full_md
    assert f"`{subagent.agent_id}`" in full_md
    for event in subagent.events:
        if event.content:
            assert event.content in full_md


def test_front_matter_reports_whole_session_totals(project_dir: Path) -> None:
    session, md, full_md, _ = _rendered(project_dir)

    for rendered in (md, full_md):
        assert "subagent_count: 1" in rendered
        assert f"total_event_count: {session.total_event_count}" in rendered
        assert f"total_tokens_used: {session.total_tokens_used}" in rendered
        # Trunk-only keys keep their existing meaning for existing consumers.
        assert f"tokens_used: {session.tokens_used}" in rendered


def test_json_sidecar_lists_subagents_and_keeps_trunk_keys(project_dir: Path) -> None:
    session, _, _, sidecar = _rendered(project_dir)
    data = json.loads(sidecar)

    assert data["event_count"] == len(session.events)
    assert data["tokens_used"] == session.tokens_used
    assert data["total_event_count"] == session.total_event_count
    assert len(data["subagents"]) == 1

    entry = data["subagents"][0]
    assert entry["agent_id"] == SUBAGENT_AGENT_ID
    assert entry["agent_type"] == "aops:pauli"
    assert entry["event_count"] == len(session.subagents[0].events)
    assert entry["started_at"]

    # The ledger reads `user_prompts`; a subagent's brief is a delegation, not
    # a human prompt, and must not be promoted into it.
    prompts = [prompt["text"] for prompt in data["user_prompts"]]
    assert not any("Review the transcript pipeline" in prompt for prompt in prompts)


# --- Size budget --------------------------------------------------------------


def _bulky_subagent(agent_id: str, chars: int) -> SubagentTranscript:
    return SubagentTranscript(
        agent_id=agent_id,
        source_file=Path(f"agent-{agent_id}.jsonl"),
        events=[
            NormalizedEvent(
                event_id=f"{agent_id}-e1",
                timestamp="2026-07-05T06:50:00Z",
                source="model",
                type="message",
                content="x" * chars,
            )
        ],
    )


def test_full_markdown_budget_names_what_it_did_not_expand(monkeypatch) -> None:
    """The budget is a safety valve, and it must be loud rather than silent."""
    from transcripts.domain import renderer

    monkeypatch.setattr(renderer, "MAX_SUBAGENT_FULL_MD_CHARS", 2_000)
    session = NormalizedSession(
        session_id="big",
        source_file=Path("big.jsonl"),
        subagents=[_bulky_subagent("aaa", 1_000), _bulky_subagent("bbb", 5_000)],
    )

    full_md = render_to_full_markdown(session, "big", "", "", "", True, CORRELATION, None)

    # The first subagent fits and is expanded in full.
    assert "x" * 1_000 in full_md
    # The second does not, and is named rather than silently dropped.
    assert "x" * 5_000 not in full_md
    assert "Size budget" in full_md
    assert "`bbb`" in full_md
    assert "subagent_count: 2" in full_md


def test_full_markdown_expands_everything_within_budget() -> None:
    session = NormalizedSession(
        session_id="small",
        source_file=Path("small.jsonl"),
        subagents=[_bulky_subagent("aaa", 100), _bulky_subagent("bbb", 100)],
    )

    full_md = render_to_full_markdown(session, "small", "", "", "", True, CORRELATION, None)

    assert "Size budget" not in full_md
    assert full_md.count("x" * 100) == 2
    assert MAX_SUBAGENT_FULL_MD_CHARS > 100


# --- Parent linkage fallback --------------------------------------------------


def test_description_falls_back_to_the_parents_spawning_tool_call() -> None:
    """Without a sidecar description, the parent's Task/Agent block supplies it."""
    from transcripts.adapters.claude import _describe_from_parent

    parent_events = [
        NormalizedEvent(
            event_id="e1",
            timestamp="2026-07-05T06:45:00Z",
            source="model",
            type="message",
            content="",
            tool_calls=[
                NormalizedToolCall(
                    name="Task",
                    args={"description": "Audit the renderer", "subagent_type": "rbg"},
                    call_id="toolu_parent_1",
                )
            ],
        )
    ]

    assert _describe_from_parent(parent_events, "toolu_parent_1") == "Audit the renderer"
    assert _describe_from_parent(parent_events, "toolu_missing") is None
    assert _describe_from_parent(parent_events, None) is None


# --- Depth, forks, and spawn/return interleaving -------------------------------
#
# Real sessions carry genuine spawn_depth > 1 nesting (confirmed live, this
# framework's own orchestrator sessions routinely spawn depth-2+ subagents),
# and the raw meta sidecar has always carried spawnDepth/isFork — the pipeline
# just never read them. These tests pin that it now does, and that a cold
# reader gets an explicit spawn/return marker at the tool-call site instead of
# having to cross-reference IDs between two separate sections.


def test_subagent_index_shows_depth_and_fork_tag() -> None:
    session = NormalizedSession(
        session_id="s1",
        source_file=Path("s1.jsonl"),
        subagents=[
            SubagentTranscript(
                agent_id="deep",
                source_file=Path("agent-deep.jsonl"),
                spawn_depth=2,
                is_fork=True,
            ),
            SubagentTranscript(
                agent_id="shallow",
                source_file=Path("agent-shallow.jsonl"),
                spawn_depth=None,
            ),
        ],
    )
    md = render_to_markdown(session, "s1", "2026-07-05T06:45:18Z", "", "", True, CORRELATION, None)

    assert "### Subagent Call Tree Lineage" in md
    assert (
        "| Level | Call Path | Agent Label | Type | Parent Agent | Events | Tokens (in / cr / out) | USD Cost | Task / Description |"
        in md
    )
    assert "`main/unlinked/deep`" in md
    assert "`main/unlinked/shallow`" in md


def test_full_markdown_heading_level_follows_spawn_depth() -> None:
    session = NormalizedSession(
        session_id="s2",
        source_file=Path("s2.jsonl"),
        subagents=[
            SubagentTranscript(agent_id="a", source_file=Path("agent-a.jsonl"), spawn_depth=1),
            SubagentTranscript(agent_id="b", source_file=Path("agent-b.jsonl"), spawn_depth=3),
        ],
    )
    full_md = render_to_full_markdown(session, "s2", "", "", "", True, CORRELATION, None)

    assert "### 🧵 Subagent 1: a" in full_md
    assert "##### 🧵 Subagent 2: b" in full_md


def test_reasoning_not_recoverable_is_marked_not_silently_omitted() -> None:
    session = NormalizedSession(
        session_id="s3",
        source_file=Path("s3.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e1",
                timestamp="2026-07-05T06:45:00Z",
                source="model",
                type="message",
                content="answer",
                thinking=None,
                thinking_opaque=True,
            )
        ],
    )
    full_md = render_to_full_markdown(session, "s3", "", "", "", True, CORRELATION, None)

    assert "not recoverable" in full_md
    assert "signature only" in full_md


def test_trunk_marks_where_a_subagent_was_spawned_and_where_it_returned() -> None:
    """The interleaving fix: a cold reader following the trunk hits an explicit
    pointer at the spawning tool call, and another at the matching tool_output,
    instead of having to jump to a separate section and correlate IDs by hand."""
    subagent = SubagentTranscript(
        agent_id="child1",
        source_file=Path("agent-child1.jsonl"),
        agent_type="rbg",
        parent_tool_use_id="toolu_spawn_1",
        events=[
            NormalizedEvent(
                event_id="c1",
                timestamp="2026-07-05T06:46:00Z",
                source="model",
                type="message",
                content="child did the work",
            )
        ],
    )
    session = NormalizedSession(
        session_id="s4",
        source_file=Path("s4.jsonl"),
        subagents=[subagent],
        events=[
            NormalizedEvent(
                event_id="p1",
                timestamp="2026-07-05T06:45:00Z",
                source="model",
                type="message",
                content="delegating",
                tool_calls=[
                    NormalizedToolCall(
                        name="Agent", args={"description": "audit"}, call_id="toolu_spawn_1"
                    )
                ],
            ),
            NormalizedEvent(
                event_id="p2",
                timestamp="2026-07-05T06:47:00Z",
                source="tool",
                type="tool_output",
                content="child's result",
                meta={"tool_use_id": "toolu_spawn_1"},
            ),
        ],
    )
    full_md = render_to_full_markdown(session, "s4", "", "", "", True, CORRELATION, None)

    spawn_marker = "spawned Subagent 1: `rbg`"
    return_marker = "Subagent 1: `rbg` returned"
    assert spawn_marker in full_md
    assert return_marker in full_md
    # The pointer must appear between the spawning call and the trunk's next
    # event, not merely somewhere in the document.
    assert (
        full_md.index(spawn_marker) < full_md.index("child's result") < full_md.index(return_marker)
    )
