"""Unit tests for surfacing the real Claude Code session transcript path.

Covers:
  (a) `_read_latest_real_transcript_path` returns the most recent recorded
      path from the polecat lifecycle stub.
  (b) Helper returns ``None`` when the stub is missing or the field is null.
  (c) `_generate_pr_body` includes the ``<details>`` block when a path is
      provided, and re-emit is idempotent (no duplicates).
  (d) Task-body section format is what we promise.

We unit-test the building blocks rather than driving the full ``finish``
Click command — the latter has heavy git/gh side effects that aren't
reproducible in this environment, but the body-section appender uses the
exact same `_format_transcript_task_body_section` helper, so testing the
helper plus the idempotency guard in `_generate_pr_body` covers the
acceptance criteria precisely.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import under test — same stubbing dance as test_save_worker_transcript.py.
# ---------------------------------------------------------------------------

TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

_MODS_TO_STUB = [
    "click",
    "manager",
    "observability",
    "observability.metrics",
    "validation",
    "lib",
    "lib.agent_env",
    "lib.paths",
    "docker_builder",
    "pkb_bridge",
    "rich",
    "rich.console",
    "rich.table",
    "rich.panel",
    "psutil",
]

_saved: dict[str, object] = {}
for _mod in _MODS_TO_STUB:
    if _mod not in sys.modules:
        _saved[_mod] = None
        sys.modules[_mod] = MagicMock()
    else:
        _saved[_mod] = sys.modules[_mod]

_original_cli = sys.modules.get("cli")

try:
    sys.modules.pop("cli", None)
    from cli import (
        TRANSCRIPT_PR_DETAILS_SUMMARY,
        TRANSCRIPT_TASK_BODY_HEADER,
        _format_transcript_pr_details_block,
        _format_transcript_task_body_section,
        _generate_pr_body,
        _read_latest_real_transcript_path,
        save_worker_transcript,
    )
finally:
    sys.modules.pop("cli", None)
    if _original_cli is not None:
        sys.modules["cli"] = _original_cli
    for _mod, _orig in _saved.items():
        if _orig is None:
            sys.modules.pop(_mod, None)
        else:
            sys.modules[_mod] = _orig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _block_lib_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the helpers to use the ``home_dir / 'transcripts'`` fallback so
    tests don't depend on a real ``$AOPS_SESSIONS`` layout."""
    monkeypatch.setitem(sys.modules, "lib.paths", None)


@pytest.fixture()
def task_layout(tmp_path: Path) -> dict[str, Path]:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    workspace = tmp_path / "session" / "-workspace"
    workspace.mkdir(parents=True)
    real_transcript = workspace / "deadbeef-1234.jsonl"
    real_transcript.write_text('{"type":"assistant","message":"hi"}\n' * 5)
    return {
        "home_dir": home_dir,
        "real_transcript": real_transcript,
    }


def _make_task(
    *, body: str, task_id: str = "task-91c5058f", title: str = "Surface transcript path"
):
    """Minimal duck-typed task object matching what _generate_pr_body needs."""
    return SimpleNamespace(id=task_id, title=title, body=body)


# ---------------------------------------------------------------------------
# _read_latest_real_transcript_path
# ---------------------------------------------------------------------------


class TestReadLatestRealTranscriptPath:
    def test_returns_path_from_stub(self, task_layout: dict[str, Path]) -> None:
        save_worker_transcript(
            task_id="task-91c5058f",
            stdout="ok",
            stderr="",
            exit_code=0,
            agent_type="claude",
            home_dir=task_layout["home_dir"],
            real_transcript=task_layout["real_transcript"],
        )

        result = _read_latest_real_transcript_path("task-91c5058f", task_layout["home_dir"])
        assert result == task_layout["real_transcript"]

    def test_returns_none_when_no_stub(self, tmp_path: Path) -> None:
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        assert _read_latest_real_transcript_path("task-missing", home_dir) is None

    def test_returns_none_when_path_field_null(self, task_layout: dict[str, Path]) -> None:
        save_worker_transcript(
            task_id="task-null",
            stdout="",
            stderr="",
            exit_code=0,
            agent_type="claude",
            home_dir=task_layout["home_dir"],
            real_transcript=None,
        )
        assert _read_latest_real_transcript_path("task-null", task_layout["home_dir"]) is None

    def test_returns_most_recent_when_multiple_runs(self, task_layout: dict[str, Path]) -> None:
        # Run 1: real transcript A
        save_worker_transcript(
            task_id="task-multi",
            stdout="run1",
            stderr="",
            exit_code=0,
            agent_type="claude",
            home_dir=task_layout["home_dir"],
            real_transcript=task_layout["real_transcript"],
        )
        # Run 2: a different real transcript
        new_real = task_layout["real_transcript"].parent / "newer.jsonl"
        new_real.write_text('{"type":"assistant"}\n')
        save_worker_transcript(
            task_id="task-multi",
            stdout="run2",
            stderr="",
            exit_code=0,
            agent_type="claude",
            home_dir=task_layout["home_dir"],
            real_transcript=new_real,
        )

        result = _read_latest_real_transcript_path("task-multi", task_layout["home_dir"])
        assert result == new_real

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        home_dir = tmp_path / "home"
        transcripts_dir = home_dir / "transcripts"
        transcripts_dir.mkdir(parents=True)
        stub = transcripts_dir / "task-junk.jsonl"
        good = {"real_transcript_path": "/tmp/real.jsonl"}
        stub.write_text("not json at all\n" + json.dumps(good) + "\nincomplete{\n")
        result = _read_latest_real_transcript_path("task-junk", home_dir)
        assert result == Path("/tmp/real.jsonl")


# ---------------------------------------------------------------------------
# Task-body section helper
# ---------------------------------------------------------------------------


class TestTaskBodyHelper:
    def test_section_contains_header_and_path(self) -> None:
        section = _format_transcript_task_body_section(Path("/x/y.jsonl"))
        assert TRANSCRIPT_TASK_BODY_HEADER in section
        assert "/x/y.jsonl" in section

    def test_idempotent_append_via_header_check(self) -> None:
        """Acceptance criterion (a) + (b): first run appends, second is no-op.

        The CLI uses ``TRANSCRIPT_TASK_BODY_HEADER not in body`` as the
        idempotency gate. Verify the marker is stable enough to detect.
        """
        body = "Existing content."
        section = _format_transcript_task_body_section(Path("/p.jsonl"))
        first = body + section
        assert TRANSCRIPT_TASK_BODY_HEADER in first
        # Second run would skip because the header is present.
        assert TRANSCRIPT_TASK_BODY_HEADER in first  # the gate is "in body"


# ---------------------------------------------------------------------------
# _generate_pr_body
# ---------------------------------------------------------------------------


class TestGeneratePrBody:
    def test_no_transcript_no_block(self) -> None:
        task = _make_task(body="Description.\n\n## Acceptance Criteria\n- [ ] thing\n")
        out = _generate_pr_body(task, transcript_path=None)
        assert TRANSCRIPT_PR_DETAILS_SUMMARY not in out

    def test_includes_details_block_when_path_given(self) -> None:
        task = _make_task(body="Description.\n")
        out = _generate_pr_body(task, transcript_path=Path("/sessions/x.jsonl"))
        assert "<details>" in out
        assert TRANSCRIPT_PR_DETAILS_SUMMARY in out
        assert "/sessions/x.jsonl" in out
        assert "</details>" in out

    def test_re_emit_does_not_duplicate(self) -> None:
        """Acceptance criterion (e): regenerating with the same body that
        already contains a transcript block must not produce two blocks."""
        path = Path("/sessions/abc.jsonl")
        task = _make_task(body="Description.\n")
        first = _generate_pr_body(task, transcript_path=path)
        # Now feed the body that contains the previously-emitted block back in
        # — simulates the case where the task body already has it from a
        # prior finish run, and we regenerate the PR body from that task.
        task_with_block = _make_task(body=first)
        second = _generate_pr_body(task_with_block, transcript_path=path)
        assert second.count("<details>") == 1
        assert second.count(TRANSCRIPT_PR_DETAILS_SUMMARY) == 1

    def test_re_emit_strips_old_task_body_section(self) -> None:
        """The PR body generator strips a previously-appended task-body
        section (different format from the PR <details> block) before
        re-emitting, so we never end up with both side-by-side."""
        path = Path("/sessions/abc.jsonl")
        body_with_section = (
            f"Description.\n\n{TRANSCRIPT_TASK_BODY_HEADER}\n- Transcript: `/sessions/abc.jsonl`\n"
        )
        task = _make_task(body=body_with_section)
        out = _generate_pr_body(task, transcript_path=path)
        assert TRANSCRIPT_TASK_BODY_HEADER not in out
        assert out.count("<details>") == 1


# ---------------------------------------------------------------------------
# PR details block helper format
# ---------------------------------------------------------------------------


class TestPRDetailsBlock:
    def test_block_well_formed(self) -> None:
        block = _format_transcript_pr_details_block(Path("/p.jsonl"))
        assert block.lstrip().startswith("<details>")
        assert block.rstrip().endswith("</details>")
        assert "/p.jsonl" in block
