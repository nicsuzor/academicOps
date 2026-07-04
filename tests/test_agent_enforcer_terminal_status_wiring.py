"""Wiring test for agent-enforcer.yml's "Compute terminal decision" step.

Worked example this guards against: PR #2080's branch forked from dev before
`scripts/ci/enforcer-terminal-status.sh` existed (added 2026-07-02, #2071) and
was never rebased. `agent-enforcer.yml` checks out the PR's OWN branch
(`ref: inputs.ref`), so the script genuinely isn't there. The step used to run
`bash scripts/ci/enforcer-terminal-status.sh` unconditionally: a missing file
exits 127 before setting any `$GITHUB_OUTPUT`, and the next step ("Post
terminal status") then tries to post an EMPTY commit-status state, which the
GitHub API rejects (422) — leaving `enforcer-status` stuck at "pending"
forever instead of a real terminal state.

This test extracts the *actual* embedded step script from the workflow YAML
(not a reimplementation) and executes it directly, mirroring the convention in
tests/test_agent_qa_terminal_status_wiring.py.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "agent-enforcer.yml"


def _extract_step_script(step_name: str) -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    for step in workflow["jobs"]["enforcer"]["steps"]:
        if step.get("name") == step_name:
            return step["run"]
    raise AssertionError(f"step {step_name!r} not found in {WORKFLOW}")


def _run(tmp_path: Path, *, committed: str = "false", review_outcome: str = "success") -> dict:
    output_path = tmp_path / "github_output"
    output_path.write_text("")
    script = _extract_step_script("Compute terminal decision")
    proc = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={
            "PATH": "/usr/bin:/bin",
            "GITHUB_OUTPUT": str(output_path),
            "COMMITTED": committed,
            "REVIEW_OUTCOME": review_outcome,
            "RETRY_OUTCOME": "",
        },
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"step itself must not crash: {proc.stderr}"
    out = {}
    for line in output_path.read_text().splitlines():
        key, _, value = line.partition("=")
        out[key] = value
    return out


def test_missing_script_fails_closed_with_actionable_description(tmp_path):
    # No scripts/ci/ directory at all — the exact pre-rebase PR-branch scenario.
    out = _run(tmp_path)
    assert out["state"] == "failure"
    assert out["failed"] == "true"
    assert "enforcer-terminal-status.sh" in out["description"]
    assert "rebase" in out["description"].lower()


def test_present_script_is_still_delegated_to_unchanged(tmp_path):
    # A stub standing in for the real script proves the guard only engages
    # when the file is absent — the normal path is untouched.
    ci_dir = tmp_path / "scripts" / "ci"
    ci_dir.mkdir(parents=True)
    stub = ci_dir / "enforcer-terminal-status.sh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        '{ echo state=success; echo description=stub-ran; echo failed=false; } >> "$GITHUB_OUTPUT"\n'
    )
    stub.chmod(0o755)

    out = _run(tmp_path)
    assert out == {"state": "success", "description": "stub-ran", "failed": "false"}
