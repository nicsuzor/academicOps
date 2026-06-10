"""Behaviour tests for the read-only freshness-diff tool (epic-ef498cc7).

These test *behaviour*, not static codebase facts: each builds a real throwaway
git repo with a known commit history plus an anchor with a known recorded SHA,
runs the verdict, and asserts the band. The three bands (FRESH / DRIFTED /
STALE) and the UNKNOWN -> STALE fail-safe are each exercised.

Hermetic: no network, no live PKB, no live TJA repo — every fixture is built in
a tmp_path so the suite runs in CI. The live TJA dogfood (74 commits / 35 days
-> STALE against the real explorations repo) is recorded in the PR body; here we
reproduce its *shape* deterministically.
"""

from __future__ import annotations

import subprocess
import textwrap
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from lib.freshness import (
    Band,
    Thresholds,
    evaluate_anchor,
    evaluate_project,
    parse_anchor,
    read_repo_state,
)

# --------------------------------------------------------------------------- #
# Helpers — build a real git repo with N commits at controlled dates.
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str, env_date: str | None = None) -> str:
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }
    if env_date:
        env["GIT_AUTHOR_DATE"] = env_date
        env["GIT_COMMITTER_DATE"] = env_date
    import os

    full_env = {**os.environ, **env}
    out = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=full_env,
    )
    return out.stdout.strip()


def _commit(repo: Path, name: str, date: datetime) -> str:
    (repo / name).write_text(name, encoding="utf-8")
    iso = date.strftime("%Y-%m-%dT%H:%M:%S")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", name, env_date=iso)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo_factory(tmp_path):
    """Returns a builder: build(n_commits, days_apart, start) -> (repo, [shas])."""

    def build(
        n_commits: int, days_apart: int = 1, start: datetime | None = None
    ) -> tuple[Path, list[str]]:
        repo = tmp_path / f"repo_{n_commits}_{days_apart}"
        repo.mkdir()
        _git(repo, "init", "-q")
        start = start or datetime(2026, 4, 1, tzinfo=UTC)
        shas = []
        for i in range(n_commits):
            shas.append(_commit(repo, f"f{i}.txt", start + timedelta(days=i * days_apart)))
        return repo, shas

    return build


def _anchor_md(sha: str | None, modified: datetime | None, *, extra: str = "") -> str:
    fm = ["---", "id: test-anchor", "type: knowledge"]
    if modified:
        fm.append(f"modified: {modified.isoformat()}")
    if sha:
        fm.append(f"repo_head: {sha}")
    fm.append("---")
    return "\n".join(fm) + f"\n\n# Anchor body\n{extra}\n"


# --------------------------------------------------------------------------- #
# Band: FRESH
# --------------------------------------------------------------------------- #


def test_fresh_when_anchor_sha_equals_head(repo_factory):
    repo, shas = repo_factory(3)
    head = shas[-1]
    anchor = parse_anchor(text=_anchor_md(head, datetime(2026, 4, 4, tzinfo=UTC)))
    state = read_repo_state(repo)
    verdict = evaluate_anchor(anchor, state, repo=repo)
    assert verdict.band is Band.FRESH
    assert verdict.commits_behind == 0
    assert verdict.is_failsafe is False
    assert verdict.banner() == ""


def test_fresh_anchor_reconciled_after_head_is_not_behind(repo_factory):
    # Anchor modified *after* HEAD's date — a freshly reconciled anchor.
    repo, shas = repo_factory(2, start=datetime(2026, 4, 1, tzinfo=UTC))
    anchor = parse_anchor(text=_anchor_md(shas[-1], datetime(2026, 6, 10, tzinfo=UTC)))
    verdict = evaluate_anchor(anchor, read_repo_state(repo), repo=repo)
    assert verdict.band is Band.FRESH
    assert verdict.days_behind == 0  # clamped, not negative


# --------------------------------------------------------------------------- #
# Band: DRIFTED
# --------------------------------------------------------------------------- #


def test_drifted_a_few_commits_behind(repo_factory):
    # 5 commits behind, 5 days — below STALE thresholds (20 commits / 30 days).
    repo, shas = repo_factory(10, days_apart=1)
    anchor_sha = shas[4]  # HEAD is shas[9] -> 5 commits ahead
    anchor = parse_anchor(text=_anchor_md(anchor_sha, datetime(2026, 4, 5, tzinfo=UTC)))
    verdict = evaluate_anchor(anchor, read_repo_state(repo), repo=repo)
    assert verdict.band is Band.DRIFTED
    assert verdict.commits_behind == 5
    assert "commits / " in verdict.banner()


def test_drifted_from_unmentioned_artifacts_only(repo_factory):
    # 0 commits behind, but ground-truth report chapters the anchor never names.
    repo, shas = repo_factory(2)
    (repo / "report").mkdir()
    (repo / "report" / "methods.qmd").write_text("stub", encoding="utf-8")
    (repo / "report" / "results.qmd").write_text("data", encoding="utf-8")
    state = read_repo_state(repo, artifact_globs=["report/*.qmd"])
    anchor = parse_anchor(
        text=_anchor_md(shas[-1], datetime(2026, 4, 4, tzinfo=UTC)),
        artifact_terms=state.artifacts,
    )
    verdict = evaluate_anchor(anchor, state, repo=repo)
    assert verdict.band is Band.DRIFTED
    assert verdict.commits_behind == 0
    assert set(verdict.missing_artifacts) == {"methods.qmd", "results.qmd"}


# --------------------------------------------------------------------------- #
# Band: STALE (the TJA-shaped case)
# --------------------------------------------------------------------------- #


def test_stale_many_commits_behind(repo_factory):
    # Reproduces the TJA failure *shape*: tens of commits + many days behind.
    repo, shas = repo_factory(40, days_apart=1, start=datetime(2026, 4, 1, tzinfo=UTC))
    anchor_sha = shas[0]  # 39 commits / 39 days behind HEAD
    anchor = parse_anchor(text=_anchor_md(anchor_sha, datetime(2026, 4, 1, tzinfo=UTC)))
    verdict = evaluate_anchor(anchor, read_repo_state(repo), repo=repo)
    assert verdict.band is Band.STALE
    assert verdict.commits_behind == 39
    assert verdict.days_behind >= 30
    assert "do NOT relay" in verdict.banner()


def test_days_behind_measured_from_sha_date_not_modified(repo_factory):
    # Regression: the genuine TJA anchor was *edited* (modified bumped) recently
    # while still anchored at an old SHA. Days-behind must come from the recorded
    # SHA's commit date (real codebase drift), not from when the prose was last
    # touched — otherwise a freshly-edited-but-stale anchor reads 0 days.
    repo, shas = repo_factory(40, days_apart=1, start=datetime(2026, 4, 1, tzinfo=UTC))
    # Anchor points at the first commit (39 days behind HEAD by commit date) but
    # claims a very recent modified stamp.
    anchor = parse_anchor(text=_anchor_md(shas[0], datetime(2026, 6, 30, tzinfo=UTC)))
    verdict = evaluate_anchor(anchor, read_repo_state(repo), repo=repo)
    assert verdict.days_behind >= 30  # from SHA date, not the recent modified stamp
    assert verdict.band is Band.STALE


def test_stale_on_days_even_if_few_commits(repo_factory):
    # Only 2 commits but 60 days apart -> STALE on the day signal alone.
    repo, shas = repo_factory(3, days_apart=30, start=datetime(2026, 1, 1, tzinfo=UTC))
    anchor = parse_anchor(text=_anchor_md(shas[0], datetime(2026, 1, 1, tzinfo=UTC)))
    verdict = evaluate_anchor(anchor, read_repo_state(repo), repo=repo)
    assert verdict.band is Band.STALE
    assert verdict.days_behind >= 30


# --------------------------------------------------------------------------- #
# Fail-safe: UNKNOWN -> STALE
# --------------------------------------------------------------------------- #


def test_failsafe_no_recorded_sha(repo_factory):
    repo, _ = repo_factory(3)
    anchor = parse_anchor(text=_anchor_md(None, datetime(2026, 4, 4, tzinfo=UTC)))
    assert anchor.last_recorded_sha is None
    verdict = evaluate_anchor(anchor, read_repo_state(repo), repo=repo)
    assert verdict.band is Band.STALE
    assert verdict.is_failsafe is True
    assert verdict.commits_behind is None
    assert "no recorded SHA" in verdict.rationale


def test_failsafe_repo_unreachable(tmp_path):
    anchor = parse_anchor(text=_anchor_md("a" * 40, datetime(2026, 4, 4, tzinfo=UTC)))
    state = read_repo_state(tmp_path / "does-not-exist")
    assert state.reachable is False
    verdict = evaluate_anchor(anchor, state, repo=tmp_path / "does-not-exist")
    assert verdict.band is Band.STALE
    assert verdict.is_failsafe is True


def test_failsafe_not_a_git_repo(tmp_path):
    (tmp_path / "plain").mkdir()
    anchor = parse_anchor(text=_anchor_md("a" * 40, datetime(2026, 4, 4, tzinfo=UTC)))
    state = read_repo_state(tmp_path / "plain")
    assert state.reachable is False
    verdict = evaluate_anchor(anchor, state, repo=tmp_path / "plain")
    assert verdict.band is Band.STALE
    assert verdict.is_failsafe is True


def test_failsafe_recorded_sha_unknown_to_repo(repo_factory):
    repo, _ = repo_factory(3)
    anchor = parse_anchor(text=_anchor_md("deadbeefdeadbeef", datetime(2026, 4, 4, tzinfo=UTC)))
    verdict = evaluate_anchor(anchor, read_repo_state(repo), repo=repo)
    assert verdict.band is Band.STALE
    assert verdict.is_failsafe is True
    assert "not reachable" in verdict.rationale


# --------------------------------------------------------------------------- #
# Anchor parsing behaviour
# --------------------------------------------------------------------------- #


def test_prose_sha_extraction_picks_head_not_old_commit():
    # Mirrors the real TJA reconciliation prose: an old commit AND a HEAD claim.
    body = textwrap.dedent(
        """\
        ---
        id: tja-like
        modified: 2026-06-10T07:29:35.394217934+00:00
        ---

        Last PKB-known commit was `9f89a60` (2026-04-23); repo HEAD is now
        **`8785a89`** (PR #25 merged 2026-05-28).
        """
    )
    anchor = parse_anchor(text=body)
    assert anchor.last_recorded_sha == "8785a89"  # the HEAD claim, not the old commit
    assert anchor.sha_source == "prose"


def test_nanosecond_modified_timestamp_parses():
    body = (
        "---\nid: x\nmodified: 2026-06-10T07:29:35.394217934+00:00\nrepo_head: abc1234\n---\n\nbody"
    )
    anchor = parse_anchor(text=body)
    assert anchor.modified is not None
    assert anchor.modified.year == 2026


def test_frontmatter_sha_beats_prose():
    body = "---\nid: x\nrepo_head: abc1234\n---\n\nHEAD is now `9999999`"
    anchor = parse_anchor(text=body)
    assert anchor.last_recorded_sha == "abc1234"
    assert anchor.sha_source == "frontmatter"


# --------------------------------------------------------------------------- #
# Project aggregate + configurable thresholds
# --------------------------------------------------------------------------- #


def test_project_aggregate_is_worst_band(repo_factory):
    repo, shas = repo_factory(40, days_apart=1, start=datetime(2026, 4, 1, tzinfo=UTC))
    fresh = parse_anchor(
        text=_anchor_md(shas[-1], datetime(2026, 6, 1, tzinfo=UTC)), anchor_id="fresh"
    )
    stale = parse_anchor(
        text=_anchor_md(shas[0], datetime(2026, 4, 1, tzinfo=UTC)), anchor_id="stale"
    )
    result = evaluate_project("p", [fresh, stale], read_repo_state(repo), repo=repo)
    assert result.aggregate_band is Band.STALE  # worst of FRESH + STALE
    bands = {v.anchor_id: v.band for v in result.anchors}
    assert bands["fresh"] is Band.FRESH
    assert bands["stale"] is Band.STALE


def test_thresholds_are_configurable(repo_factory):
    repo, shas = repo_factory(10, days_apart=1)
    anchor = parse_anchor(text=_anchor_md(shas[0], datetime(2026, 4, 1, tzinfo=UTC)))
    # 9 commits behind. Default -> DRIFTED. Tighten stale_commits to 5 -> STALE.
    default = evaluate_anchor(anchor, read_repo_state(repo), repo=repo)
    assert default.band is Band.DRIFTED
    strict = evaluate_anchor(
        anchor,
        read_repo_state(repo),
        repo=repo,
        thresholds=Thresholds(stale_commits=5, stale_days=999),
    )
    assert strict.band is Band.STALE
