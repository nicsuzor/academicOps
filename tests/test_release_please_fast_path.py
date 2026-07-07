"""Static wiring tests for the release-please fast path (pr-pipeline.md §3.13).

Release-please PRs (head ref `release-please--*`) are deterministic bot output —
version bump + CHANGELOG + uv.lock. They skip the agent reviewers and go green on
Lint+Pytest, but the release PR itself is NOT auto-merged: it accumulates every
feature PR merged since the last release, and the maintainer's deliberate merge of
that standing PR is the single human approval that batches the release and cuts the
next stable tag. These assert the structure the runtime behaviour depends on.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = REPO_ROOT / ".github" / "workflows" / "pr-pipeline.yml"
BUILD = REPO_ROOT / ".github" / "workflows" / "build-extension.yml"
ENFORCER = REPO_ROOT / ".github" / "workflows" / "agent-enforcer.yml"

RELEASE_GUARD = "!startsWith(github.event.pull_request.head.ref, 'release-please')"


def _jobs(path: Path) -> dict:
    return yaml.safe_load(path.read_text())["jobs"]


# ── The agent reviewers skip release-please PRs ──────────────────────────────


def test_agent_reviewers_skip_release_please_prs():
    """enforcer / qa / review-attestation / alignment-queue must each carry the
    release-please skip guard, so no agent runner fires on a release PR."""
    jobs = _jobs(PIPELINE)
    for name in ("enforcer", "qa", "review-attestation", "alignment-queue"):
        assert RELEASE_GUARD in jobs[name]["if"], (name, jobs[name]["if"])


# ── release-autogreen satisfies the required checks from mechanical green ────


def test_release_autogreen_job_exists_and_is_gated():
    """The fast-path job runs ONLY for same-repo release-please PRs and ONLY once
    Lint AND Pytest are green with no lint autofix commit."""
    jobs = _jobs(PIPELINE)
    assert "release-autogreen" in jobs, "release-autogreen job missing from pr-pipeline.yml"
    job = jobs["release-autogreen"]
    assert set(job["needs"]) == {"lint", "pytest"}, job["needs"]
    cond = job["if"]
    assert "startsWith(github.event.pull_request.head.ref, 'release-please')" in cond, cond
    assert "needs.lint.result == 'success'" in cond, cond
    assert "needs.pytest.result == 'success'" in cond, cond
    assert "needs.lint.outputs.committed != 'true'" in cond, cond
    assert "head.repo.full_name == github.repository" in cond, cond


def test_release_autogreen_posts_all_required_agent_statuses():
    """It must post enforcer-status, qa-status, admit-status, AND review-attestation
    green — the four ruleset-required checks the reviewers would otherwise own.
    review-attestation must carry the §10 target_sha. It must NOT arm auto-merge:
    the release PR stays open so the maintainer's merge can batch it (§3.13)."""
    job = _jobs(PIPELINE)["release-autogreen"]
    body = "\n".join(s.get("run", "") for s in job["steps"] if isinstance(s, dict))
    for ctx in ("enforcer-status", "qa-status", "admit-status", "review-attestation"):
        assert ctx in body, f"{ctx} not posted by release-autogreen:\n{body}"
    assert 'state="success"' in body, body
    assert "target_sha=$HEAD_SHA" in body, body  # attestation auditable to the head SHA
    assert "--auto" not in body, body  # deliberately not armed — batching needs a human merge


def test_release_autogreen_uses_bot_pat():
    """A ruleset-trusted required check cannot be posted with the default token
    (§4.7) — the job must use AOPS_BOT_GH_TOKEN."""
    job = _jobs(PIPELINE)["release-autogreen"]
    assert "AOPS_BOT_GH_TOKEN" in str(job.get("env", {})), job.get("env")


# ── The PR-pipeline gate no longer imposes an Environment approval ───────────


def test_gate_job_has_no_environment_approval():
    """The retired `production` gate on the PR pipeline blocked even Lint/Pytest;
    the gate job must now be a plain passthrough with no `environment:`."""
    gate = _jobs(PIPELINE)["gate"]
    assert "environment" not in gate, gate.get("environment")


def test_enforcer_reusable_workflow_has_no_release_environment():
    """The dead release-please `production` environment on agent-enforcer.yml is
    removed (release PRs no longer run the enforcer at all)."""
    enf = _jobs(ENFORCER)["enforcer"]
    assert "environment" not in enf, enf.get("environment")


# ── The single approval lives at the release-PR merge, not at deploy ─────────


def test_deploy_step_has_no_production_environment_gate():
    """The single human approval moved to the release-PR merge (§3.13);
    build-and-deploy no longer carries a `production` environment gate."""
    job = _jobs(BUILD)["build-and-deploy"]
    assert "environment" not in job, job.get("environment")


def test_deploy_concurrency_queues_instead_of_cancelling_in_flight_publish():
    """A stable tag's deploy publishes to the `dist` branch and Docker `:latest`;
    a fast-follow release-PR merge must queue behind it, not cancel it mid-publish —
    cancel-in-progress: true would let a second tag clobber the first's publish."""
    concurrency = yaml.safe_load(BUILD.read_text())["concurrency"]
    assert concurrency["cancel-in-progress"] is False, concurrency
