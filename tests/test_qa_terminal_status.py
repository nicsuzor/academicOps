"""Tests for the QA terminal-status decision logic (aops_e958bd56).

`scripts/ci/qa-terminal-status.sh` decides the terminal `qa-status`
(state + description) for a single agent-qa.yml pass. It fixes a false-green:
the old inline fallback looked up ANY APPROVED/CHANGES_REQUESTED review on the
head SHA — NOT scoped to marsha's "QA Verification" marker — so an ENFORCER
approval ("## Enforcer Review — clean") sitting on the same SHA was accepted as
a QA pass and posted qa-status=success even though the QA agent never ran
(live on PR #2135, 2026-07-06). The fix scopes the lookup to the QA marker and
fails closed: absent a genuine QA verdict review on the exact HEAD_SHA,
qa-status is failure — a missing QA verdict is never a pass.

These tests exercise the pure decision (env + reviews-array → state/
description/failed) by injecting the reviews JSON via REVIEWS_JSON, so no
`gh` stub is needed (mirrors tests/test_enforcer_terminal_status.py).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "qa-terminal-status.sh"
SHA = "a29f1c5100000000000000000000000000000000"
OTHER_SHA = "deadbeef00000000000000000000000000000000"

# Review bodies exactly as the two agents post them (qa.agent.md §Identity:
# "# QA Verification"; enforcer.agent.md §5: "## Enforcer Review").
QA_BODY = "# QA Verification — VERIFIED"
ENFORCER_BODY = "## Enforcer Review — clean"


def _review(sha: str, state: str, body: str = QA_BODY) -> dict:
    return {"id": 1, "commit_id": sha, "state": state, "body": body}


def run(
    tmp_path: Path,
    *,
    reviews: list[dict] | None = None,
    review_outcome: str = "success",
) -> dict:
    rf = tmp_path / "reviews.json"
    rf.write_text(json.dumps(reviews if reviews is not None else []))
    env = {
        "HEAD_SHA": SHA,
        "REVIEW_OUTCOME": review_outcome,
        "REVIEWS_JSON": str(rf),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
    }
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"
    out: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def test_script_exists():
    assert SCRIPT.exists(), f"missing {SCRIPT}"


def test_head_sha_required_fails_fast():
    env = {"REVIEW_OUTCOME": "success", "PATH": "/usr/bin:/bin:/usr/local/bin"}
    proc = subprocess.run(
        ["bash", str(SCRIPT)], capture_output=True, text=True, env=env, timeout=20
    )
    assert proc.returncode != 0
    assert "HEAD_SHA" in proc.stderr


# ── The core fix: a QA-marked verdict on HEAD_SHA is honoured ────────────────


def test_qa_approved_on_head_sha_is_success(tmp_path: Path):
    out = run(tmp_path, reviews=[_review(SHA, "APPROVED")])
    assert out["state"] == "success"
    assert out["failed"] == "false"
    assert out["description"] == "3/3 dimensions pass"


def test_qa_changes_requested_on_head_sha_is_failure(tmp_path: Path):
    out = run(tmp_path, reviews=[_review(SHA, "CHANGES_REQUESTED")])
    assert out["state"] == "failure"
    assert out["failed"] == "true"
    assert "Verification failed" in out["description"]


def test_latest_qa_review_wins_when_multiple_exist(tmp_path: Path):
    """A superseded APPROVED followed by a CHANGES_REQUESTED resolves to the
    newer verdict (array-position `last`, mirroring the SHA-skip selection)."""
    out = run(
        tmp_path,
        reviews=[_review(SHA, "APPROVED"), _review(SHA, "CHANGES_REQUESTED")],
    )
    assert out["state"] == "failure"


# ── The regression: an unscoped (non-QA) approval must NOT leak through ──────


def test_enforcer_approval_on_head_sha_is_not_a_qa_pass(tmp_path: Path):
    """THE aops_e958bd56 REPRO. The enforcer's APPROVED review sits on the exact
    HEAD_SHA but its body carries the "## Enforcer Review" marker, not
    "QA Verification". The QA agent never ran (review_outcome != success). The
    old unscoped lookup posted qa-status=success off this approval; the fix must
    fail closed — a non-running QA agent yields qa-status != success."""
    out = run(
        tmp_path,
        reviews=[_review(SHA, "APPROVED", body=ENFORCER_BODY)],
        review_outcome="failure",
    )
    assert out["state"] == "failure"
    assert out["failed"] == "true"
    assert "Agent run failed" in out["description"]


def test_enforcer_approval_does_not_green_even_when_qa_agent_ran(tmp_path: Path):
    """Even if the QA agent step exited success, an enforcer-only approval on the
    SHA is not a QA verdict — fail closed to "posted no verdict"."""
    out = run(
        tmp_path,
        reviews=[_review(SHA, "APPROVED", body=ENFORCER_BODY)],
        review_outcome="success",
    )
    assert out["state"] == "failure"
    assert "no APPROVED/CHANGES_REQUESTED review" in out["description"]


@pytest.mark.parametrize("state", ["APPROVED", "CHANGES_REQUESTED"])
def test_body_without_qa_marker_is_ignored(tmp_path: Path, state: str):
    """Any review whose body lacks the QA marker — regardless of its state — is
    not a QA verdict. Covers the marker-absent half of the class."""
    out = run(
        tmp_path,
        reviews=[_review(SHA, state, body="LGTM, merging")],
        review_outcome="success",
    )
    assert out["state"] == "failure"
    assert out["failed"] == "true"


def test_body_mentioning_marker_mid_prose_is_ignored(tmp_path: Path):
    """The marker is anchored to the body's first line. A review whose prose
    merely mentions "QA Verification" further down (e.g. an enforcer review
    discussing the QA step) must NOT be counted as a QA verdict."""
    body = "## Enforcer Review — clean\n\nThe QA Verification step also passed."
    out = run(
        tmp_path,
        reviews=[_review(SHA, "APPROVED", body=body)],
        review_outcome="success",
    )
    assert out["state"] == "failure"
    assert out["failed"] == "true"


def test_missing_body_field_is_ignored(tmp_path: Path):
    """A review object with no `body` key at all must not crash the jq filter
    (`.body // ""`) nor count as a verdict."""
    out = run(
        tmp_path,
        reviews=[{"id": 1, "commit_id": SHA, "state": "APPROVED"}],
        review_outcome="success",
    )
    assert out["state"] == "failure"


# ── Stale-SHA guard: a QA verdict for a DIFFERENT sha is not this SHA's ──────


def test_qa_review_on_other_sha_is_not_a_match(tmp_path: Path):
    out = run(
        tmp_path,
        reviews=[_review(OTHER_SHA, "APPROVED")],
        review_outcome="success",
    )
    assert out["state"] == "failure"
    assert "no APPROVED/CHANGES_REQUESTED review" in out["description"]


# ── Fail-closed absence cases ───────────────────────────────────────────────


def test_no_review_but_agent_succeeded_is_failure(tmp_path: Path):
    out = run(tmp_path, reviews=[], review_outcome="success")
    assert out["state"] == "failure"
    assert out["failed"] == "true"
    assert "no APPROVED/CHANGES_REQUESTED review" in out["description"]


@pytest.mark.parametrize("outcome", ["failure", "cancelled", "skipped", ""])
def test_no_review_and_agent_did_not_succeed_is_failure(tmp_path: Path, outcome: str):
    """A non-running / failed QA agent with no verdict on the SHA must be
    failure — the fail-closed guarantee the false-green violated."""
    out = run(tmp_path, reviews=[], review_outcome=outcome)
    assert out["state"] == "failure"
    assert out["failed"] == "true"
    assert "Agent run failed" in out["description"]


def test_transient_gh_api_failure_degrades_to_failure_not_crash(tmp_path: Path):
    """A transient `gh api` failure on the live review lookup must degrade to
    "no genuine verdict found" and fall through to a fail-closed failure — not
    crash the script under `set -e` with zero outputs emitted (which would leave
    qa-status stuck at pending, a required check that never resolves)."""
    fake_bin = tmp_path / "fakebin"
    fake_bin.mkdir()
    fake_gh = fake_bin / "gh"
    fake_gh.write_text("#!/usr/bin/env bash\necho 'simulated transient gh failure' >&2\nexit 1\n")
    fake_gh.chmod(0o755)
    env = {
        "HEAD_SHA": SHA,
        "REVIEW_OUTCOME": "success",
        "REPO": "o/r",
        "PR_NUMBER": "1",
        "PATH": f"{fake_bin}:/usr/bin:/bin",
    }
    proc = subprocess.run(
        ["bash", str(SCRIPT)], capture_output=True, text=True, env=env, timeout=20
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"
    out: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    assert out["state"] == "failure"
    assert out["failed"] == "true"
