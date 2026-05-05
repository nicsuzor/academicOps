"""Tests for aops-core/scripts/close_loop.py — /sleep Phase 6 Activity 4a helper.

Coverage targets (per the Part B plan):
- Each match signal (pr_url, task_id_in_body, head_ref, title)
- Closed-without-merge → re-queued to inbox (always)
- Idempotency
- Cursor advancement
- Missing tracked-repos.json fallback to defaults
- CI no-op guard

The script is pure modulo the gh fetcher and PKB writes. The fetcher is injected
in `sweep_repo`; PKB writes are deferred (returned as a `PKBWrites` plan), so
nothing in the script reaches out to the network or the PKB MCP from these tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make `scripts` importable as `close_loop`.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import close_loop  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    p = tmp_path / "state"
    p.mkdir()
    return p


@pytest.fixture
def sample_tasks() -> list[dict]:
    return [
        {
            "id": "task-aaaa1111",
            "title": "Wire close-loop sweep",
            "branch": "feat/close-loop",
            "pr_url": None,
        },
        {
            "id": "task-bbbb2222",
            "title": "Add gate-1 verification audit",
            "branch": "feat/audit",
            "pr_url": "https://github.com/nicsuzor/academicOps/pull/123",
        },
        {
            "id": "task-cccc3333",
            "title": "Daily reads from sleep artefact",
            "branch": "feat/daily-artefact",
            "pr_url": None,
        },
        {
            "id": "task-dddd4444",
            "title": "Refactor planner gate",
            "branch": None,
            "pr_url": None,
        },
    ]


# ---------------------------------------------------------------------------
# Match precedence — one test per signal
# ---------------------------------------------------------------------------


class TestMatchPrecedence:
    def test_match_by_pr_url(self, sample_tasks):
        pr = {
            "number": 123,
            "title": "something completely unrelated",
            "url": "https://github.com/nicsuzor/academicOps/pull/123",
            "headRefName": "irrelevant-branch",
            "body": "no task ids here",
        }
        m = close_loop.match_pr_to_task(pr, sample_tasks)
        assert m.signal == "pr_url"
        assert m.task_id == "task-bbbb2222"

    def test_match_by_task_id_in_body(self, sample_tasks):
        pr = {
            "number": 200,
            "title": "Different title",
            "url": "https://github.com/nicsuzor/academicOps/pull/200",
            "headRefName": "some/branch",
            "body": "Closes task-aaaa1111 — see linked task for context.",
        }
        m = close_loop.match_pr_to_task(pr, sample_tasks)
        assert m.signal == "task_id_in_body"
        assert m.task_id == "task-aaaa1111"

    def test_match_by_head_ref(self, sample_tasks):
        pr = {
            "number": 201,
            "title": "Some other thing",
            "url": "https://github.com/nicsuzor/academicOps/pull/201",
            "headRefName": "feat/daily-artefact",
            "body": "(no task id mentioned)",
        }
        m = close_loop.match_pr_to_task(pr, sample_tasks)
        assert m.signal == "head_ref"
        assert m.task_id == "task-cccc3333"

    def test_match_by_title_with_conventional_prefix(self, sample_tasks):
        pr = {
            "number": 202,
            "title": "feat(planner): Refactor planner gate",
            "url": "https://github.com/nicsuzor/academicOps/pull/202",
            "headRefName": "totally/different",
            "body": "no ids",
        }
        m = close_loop.match_pr_to_task(pr, sample_tasks)
        assert m.signal == "title"
        assert m.task_id == "task-dddd4444"

    def test_no_match(self, sample_tasks):
        pr = {
            "number": 203,
            "title": "Something nobody is tracking",
            "url": "https://github.com/nicsuzor/x/pull/203",
            "headRefName": "rando",
            "body": "just text",
        }
        m = close_loop.match_pr_to_task(pr, sample_tasks)
        assert m.signal == "none"
        assert m.task_id is None


# ---------------------------------------------------------------------------
# Closed-without-merge → re-queued to inbox (always)
# ---------------------------------------------------------------------------


def test_closed_without_merge_requeues_to_inbox(sample_tasks):
    closed_prs = [
        {
            "number": 999,
            "title": "feat: Wire close-loop sweep",
            "url": "https://github.com/nicsuzor/academicOps/pull/999",
            "headRefName": "feat/close-loop",
            "mergedAt": None,
            "closedAt": "2026-05-04T10:00:00Z",
            "body": "rejected by reviewer",
            "state": "CLOSED",
        }
    ]
    result = close_loop.sweep_repo(
        repo="nicsuzor/academicOps",
        tasks=sample_tasks,
        cursor=None,
        fetcher=lambda repo, since: closed_prs,
        open_fetcher=lambda repo: [],
    )
    assert len(result.writes.requeued) == 1
    assert len(result.writes.completed) == 0
    rq = result.writes.requeued[0]
    assert rq["task_id"] == "task-aaaa1111"
    assert "re-queued to inbox" in rq["annotation"]


def test_merged_pr_marks_completed(sample_tasks):
    closed_prs = [
        {
            "number": 1000,
            "title": "feat: Wire close-loop sweep",
            "url": "https://github.com/nicsuzor/academicOps/pull/1000",
            "headRefName": "feat/close-loop",
            "mergedAt": "2026-05-04T11:00:00Z",
            "closedAt": "2026-05-04T11:00:00Z",
            "body": "merged via auto",
            "state": "MERGED",
        }
    ]
    result = close_loop.sweep_repo(
        repo="nicsuzor/academicOps",
        tasks=sample_tasks,
        cursor=None,
        fetcher=lambda repo, since: closed_prs,
        open_fetcher=lambda repo: [],
    )
    assert len(result.writes.completed) == 1
    assert len(result.writes.requeued) == 0
    c = result.writes.completed[0]
    assert c["task_id"] == "task-aaaa1111"
    assert "PR #1000 merged" in c["completion_evidence"]
    assert "https://github.com/nicsuzor/academicOps/pull/1000" in c["completion_evidence"]


# ---------------------------------------------------------------------------
# Idempotency: running twice with the cursor in place yields no further writes
# ---------------------------------------------------------------------------


def test_sweep_idempotent_with_cursor(sample_tasks):
    closed_prs = [
        {
            "number": 1001,
            "title": "feat: Wire close-loop sweep",
            "url": "https://github.com/nicsuzor/academicOps/pull/1001",
            "headRefName": "feat/close-loop",
            "mergedAt": "2026-05-04T11:00:00Z",
            "closedAt": "2026-05-04T11:00:00Z",
            "body": "",
            "state": "MERGED",
        }
    ]

    call_log: list[str | None] = []

    def fetcher(repo, since):
        call_log.append(since)
        # Real gh would filter by `closed:>since`. Simulate that filter here so
        # idempotency is observable: once the cursor is past the PR's close time,
        # the fetch returns nothing.
        if since and since >= "2026-05-04T11:00:00Z":
            return []
        return closed_prs

    # First run: cursor is None, PR comes back, it gets completed.
    r1 = close_loop.sweep_repo(
        repo="nicsuzor/academicOps",
        tasks=sample_tasks,
        cursor=None,
        fetcher=fetcher,
        open_fetcher=lambda repo: [],
    )
    assert len(r1.writes.completed) == 1
    assert r1.new_cursor == "2026-05-04T11:00:00Z"

    # Second run: cursor == new_cursor → fetcher returns []; no writes.
    r2 = close_loop.sweep_repo(
        repo="nicsuzor/academicOps",
        tasks=sample_tasks,
        cursor=r1.new_cursor,
        fetcher=fetcher,
        open_fetcher=lambda repo: [],
    )
    assert r2.closed_prs_seen == 0
    assert len(r2.writes.completed) == 0
    assert len(r2.writes.requeued) == 0
    # cursor is preserved (no new max)
    assert r2.new_cursor == r1.new_cursor


# ---------------------------------------------------------------------------
# Cursor advancement
# ---------------------------------------------------------------------------


def test_cursor_advances_to_max_close_time(sample_tasks):
    closed_prs = [
        {
            "number": 1,
            "title": "feat: Wire close-loop sweep",
            "url": "https://github.com/nicsuzor/academicOps/pull/1",
            "headRefName": "feat/close-loop",
            "mergedAt": "2026-05-01T10:00:00Z",
            "closedAt": "2026-05-01T10:00:00Z",
            "body": "",
            "state": "MERGED",
        },
        {
            "number": 2,
            "title": "feat(planner): Refactor planner gate",
            "url": "https://github.com/nicsuzor/academicOps/pull/2",
            "headRefName": "irrelevant",
            "mergedAt": "2026-05-04T18:00:00Z",
            "closedAt": "2026-05-04T18:00:00Z",
            "body": "",
            "state": "MERGED",
        },
    ]
    result = close_loop.sweep_repo(
        repo="nicsuzor/academicOps",
        tasks=sample_tasks,
        cursor=None,
        fetcher=lambda repo, since: closed_prs,
        open_fetcher=lambda repo: [],
    )
    assert result.new_cursor == "2026-05-04T18:00:00Z"


def test_save_and_load_cursor_roundtrip(state_dir):
    cursor_file = state_dir / "close-loop-cursor.json"
    payload = {
        "nicsuzor/academicOps": "2026-05-04T18:00:00Z",
        "nicsuzor/brain": "2026-05-03T09:00:00Z",
    }
    close_loop.save_cursor(payload, cursor_file)
    loaded = close_loop.load_cursor(cursor_file)
    assert loaded == payload


# ---------------------------------------------------------------------------
# Missing tracked-repos.json → fallback to defaults
# ---------------------------------------------------------------------------


def test_missing_tracked_repos_falls_back_to_defaults(state_dir):
    missing = state_dir / "tracked-repos.json"
    assert not missing.exists()
    repos = close_loop.load_tracked_repos(missing)
    assert repos == close_loop.DEFAULT_TRACKED_REPOS
    # And those defaults explicitly include both expected repos.
    assert "nicsuzor/academicOps" in repos
    assert "nicsuzor/brain" in repos


def test_malformed_tracked_repos_falls_back_to_defaults(state_dir):
    bad = state_dir / "tracked-repos.json"
    bad.write_text("{not valid json")
    repos = close_loop.load_tracked_repos(bad)
    assert repos == close_loop.DEFAULT_TRACKED_REPOS


def test_ensure_tracked_repos_file_creates_default(state_dir):
    p = state_dir / "tracked-repos.json"
    assert not p.exists()
    close_loop.ensure_tracked_repos_file(p)
    assert p.exists()
    data = json.loads(p.read_text())
    assert data == {"repos": list(close_loop.DEFAULT_TRACKED_REPOS)}


def test_ensure_tracked_repos_file_is_idempotent(state_dir):
    p = state_dir / "tracked-repos.json"
    p.write_text(json.dumps({"repos": ["nicsuzor/custom"]}))
    close_loop.ensure_tracked_repos_file(p)
    # Existing file is preserved — never overwritten.
    data = json.loads(p.read_text())
    assert data == {"repos": ["nicsuzor/custom"]}


# ---------------------------------------------------------------------------
# CI no-op guard
# ---------------------------------------------------------------------------


class TestCINoopGuard:
    def test_is_ci_environment_detects_github_actions(self, monkeypatch):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("CLOSE_LOOP_FORCE_CI_NOOP", raising=False)
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        assert close_loop.is_ci_environment() is True

    def test_is_ci_environment_detects_force_flag(self, monkeypatch):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.setenv("CLOSE_LOOP_FORCE_CI_NOOP", "1")
        assert close_loop.is_ci_environment() is True

    def test_not_ci_when_unset(self, monkeypatch):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("CLOSE_LOOP_FORCE_CI_NOOP", raising=False)
        assert close_loop.is_ci_environment() is False

    def test_main_writes_noop_artefact_in_ci(self, state_dir, monkeypatch, capsys):
        monkeypatch.setenv("CLOSE_LOOP_FORCE_CI_NOOP", "1")
        rc = close_loop.main(["--state-dir", str(state_dir)])
        assert rc == 0
        artefact = state_dir / "pr-state.json"
        assert artefact.exists()
        payload = json.loads(artefact.read_text())
        assert payload.get("ci_noop") is True
        assert "PKB MCP unavailable" in payload.get("reason", "")
        # CI guard does NOT advance cursors or write tracked-repos.json.
        assert not (state_dir / "close-loop-cursor.json").exists()
        out = capsys.readouterr().out
        assert "CI environment detected" in out


# ---------------------------------------------------------------------------
# Artefact write smoke test
# ---------------------------------------------------------------------------


def test_write_artefact_includes_per_repo_counts(state_dir, sample_tasks):
    closed_prs = [
        {
            "number": 1,
            "title": "feat: Wire close-loop sweep",
            "url": "https://github.com/nicsuzor/academicOps/pull/1",
            "headRefName": "feat/close-loop",
            "mergedAt": "2026-05-01T10:00:00Z",
            "closedAt": "2026-05-01T10:00:00Z",
            "body": "",
            "state": "MERGED",
        },
        {
            "number": 2,
            "title": "Unmatchable thing",
            "url": "https://github.com/nicsuzor/academicOps/pull/2",
            "headRefName": "x",
            "mergedAt": None,
            "closedAt": "2026-05-02T10:00:00Z",
            "body": "",
            "state": "CLOSED",
        },
    ]
    result = close_loop.sweep_repo(
        repo="nicsuzor/academicOps",
        tasks=sample_tasks,
        cursor=None,
        fetcher=lambda repo, since: closed_prs,
        open_fetcher=lambda repo: [],
    )
    artefact = close_loop.write_artefact([result], state_dir / "pr-state.json")
    payload = json.loads(artefact.read_text())
    assert payload["schema"] == 1
    assert "produced_at" in payload
    repo_block = payload["repos"]["nicsuzor/academicOps"]
    assert repo_block["closed_prs_seen"] == 2
    assert repo_block["completed_count"] == 1
    assert repo_block["ambiguous_count"] == 1
    assert repo_block["new_cursor"] == "2026-05-02T10:00:00Z"
