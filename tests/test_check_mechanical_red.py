"""Tests for scripts/ci/check-mechanical-red.sh — the pre-admission gate.

The script decides whether the pre-admission mechanical responder should fire
(specs/workflows/pr-pipeline.md §3.8). It is a deterministic check over
GitHub commit-status string values and a Responder-By: commit count.

Guards implemented (tested here in coverage order):
  G1 — No-op-on-green: both enforcer-status and qa-status are 'success' → false.
  G2 — Convergence guard: either status absent or 'pending' → false.
  G3 — Stage-2 guard: admit-status is 'success' → false.
  G4 — Ceiling guard: Responder-By: count >= MAX_RESPONDER_RUNS → false.
  ✓  — All guards pass (at least one red, pre-admission, below ceiling) → true.

Tests use STATUSES_JSON and RESPONDER_COUNT_JSON to exercise the pure decision
without any gh/git stub, following the pattern of test_review_attestation.py.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "check-mechanical-red.sh"


def _make_status(context: str, state: str) -> dict:
    return {
        "context": context,
        "state": state,
        "created_at": "2026-06-17T00:00:00Z",
    }


def _make_checkrun(conclusion: str, *, name: str = "Pytest", status: str = "completed") -> dict:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "completed_at": "2026-06-20T00:00:00Z",
        "started_at": "2026-06-20T00:00:00Z",
    }


def run(
    *,
    statuses: list[dict],
    responder_count: int = 0,
    max_responder_runs: int | None = None,
    pytest_result: str | None = None,
    base_check_runs: list[dict] | None = None,
) -> dict[str, str]:
    """Run check-mechanical-red.sh with injected inputs; return parsed outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sf_path = Path(tmpdir) / "statuses.json"
        cf_path = Path(tmpdir) / "responder_count.txt"
        sf_path.write_text(json.dumps(statuses))
        cf_path.write_text(str(responder_count))

        env: dict[str, str] = {
            "STATUSES_JSON": str(sf_path),
            "RESPONDER_COUNT_JSON": str(cf_path),
            "HEAD_SHA": "abc1234567890123456789012345678901234567890",
            "REPO": "nicsuzor/academicOps",
            # Inherit the caller's PATH so bash/jq resolve on Nix, Homebrew, etc.
            "PATH": os.environ.get("PATH", ""),
        }
        if max_responder_runs is not None:
            env["MAX_RESPONDER_RUNS"] = str(max_responder_runs)
        if pytest_result is not None:
            env["PYTEST_RESULT"] = pytest_result
        if base_check_runs is not None:
            bcr_path = Path(tmpdir) / "base_check_runs.json"
            bcr_path.write_text(json.dumps(base_check_runs))
            env["BASE_CHECK_RUNS_JSON"] = str(bcr_path)

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


# ── G1: No-op-on-green ──────────────────────────────────────────────────────


def test_both_green_no_fire():
    """G1: Both enforcer and qa green → responder must NOT fire (P5 guard)."""
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "false"


def test_both_green_admitted_no_fire():
    """G1 (dominated by G1): green + admitted → no fire."""
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "success"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "false"


# ── G2: Convergence guard ────────────────────────────────────────────────────


def test_absent_statuses_no_fire():
    """G2: No statuses posted at all → Stage 1 not converged → no fire."""
    out = run(statuses=[])
    assert out["has_mechanical_red"] == "false"


def test_enforcer_pending_no_fire():
    """G2: enforcer-status still pending → convergence guard fires."""
    statuses = [
        _make_status("enforcer-status", "pending"),
        _make_status("qa-status", "failure"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "false"


def test_qa_pending_no_fire():
    """G2: qa-status still pending → convergence guard fires."""
    statuses = [
        _make_status("enforcer-status", "failure"),
        _make_status("qa-status", "pending"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "false"


# ── G3: Stage-2 guard ────────────────────────────────────────────────────────


def test_enforcer_red_but_already_admitted_no_fire():
    """G3: PR admitted → Stage-2 mechanic owns it; pre-admission responder must NOT fire."""
    statuses = [
        _make_status("enforcer-status", "failure"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "success"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "false"


def test_both_red_but_already_admitted_no_fire():
    """G3: admitted + red → mechanic's job, not the responder's."""
    statuses = [
        _make_status("enforcer-status", "failure"),
        _make_status("qa-status", "failure"),
        _make_status("admit-status", "success"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "false"


# ── G4: Ceiling guard ────────────────────────────────────────────────────────


def test_ceiling_reached_no_fire():
    """G4: Responder-By: count >= MAX_RESPONDER_RUNS → surface to human."""
    statuses = [
        _make_status("enforcer-status", "failure"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses, responder_count=3, max_responder_runs=3)
    assert out["has_mechanical_red"] == "false"


def test_ceiling_exceeded_no_fire():
    """G4: Count above ceiling (defensive test)."""
    statuses = [
        _make_status("enforcer-status", "failure"),
        _make_status("qa-status", "failure"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses, responder_count=5, max_responder_runs=3)
    assert out["has_mechanical_red"] == "false"


def test_ceiling_not_yet_reached_allows_fire():
    """G4: Count below ceiling → ceiling guard does not block."""
    statuses = [
        _make_status("enforcer-status", "failure"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses, responder_count=2, max_responder_runs=3)
    assert out["has_mechanical_red"] == "true"


# ── Positive cases: responder SHOULD fire ────────────────────────────────────


def test_enforcer_red_fires():
    """enforcer-status=failure + qa green + pre-admission → fire."""
    statuses = [
        _make_status("enforcer-status", "failure"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "true"


def test_qa_red_fires():
    """qa-status=failure + enforcer green + pre-admission → fire."""
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "failure"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "true"


def test_both_red_fires():
    """Both enforcer and qa red + pre-admission → fire."""
    statuses = [
        _make_status("enforcer-status", "failure"),
        _make_status("qa-status", "failure"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "true"


def test_admit_absent_red_fires():
    """admit-status absent (fresh PR) + enforcer red → fire."""
    statuses = [
        _make_status("enforcer-status", "failure"),
        _make_status("qa-status", "success"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "true"


def test_latest_status_wins_red():
    """Latest status wins when multiple entries exist for the same context."""
    statuses = [
        {"context": "enforcer-status", "state": "success", "created_at": "2026-06-17T00:00:00Z"},
        {"context": "enforcer-status", "state": "failure", "created_at": "2026-06-17T00:01:00Z"},
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "true"


def test_latest_status_wins_green():
    """Latest status wins — a newer success supersedes an older failure."""
    statuses = [
        {"context": "enforcer-status", "state": "failure", "created_at": "2026-06-17T00:00:00Z"},
        {"context": "enforcer-status", "state": "success", "created_at": "2026-06-17T00:01:00Z"},
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses)
    assert out["has_mechanical_red"] == "false"


# ── Pytest-only red trigger (#1965) ──────────────────────────────────────────
# `Pytest` is a check-run, not a commit status. enforcer/qa green + Pytest red
# previously dispatched NO responder (root cause). A Pytest failure attributable
# to the PR's own diff (NOT failing on base) is now an eligible trigger.


def test_pytest_red_pr_attributable_fires():
    """enforcer/qa green + Pytest red + base Pytest GREEN → PR-attributable → fire."""
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(
        statuses=statuses,
        pytest_result="failure",
        base_check_runs=[_make_checkrun("success")],
    )
    assert out["has_mechanical_red"] == "true"


def test_pytest_red_base_broken_no_fire():
    """#1965 thundering-herd guard: Pytest red on HEAD AND on base → NOT attributable → no fire."""
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(
        statuses=statuses,
        pytest_result="failure",
        base_check_runs=[_make_checkrun("failure")],
    )
    assert out["has_mechanical_red"] == "false"
    assert "Base-broken Pytest guard" in out["reason"]


def test_pytest_red_no_base_history_fires():
    """Pytest red on HEAD + no completed base Pytest run → treated as not-broken → fire."""
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses, pytest_result="failure", base_check_runs=[])
    assert out["has_mechanical_red"] == "true"


def test_pytest_red_base_in_progress_ignored_uses_last_completed():
    """An in-progress base run is ignored; the latest COMPLETED base Pytest decides."""
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    base = [
        {
            "name": "Pytest",
            "status": "completed",
            "conclusion": "failure",
            "completed_at": "2026-06-20T00:00:00Z",
        },
        # A newer, still-running run must not flip the verdict.
        {
            "name": "Pytest",
            "status": "in_progress",
            "conclusion": None,
            "started_at": "2026-06-20T01:00:00Z",
        },
    ]
    out = run(statuses=statuses, pytest_result="failure", base_check_runs=base)
    assert out["has_mechanical_red"] == "false"
    assert "Base-broken Pytest guard" in out["reason"]


def test_pytest_red_base_checkruns_object_form():
    """Live check-runs API returns {check_runs:[...]}; the script normalises it.

    BASE_CHECK_RUNS_JSON here holds the object form (not a bare array), matching
    exactly what `gh api .../check-runs` returns in a live run.
    """
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    with tempfile.TemporaryDirectory() as d:
        sf = Path(d) / "s.json"
        sf.write_text(json.dumps(statuses))
        cf = Path(d) / "c.txt"
        cf.write_text("0")
        bf = Path(d) / "b.json"
        bf.write_text(json.dumps({"total_count": 1, "check_runs": [_make_checkrun("failure")]}))
        env = {
            "STATUSES_JSON": str(sf),
            "RESPONDER_COUNT_JSON": str(cf),
            "BASE_CHECK_RUNS_JSON": str(bf),
            "PYTEST_RESULT": "failure",
            "HEAD_SHA": "abc1234567890123456789012345678901234567890",
            "REPO": "nicsuzor/academicOps",
            "PATH": os.environ.get("PATH", ""),
        }
        proc = subprocess.run(
            ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=True
        )
    parsed = {
        k: v for k, _, v in (ln.partition("=") for ln in proc.stdout.splitlines() if "=" in ln)
    }
    assert parsed["has_mechanical_red"] == "false"
    assert "Base-broken Pytest guard" in parsed["reason"]


def test_pytest_green_all_green_no_fire():
    """enforcer/qa green + Pytest green → no-op-on-green (no base fetch needed)."""
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses, pytest_result="success")
    assert out["has_mechanical_red"] == "false"
    assert "No-op-on-green" in out["reason"]


def test_pytest_skipped_treated_as_non_trigger():
    """A skipped Pytest job is not a trigger; enforcer/qa green → no fire."""
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses, pytest_result="skipped")
    assert out["has_mechanical_red"] == "false"


def test_enforcer_red_with_pytest_red_fires_without_base_fetch():
    """When enforcer is already red, the responder fires on that trigger; Pytest/base
    are irrelevant — the base-broken guard only gates the Pytest-ONLY case.
    No BASE_CHECK_RUNS_JSON is injected, proving no base fetch occurs on this path."""
    statuses = [
        _make_status("enforcer-status", "failure"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(statuses=statuses, pytest_result="failure")  # no base_check_runs
    assert out["has_mechanical_red"] == "true"


def test_pytest_red_but_admitted_no_fire():
    """Stage-2 guard still dominates: Pytest red but admitted → mechanic owns it."""
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "success"),
    ]
    out = run(
        statuses=statuses,
        pytest_result="failure",
        base_check_runs=[_make_checkrun("success")],
    )
    assert out["has_mechanical_red"] == "false"


def test_pytest_red_at_ceiling_no_fire():
    """Ceiling guard still dominates: PR-attributable Pytest red but budget exhausted → no fire."""
    statuses = [
        _make_status("enforcer-status", "success"),
        _make_status("qa-status", "success"),
        _make_status("admit-status", "pending"),
    ]
    out = run(
        statuses=statuses,
        pytest_result="failure",
        base_check_runs=[_make_checkrun("success")],
        responder_count=3,
        max_responder_runs=3,
    )
    assert out["has_mechanical_red"] == "false"
