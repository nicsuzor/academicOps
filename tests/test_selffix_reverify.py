"""Tests for the pre-admission self-fix re-verify decision (epic aops-262def9f WI5).

`scripts/ci/selffix-reverify.sh` decides whether a pre-admission `synchronize`
should RE-DISPATCH the named reviewers (enforcer + qa) because the branch tip is a
BOT SELF-FIX commit whose fixed SHA would otherwise never get a fresh qa verdict
before the human admit gate (the reachable-path contradiction the §3.1 fire-once
gate creates — pr-pipeline.yml enforcer :293 / qa :318).

The decision is a pure function over (HEAD commit message, loop-capable self-fix
count, ceiling). These tests inject those via env (HEAD_MESSAGE / SELFFIX_COUNT /
COMPARE_JSON) so no `gh` stub is needed — mirroring test_review_attestation.py and
test_check_mechanical_red.py.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "selffix-reverify.sh"
SHA = "abc123def456abc123def456abc123def456abcd"


def run(
    head_message: str, *, selffix_count: int | None = None, max_reverify: str | None = None
) -> str:
    env = {
        "REPO": "o/r",
        "HEAD_SHA": SHA,
        "BASE_BRANCH": "dev",
        "HEAD_MESSAGE": head_message,
        "PATH": "/usr/bin:/bin:/usr/local/bin",
    }
    # Inject the count so no live gh call is made; default to 1 (this tip counts).
    env["SELFFIX_COUNT"] = str(selffix_count if selffix_count is not None else 1)
    if max_reverify is not None:
        env["MAX_SELFFIX_REVERIFY"] = max_reverify
    proc = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=True
    )
    out: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out["reverify"]


def test_script_exists_and_executable():
    assert SCRIPT.exists(), f"missing {SCRIPT}"


def test_enforcer_selffix_head_reverifies():
    """An enforcer self-fix tip (Enforcer-By: trailer) under the ceiling → re-fire."""
    msg = "fix: correct axiom coupling\n\nEnforcer-By: agent"
    assert run(msg, selffix_count=1) == "true"


def test_responder_selffix_head_reverifies():
    """A pre-admission responder tip (Responder-By: trailer) → re-fire."""
    msg = "fix: clear mechanical red\n\nResponder-By: agent"
    assert run(msg, selffix_count=2) == "true"


def test_lint_autofix_head_reverifies():
    """A lint autofix tip (deterministic style commit) still needs a fresh verdict."""
    msg = "style: autofix lint, formatting, and MCP name normalization"
    # Lint autofix is a TRIGGER but not counted; count of loop-capable commits is 0.
    assert run(msg, selffix_count=0) == "true"


def test_human_push_head_does_not_reverify():
    """Fire-once preserved: a human (non-self-fix) tip must NOT re-fire the reviewers."""
    msg = "feat: implement the thing the maintainer asked for"
    assert run(msg, selffix_count=0) == "false"


def test_trailer_must_be_line_anchored_not_substring():
    """A commit that merely MENTIONS the trailer in prose is not a self-fix tip."""
    msg = "docs: explain how the Enforcer-By: trailer works in prose"
    assert run(msg, selffix_count=0) == "false"


def test_ceiling_reached_stops_reverify():
    """At/above MAX_SELFFIX_REVERIFY, stop auto-re-firing (admission boundary re-verifies)."""
    msg = "fix: another enforcer pass\n\nEnforcer-By: agent"
    assert run(msg, selffix_count=5, max_reverify="5") == "false"
    assert run(msg, selffix_count=6, max_reverify="5") == "false"


def test_below_ceiling_still_reverifies():
    msg = "fix: enforcer pass\n\nEnforcer-By: agent"
    assert run(msg, selffix_count=4, max_reverify="5") == "true"


def test_lint_autofix_not_counted_toward_ceiling(tmp_path: Path):
    """The ceiling counts only loop-capable (Enforcer-By/Responder-By) commits; a
    branch full of idempotent lint autofixes never exhausts the budget. Exercised
    via the COMPARE_JSON path so the jq count logic itself is covered."""
    compare = {
        "commits": [
            {"commit": {"message": "style: autofix lint, formatting, and MCP name normalization"}},
            {"commit": {"message": "style: autofix lint, formatting, and MCP name normalization"}},
            {"commit": {"message": "fix: correct thing\n\nEnforcer-By: agent"}},
        ]
    }
    cf = tmp_path / "compare.json"
    cf.write_text(json.dumps(compare))
    env = {
        "REPO": "o/r",
        "HEAD_SHA": SHA,
        "BASE_BRANCH": "dev",
        "HEAD_MESSAGE": "fix: correct thing\n\nEnforcer-By: agent",
        "COMPARE_JSON": str(cf),
        "MAX_SELFFIX_REVERIFY": "5",
        "PATH": "/usr/bin:/bin:/usr/local/bin",
    }
    proc = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=True
    )
    # Only the one Enforcer-By: commit is counted → 1 < 5 → reverify.
    assert "reverify=true" in proc.stdout, proc.stdout


def test_malformed_count_fails_closed():
    """A non-numeric injected count must fail closed (no re-fire), never crash-open."""
    env = {
        "REPO": "o/r",
        "HEAD_SHA": SHA,
        "BASE_BRANCH": "dev",
        "HEAD_MESSAGE": "fix: x\n\nEnforcer-By: agent",
        "SELFFIX_COUNT": "not-a-number",
        "PATH": "/usr/bin:/bin:/usr/local/bin",
    }
    proc = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=True
    )
    assert "reverify=false" in proc.stdout, proc.stdout
