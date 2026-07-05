"""Static wiring tests for the draft→ready git-surface binding (epic aops-262def9f
WI4). The ready-for-review gate is event-driven and cannot be triggered from a dev
checkout, so these assert the structure the runtime behaviour depends on (the same
convention as test_pr_pipeline_review_gate.py). The runtime event sequence to replay
is documented in the workflow's own TEST PLAN comment.

Invariant under test: a PR is not PRESENTED as "ready for review" without an
independent QA verdict (qa-status success) bound to the CURRENT head SHA — via the
existing evidence channel (review-attestation.sh REVIEWERS=qa-status), inventing no
parallel status, and NOT duplicating the required review-attestation merge gate.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / ".github" / "workflows" / "ready-for-review-gate.yml"
RULESET = REPO_ROOT / ".github" / "rulesets" / "pr-review-and-merge.yml"


def _wf() -> dict:
    return yaml.safe_load(GATE.read_text())


def _triggers(wf: dict) -> dict:
    # PyYAML parses the bare `on:` key as boolean True.
    return wf.get("on", wf.get(True))


def _job() -> dict:
    return _wf()["jobs"]["qa-verdict-binding"]


def _job_body() -> str:
    return "\n".join(step.get("run", "") for step in _job()["steps"] if isinstance(step, dict))


def test_gate_file_exists():
    assert GATE.exists(), f"missing {GATE}"


def test_triggers_only_on_ready_for_review():
    """The gate binds the draft→ready transition — it must fire on `ready_for_review`
    and nothing else (it is not a per-push or per-review gate)."""
    triggers = _triggers(_wf())
    assert "pull_request" in triggers, triggers
    types = triggers["pull_request"]["types"]
    assert types == ["ready_for_review"], types


def test_reads_qa_verdict_via_existing_attestation_channel():
    """WI4 must reuse the existing evidence channel (review-attestation.sh with
    REVIEWERS=qa-status), not invent a parallel signal."""
    steps = _job()["steps"]
    verdict = [s for s in steps if "review-attestation.sh" in str(s.get("run", ""))]
    assert verdict, "ready-gate does not run review-attestation.sh"
    env = verdict[0].get("env", {})
    assert env.get("REVIEWERS") == "qa-status", env
    # It must bind to the live head SHA (a stale earlier-SHA verdict must not satisfy).
    assert "HEAD_SHA" in env, env


def test_undoes_ready_only_on_definitive_failure():
    """Fail-open: convert back to draft ONLY on a definitive `state == 'failure'`
    verdict, never on an unknown/empty (gh-error) state — the presentation guard must
    not fight a transient infra fault, and the required review-attestation check still
    blocks the merge."""
    steps = _job()["steps"]
    undo = [s for s in steps if "--undo" in str(s.get("run", ""))]
    assert undo, "ready-gate never calls `gh pr ready --undo`"
    assert undo[0]["if"].strip() == "steps.verdict.outputs.state == 'failure'", undo[0]["if"]
    assert "gh pr ready" in undo[0]["run"], undo[0]["run"]


def test_verdict_step_is_fail_open():
    """The verdict check must be continue-on-error so a gh/api fault leaves the PR
    ready (empty state → neither success nor failure branch fires the undo)."""
    steps = _job()["steps"]
    verdict = [s for s in steps if "review-attestation.sh" in str(s.get("run", ""))]
    assert verdict[0].get("continue-on-error") is True, verdict[0]


def test_scoped_to_same_repo_and_skips_release_please():
    """Same-repo only (fork runs cannot mint the bot token / run reviewers) and
    release-please PRs are exempt (they auto-green; undoing their ready would break
    the release flow)."""
    cond = _job()["if"]
    assert "github.event.pull_request.head.repo.full_name == github.repository" in cond, cond
    assert "!startsWith(github.event.pull_request.head.ref, 'release-please')" in cond, cond


def test_does_not_post_a_new_required_status_context():
    """WI4 takes the presentation-binding option (undo ready), NOT a parallel required
    status — review-attestation already fail-closes the merge gate. The gate must not
    write any of the ruleset's required status contexts (no duplication)."""
    body = _job_body()
    ruleset = RULESET.read_text()
    required = [
        line.split("context:", 1)[1].strip().strip('"')
        for line in ruleset.splitlines()
        if "context:" in line and not line.strip().startswith("#")
    ]
    # The gate posts NO commit statuses at all (it only reads them + undoes ready).
    assert "gh api" not in body or "statuses/" not in body, body
    for ctx in required:
        assert f'context="{ctx}"' not in body, f"ready-gate must not post required status {ctx!r}"
