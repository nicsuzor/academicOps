"""Static wiring tests for the inverted review gradient + fail-closed
attestation in the PR pipeline (GitHub issue #1450, pr-pipeline.md §3.4/§3.7).

These assert the structure that the runtime behaviour depends on:
  - AC3: the `qa` job is NOT gated off by a red enforcer VERDICT — a failing PR
    gets MORE review, not less.
  - AC1/AC2: a required, fail-closed `review-attestation` aggregator job exists
    and is wired into branch protection, so a dead/skipped pipeline cannot read
    as a pass.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = REPO_ROOT / ".github" / "workflows" / "pr-pipeline.yml"
RULESET = REPO_ROOT / ".github" / "rulesets" / "pr-review-and-merge.yml"
VALIDATE = REPO_ROOT / "scripts" / "validate-ruleset-alignment.sh"


def _jobs() -> dict:
    return yaml.safe_load(PIPELINE.read_text())["jobs"]


# ── AC3: inverted review gradient ────────────────────────────────────────────


def test_qa_runs_on_red_enforcer_verdict():
    """AC3: qa must run when the enforcer returns a red VERDICT (result failure),
    so a failing PR receives MORE review, not less. The old gate
    `needs.enforcer.result == 'success'` suppressed qa on every enforcer-red PR.
    """
    qa_if = _jobs()["qa"]["if"]
    # qa tolerates an enforcer failure verdict ...
    assert "needs.enforcer.result == 'failure'" in qa_if, qa_if
    # ... and is no longer gated *solely* on enforcer success.
    assert "needs.enforcer.result == 'success' &&" not in qa_if, qa_if


def test_qa_still_short_circuits_on_enforcer_commit():
    """Convergence is preserved: qa is skipped when the enforcer COMMITTED (the
    SHA changed); the verdict colour, not the commit, is what was decoupled."""
    qa_if = _jobs()["qa"]["if"]
    assert "needs.enforcer.outputs.committed != 'true'" in qa_if, qa_if


# ── AC1/AC2: fail-closed liveness + named-reviewer attestation ───────────────


def test_review_attestation_job_exists_and_runs_always():
    """AC2: the attestation job runs `if: always()` after the named reviewers, so
    the liveness signal is posted explicitly whenever the workflow runs."""
    ra = _jobs()["review-attestation"]
    assert set(ra["needs"]) >= {"enforcer", "qa"}, ra["needs"]
    assert ra["if"].strip().startswith("always()"), ra["if"]


def test_review_attestation_fails_closed():
    """AC2: the job must exit non-zero when the decision is not `success`, so the
    check itself goes red (not merely an informational status)."""
    ra = _jobs()["review-attestation"]
    body = "\n".join(step.get("run", "") for step in ra["steps"] if isinstance(step, dict))
    assert "review-attestation.sh" in body
    assert 'if [ "$STATE" != "success" ]' in body
    assert "exit 1" in body


def test_review_attestation_is_required_in_ruleset():
    """AC2: the attestation is a REQUIRED status check — absence (a dead pipeline
    that posts nothing) leaves it unsatisfied and the PR unmergeable."""
    text = RULESET.read_text()
    # In the required_status_checks block, before the Code quality divider.
    block = text.split("required_status_checks:")[1].split("# ─", 1)[0]
    assert 'context: "review-attestation"' in block, block


def test_ruleset_alignment_passes():
    """The required `review-attestation` context resolves to a real producer —
    the alignment validator (run in CI) must pass with it present."""
    proc = subprocess.run(
        ["bash", str(VALIDATE)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "review-attestation" in proc.stdout
