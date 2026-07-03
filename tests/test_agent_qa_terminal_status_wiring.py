"""Functional test for agent-qa.yml's "Post terminal status" step — the QA
counterpart to tests/test_enforcer_terminal_status.py, closing the gap an RBG
compliance audit caught: the enforcer's self-review-fallback recovery is
extracted to a tested script (scripts/ci/enforcer-terminal-status.sh), but
QA's equivalent logic lives as inline YAML bash with no test coverage at all.

Rather than re-testing scripts/ci/self-review-fallback.sh's logic in
isolation again (that's tests/test_self_review_fallback.py's job), this
extracts the REAL "run:" script from the live agent-qa.yml, executes it
against a stubbed `gh` (which faithfully emulates `gh api --jq <expr>`
filtering, not just a raw dump), and asserts on the actual
`gh api .../statuses/...` call it makes — proving the YAML wiring itself
(variable names, quoting, sourcing the shared lib, assigning the result back
into REVIEW_STATE) is correct, not just that the shared function it calls is
correct in isolation.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "agent-qa.yml"
SHA = "2c68ca655dc112fcadfbf69324112bc182bcdb3b"

GH_STUB = r"""#!/usr/bin/env bash
# Test double for `gh`: logs each invocation's argv as one JSON array per
# line (unambiguous, unlike whitespace-joining), and faithfully applies a
# `--jq <expr>` argument when present — mirroring real `gh api` behaviour —
# so REVIEW_STATE ends up as the real filtered string, not a raw JSON dump.
jq -cn '$ARGS.positional' --args -- "$@" >> "$CALLS_LOG"

jq_expr=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "--jq" ]; then
    jq_expr="$arg"
  fi
  prev="$arg"
done

case "$*" in
  *"commits/$HEAD_SHA/statuses"*"qa-status"*)
    exit 1  # simulates "no current status" — 2>/dev/null || echo "" upstream
    ;;
  *"pulls/"*"/reviews"*)
    if [ -n "$jq_expr" ]; then jq -r "$jq_expr" < "$REVIEWS_FILE"; else cat "$REVIEWS_FILE"; fi
    ;;
  *"issues/"*"/comments"*)
    cat "$COMMENTS_FILE"
    ;;
  *"statuses/$HEAD_SHA"*)
    exit 0  # the final status POST — recorded above, nothing else to do
    ;;
  *)
    exit 1
    ;;
esac
"""


def _terminal_status_script() -> str:
    doc = yaml.safe_load(WORKFLOW.read_text())
    for step in doc["jobs"]["qa"]["steps"]:
        if step.get("name") == "Post terminal status":
            return step["run"]
    raise AssertionError('"Post terminal status" step not found in agent-qa.yml')


def _run(tmp_path: Path, *, reviews: list, comments: list) -> dict:
    """Execute the real embedded script against a stubbed `gh`, and return the
    -f key=value arguments of the final `gh api repos/.../statuses/...` call
    it made (the terminal qa-status post) — the observable outcome that
    actually matters.
    """
    script = _terminal_status_script()
    # steps.review.outcome is a GHA expression substituted before the shell
    # ever sees it; pin it to "success" the way GHA would for this scenario
    # (the agent's action step completed — it just couldn't post a review).
    script = script.replace("${{ steps.review.outcome }}", "success")

    fake_bin = tmp_path / "fakebin"
    fake_bin.mkdir()
    calls_log = tmp_path / "gh_calls.jsonl"
    reviews_file = tmp_path / "reviews.json"
    reviews_file.write_text(json.dumps(reviews))
    comments_file = tmp_path / "comments.json"
    comments_file.write_text(json.dumps(comments))

    fake_gh = fake_bin / "gh"
    fake_gh.write_text(GH_STUB)
    fake_gh.chmod(0o755)

    env = {
        "HEAD_SHA": SHA,
        "REPO": "nicsuzor/academicOps",
        "PR_NUMBER": "2081",
        "AGENT_NAME": "qa",
        "GITHUB_RUN_ID": "1",
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "CALLS_LOG": str(calls_log),
        "REVIEWS_FILE": str(reviews_file),
        "COMMENTS_FILE": str(comments_file),
    }
    proc = subprocess.run(
        ["bash", "-c", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"

    calls = (
        [json.loads(line) for line in calls_log.read_text().splitlines()]
        if calls_log.exists()
        else []
    )
    final_status_calls = [c for c in calls if any(f"statuses/{SHA}" in a for a in c) and "-f" in c]
    assert final_status_calls, f"no final status call captured; all calls:\n{calls}"
    last = final_status_calls[-1]

    out: dict[str, str] = {}
    i = 0
    while i < len(last):
        if last[i] == "-f" and i + 1 < len(last) and "=" in last[i + 1]:
            k, v = last[i + 1].split("=", 1)
            out[k] = v
        i += 1
    return out


def _fallback_comment(sha: str, verdict: str, login: str = "claude[bot]") -> dict:
    return {
        "user": {"login": login},
        "body": (
            "# QA Verification\n\n**Verdict**: placeholder\n\n"
            f"<!-- aops:self-review-fallback agent=qa sha={sha} verdict={verdict} -->\n\nreasoning..."
        ),
    }


def test_step_exists_in_workflow():
    assert _terminal_status_script(), "Post terminal status step has no run script"


def test_formal_review_approved_posts_success(tmp_path: Path):
    """Sanity baseline: the pre-existing (non-fallback) path still works."""
    reviews = [{"commit_id": SHA, "state": "APPROVED"}]
    out = _run(tmp_path, reviews=reviews, comments=[])
    assert out["state"] == "success"


def test_self_review_fallback_changes_requested_recovered(tmp_path: Path):
    """The exact PR #2081 shape: no formal review exists (self-review
    collision), but a claude[bot] fallback comment carries the verdict — the
    real embedded YAML bash must recover CHANGES_REQUESTED from it, proving
    the source + function-call wiring (not just the shared script) works."""
    out = _run(tmp_path, reviews=[], comments=[_fallback_comment(SHA, "CHANGES_REQUESTED")])
    assert out["state"] == "failure"
    assert out["context"] == "qa-status"


def test_self_review_fallback_approved_recovered(tmp_path: Path):
    out = _run(tmp_path, reviews=[], comments=[_fallback_comment(SHA, "APPROVED")])
    assert out["state"] == "success"


def test_untrusted_fallback_author_ignored_end_to_end(tmp_path: Path):
    """The trust-scoping check (claude[bot] only) must hold through the real
    YAML wiring, not just in the isolated shared-function tests — this is
    exactly the security-relevant path the audit flagged as unverified."""
    out = _run(
        tmp_path,
        reviews=[],
        comments=[_fallback_comment(SHA, "APPROVED", login="some-random-user")],
    )
    assert out["state"] == "failure"
    assert out["description"] == "QA posted no APPROVED/CHANGES_REQUESTED review"


def test_no_review_and_no_fallback_is_the_original_failure_path(tmp_path: Path):
    out = _run(tmp_path, reviews=[], comments=[])
    assert out["state"] == "failure"
    assert out["description"] == "QA posted no APPROVED/CHANGES_REQUESTED review"
