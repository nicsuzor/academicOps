"""Tests for scripts/ci/find-conflicting-admitted-prs.sh — the conflict-admission
sweep's discover step (specs/workflows/pr-pipeline.md §3.11).

The script selects open PRs that are CONFLICTING with the base AND approved by a
write-class maintainer, excluding drafts, forks, already-CHANGES_REQUESTED PRs,
and any PR whose head SHA already carries a terminal mechanic-status. It is a
deterministic function over the `gh pr list` JSON, a {login: permission} map, and
a {sha: mechanic-state} map — all injectable, so the decision is tested without
any gh stub (same pattern as test_check_mechanical_red.py).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "find-conflicting-admitted-prs.sh"


def _pr(
    number: int,
    *,
    mergeable: str = "CONFLICTING",
    draft: bool = False,
    cross_repo: bool = False,
    ref: str = "feature",
    sha: str = "deadbeef",
    reviews: list[tuple[str, str]] | None = None,
) -> dict:
    """Build one `gh pr list` element. reviews = list of (login, state)."""
    return {
        "number": number,
        "headRefName": ref,
        "headRefOid": sha,
        "mergeable": mergeable,
        "isDraft": draft,
        "isCrossRepository": cross_repo,
        "latestReviews": [{"author": {"login": lg}, "state": st} for lg, st in (reviews or [])],
    }


def run(
    *,
    prs: list[dict],
    perms: dict[str, str] | None = None,
    mech_status: dict[str, str] | None = None,
    allowlist: str = "nicsuzor",
) -> dict[str, str]:
    """Run the discover script with injected inputs; return parsed key=val outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prs_path = Path(tmpdir) / "prs.json"
        perm_path = Path(tmpdir) / "perms.json"
        mech_path = Path(tmpdir) / "mech.json"
        prs_path.write_text(json.dumps(prs))
        perm_path.write_text(json.dumps(perms or {}))
        mech_path.write_text(json.dumps(mech_status or {}))

        env: dict[str, str] = {
            "REPO": "nicsuzor/academicOps",
            "BASE_BRANCH": "dev",
            "ADMIT_ALLOWLIST": allowlist,
            "PRS_JSON": str(prs_path),
            "PERM_JSON": str(perm_path),
            "MECH_STATUS_JSON": str(mech_path),
            "PATH": os.environ.get("PATH", ""),
        }
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


def _numbers(out: dict[str, str]) -> list[int]:
    return [item["number"] for item in json.loads(out["matrix"])]


def test_conflicting_approved_writeclass_is_selected():
    out = run(
        prs=[_pr(10, sha="sha10", reviews=[("nic", "APPROVED")])],
        perms={"nic": "write"},
    )
    assert out["any"] == "true"
    assert _numbers(out) == [10]
    assert json.loads(out["matrix"])[0] == {"number": 10, "ref": "feature", "sha": "sha10"}


def test_mergeable_pr_excluded():
    out = run(
        prs=[_pr(11, mergeable="MERGEABLE", reviews=[("nic", "APPROVED")])],
        perms={"nic": "write"},
    )
    assert out["any"] == "false"
    assert _numbers(out) == []


def test_unknown_mergeability_excluded():
    out = run(
        prs=[_pr(12, mergeable="UNKNOWN", reviews=[("nic", "APPROVED")])],
        perms={"nic": "write"},
    )
    assert out["any"] == "false"


def test_draft_excluded():
    out = run(
        prs=[_pr(13, draft=True, reviews=[("nic", "APPROVED")])],
        perms={"nic": "write"},
    )
    assert out["any"] == "false"


def test_fork_pr_excluded():
    out = run(
        prs=[_pr(14, cross_repo=True, reviews=[("nic", "APPROVED")])],
        perms={"nic": "write"},
    )
    assert out["any"] == "false"


def test_approval_from_non_writeclass_excluded():
    out = run(
        prs=[_pr(15, reviews=[("randos", "APPROVED")])],
        perms={"randos": "read"},
    )
    assert out["any"] == "false"


def test_changes_requested_by_writeclass_blocks():
    # One write-class APPROVED but another write-class CHANGES_REQUESTED → blocked.
    out = run(
        prs=[_pr(16, reviews=[("nic", "APPROVED"), ("boss", "CHANGES_REQUESTED")])],
        perms={"nic": "write", "boss": "admin"},
    )
    assert out["any"] == "false"


def test_terminal_mechanic_status_failure_excluded():
    out = run(
        prs=[_pr(17, sha="sha17", reviews=[("nic", "APPROVED")])],
        perms={"nic": "write"},
        mech_status={"sha17": "failure"},
    )
    assert out["any"] == "false"


def test_terminal_mechanic_status_success_excluded():
    out = run(
        prs=[_pr(18, sha="sha18", reviews=[("nic", "APPROVED")])],
        perms={"nic": "write"},
        mech_status={"sha18": "success"},
    )
    assert out["any"] == "false"


def test_pending_mechanic_status_still_selected():
    # A pending mechanic-status means a run is in flight, not terminal — the
    # mechanic's own concurrency group + SHA-skip de-dupes; discover still lists it.
    out = run(
        prs=[_pr(19, sha="sha19", reviews=[("nic", "APPROVED")])],
        perms={"nic": "write"},
        mech_status={"sha19": "pending"},
    )
    assert out["any"] == "true"
    assert _numbers(out) == [19]


def test_allowlist_login_admits_without_permission():
    # Allowlisted maintainer admits even when the permission API returns none.
    out = run(
        prs=[_pr(20, reviews=[("nicsuzor", "APPROVED")])],
        perms={"nicsuzor": "none"},
        allowlist="nicsuzor",
    )
    assert out["any"] == "true"


def test_empty_pr_list():
    out = run(prs=[])
    assert out["any"] == "false"
    assert out["matrix"] == "[]"


def test_multiple_candidates_selected():
    out = run(
        prs=[
            _pr(21, sha="s21", reviews=[("nic", "APPROVED")]),
            _pr(22, mergeable="MERGEABLE", reviews=[("nic", "APPROVED")]),
            _pr(23, sha="s23", reviews=[("nic", "APPROVED")]),
        ],
        perms={"nic": "maintain"},
    )
    assert out["any"] == "true"
    assert sorted(_numbers(out)) == [21, 23]
