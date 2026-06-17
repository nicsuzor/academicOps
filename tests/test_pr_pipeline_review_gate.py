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


# ── §3.8: pre-admission mechanical responder wiring ─────────────────────────


def test_check_mechred_job_exists_with_convergence_condition():
    """§3.8: check-mechred fires on Stage-1 convergence (same precondition as
    check-admit) — lint succeeded + enforcer/qa ran to a verdict + no commits."""
    jobs = _jobs()
    assert "check-mechred" in jobs, "check-mechred job is missing from pr-pipeline.yml"
    cm = jobs["check-mechred"]
    assert set(cm["needs"]) >= {"lint", "enforcer", "qa"}, cm["needs"]
    cm_if = cm["if"]
    assert "needs.lint.outputs.committed != 'true'" in cm_if
    assert "needs.enforcer.outputs.committed != 'true'" in cm_if
    assert "needs.qa.outputs.committed != 'true'" in cm_if


def test_pre_admission_responder_gated_on_mechred_output():
    """§3.8 no-op-on-green: responder runs ONLY when check-mechred says there
    is mechanical red (has_mechanical_red='true'). Must never fire on green PRs."""
    jobs = _jobs()
    assert "pre-admission-responder" in jobs, "pre-admission-responder job is missing"
    par = jobs["pre-admission-responder"]
    assert "check-mechred" in par["needs"], par["needs"]
    assert "needs.check-mechred.outputs.has_mechanical_red == 'true'" in par["if"], par["if"]


def test_check_admit_waits_for_responder():
    """§3.8 sequencing: check-admit must wait for pre-admission-responder to
    complete (or be skipped) before dispatching the mechanic, preventing a race
    where the mechanic runs on a SHA the responder is still fixing."""
    jobs = _jobs()
    ca = jobs["check-admit"]
    assert "pre-admission-responder" in ca["needs"], ca["needs"]
    ca_if = ca["if"]
    # Responder committed → short-circuit (convergence not satisfied)
    assert "needs.pre-admission-responder.outputs.committed != 'true'" in ca_if, ca_if
    # Responder skipped (green path) is an acceptable result for check-admit to proceed
    assert "needs.pre-admission-responder.result == 'skipped'" in ca_if, ca_if


def test_stage2_mechanic_path_unchanged():
    """§3.8 (non-regression): the Stage-2 mechanic still only fires when the PR
    is admitted (admit-status=success). The pre-admission responder must not
    change this gate — the mechanic is post-admission only."""
    jobs = _jobs()
    mechanic = jobs["mechanic"]
    assert mechanic["if"].strip() == "needs.check-admit.outputs.admitted == 'true'", mechanic["if"]


def test_responder_agent_file_has_judgment_boundary():
    """§3.8: the responder agent file must document the mechanical/judgment
    boundary from enforcer.agent.md §3. Judgment calls and recusal flags are
    NEVER auto-applied pre-admission."""
    agent_file = REPO_ROOT / ".github" / "agents" / "pre-admission-responder.agent.md"
    assert agent_file.exists(), f"Agent file not found: {agent_file}"
    content = agent_file.read_text()
    assert "Mechanical" in content, "mechanical/judgment boundary not documented"
    assert "Judgment" in content, "mechanical/judgment boundary not documented"
    assert "recusal" in content.lower(), "recusal flag handling not documented"
    assert "Responder-By:" in content, "commit trailer not documented"
