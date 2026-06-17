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


def run(
    *,
    statuses: list[dict],
    responder_count: int = 0,
    max_responder_runs: int | None = None,
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
