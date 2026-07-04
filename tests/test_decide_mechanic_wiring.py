"""Wiring test for admit-on-review.yml's "Decide mechanic dispatch + mode" step.

Root cause this guards against (PR #2094, closed by the corrected version of
draft PR #2101): a PR could have `enforcer-status`/`qa-status` green and no
merge conflict, yet still carry an unaddressed third-party (Copilot) review
comment — and the ORIGINAL `decide-mechanic` logic only ever checked
reviewer-colour + mergeability, so it computed `need_mechanic=false` and let
an already-armed auto-merge complete untouched.

This test extracts the *actual* embedded "Decide mechanic dispatch + mode"
step script from the workflow YAML (not a reimplementation) and executes it
directly against every combination of the three input signals, asserting both
`need_mechanic` AND `mechanic_mode` — the second output is the fix for a
SEPARATE bug the same incident review surfaced: even a correct dispatch is
useless if the mechanic runs in the wrong mode (Stage-2 default carries no
comment-triage instructions; only `mode: review-response` does). Mirrors the
convention in tests/test_agent_enforcer_terminal_status_wiring.py.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "admit-on-review.yml"


def _extract_step_script(step_name: str) -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    for step in workflow["jobs"]["decide-mechanic"]["steps"]:
        if step.get("name") == step_name:
            return step["run"]
    raise AssertionError(f"step {step_name!r} not found in {WORKFLOW}")


def _run(
    tmp_path: Path, *, enf: str, qa: str, mergeable: str, has_unresolved_comments: str
) -> dict:
    output_path = tmp_path / "github_output"
    output_path.write_text("")
    script = _extract_step_script("Decide mechanic dispatch + mode")
    proc = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={
            "PATH": "/usr/bin:/bin",
            "GITHUB_OUTPUT": str(output_path),
            "HEAD_SHA": "deadbeef",
            "ENF": enf,
            "QA": qa,
            "MERGEABLE": mergeable,
            "HAS_UNRESOLVED_COMMENTS": has_unresolved_comments,
        },
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"step itself must not crash: {proc.stderr}"
    out: dict[str, str] = {}
    for line in output_path.read_text().splitlines():
        key, _, value = line.partition("=")
        out[key] = value
    return out


# ── The all-clear case: no mechanic needed ──────────────────────────────────


def test_all_green_no_conflict_no_comments_no_mechanic(tmp_path):
    out = _run(
        tmp_path,
        enf="success",
        qa="success",
        mergeable="MERGEABLE",
        has_unresolved_comments="false",
    )
    assert out["need_mechanic"] == "false"
    assert out["mechanic_mode"] == ""


# ── Comment-only case: THE #2094 REGRESSION THIS TEST GUARDS ────────────────


def test_green_reviewers_not_conflicting_unresolved_comments_dispatches_review_response(tmp_path):
    """The exact PR #2094 shape: enforcer/qa green, not conflicting, but an
    unaddressed third-party comment/review remains. The original logic
    computed need_mechanic=false here — this is the regression this whole
    gate exists to close."""
    out = _run(
        tmp_path, enf="success", qa="success", mergeable="MERGEABLE", has_unresolved_comments="true"
    )
    assert out["need_mechanic"] == "true"
    assert out["mechanic_mode"] == "review-response"


# ── Red reviewer takes priority over comments, and uses Stage-2 mode ────────


def test_red_enforcer_dispatches_stage2_mode_regardless_of_comments(tmp_path):
    out = _run(
        tmp_path, enf="failure", qa="success", mergeable="MERGEABLE", has_unresolved_comments="true"
    )
    assert out["need_mechanic"] == "true"
    assert out["mechanic_mode"] == ""  # Stage-2 default, NOT review-response


def test_red_qa_dispatches_stage2_mode(tmp_path):
    out = _run(
        tmp_path,
        enf="success",
        qa="failure",
        mergeable="MERGEABLE",
        has_unresolved_comments="false",
    )
    assert out["need_mechanic"] == "true"
    assert out["mechanic_mode"] == ""


def test_pending_reviewer_dispatches_stage2_mode(tmp_path):
    """Absent/pending reviewer state (empty string) is also not 'success' — dispatch."""
    out = _run(
        tmp_path, enf="", qa="success", mergeable="MERGEABLE", has_unresolved_comments="false"
    )
    assert out["need_mechanic"] == "true"
    assert out["mechanic_mode"] == ""


# ── Conflicting takes priority over everything, uses Stage-2 mode ──────────


def test_conflicting_dispatches_stage2_mode_regardless_of_reviewer_colour_or_comments(tmp_path):
    out = _run(
        tmp_path,
        enf="success",
        qa="success",
        mergeable="CONFLICTING",
        has_unresolved_comments="true",
    )
    assert out["need_mechanic"] == "true"
    assert out["mechanic_mode"] == ""


def test_conflicting_with_red_reviewer_still_stage2_mode(tmp_path):
    out = _run(
        tmp_path,
        enf="failure",
        qa="failure",
        mergeable="CONFLICTING",
        has_unresolved_comments="true",
    )
    assert out["need_mechanic"] == "true"
    assert out["mechanic_mode"] == ""


# ── Missing HAS_UNRESOLVED_COMMENTS input degrades safely ───────────────────


def test_missing_comments_signal_defaults_to_no_dispatch_on_that_axis(tmp_path):
    """If admit-comment-triage's output is somehow absent, the dispatch decision
    must not crash — it simply doesn't fire on that axis (the REQUIRED
    comment-triage-status check, not this dispatch heuristic, is what actually
    blocks merge; see §3.10.1)."""
    out = _run(
        tmp_path, enf="success", qa="success", mergeable="MERGEABLE", has_unresolved_comments=""
    )
    assert out["need_mechanic"] == "false"
    assert out["mechanic_mode"] == ""
