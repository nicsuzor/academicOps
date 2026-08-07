"""Tests for user-prompt vs hook-injection rendering fidelity (task aops_94fee2b1)."""

from __future__ import annotations

from pathlib import Path

from transcripts.adapters.agy import load_agy_transcript
from transcripts.adapters.claude import load_claude_transcript, normalize_claude_transcript
from transcripts.domain.ledger import generate_prompt_ledger
from transcripts.domain.renderer import (
    build_json_sidecar,
    render_to_full_markdown,
    render_to_html,
)
from transcripts.model import NormalizedEvent, NormalizedSession


def test_user_event_classification_meta_on_claude_transcript():
    """Criterion 2: NormalizedEvent.meta carries classification for every user event."""
    fixture_path = Path("tests/transcripts/fixtures/claude_session.jsonl")
    parsed = load_claude_transcript(fixture_path)
    session = normalize_claude_transcript(parsed)

    user_events = [e for e in session.events if e.source == "user"]
    assert len(user_events) > 0

    kinds = set()
    for e in user_events:
        assert "prompt_kind" in e.meta
        assert "is_human" in e.meta
        kinds.add(e.meta["prompt_kind"])

    # Expect at least three kinds across user events (e.g. human_prompt, stop_hook_feedback, etc.)
    assert len(kinds) >= 2


def test_user_event_classification_on_agy_transcript():
    """Criterion 9: agy adapter classifies user prompt events."""
    fixture_path = Path("tests/transcripts/fixtures/agy_session.jsonl")
    session = load_agy_transcript(fixture_path)

    user_events = [e for e in session.events if e.source == "user"]
    assert len(user_events) > 0

    for e in user_events:
        assert "prompt_kind" in e.meta
        assert "is_human" in e.meta
        if "<USER_REQUEST>" in e.content:
            assert e.meta["is_human"] is True
            assert e.meta["human_content"] == "/pull epic_XXXXXXXX"


def test_sidecar_user_prompts_filters_injected_content(tmp_path):
    """Criterion 6 & 7: user_prompts contains only human-typed prompts; injected content retained in injected_prompts."""
    human_event = NormalizedEvent(
        event_id="e1",
        timestamp="2026-08-04T10:00:00Z",
        source="user",
        type="message",
        content="Please run tests.",
        meta={
            "prompt_kind": "human_prompt",
            "is_human": True,
            "human_content": "Please run tests.",
            "injected_content": "",
        },
    )
    injected_event = NormalizedEvent(
        event_id="e2",
        timestamp="2026-08-04T10:01:00Z",
        source="user",
        type="message",
        content="<system-reminder>Do not leak credentials</system-reminder>",
        meta={
            "prompt_kind": "system_reminder",
            "is_human": False,
            "human_content": "",
            "injected_content": "<system-reminder>Do not leak credentials</system-reminder>",
        },
    )
    session = NormalizedSession(
        session_id="test_sess",
        source_file=Path("dummy.jsonl"),
        events=[human_event, injected_event],
    )

    sidecar = build_json_sidecar(
        session=session,
        slug="test-slug",
        started_at="2026-08-04T10:00:00Z",
        last_modified="2026-08-04T10:01:00Z",
        ended_at="2026-08-04T10:01:00Z",
        has_user_context=True,
        correlation={},
        insights=None,
    )

    # user_prompts must only contain the human prompt
    prompt_texts = [p["text"] for p in sidecar["user_prompts"]]
    assert prompt_texts == ["Please run tests."]
    assert "<system-reminder>" not in " ".join(prompt_texts)

    # injected_prompts must retain the injected prompt
    injected_texts = [p["text"] for p in sidecar["injected_prompts"]]
    assert len(injected_texts) == 1
    assert "<system-reminder>" in injected_texts[0]
    assert sidecar["injected_prompts"][0]["kind"] == "system_reminder"


def test_markdown_and_html_distinction_rendering():
    """Criterion 4 & 5: Rendered markdown and HTML make human content immediately distinguishable from injected content."""
    human_event = NormalizedEvent(
        event_id="e1",
        timestamp="2026-08-04T10:00:00Z",
        source="user",
        type="message",
        content="Deploy the application",
        meta={
            "prompt_kind": "human_prompt",
            "is_human": True,
            "human_content": "Deploy the application",
            "injected_content": "",
        },
    )
    injected_event = NormalizedEvent(
        event_id="e2",
        timestamp="2026-08-04T10:01:00Z",
        source="user",
        type="message",
        content="<system-reminder>Remember security checks</system-reminder>",
        meta={
            "prompt_kind": "system_reminder",
            "is_human": False,
            "human_content": "",
            "injected_content": "<system-reminder>Remember security checks</system-reminder>",
        },
    )
    session = NormalizedSession(
        session_id="test_sess",
        source_file=Path("dummy.jsonl"),
        events=[human_event, injected_event],
    )

    md = render_to_full_markdown(
        session=session,
        slug="test-slug",
        started_at="2026-08-04T10:00:00Z",
        last_modified="2026-08-04T10:01:00Z",
        ended_at="2026-08-04T10:01:00Z",
        has_user_context=True,
        correlation={},
        insights=None,
    )

    assert "#### 🤷 User" in md
    assert "#### 📌 Injected Context (`system_reminder`)" in md
    assert "> **Injected Context (`system_reminder`):**" in md

    html = render_to_html(
        session=session,
        slug="test-slug",
        started_at="2026-08-04T10:00:00Z",
        last_modified="2026-08-04T10:01:00Z",
        ended_at="2026-08-04T10:01:00Z",
        has_user_context=True,
        correlation={},
        insights=None,
    )

    assert 'class="event user human"' in html
    assert 'class="event user injected"' in html
    assert "Human Prompt" in html
    assert "Injected Context" in html


def test_prompt_ledger_generation_with_filtered_sidecars(tmp_path):
    """Criterion 8: Prompt ledger still generates correctly using user_prompts."""
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir(parents=True)

    sidecar_data = {
        "session_id": "1234567890",
        "has_user_context": True,
        "started_at": "2026-08-04T10:00:00Z",
        "project": "test-proj",
        "user_prompts": [{"text": "Fix the pipeline bug", "timestamp": "2026-08-04T10:00:00Z"}],
        "injected_prompts": [
            {"text": "<system-reminder>rule</system-reminder>", "timestamp": "2026-08-04T10:00:00Z"}
        ],
    }

    import json

    (transcripts_dir / "sidecar.json").write_text(json.dumps(sidecar_data), encoding="utf-8")

    res = generate_prompt_ledger(tmp_path, since_arg=None)
    assert res == 0

    ledger_content = (tmp_path / "state" / "prompt_ledger.md").read_text(encoding="utf-8")
    assert "Fix the pipeline bug" in ledger_content
    assert "<system-reminder>" not in ledger_content
