#!/usr/bin/env python3
"""Tests for `polecat analyze` post-mortem diagnostics (#487).

Covers the structured exit-metadata pipeline end to end:

  build_exit_metadata  →  write_exit_metadata  →  read_exit_metadata
                       →  `polecat analyze`  /  format_exit_oneline

The headline integration test (`test_compliance_blocked_dispatch_then_analyze`)
exercises the AC#4 path: it reproduces the artifacts a polecat *designed to
fail on the compliance gate* leaves behind — a turn transcript plus agent
output carrying the enforcer's OVERDUE block message — feeds them through the
real `build_exit_metadata` derivation, persists them, then runs `polecat
analyze` and asserts the rendered summary reports the correct `exit_reason`
and `turns_used`.

We reproduce the dispatch *artifacts* rather than spinning a real Docker
container + Claude session, matching the rest of the polecat test suite (see
test_cli_list.py) which mocks the container boundary — there is no Docker or
live agent in unit CI.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from cli import main  # noqa: E402
from postmortem import (  # noqa: E402
    build_exit_metadata,
    detect_compliance_block,
    format_exit_oneline,
    read_exit_metadata,
    write_exit_metadata,
)

# The enforcer-gate OVERDUE block message, verbatim from
# aops-core/hooks/templates/enforcer-policy-message.md — the signal a
# compliance-blocked polecat leaves in its output.
COMPLIANCE_BLOCK_OUTPUT = (
    "Working on the task...\n"
    "✕ Compliance check required (22 ops since last check). ◇\n"
    "ERROR: Compliance check OVERDUE. You need to invoke the enforcer agent.\n"
)


def _fake_task(task_id="task-cbc44700"):
    return SimpleNamespace(
        id=task_id,
        title="Update VISION.md",
        status="in_progress",
        assignee=None,
        project="mem",
        priority=2,
        modified=None,
        depends_on=[],
        pr_url=None,
        pr=None,
    )


def _write_transcript(path: Path, n_assistant_turns: int) -> Path:
    """Write a fake Claude session transcript with N assistant turns."""
    lines = []
    for i in range(n_assistant_turns):
        lines.append(json.dumps({"type": "user", "message": f"prompt {i}"}))
        lines.append(json.dumps({"type": "assistant", "message": f"response {i}"}))
    path.write_text("\n".join(lines) + "\n")
    return path


# ---------------------------------------------------------------------------
# detect_compliance_block
# ---------------------------------------------------------------------------


class TestDetectComplianceBlock:
    def test_overdue_block_is_detected(self):
        blocked, countdown = detect_compliance_block(COMPLIANCE_BLOCK_OUTPUT, "")
        assert blocked is True
        assert countdown == 0  # overdue => 0 remaining

    def test_countdown_warning_is_not_a_block(self):
        # The non-blocking countdown warning must NOT be read as a block.
        out = "◇ 5 turns until compliance check.\nstill working\n"
        blocked, countdown = detect_compliance_block(out, "")
        assert blocked is False
        assert countdown == 5

    def test_clean_output_is_not_a_block(self):
        blocked, countdown = detect_compliance_block("all good\n", "")
        assert blocked is False
        assert countdown == 0


# ---------------------------------------------------------------------------
# build_exit_metadata — exit_reason derivation
# ---------------------------------------------------------------------------


class TestBuildExitMetadata:
    def test_compliance_blocked_path(self, tmp_path):
        transcript = _write_transcript(tmp_path / "session.jsonl", 11)
        meta = build_exit_metadata(
            task=_fake_task(),
            exit_code=1,
            stdout=COMPLIANCE_BLOCK_OUTPUT,
            stderr="",
            worktree_path=None,
            real_transcript=transcript,
            turns_max=30,
            budget_exhausted=False,
        )
        assert meta["exit_reason"] == "compliance_blocked"
        assert meta["compliance_blocked"] is True
        assert meta["compliance_countdown_at_exit"] == 0
        assert meta["turns_used"] == 11
        assert meta["turns_max"] == 30
        assert meta["repo_cloned"] == "mem"
        assert meta["transcript_path"] == str(transcript)

    def test_max_turns_path(self, tmp_path):
        meta = build_exit_metadata(
            task=_fake_task(),
            exit_code=6,
            stdout="Reached max turns\n",
            stderr="",
            worktree_path=None,
            real_transcript=None,
            turns_max=40,
            budget_exhausted=True,
        )
        assert meta["exit_reason"] == "max_turns"
        # Falls back to turns_max when no transcript is available.
        assert meta["turns_used"] == 40

    def test_success_path(self):
        meta = build_exit_metadata(
            task=_fake_task(),
            exit_code=0,
            stdout="done\n",
            stderr="",
            worktree_path=None,
            real_transcript=None,
            turns_max=100,
            budget_exhausted=False,
        )
        assert meta["exit_reason"] == "success"

    def test_error_path(self):
        meta = build_exit_metadata(
            task=_fake_task(),
            exit_code=1,
            stdout="boom\n",
            stderr="traceback\n",
            worktree_path=None,
            real_transcript=None,
            turns_max=100,
            budget_exhausted=False,
        )
        assert meta["exit_reason"] == "error"

    def test_compliance_block_wins_over_max_turns(self, tmp_path):
        # A block that also exhausts the budget reports the block (root cause).
        meta = build_exit_metadata(
            task=_fake_task(),
            exit_code=6,
            stdout=COMPLIANCE_BLOCK_OUTPUT + "Reached max turns\n",
            stderr="",
            worktree_path=None,
            real_transcript=None,
            turns_max=30,
            budget_exhausted=True,
        )
        assert meta["exit_reason"] == "compliance_blocked"


# ---------------------------------------------------------------------------
# write / read round-trip
# ---------------------------------------------------------------------------


class TestReadWriteRoundTrip:
    def test_round_trip_returns_last_exit_metadata(self, tmp_path, monkeypatch):
        monkeypatch.setenv("POLECAT_HOME", str(tmp_path))
        meta = {"type": "exit_metadata", "exit_reason": "success", "turns_used": 3}
        write_exit_metadata("task-abc12300", meta, tmp_path)
        got = read_exit_metadata("task-abc12300", home_dir=tmp_path)
        assert got is not None
        assert got["exit_reason"] == "success"
        assert got["turns_used"] == 3

    def test_read_missing_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setenv("POLECAT_HOME", str(tmp_path))
        assert read_exit_metadata("task-doesnotexist", home_dir=tmp_path) is None


# ---------------------------------------------------------------------------
# format_exit_oneline (used by `polecat list`)
# ---------------------------------------------------------------------------


class TestFormatExitOneline:
    def test_none_metadata_is_empty(self):
        assert format_exit_oneline(None) == ""

    def test_compliance_block_oneline(self):
        meta = {
            "exit_reason": "compliance_blocked",
            "turns_used": 11,
            "turns_max": 30,
            "commits_count": 0,
        }
        line = format_exit_oneline(meta)
        assert "compliance_blocked" in line
        assert "11/30 turns" in line


# ---------------------------------------------------------------------------
# AC#4 — integration: compliance-blocked dispatch artifacts → `polecat analyze`
# ---------------------------------------------------------------------------


class TestAnalyzeIntegration:
    def test_compliance_blocked_dispatch_then_analyze(self, tmp_path, monkeypatch):
        monkeypatch.setenv("POLECAT_HOME", str(tmp_path))
        task = _fake_task()

        # 1. Reproduce the artifacts a compliance-blocked polecat leaves behind:
        #    a turn transcript (11 assistant turns) + the enforcer block output.
        transcript = _write_transcript(tmp_path / "session.jsonl", 11)
        meta = build_exit_metadata(
            task=task,
            exit_code=1,
            stdout=COMPLIANCE_BLOCK_OUTPUT,
            stderr="",
            worktree_path=None,
            real_transcript=transcript,
            turns_max=30,
            budget_exhausted=False,
        )
        write_exit_metadata(task.id, meta, tmp_path)

        # 2. Run `polecat analyze <task-id>` with the task resolvable and no
        #    worktree present (already cleaned up) — must degrade gracefully.
        fake_manager = SimpleNamespace(
            storage=None,
            home_dir=tmp_path,
            polecats_dir=tmp_path / "worktrees",
            verbose=False,
        )
        runner = CliRunner()
        with (
            patch("diagnostics.PolecatManager", return_value=fake_manager),
            patch("polecat.pkb_bridge.get_task", return_value=task),
        ):
            result = runner.invoke(main, ["analyze", task.id])

        assert result.exit_code == 0, result.output
        # 3. The summary reports the right exit_reason + turns_used.
        assert "POST-MORTEM" in result.output
        assert "compliance_blocked" in result.output
        assert "11/30" in result.output
        # Missing worktree handled gracefully, not crashed.
        assert "Worktree not found" in result.output

    def test_analyze_without_exit_metadata(self, tmp_path, monkeypatch):
        monkeypatch.setenv("POLECAT_HOME", str(tmp_path))
        task = _fake_task("task-noexit00")
        fake_manager = SimpleNamespace(
            storage=None,
            home_dir=tmp_path,
            polecats_dir=tmp_path / "worktrees",
            verbose=False,
        )
        runner = CliRunner()
        with (
            patch("diagnostics.PolecatManager", return_value=fake_manager),
            patch("polecat.pkb_bridge.get_task", return_value=task),
        ):
            result = runner.invoke(main, ["analyze", task.id])

        assert result.exit_code == 0, result.output
        assert "No exit metadata" in result.output
