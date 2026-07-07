"""Functional wiring test for agent-qa.yml's terminal qa-status steps.

The terminal decision was extracted from inline YAML bash into the unit-tested
`scripts/ci/qa-terminal-status.sh` (aops_e958bd56 — see tests/test_qa_terminal_
status.py for the decision logic itself, including the marker-scoping fix that
stops an enforcer approval leaking through as a false qa-status=success).

This test validates the WIRING that the unit test cannot see: that the two live
workflow steps are correctly connected —

  1. "Compute terminal decision" actually invokes scripts/ci/qa-terminal-status.sh
     and captures its `state`/`description` into $GITHUB_OUTPUT, and
  2. "Post terminal status" forwards THOSE outputs (not a re-derived verdict) to
     the `gh api .../statuses/...` POST.

It runs both steps' REAL `run:` bodies end-to-end: the decision step against the
real script (reviews injected via REVIEWS_JSON so no `gh` call is made), then the
post step against a stubbed `gh`, emulating the GHA `${{ steps.decision.outputs.* }}`
substitution the runner would perform between them.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "agent-qa.yml"
SHA = "2c68ca655dc112fcadfbf69324112bc182bcdb3b"

# Review bodies exactly as the agents post them (qa.agent.md §Identity;
# enforcer.agent.md §5).
QA_BODY = "# QA Verification — VERIFIED"
ENFORCER_BODY = "## Enforcer Review — clean"

GH_STUB = r"""#!/usr/bin/env bash
# Test double for `gh`: logs each invocation's argv as one JSON array per line,
# and faithfully applies a `--jq <expr>` argument when present.
jq -cn '$ARGS.positional' --args -- "$@" >> "$CALLS_LOG"

jq_expr=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "--jq" ]; then jq_expr="$arg"; fi
  prev="$arg"
done

case "$*" in
  *"commits/$HEAD_SHA/statuses"*)
    exit 1  # simulates "no current status" — 2>/dev/null || echo "" upstream
    ;;
  *"statuses/$HEAD_SHA"*)
    exit 0  # the final status POST — recorded above, nothing else to do
    ;;
  *)
    exit 1
    ;;
esac
"""


def _step_run(name: str) -> str:
    doc = yaml.safe_load(WORKFLOW.read_text())
    for step in doc["jobs"]["qa"]["steps"]:
        if step.get("name") == name:
            return step["run"]
    raise AssertionError(f'"{name}" step not found in agent-qa.yml')


def _run(tmp_path: Path, *, reviews: list, review_outcome: str = "success") -> dict:
    fake_bin = tmp_path / "fakebin"
    fake_bin.mkdir()
    calls_log = tmp_path / "gh_calls.jsonl"
    reviews_file = tmp_path / "reviews.json"
    gh_out = tmp_path / "github_output"
    reviews_file.write_text(json.dumps(reviews))
    gh_out.write_text("")

    fake_gh = fake_bin / "gh"
    fake_gh.write_text(GH_STUB)
    fake_gh.chmod(0o755)

    base_env = {
        "HEAD_SHA": SHA,
        "REPO": "nicsuzor/academicOps",
        "PR_NUMBER": "2081",
        "AGENT_NAME": "qa",
        "GITHUB_RUN_ID": "1",
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "CALLS_LOG": str(calls_log),
        "GITHUB_OUTPUT": str(gh_out),
    }

    # ── Step 1: "Compute terminal decision" — real script, reviews via REVIEWS_JSON
    decision_script = _step_run("Compute terminal decision")
    dec_env = {**base_env, "REVIEW_OUTCOME": review_outcome, "REVIEWS_JSON": str(reviews_file)}
    proc = subprocess.run(
        ["bash", "-c", decision_script],
        cwd=REPO_ROOT,
        env=dec_env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 0, f"decision stderr={proc.stderr}\nstdout={proc.stdout}"

    decision: dict[str, str] = {}
    for line in gh_out.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            decision[k] = v

    # ── Emulate the GHA runner substituting ${{ steps.decision.outputs.* }} ──
    post_script = _step_run("Post terminal status")
    post_script = re.sub(
        r"\$\{\{\s*steps\.decision\.outputs\.(\w+)\s*\}\}",
        lambda m: decision.get(m.group(1), ""),
        post_script,
    )

    proc = subprocess.run(
        ["bash", "-c", post_script],
        cwd=REPO_ROOT,
        env=base_env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 0, f"post stderr={proc.stderr}\nstdout={proc.stdout}"

    calls = (
        [json.loads(line) for line in calls_log.read_text().splitlines()]
        if calls_log.exists()
        else []
    )
    final = [c for c in calls if any(f"statuses/{SHA}" in a for a in c) and "-f" in c]
    assert final, f"no final status POST captured; all calls:\n{calls}\ndecision={decision}"
    last = final[-1]

    out: dict[str, str] = {}
    i = 0
    while i < len(last):
        if last[i] == "-f" and i + 1 < len(last) and "=" in last[i + 1]:
            k, v = last[i + 1].split("=", 1)
            out[k] = v
        i += 1
    return out


def test_steps_exist_in_workflow():
    assert _step_run("Compute terminal decision")
    assert _step_run("Post terminal status")


def test_qa_review_approved_posts_success(tmp_path: Path):
    out = _run(tmp_path, reviews=[{"commit_id": SHA, "state": "APPROVED", "body": QA_BODY}])
    assert out["state"] == "success"
    assert out["context"] == "qa-status"


def test_qa_review_changes_requested_posts_failure(tmp_path: Path):
    out = _run(
        tmp_path, reviews=[{"commit_id": SHA, "state": "CHANGES_REQUESTED", "body": QA_BODY}]
    )
    assert out["state"] == "failure"


def test_no_review_posts_failure(tmp_path: Path):
    out = _run(tmp_path, reviews=[])
    assert out["state"] == "failure"
    assert out["description"] == "QA posted no APPROVED/CHANGES_REQUESTED review"


def test_enforcer_approval_does_not_post_qa_success(tmp_path: Path):
    """End-to-end wiring of the aops_e958bd56 fix: an enforcer APPROVED review on
    the exact head SHA, with the QA agent having failed to run, must NOT surface
    as qa-status=success through the live two-step path."""
    out = _run(
        tmp_path,
        reviews=[{"commit_id": SHA, "state": "APPROVED", "body": ENFORCER_BODY}],
        review_outcome="failure",
    )
    assert out["state"] == "failure"
    assert out["description"] == "Agent run failed without a verdict review"
