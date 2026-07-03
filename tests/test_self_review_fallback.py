"""Tests for scripts/ci/self-review-fallback.sh — the shared self-review
identity-collision fallback recovery predicate
(specs/workflows/pr-pipeline.md §4.2 "Self-review identity-collision
fallback").

This is the single source of truth `scripts/ci/enforcer-terminal-status.sh`
and `agent-qa.yml`'s terminal-status step both source instead of
reimplementing the marker format, the `jq` filter, and the trust-scoping
check independently (an RBG-caught single-source-of-truth violation in the
PR that first introduced this mechanism — the two copies existed briefly,
one tested, one not).

Exercised here in isolation via `bash -c`, mirroring
tests/test_reviewer_authz.py's convention for a sourced-library predicate.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LIB = REPO_ROOT / "scripts" / "ci" / "self-review-fallback.sh"
SHA = "a29f1c5100000000000000000000000000000000"
OTHER_SHA = "deadbeef00000000000000000000000000000000"


def _comment(agent: str, sha: str, verdict: str, login: str = "claude[bot]") -> dict:
    return {
        "user": {"login": login},
        "body": (
            f"## {agent.title()} Review\n\n**Verdict: placeholder**\n\n"
            f"<!-- aops:self-review-fallback agent={agent} sha={sha} verdict={verdict} -->\n\n"
            "reasoning..."
        ),
    }


def _run(comments: list[dict], agent_name: str, head_sha: str) -> str:
    comments_json = json.dumps(comments)
    full_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LIB_PATH": str(LIB),
    }  # allow-fallback: minimal sane PATH for a test subprocess, mirrors test_reviewer_authz.py
    proc = subprocess.run(
        [
            "bash",
            "-c",
            'source "$LIB_PATH"; fallback_verdict_from_comments "$1" "$2" "$3"',
            "_",
            comments_json,
            agent_name,
            head_sha,
        ],
        env=full_env,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def test_script_exists():
    assert LIB.exists(), f"missing {LIB}"


def test_no_comments_returns_empty():
    assert _run([], "enforcer", SHA) == ""


def test_matching_approved_marker_recovered():
    assert _run([_comment("enforcer", SHA, "APPROVED")], "enforcer", SHA) == "APPROVED"


def test_matching_changes_requested_marker_recovered():
    out = _run([_comment("enforcer", SHA, "CHANGES_REQUESTED")], "enforcer", SHA)
    assert out == "CHANGES_REQUESTED"


def test_qa_agent_name_recovered_independently_of_enforcer():
    """The shared function must be genuinely agent-parameterized, not
    hardcoded to "enforcer" — this is the exact bug the duplication would
    have silently diverged on."""
    assert _run([_comment("qa", SHA, "APPROVED")], "qa", SHA) == "APPROVED"


def test_enforcer_marker_not_matched_when_querying_for_qa():
    """An enforcer fallback comment must not be misread as a qa verdict, even
    on the same SHA — agent scoping is exact, not a prefix/substring match."""
    assert _run([_comment("enforcer", SHA, "APPROVED")], "qa", SHA) == ""


def test_different_sha_is_not_a_match():
    """SHA-scoping is exact — a stale fallback comment from an earlier SHA
    must never be read as the current SHA's verdict."""
    assert _run([_comment("enforcer", OTHER_SHA, "APPROVED")], "enforcer", SHA) == ""


def test_untrusted_author_is_ignored():
    """Trust is scoped to claude[bot] specifically — the same identity a
    genuine review would have come from. An arbitrary commenter forging the
    marker text must not be able to manufacture a verdict."""
    out = _run([_comment("enforcer", SHA, "APPROVED", login="some-random-user")], "enforcer", SHA)
    assert out == ""


def test_latest_matching_comment_wins():
    """If somehow more than one fallback comment exists for the same agent
    and SHA, the most recent (last in the array) governs."""
    comments = [
        _comment("enforcer", SHA, "CHANGES_REQUESTED"),
        _comment("enforcer", SHA, "APPROVED"),
    ]
    assert _run(comments, "enforcer", SHA) == "APPROVED"


def test_marker_verdict_wins_over_prose_mentioning_the_other_verdict():
    """The body may mention the other verdict in prose (e.g. quoting a prior
    state) without that mention being mistaken for the marker's own verdict —
    only the value immediately following the marker governs."""
    comment = {
        "user": {"login": "claude[bot]"},
        "body": (
            "## Enforcer Review\n\n"
            "Unlike the prior pass (verdict=APPROVED), this pass found issues.\n\n"
            f"<!-- aops:self-review-fallback agent=enforcer sha={SHA} verdict=CHANGES_REQUESTED -->\n\n"
            "reasoning..."
        ),
    }
    assert _run([comment], "enforcer", SHA) == "CHANGES_REQUESTED"


def test_never_exits_the_caller_pure_function():
    """A no-match call must not itself cause the caller to exit — this is a
    pure predicate, mirroring reviewer-authz.sh's contract."""
    full_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LIB_PATH": str(LIB),
    }  # allow-fallback: minimal sane PATH for a test subprocess, mirrors test_reviewer_authz.py
    proc = subprocess.run(
        [
            "bash",
            "-c",
            'set -euo pipefail; source "$LIB_PATH"; '
            'v=$(fallback_verdict_from_comments "[]" "enforcer" "abc"); echo "reached:${v}:end"',
        ],
        env=full_env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    assert proc.stdout.strip() == "reached::end"
