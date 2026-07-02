"""Structural tests for .github/workflows/conflict-admission-sweep.yml
(specs/workflows/pr-pipeline.md §3.11, §5.1).

This workflow had no YAML-structure test before the §5.1 admission-primitive
consolidation. Two things are pinned here so a future edit can't silently
regress them:

1. The `admit` job re-resolves the PR's live HEAD SHA (fixing a latent
   staleness race — the old code trusted a SHA snapshotted by the separate,
   earlier `discover` job) and calls the shared scripts/ci/admit-pr.sh with
   that freshly-resolved SHA, not the discover-time snapshot.
2. The `mechanic` job deliberately still uses the discover-time
   `matrix.pr.sha` snapshot — NOT `admit`'s freshly-resolved SHA. This is a
   documented, intentional asymmetry (matrix-to-matrix output correlation
   isn't supported by GHA, and the `sha` input there only affects an
   informational status, not a required check), not an oversight.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "conflict-admission-sweep.yml"


def _jobs() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]


def test_admit_job_checks_out_before_resolving_sha():
    steps = _jobs()["admit"]["steps"]
    assert any(step.get("uses", "").startswith("actions/checkout") for step in steps)


def test_admit_job_resolves_live_sha_not_matrix_snapshot():
    steps = _jobs()["admit"]["steps"]
    resolve_steps = [s for s in steps if s.get("id") == "resolve"]
    assert len(resolve_steps) == 1, "expected exactly one step id: resolve"
    resolve_body = resolve_steps[0].get("run", "")
    assert "gh pr view" in resolve_body
    assert "headRefOid" in resolve_body
    assert "sha=$HEAD_SHA" in resolve_body or 'sha="$HEAD_SHA"' in resolve_body


def test_admit_job_calls_shared_admit_pr_script_with_resolved_sha():
    steps = _jobs()["admit"]["steps"]
    grant_steps = [s for s in steps if s.get("run") == "bash scripts/ci/admit-pr.sh"]
    assert len(grant_steps) == 1, "expected exactly one step calling scripts/ci/admit-pr.sh"
    env = grant_steps[0].get("env", {})
    assert env.get("SHA") == "${{ steps.resolve.outputs.sha }}", env
    assert "matrix.pr.sha" not in env.get("SHA", "")
    assert "PR_NUMBER" in env
    assert "REASON" in env
    assert "conflict-admission sweep" in env["REASON"]


def test_admit_job_no_longer_inlines_gh_api_status_call():
    # The mechanical admit-status POST + auto-merge arm now lives solely in
    # scripts/ci/admit-pr.sh — the workflow step must not reimplement it.
    steps = _jobs()["admit"]["steps"]
    bodies = " ".join(s.get("run", "") for s in steps)
    assert 'context="admit-status"' not in bodies
    assert "gh pr merge" not in bodies


def test_mechanic_job_deliberately_uses_matrix_snapshot_sha():
    mechanic = _jobs()["mechanic"]
    assert mechanic["with"]["sha"] == "${{ matrix.pr.sha }}"


def test_mechanic_job_needs_admit():
    mechanic = _jobs()["mechanic"]
    assert "admit" in mechanic["needs"]
