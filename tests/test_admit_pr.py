"""Tests for scripts/ci/admit-pr.sh — the shared "grant admission" mechanical
action (specs/workflows/pr-pipeline.md §5.1).

Single source of truth that admit-on-review.yml's `admit` job and
conflict-admission-sweep.yml's `admit` job both call instead of reimplementing
the POST admit-status + arm-auto-merge sequence independently.

`gh` is stubbed with a real executable shim file prepended onto $PATH (NOT
`export -f gh` — function exports don't propagate across the
`subprocess.run(["bash", SCRIPT])` fresh-process invocation this test suite
uses everywhere else). The shim logs each invocation's argv as one JSON line
to $GH_STUB_LOG, which the test reads back to assert on the exact calls made.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "admit-pr.sh"

GH_STUB = """#!/usr/bin/env bash
python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "$@" >> "$GH_STUB_LOG"
if [[ "${GH_STUB_MERGE_FAILS:-}" == "true" ]] && [[ "$1" == "pr" ]] && [[ "$2" == "merge" ]]; then
  exit 1
fi
if [[ "${GH_STUB_STATUS_FAILS:-}" == "true" ]] && [[ "$1" == "api" ]]; then
  exit 1
fi
exit 0
"""


def run(
    *,
    repo: str = "nicsuzor/academicOps",
    pr_number: str = "42",
    sha: str = "deadbeef",
    reason: str = "test reason",
    gh_token: str | None = "fake-token",
    merge_fails: bool = False,
    status_fails: bool = False,
) -> tuple[subprocess.CompletedProcess, list[list[str]], str]:
    """Run admit-pr.sh with a stubbed `gh`; return (proc, decoded gh calls, GITHUB_OUTPUT contents)."""
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        gh_stub = tmpdir / "gh"
        gh_stub.write_text(GH_STUB)
        gh_stub.chmod(gh_stub.stat().st_mode | stat.S_IEXEC)

        log_path = tmpdir / "gh_calls.jsonl"
        log_path.write_text("")
        output_path = tmpdir / "github_output"
        output_path.write_text("")

        env = {
            "PATH": f"{tmpdir}:{os.environ.get('PATH', '/usr/bin:/bin')}",
            "GH_STUB_LOG": str(log_path),
            "REPO": repo,
            "PR_NUMBER": pr_number,
            "SHA": sha,
            "REASON": reason,
            "GITHUB_OUTPUT": str(output_path),
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_REPOSITORY": repo,
            "GITHUB_RUN_ID": "12345",
        }
        if gh_token is not None:
            env["GH_TOKEN"] = gh_token
        if merge_fails:
            env["GH_STUB_MERGE_FAILS"] = "true"
        if status_fails:
            env["GH_STUB_STATUS_FAILS"] = "true"

        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            env=env,
            capture_output=True,
            text=True,
        )
        calls = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
        return proc, calls, output_path.read_text()


def test_missing_gh_token_fails_closed():
    proc, calls, _ = run(gh_token=None)
    assert proc.returncode != 0
    assert calls == []  # never even attempted a gh call


def test_posts_admit_status_success():
    proc, calls, _ = run(
        sha="abc123", repo="nicsuzor/academicOps", reason="Admitted by maintainer review approval"
    )
    assert proc.returncode == 0, proc.stderr
    status_call = calls[0]
    assert status_call[0] == "api"
    assert status_call[1] == "repos/nicsuzor/academicOps/statuses/abc123"
    joined = " ".join(status_call)
    assert "state=success" in joined
    assert "context=admit-status" in joined
    assert "description=Admitted by maintainer review approval" in joined
    assert "target_url=https://github.com/nicsuzor/academicOps/actions/runs/12345" in joined


def test_arms_auto_merge():
    proc, calls, _ = run(pr_number="99", repo="nicsuzor/academicOps")
    assert proc.returncode == 0, proc.stderr
    merge_call = calls[1]
    assert merge_call[0:2] == ["pr", "merge"]
    assert "99" in merge_call
    assert "--auto" in merge_call
    assert "--squash" in merge_call
    assert "--delete-branch" in merge_call


def test_merge_failure_is_tolerated_not_fatal():
    proc, calls, _ = run(merge_fails=True)
    assert proc.returncode == 0, proc.stderr
    assert len(calls) == 2  # both gh calls were still attempted
    assert "WARNING" in proc.stdout


def test_status_post_failure_is_fatal_unlike_merge():
    # A failed admit-status POST must abort — this is the required check;
    # silently continuing would let a caller believe admission succeeded when
    # it didn't.
    proc, calls, _ = run(status_fails=True)
    assert proc.returncode != 0
    assert len(calls) == 1  # never reached the gh pr merge call


def test_emits_admitted_sha_to_stdout():
    proc, _, _ = run(sha="feedface")
    assert "admitted_sha=feedface" in proc.stdout


def test_emits_admitted_sha_to_github_output():
    _, _, output = run(sha="feedface")
    assert "admitted_sha=feedface" in output


def test_reason_distinguishes_admission_path():
    # Two different callers (admit-on-review.yml vs conflict-admission-sweep.yml)
    # pass distinct REASON strings so the audit trail on the PR checks tab shows
    # which path admitted the PR.
    _, calls_a, _ = run(
        reason="Admitted by maintainer review approval — good idea, make it mergeable"
    )
    _, calls_b, _ = run(
        reason="Admitted by standing maintainer approval (conflict-admission sweep, §3.11)"
    )
    desc_a = " ".join(calls_a[0])
    desc_b = " ".join(calls_b[0])
    assert "maintainer review approval" in desc_a
    assert "conflict-admission sweep" in desc_b
