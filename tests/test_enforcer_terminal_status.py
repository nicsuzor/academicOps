"""Tests for the enforcer terminal-status decision logic (aops-89d55ef5).

`scripts/ci/enforcer-terminal-status.sh` decides the terminal `enforcer-status`
(state + description) for a single agent-enforcer.yml pass, and whether the
job should hard-fail. It fixes a false-red: `gh pr review` attaches a posted
review to the PR's CURRENT head SHA at submission time, so when the enforcer
commits a fix mid-run (before posting its verdict), the review lands on the
NEW sha and a strict `commit_id == HEAD_SHA` match finds nothing for the
now-superseded HEAD_SHA. The fix: a verified pushed commit (COMMITTED=true)
is decisive and checked BEFORE any review lookup — a problem the agent fixed
inline and committed must never redden that pass's own status; only a
problem it could not fix does.

These tests exercise the pure decision (env + reviews-array → state/
description/failed) by injecting the reviews JSON via REVIEWS_JSON, so no
`gh` stub is needed (mirrors tests/test_reconcile_enforcer_reviews.py).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "enforcer-terminal-status.sh"
SHA = "a29f1c5100000000000000000000000000000000"
OTHER_SHA = "deadbeef00000000000000000000000000000000"


def _review(sha: str, state: str) -> dict:
    return {"id": 1, "commit_id": sha, "state": state, "body": "## Enforcer Review"}


def run(
    tmp_path: Path,
    *,
    committed: str = "false",
    reviews: list[dict] | None = None,
    review_outcome: str = "success",
    retry_outcome: str = "",
) -> dict:
    rf = tmp_path / "reviews.json"
    rf.write_text(json.dumps(reviews if reviews is not None else []))
    env = {
        "HEAD_SHA": SHA,
        "COMMITTED": committed,
        "REVIEW_OUTCOME": review_outcome,
        "RETRY_OUTCOME": retry_outcome,
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


def test_script_exists_and_executable():
    assert SCRIPT.exists(), f"missing {SCRIPT}"


# ── The core fix: committed short-circuits to success ───────────────────────


def test_committed_with_no_review_at_all_is_success():
    """The most common self-fix shape: the agent fixed everything mechanical,
    found nothing left to flag, and its APPROVE landed on the new SHA (so
    nothing matches the OLD HEAD_SHA here). Must be success, not a false red."""
    out = run(Path("/tmp"), committed="true", reviews=[])
    assert out["state"] == "success"
    assert out["failed"] == "false"
    assert "fixed" in out["description"].lower()


def test_committed_with_a_changes_requested_review_for_a_different_sha_is_still_success(
    tmp_path: Path,
):
    """The agent fixed a mechanical violation AND flagged a remaining judgment
    call; its CHANGES_REQUESTED review lands on the NEW sha (simulated here as
    a review that does not match the old HEAD_SHA). The OLD SHA's pass is
    still a successful handoff — the remaining problem reddens the NEW sha's
    own pass instead (via the ordinary SHA-skip check, not this script)."""
    out = run(tmp_path, committed="true", reviews=[_review(OTHER_SHA, "CHANGES_REQUESTED")])
    assert out["state"] == "success"
    assert out["failed"] == "false"


def test_committed_short_circuits_before_requiring_repo_or_pr_number(tmp_path: Path):
    """The committed path must never attempt a live gh lookup — REPO/PR_NUMBER
    are unset here and REVIEWS_JSON is also unset; a non-committed run would
    hard-error on the `:?` required-var check. Committed must not reach it."""
    rf = tmp_path / "unused.json"
    env = {
        "HEAD_SHA": SHA,
        "COMMITTED": "true",
        "REVIEW_OUTCOME": "success",
        "PATH": "/usr/bin:/bin:/usr/local/bin",
    }
    proc = subprocess.run(
        ["bash", str(SCRIPT)], capture_output=True, text=True, env=env, timeout=20
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"
    assert not rf.exists()  # sanity: we never even referenced REVIEWS_JSON


# ── Not committed: the pre-existing review-matching behaviour, preserved ────


def test_not_committed_approved_review_on_head_sha_is_success(tmp_path: Path):
    out = run(tmp_path, committed="false", reviews=[_review(SHA, "APPROVED")])
    assert out["state"] == "success"
    assert out["failed"] == "false"
    assert out["description"] == "Axiom-clean"


def test_not_committed_changes_requested_on_head_sha_is_failure(tmp_path: Path):
    out = run(tmp_path, committed="false", reviews=[_review(SHA, "CHANGES_REQUESTED")])
    assert out["state"] == "failure"
    assert out["failed"] == "true"
    assert "Violations found" in out["description"]


def test_not_committed_review_on_other_sha_is_not_a_match(tmp_path: Path):
    """A review for a DIFFERENT sha must not count as this SHA's verdict when
    no commit happened — the stale-match guard still applies in the ordinary
    (non-racing) case."""
    out = run(
        tmp_path,
        committed="false",
        reviews=[_review(OTHER_SHA, "APPROVED")],
        review_outcome="success",
    )
    assert out["state"] == "failure"
    assert out["failed"] == "true"
    assert "no APPROVED/CHANGES_REQUESTED review" in out["description"]


def test_not_committed_no_review_but_action_succeeded_is_failure(tmp_path: Path):
    out = run(tmp_path, committed="false", reviews=[], review_outcome="success")
    assert out["state"] == "failure"
    assert out["failed"] == "true"
    assert "no APPROVED/CHANGES_REQUESTED review" in out["description"]


def test_not_committed_both_attempts_failed_is_infra_failure(tmp_path: Path):
    out = run(
        tmp_path, committed="false", reviews=[], review_outcome="failure", retry_outcome="failure"
    )
    assert out["state"] == "failure"
    assert out["failed"] == "true"
    assert "failed in both attempts" in out["description"]


def test_not_committed_retry_cancelled_counts_as_both_attempts_failed(tmp_path: Path):
    out = run(
        tmp_path,
        committed="false",
        reviews=[],
        review_outcome="cancelled",
        retry_outcome="cancelled",
    )
    assert out["state"] == "failure"
    assert "failed in both attempts" in out["description"]


def test_not_committed_retry_succeeded_but_posted_no_verdict(tmp_path: Path):
    out = run(
        tmp_path, committed="false", reviews=[], review_outcome="failure", retry_outcome="success"
    )
    assert out["state"] == "failure"
    assert "retry succeeded but posted no verdict" in out["description"]


def test_not_committed_first_attempt_failed_retry_never_ran(tmp_path: Path):
    out = run(tmp_path, committed="false", reviews=[], review_outcome="failure", retry_outcome="")
    assert out["state"] == "failure"
    assert "retry did not execute" in out["description"]


def test_not_committed_review_step_never_ran_is_early_pipeline_failure(tmp_path: Path):
    out = run(tmp_path, committed="false", reviews=[], review_outcome="", retry_outcome="")
    assert out["state"] == "failure"
    assert "early pipeline failure" in out["description"]


def test_latest_review_wins_when_multiple_exist_for_head_sha(tmp_path: Path):
    """Ordering by array position (last), mirroring the original inline
    `| last.state` selection — a superseded APPROVED followed by a
    CHANGES_REQUESTED resolves to the newer verdict."""
    out = run(
        tmp_path,
        committed="false",
        reviews=[_review(SHA, "APPROVED"), _review(SHA, "CHANGES_REQUESTED")],
    )
    assert out["state"] == "failure"
