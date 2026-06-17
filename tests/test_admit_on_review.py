"""Tests for the review-driven admission authorization decision.

`scripts/ci/admit-on-review.sh` is the fail-closed, default-deny core of the v2
PR pipeline's admission gate (specs/workflows/pr-pipeline.md §3.2). The admission
signal is a maintainer's PR **review approval**; this script decides whether a
`pull_request_review` event should admit the PR. It must default-deny: only a
write-class maintainer's `approved` review admits; a non-approval state, or an
approval from someone without write access (and not on the explicit allowlist),
is a `skip`. An external contributor's approving review must never admit a PR.

These tests exercise the pure decision (env inputs → state/description) directly,
so no `gh`/event stub is needed.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "admit-on-review.sh"


def run(
    *,
    review_state: str,
    reviewer_login: str = "nicsuzor",
    reviewer_permission: str | None = None,
    admit_allowlist: str | None = None,
) -> dict:
    """Run the decision script with injected inputs; return parsed state/desc."""
    env = {
        "REVIEW_STATE": review_state,
        "REVIEWER_LOGIN": reviewer_login,
        # Inherit the caller's PATH so `bash` resolves across dev environments
        # (nix, homebrew, etc.) rather than only the default FHS locations.
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    if reviewer_permission is not None:
        env["REVIEWER_PERMISSION"] = reviewer_permission
    if admit_allowlist is not None:
        env["ADMIT_ALLOWLIST"] = admit_allowlist
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    out: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k] = v
    return out


def test_maintainer_write_approval_admits():
    out = run(review_state="approved", reviewer_login="someone", reviewer_permission="write")
    assert out["state"] == "admit"


def test_admin_approval_admits():
    out = run(review_state="approved", reviewer_login="someone", reviewer_permission="admin")
    assert out["state"] == "admit"


def test_maintain_permission_admits():
    out = run(review_state="approved", reviewer_login="someone", reviewer_permission="maintain")
    assert out["state"] == "admit"


def test_commented_review_does_not_admit():
    out = run(review_state="commented", reviewer_permission="admin")
    assert out["state"] == "skip"


def test_changes_requested_does_not_admit():
    out = run(review_state="changes_requested", reviewer_permission="admin")
    assert out["state"] == "skip"


def test_dismissed_review_does_not_admit():
    out = run(review_state="dismissed", reviewer_permission="admin")
    assert out["state"] == "skip"


def test_external_contributor_approval_fails_closed():
    # An approving review from a read-only / non-collaborator account must NOT admit.
    out = run(review_state="approved", reviewer_login="outsider", reviewer_permission="read")
    assert out["state"] == "skip"


def test_triage_permission_does_not_admit():
    # triage is below write — not enough to admit.
    out = run(review_state="approved", reviewer_login="someone", reviewer_permission="triage")
    assert out["state"] == "skip"


def test_unresolved_permission_defaults_deny():
    # When the workflow could not resolve a permission, the default is "none".
    out = run(review_state="approved", reviewer_login="someone")
    assert out["state"] == "skip"


def test_none_permission_fails_closed():
    out = run(review_state="approved", reviewer_login="someone", reviewer_permission="none")
    assert out["state"] == "skip"


def test_allowlist_admits_without_write_permission():
    # The maintainer allowlist is belt-and-suspenders: it admits even if the
    # permission read returned something below write (e.g. an API hiccup → none).
    out = run(
        review_state="approved",
        reviewer_login="nicsuzor",
        reviewer_permission="none",
        admit_allowlist="nicsuzor",
    )
    assert out["state"] == "admit"


def test_allowlist_does_not_bypass_approval_requirement():
    # Even an allowlisted maintainer must actually APPROVE — a comment is not admission.
    out = run(
        review_state="commented",
        reviewer_login="nicsuzor",
        reviewer_permission="admin",
        admit_allowlist="nicsuzor",
    )
    assert out["state"] == "skip"


def test_allowlist_is_per_login_not_substring():
    # An allowlist of "nicsuzor" must not admit "nicsuzor2" or "evil-nicsuzor".
    out = run(
        review_state="approved",
        reviewer_login="nicsuzor2",
        reviewer_permission="read",
        admit_allowlist="nicsuzor",
    )
    assert out["state"] == "skip"
