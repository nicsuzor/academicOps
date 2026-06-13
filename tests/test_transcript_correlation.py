"""Launch-context task/PR correlation for session summaries.

Dispatched and subagent sessions rarely touch the task tools in-session, so
``task_id`` / ``pull_requests`` were mostly null. ``_finalize_correlation``
recovers them from two launch-context signals:

* Lever A — the working branch is named after the task (``polecat/aops-...``),
  so the 8-hex id is lifted straight off ``git_branches``.
* Lever B — a subagent inherits its parent session's task_id / PRs (the parent
  id is encoded in its summary filename).

And ``_should_overwrite_existing`` gains triggers so a normal re-run backfills
these onto summaries that predate the feature, in place.

``transcript.py`` is loaded dynamically the same way the sibling
transcript-script tests do (it is not importable as a module).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def ts():
    repo_root = Path(__file__).parent.parent
    script_path = repo_root / "aops-core" / "scripts" / "transcript.py"
    spec = importlib.util.spec_from_file_location("transcript_script_corr", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["transcript_script_corr"] = module
    spec.loader.exec_module(module)
    return module


class _Stub:
    """Minimal stand-in for ParsedSession with the fields _finalize reads."""

    def __init__(self, **kw):
        self.task_id = kw.get("task_id")
        self.git_branches = kw.get("git_branches", [])
        self.repo = kw.get("repo")  # None => _resolve_pr_numbers returns [] (no network)
        self.parent_session = kw.get("parent_session")
        self.pull_requests = None


class TestTaskIdFromBranches:
    @pytest.mark.parametrize(
        "branch,expected",
        [
            ("polecat/aops-0e8d8079", "aops-0e8d8079"),
            ("crew/aops-12345678", "aops-12345678"),
            ("junior/aops-d9ba7159", "aops-d9ba7159"),
            ("feature/aops-deadbeef", "aops-deadbeef"),
            # 6-hex worktree suffix must NOT match (the {8} anchor discriminates)
            ("junior/silly-cray-59d71c", None),
            ("dev", None),
            ("main", None),
            ("release-please--branches--dev", None),
        ],
    )
    def test_single_branch(self, ts, branch, expected) -> None:
        assert ts._task_id_from_branches([branch]) == expected

    def test_first_qualifying_branch_wins_over_base(self, ts) -> None:
        assert ts._task_id_from_branches(["dev", "polecat/aops-0e8d8079"]) == "aops-0e8d8079"

    def test_empty(self, ts) -> None:
        assert ts._task_id_from_branches([]) is None


class TestFinalizeCorrelation:
    def test_lever_a_branch_derives_task_id(self, ts) -> None:
        s = _Stub(git_branches=["dev", "polecat/aops-0e8d8079"], repo=None)
        ts._finalize_correlation(s)
        assert s.task_id == "aops-0e8d8079"
        assert s.pull_requests == []

    def test_existing_task_id_takes_precedence_over_branch(self, ts) -> None:
        s = _Stub(task_id="aops-preexist", git_branches=["polecat/aops-0e8d8079"], repo=None)
        ts._finalize_correlation(s)
        assert s.task_id == "aops-preexist"

    def test_lever_b_inherits_from_parent(self, ts, tmp_path, monkeypatch) -> None:
        # Point the sessions repo at a tmp dir holding one parent summary.
        monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path))
        summaries = tmp_path / "summaries"
        summaries.mkdir()
        (summaries / "20260601-1200-deadbeef-aops-claude-session.json").write_text(
            json.dumps({"task_id": "aops-99887766", "pull_requests": [42]})
        )
        s = _Stub(git_branches=["dev"], repo=None, parent_session="deadbeef")
        ts._finalize_correlation(s)
        assert s.task_id == "aops-99887766"
        assert s.pull_requests == [42]

    def test_no_parent_no_branch_leaves_empty(self, ts) -> None:
        s = _Stub(git_branches=["dev"], repo=None)
        ts._finalize_correlation(s)
        assert s.task_id is None
        assert s.pull_requests == []


class TestPrSkipPrefixes:
    """polecat/ and crew/ branches carry real feature PRs (verified:
    polecat/aops-2ab6f912 -> #1037), so they must NOT be skipped during PR
    resolution. Only bot-release and ephemeral-worktree prefixes stay skipped.
    """

    def test_polecat_and_crew_not_skipped(self, ts) -> None:
        assert not any(p.startswith("polecat") for p in ts._PR_SKIP_PREFIXES)
        assert not any(p.startswith("crew") for p in ts._PR_SKIP_PREFIXES)

    def test_release_and_worktree_still_skipped(self, ts) -> None:
        assert "release-please--" in ts._PR_SKIP_PREFIXES
        assert "worktree-" in ts._PR_SKIP_PREFIXES


class TestOverwriteTriggers:
    def test_task_id_resolved_triggers_refresh(self, ts) -> None:
        new = {"timeline_events": [], "task_id": "aops-0e8d8079"}
        existing = {"timeline_events": [], "task_id": None}
        assert ts._should_overwrite_existing(new, existing) == "task_id resolved"

    def test_pull_requests_resolved_triggers_refresh(self, ts) -> None:
        new = {"timeline_events": [], "pull_requests": [7]}
        existing = {"timeline_events": []}
        assert ts._should_overwrite_existing(new, existing) == "pull_requests resolved"

    def test_no_correlation_change_still_skips(self, ts) -> None:
        new = {"timeline_events": [], "task_id": "aops-0e8d8079", "pull_requests": [7]}
        existing = {"timeline_events": [], "task_id": "aops-0e8d8079", "pull_requests": [7]}
        assert ts._should_overwrite_existing(new, existing) is None
