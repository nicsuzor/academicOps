"""Tests for the fail-closed review-attestation decision logic.

`scripts/ci/review-attestation.sh` is the named-reviewer liveness + on-this-SHA
attestation check for the PR pipeline (specs/workflows/pr-pipeline.md §3.7,
GitHub issue #1450). It must FAIL CLOSED: only a genuine terminal `success`
whose attestation `target_sha` equals the SHA under review counts as a live
pass. Absent / pending / red / stale all read as failure, so a dead or skipped
pipeline can never be silently treated as a pass.

These tests exercise the pure decision (statuses-array → state/description) by
injecting the statuses JSON via STATUSES_JSON, so no `gh` stub is needed.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "review-attestation.sh"
SHA = "abc123def456abc123def456abc123def456abcd"
OTHER_SHA = "0000000000000000000000000000000000000000"


def _status(context: str, state: str, sha: str, ts: str) -> dict:
    return {
        "context": context,
        "state": state,
        "created_at": ts,
        "target_url": f"https://github.com/o/r/actions/runs/1?target_sha={sha}",
    }


def run(statuses: list[dict], tmp_path: Path, reviewers: str | None = None) -> dict:
    """Run the script with an injected statuses array; return parsed state/desc."""
    sf = tmp_path / "statuses.json"
    sf.write_text(json.dumps(statuses))
    env = {
        "REPO": "o/r",
        "HEAD_SHA": SHA,
        "STATUSES_JSON": str(sf),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
    }
    if reviewers is not None:
        env["REVIEWERS"] = reviewers
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
            k, v = line.split("=", 1)
            out[k] = v
    return out


def test_script_exists_and_executable():
    assert SCRIPT.exists(), f"missing {SCRIPT}"


def test_both_reviewers_live_on_this_sha_passes(tmp_path: Path):
    """AC1: a named reviewer provably ran on THIS exact SHA → attest success."""
    statuses = [
        _status("enforcer-status", "success", SHA, "2026-06-10T00:00:00Z"),
        _status("qa-status", "success", SHA, "2026-06-10T00:01:00Z"),
    ]
    out = run(statuses, tmp_path)
    assert out["state"] == "success"
    assert SHA[:12] in out["description"]


def test_absent_reviewer_fails_closed(tmp_path: Path):
    """AC2: a dead/skipped pipeline (status absent) must NOT read as a pass."""
    statuses = [_status("enforcer-status", "success", SHA, "2026-06-10T00:00:00Z")]
    out = run(statuses, tmp_path)
    assert out["state"] == "failure"
    assert "qa-status:absent" in out["description"]


def test_completely_dead_pipeline_fails_closed(tmp_path: Path):
    """AC2: no statuses at all (startup_failure / never ran) → failure, not pass."""
    out = run([], tmp_path)
    assert out["state"] == "failure"
    assert "enforcer-status:absent" in out["description"]
    assert "qa-status:absent" in out["description"]


def test_stale_success_for_other_sha_fails_closed(tmp_path: Path):
    """AC1/AC2: a success carrying a DIFFERENT SHA's attestation is not proof
    this diff was reviewed → stale → fail closed."""
    statuses = [
        _status("enforcer-status", "success", OTHER_SHA, "2026-06-10T00:00:00Z"),
        _status("qa-status", "success", SHA, "2026-06-10T00:01:00Z"),
    ]
    out = run(statuses, tmp_path)
    assert out["state"] == "failure"
    assert "enforcer-status:stale" in out["description"]


def test_red_verdict_fails_closed(tmp_path: Path):
    """A genuine red reviewer verdict on this SHA blocks (and is named)."""
    statuses = [
        _status("enforcer-status", "failure", SHA, "2026-06-10T00:00:00Z"),
        _status("qa-status", "success", SHA, "2026-06-10T00:01:00Z"),
    ]
    out = run(statuses, tmp_path)
    assert out["state"] == "failure"
    assert "enforcer-status:failure" in out["description"]


def test_pending_then_success_takes_latest(tmp_path: Path):
    """The latest status per context wins: a pending superseded by a later
    success on this SHA is a live pass."""
    statuses = [
        _status("enforcer-status", "pending", SHA, "2026-06-10T00:00:00Z"),
        _status("enforcer-status", "success", SHA, "2026-06-10T00:05:00Z"),
        _status("qa-status", "success", SHA, "2026-06-10T00:01:00Z"),
    ]
    out = run(statuses, tmp_path)
    assert out["state"] == "success"


def test_success_then_late_failure_fails_closed(tmp_path: Path):
    """A late-arriving red verdict (newer created_at) supersedes an earlier
    success — the most recent verdict on the SHA governs (F7 late-review)."""
    statuses = [
        _status("qa-status", "success", SHA, "2026-06-10T00:01:00Z"),
        _status("qa-status", "failure", SHA, "2026-06-10T00:09:00Z"),
        _status("enforcer-status", "success", SHA, "2026-06-10T00:00:00Z"),
    ]
    out = run(statuses, tmp_path)
    assert out["state"] == "failure"
    assert "qa-status:failure" in out["description"]


def test_custom_reviewer_set(tmp_path: Path):
    """The reviewer set is configurable (cross-repo consumers may name others)."""
    statuses = [_status("enforcer-status", "success", SHA, "2026-06-10T00:00:00Z")]
    out = run(statuses, tmp_path, reviewers="enforcer-status")
    assert out["state"] == "success"


def _run_with_summary(statuses: list[dict], tmp_path: Path) -> str:
    """Run the script with a GITHUB_STEP_SUMMARY sink; return the summary text."""
    sf = tmp_path / "statuses.json"
    sf.write_text(json.dumps(statuses))
    summary = tmp_path / "summary.md"
    summary.write_text("")
    subprocess.run(
        ["bash", str(SCRIPT)],
        env={
            "REPO": "o/r",
            "HEAD_SHA": SHA,
            "STATUSES_JSON": str(sf),
            "GITHUB_STEP_SUMMARY": str(summary),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
        },
        capture_output=True,
        text=True,
        check=True,
    )
    return summary.read_text()


def test_absent_failure_writes_actionable_summary(tmp_path: Path):
    """On an absent reviewer, the run summary explains the cause and points to
    the remedy (approve to admit / Force Review) — not just the terse token."""
    statuses = [_status("enforcer-status", "success", SHA, "2026-06-10T00:00:00Z")]
    text = _run_with_summary(statuses, tmp_path)
    assert "Review attestation failed" in text
    assert "qa-status" in text
    assert "Force Review" in text  # the §3.12 escape-hatch remedy is surfaced


def test_success_writes_no_failure_summary(tmp_path: Path):
    """A passing attestation must not emit a failure summary."""
    statuses = [
        _status("enforcer-status", "success", SHA, "2026-06-10T00:00:00Z"),
        _status("qa-status", "success", SHA, "2026-06-10T00:01:00Z"),
    ]
    text = _run_with_summary(statuses, tmp_path)
    assert text.strip() == ""
