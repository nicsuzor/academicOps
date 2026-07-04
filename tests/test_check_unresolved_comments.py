"""Tests for scripts/ci/check-unresolved-comments.sh — the #2094 comment gate.

The script decides whether `admit-on-review.yml`'s `decide-mechanic` job should
dispatch the mechanic because a third-party (or human) review comment thread
was never addressed — regardless of enforcer/qa colour or PR mergeability
(specs/workflows/pr-pipeline.md §5). It is a deterministic check over the PR's
review-comments list: a root comment (in_reply_to_id is null) authored by
anyone NOT in EXCLUDE_LOGINS, with zero replies from anyone, counts as open.

Tests use COMMENTS_JSON to exercise the pure decision without any gh stub,
following the pattern of test_check_mechanical_red.py / test_review_attestation.py.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "check-unresolved-comments.sh"


def _root(comment_id: int, login: str, *, path: str = "foo.py", line: int = 5) -> dict:
    return {
        "id": comment_id,
        "in_reply_to_id": None,
        "user": {"login": login},
        "path": path,
        "line": line,
    }


def _reply(comment_id: int, login: str, in_reply_to_id: int) -> dict:
    return {
        "id": comment_id,
        "in_reply_to_id": in_reply_to_id,
        "user": {"login": login},
        "path": "foo.py",
        "line": 5,
    }


def run(*, comments: list[dict], exclude_logins: str | None = None) -> dict[str, str]:
    """Run check-unresolved-comments.sh with injected comments; return parsed outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cf_path = Path(tmpdir) / "comments.json"
        cf_path.write_text(json.dumps(comments))

        env: dict[str, str] = {
            "COMMENTS_JSON": str(cf_path),
            "REPO": "nicsuzor/academicOps",
            "PR_NUMBER": "2094",
            # Inherit the caller's PATH so bash/jq resolve on Nix, Homebrew, etc.
            "PATH": os.environ.get("PATH", ""),
        }
        if exclude_logins is not None:
            env["EXCLUDE_LOGINS"] = exclude_logins

        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

    out: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k] = v
    return out


# ── No open threads ──────────────────────────────────────────────────────────


def test_no_comments_no_fire():
    """No comments at all → nothing to address."""
    out = run(comments=[])
    assert out["has_unresolved_comments"] == "false"


def test_malformed_json_defaults_empty_no_fire():
    """A malformed comments payload is normalised to [] rather than crashing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cf_path = Path(tmpdir) / "comments.json"
        cf_path.write_text("not json")
        env = {
            "COMMENTS_JSON": str(cf_path),
            "REPO": "nicsuzor/academicOps",
            "PR_NUMBER": "2094",
            "PATH": os.environ.get("PATH", ""),
        }
        proc = subprocess.run(
            ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=True
        )
    assert "has_unresolved_comments=false" in proc.stdout


# ── PR #2094 replication ─────────────────────────────────────────────────────


def test_copilot_comment_with_no_reply_fires():
    """The exact PR #2094 shape: two Copilot comments, no replies → must fire."""
    comments = [
        _root(1, "Copilot", path="tests/test_agent_enforcer_terminal_status_wiring.py"),
        _root(2, "Copilot", path="tests/test_agent_enforcer_terminal_status_wiring.py"),
    ]
    out = run(comments=comments)
    assert out["has_unresolved_comments"] == "true"
    assert "Copilot" in out["reason"]
    assert "2" in out["reason"]


def test_copilot_comment_replied_by_our_bot_no_fire():
    """A Copilot thread with ANY reply (content not evaluated) counts as addressed."""
    comments = [
        _root(1, "Copilot"),
        _reply(2, "claude[bot]", in_reply_to_id=1),
    ]
    out = run(comments=comments)
    assert out["has_unresolved_comments"] == "false"


def test_copilot_comment_replied_by_human_no_fire():
    """A reply from a human also counts — presence, not authorship, is what matters."""
    comments = [
        _root(1, "Copilot"),
        _reply(2, "nicsuzor", in_reply_to_id=1),
    ]
    out = run(comments=comments)
    assert out["has_unresolved_comments"] == "false"


# ── Excluded (our own automation) authors ────────────────────────────────────


def test_own_bot_comment_excluded_no_fire():
    """A root comment authored by our own reviewer identity doesn't count."""
    comments = [_root(1, "claude[bot]")]
    out = run(comments=comments)
    assert out["has_unresolved_comments"] == "false"


def test_botnicbot_comment_excluded_no_fire():
    comments = [_root(1, "botnicbot")]
    out = run(comments=comments)
    assert out["has_unresolved_comments"] == "false"


def test_custom_exclude_list_overrides_default():
    """EXCLUDE_LOGINS is fully overridable — a custom list replaces the default."""
    comments = [_root(1, "some-other-bot[bot]")]
    out = run(comments=comments, exclude_logins="some-other-bot[bot]")
    assert out["has_unresolved_comments"] == "false"


def test_custom_exclude_list_does_not_cover_copilot():
    """Overriding EXCLUDE_LOGINS to something else no longer protects claude[bot]."""
    comments = [_root(1, "claude[bot]")]
    out = run(comments=comments, exclude_logins="some-other-bot[bot]")
    assert out["has_unresolved_comments"] == "true"


# ── Mixed / multiple threads ─────────────────────────────────────────────────


def test_multiple_open_threads_mixed_authors_fires():
    """Two independent open threads from different reviewers → fire, both named."""
    comments = [
        _root(1, "Copilot", path="a.py"),
        _root(2, "nicsuzor", path="b.py"),
    ]
    out = run(comments=comments)
    assert out["has_unresolved_comments"] == "true"
    assert "Copilot" in out["reason"]
    assert "nicsuzor" in out["reason"]


def test_one_open_one_addressed_thread_fires_on_the_open_one():
    """Only the unaddressed thread should count, but its presence alone fires."""
    comments = [
        _root(1, "Copilot", path="a.py"),
        _reply(2, "claude[bot]", in_reply_to_id=1),
        _root(3, "Copilot", path="b.py"),
    ]
    out = run(comments=comments)
    assert out["has_unresolved_comments"] == "true"
    assert "1" in out["reason"]


def test_reply_comment_from_copilot_is_not_treated_as_a_root():
    """A Copilot comment that is itself a reply (in_reply_to_id set) is not a root
    needing its own address — only root comments are evaluated."""
    comments = [
        _root(1, "nicsuzor"),
        _reply(2, "Copilot", in_reply_to_id=1),
    ]
    out = run(comments=comments)
    assert out["has_unresolved_comments"] == "false"
