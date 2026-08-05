"""Unit tests for run record folding into session transcript renderings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from transcripts.domain.renderer import (
    build_json_sidecar,
    render_session_to_all_formats,
    render_to_full_markdown,
    render_to_html,
    render_to_markdown,
)
from transcripts.model import NormalizedEvent, NormalizedSession


def _make_sample_session(session_id: str = "session-123") -> NormalizedSession:
    return NormalizedSession(
        session_id=session_id,
        source_file=Path("sample.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e1",
                timestamp="2026-08-05T12:00:00Z",
                source="user",
                type="message",
                content="Please complete the task.",
            ),
            NormalizedEvent(
                event_id="e2",
                timestamp="2026-08-05T12:00:10Z",
                source="model",
                type="message",
                content="Done successfully.",
            ),
        ],
        tokens_used=1500,
        cost_usd=0.005,
    )


def _make_sample_run_record() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "session_id": "session-123",
        "container_id": "c1234567890a",
        "container_name": "polecat-session-123",
        "agent": "claude",
        "task_id": "aops_332181bf",
        "seeded_prompt": "/pull aops_332181bf",
        "commit_start": "abc1234",
        "commit_end": "def5678",
        "exit_code": 0,
        "status": "success",
        "delivery_guard": {"ok": True, "error": None},
        "duration_seconds": 45.2,
        "worker_model": "claude-3-5-sonnet",
    }


def test_render_to_markdown_with_run_record() -> None:
    session = _make_sample_session()
    run_rec = _make_sample_run_record()

    md = render_to_markdown(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=True,
        correlation={"project": "aops", "task_id": "aops_332181bf", "pr_number": None},
        insights=None,
        run_record=run_rec,
    )

    # Check YAML front matter includes run record fields
    assert "status: success" in md
    assert "exit_code: 0" in md
    assert "commit_start: abc1234" in md
    assert "commit_end: def5678" in md
    assert "agent: claude" in md
    assert "worker_model: claude-3-5-sonnet" in md
    assert "duration_seconds: 45.2" in md
    assert "container_name: polecat-session-123" in md

    # Check structured section header and questions answered
    assert "## ⚡ Run Record & Identity Chain" in md
    # What was this
    assert "**Agent:** `claude`" in md
    assert "**Model:** `claude-3-5-sonnet`" in md
    assert "**Container:** `polecat-session-123`" in md
    assert "**Seeded Prompt:** `/pull aops_332181bf`" in md
    # Did it work
    assert "**Status:** `success`" in md
    assert "**Exit Code:** `0`" in md
    assert "**Duration:** `45.2s`" in md
    # At what commit
    assert "**Commit Chain:** `abc1234` → `def5678`" in md


def test_render_to_full_markdown_with_run_record() -> None:
    session = _make_sample_session()
    run_rec = _make_sample_run_record()

    full_md = render_to_full_markdown(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=True,
        correlation={"project": "aops", "task_id": "aops_332181bf", "pr_number": None},
        insights=None,
        run_record=run_rec,
    )

    assert "## ⚡ Run Record & Identity Chain" in full_md
    assert "**Agent:** `claude`" in full_md
    assert "**Commit Chain:** `abc1234` → `def5678`" in full_md


def test_render_to_html_with_run_record() -> None:
    session = _make_sample_session()
    run_rec = _make_sample_run_record()

    html = render_to_html(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=True,
        correlation={"project": "aops", "task_id": "aops_332181bf", "pr_number": None},
        insights=None,
        run_record=run_rec,
    )

    assert "Status" in html
    assert "badge status-badge status-success" in html
    assert "Exit Code" in html
    assert "Commit Chain" in html
    assert "abc1234" in html
    assert "def5678" in html
    assert "Worker / Model" in html
    assert "claude (claude-3-5-sonnet)" in html
    assert "Duration" in html
    assert "45.2s" in html


def test_build_json_sidecar_with_run_record() -> None:
    session = _make_sample_session()
    run_rec = _make_sample_run_record()

    sidecar = build_json_sidecar(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=True,
        correlation={"project": "aops", "task_id": "aops_332181bf", "pr_number": None},
        insights=None,
        run_record=run_rec,
    )

    assert "run_record" in sidecar
    assert sidecar["run_record"] == run_rec


def test_render_session_to_all_formats_with_run_record() -> None:
    session = _make_sample_session()
    run_rec = _make_sample_run_record()

    md, html, json_sidecar = render_session_to_all_formats(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=True,
        correlation={"project": "aops", "task_id": "aops_332181bf", "pr_number": None},
        insights=None,
        run_record=run_rec,
    )

    assert "## ⚡ Run Record & Identity Chain" in md
    assert "status-success" in html
    assert json_sidecar["run_record"] == run_rec


def test_session_attribute_run_record_fallback() -> None:
    session = _make_sample_session()
    run_rec = _make_sample_run_record()
    session.run_record = run_rec

    # Call without passing run_record parameter explicitly
    md = render_to_markdown(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=True,
        correlation={"project": "aops"},
        insights=None,
    )

    assert "## ⚡ Run Record & Identity Chain" in md
    assert "status: success" in md

    sidecar = build_json_sidecar(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=True,
        correlation={"project": "aops"},
        insights=None,
    )
    assert sidecar["run_record"] == run_rec


def test_null_and_empty_run_record_fallback() -> None:
    session = _make_sample_session()

    # 1. run_record is None
    md = render_to_markdown(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=True,
        correlation={"project": "aops"},
        insights=None,
        run_record=None,
    )

    assert "## ⚡ Run Record & Identity Chain" not in md
    assert "status:" not in md
    assert "commit_start:" not in md

    html = render_to_html(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=True,
        correlation={"project": "aops"},
        insights=None,
        run_record=None,
    )
    assert '<span class="badge status-badge' not in html

    sidecar = build_json_sidecar(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=True,
        correlation={"project": "aops"},
        insights=None,
        run_record=None,
    )
    assert sidecar["run_record"] is None

    # 2. run_record is empty dict {}
    md_empty = render_to_markdown(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=True,
        correlation={"project": "aops"},
        insights=None,
        run_record={},
    )
    assert "## ⚡ Run Record & Identity Chain" not in md_empty


def test_delivery_guard_error_rendering() -> None:
    session = _make_sample_session()
    run_rec = {
        "agent": "Worker",
        "status": "delivery_guard_failed",
        "exit_code": 0,
        "delivery_guard": {"ok": False, "error": "Uncommitted changes in repository"},
    }

    md = render_to_markdown(
        session=session,
        slug="test-slug",
        started_at="2026-08-05T12:00:00Z",
        last_modified="2026-08-05T12:00:10Z",
        ended_at="2026-08-05T12:00:10Z",
        has_user_context=False,
        correlation={"project": "aops"},
        insights=None,
        run_record=run_rec,
    )

    assert "## ⚡ Run Record & Identity Chain" in md
    assert "**Status:** `delivery_guard_failed`" in md
    assert "**Delivery Guard Error:** Uncommitted changes in repository" in md
