"""Tests for the idempotent single-verdict reconciler (aops-1adfd28d).

`scripts/ci/reconcile-enforcer-reviews.sh` enforces: AT MOST ONE enforcer
verdict review stands per SHA. It dismisses every standing enforcer verdict
review for HEAD_SHA except the newest.

The decision (which review ids to keep / dismiss) is a pure function over the
reviews array, injected via REVIEWS_JSON so it is unit-tested without a gh stub
(mirroring tests/test_review_attestation.py). In REVIEWS_JSON mode the script
performs NO gh calls — it only prints `keep=`/`dismiss=`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "reconcile-enforcer-reviews.sh"
SHA = "a29f1c5100000000000000000000000000000000"
OTHER_SHA = "deadbeef00000000000000000000000000000000"


def _review(rid: int, sha: str, state: str, body: str = "## Enforcer Review") -> dict:
    return {"id": rid, "commit_id": sha, "state": state, "body": body}


def run(reviews: list[dict], tmp_path: Path) -> dict:
    rf = tmp_path / "reviews.json"
    rf.write_text(json.dumps(reviews))
    env = {
        "REPO": "nicsuzor/academicOps",
        "PR_NUMBER": "1700",
        "HEAD_SHA": SHA,
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
        if line.startswith("keep="):
            out["keep"] = line[len("keep=") :].strip()
        elif line.startswith("dismiss="):
            out["dismiss"] = line[len("dismiss=") :].strip()
    return out


def test_two_standing_verdicts_keeps_newest_dismisses_older(tmp_path: Path):
    """The core invariant: two standing enforcer verdicts on one SHA → keep the
    newest (highest id), dismiss the older. Never two standing."""
    reviews = [
        _review(4464182548, SHA, "APPROVED"),  # zombie's first post
        _review(4464186473, SHA, "APPROVED"),  # retry's authoritative post
    ]
    out = run(reviews, tmp_path)
    assert out["keep"] == "4464186473"
    assert out["dismiss"] == "4464182548"


def test_silent_replay_triplicate_collapses_to_one(tmp_path: Path):
    """The observed run 27250704371 shape: the zombie silent-replayed (2 posts)
    and the retry posted a third. All but the newest must be dismissed."""
    reviews = [
        _review(4464182548, SHA, "APPROVED"),
        _review(4464182991, SHA, "APPROVED"),
        _review(4464186473, SHA, "APPROVED"),
    ]
    out = run(reviews, tmp_path)
    assert out["keep"] == "4464186473"
    assert set(out["dismiss"].split()) == {"4464182548", "4464182991"}


def test_idempotent_single_standing_is_noop(tmp_path: Path):
    """Re-running after reconciliation (older reviews now DISMISSED) dismisses
    nothing — the script is idempotent."""
    reviews = [
        _review(4464182548, SHA, "DISMISSED"),
        _review(4464186473, SHA, "APPROVED"),
    ]
    out = run(reviews, tmp_path)
    assert out["keep"] == "4464186473"
    assert out["dismiss"] == ""


def test_changes_requested_newest_wins_over_older_approved(tmp_path: Path):
    """Ordering is by id, not by state — a newer CHANGES_REQUESTED supersedes an
    older APPROVED (the gate then reads the standing failing verdict)."""
    reviews = [
        _review(100, SHA, "APPROVED"),
        _review(200, SHA, "CHANGES_REQUESTED"),
    ]
    out = run(reviews, tmp_path)
    assert out["keep"] == "200"
    assert out["dismiss"] == "100"


def test_ignores_other_sha_and_non_enforcer_reviews(tmp_path: Path):
    """Only standing enforcer verdicts on THIS SHA are reconciled — a review on
    another SHA, and a non-enforcer review on this SHA, are left untouched."""
    reviews = [
        _review(300, SHA, "APPROVED"),
        _review(301, OTHER_SHA, "APPROVED"),  # different SHA
        _review(302, SHA, "APPROVED", body="LGTM from a human"),  # not enforcer
        _review(303, SHA, "COMMENTED"),  # not a verdict
    ]
    out = run(reviews, tmp_path)
    # Only review 300 is a standing enforcer verdict on this SHA → it is the sole
    # standing one, nothing to dismiss.
    assert out["keep"] == "300"
    assert out["dismiss"] == ""


def test_no_enforcer_reviews_is_noop(tmp_path: Path):
    """No enforcer verdict on this SHA (agent posted none) → no-op, fail-open."""
    reviews = [_review(400, OTHER_SHA, "APPROVED")]
    out = run(reviews, tmp_path)
    assert out["keep"] == ""
    assert out["dismiss"] == ""
