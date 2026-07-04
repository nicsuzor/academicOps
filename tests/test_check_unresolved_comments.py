"""Tests for scripts/ci/check-unresolved-comments.sh — the #2094 comment gate.

The script feeds two consumers: the REQUIRED `comment-triage-status` check
(pr-pipeline.yml / admit-on-review.yml) and the mechanic's review-response
dispatch decision (admit-on-review.yml's `decide-mechanic`). It is a
deterministic, FAIL-CLOSED check over two surfaces:

  1. Inline review-comment threads (`/pulls/{pr}/comments`): a root comment
     (in_reply_to_id is null) authored by anyone NOT in EXCLUDE_LOGINS, with
     zero replies from anyone, counts as open.
  2. Review bodies (`/pulls/{pr}/reviews`): a COMMENTED/CHANGES_REQUESTED
     review with a non-empty body from anyone NOT in EXCLUDE_LOGINS, with no
     PR-level (issue) comment posted after it, counts as open. This catches a
     third-party review with substantive feedback in the body but ZERO inline
     comments — a class PR #2101's version of this script could not detect.

Tests use *_JSON env overrides to exercise the pure decision without any gh
stub, following the pattern of test_check_mechanical_red.py /
test_review_attestation.py.
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


def _review(
    review_id: int,
    login: str,
    *,
    state: str = "COMMENTED",
    body: str = "Substantive feedback here.",
    submitted_at: str = "2026-07-04T03:41:53Z",
) -> dict:
    return {
        "id": review_id,
        "user": {"login": login},
        "state": state,
        "body": body,
        "submitted_at": submitted_at,
    }


def _issue_comment(created_at: str) -> dict:
    return {"created_at": created_at}


def run(
    *,
    comments: list[dict] | None = None,
    reviews: list[dict] | None = None,
    issue_comments: list[dict] | None = None,
    exclude_logins: str | None = None,
    raw_comments: str | None = None,
) -> dict[str, str]:
    """Run check-unresolved-comments.sh with injected fixtures; return parsed outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        comments_path = Path(tmpdir) / "comments.json"
        reviews_path = Path(tmpdir) / "reviews.json"
        issue_comments_path = Path(tmpdir) / "issue_comments.json"

        if raw_comments is not None:
            comments_path.write_text(raw_comments)
        else:
            comments_path.write_text(json.dumps(comments or []))
        reviews_path.write_text(json.dumps(reviews or []))
        issue_comments_path.write_text(json.dumps(issue_comments or []))

        env: dict[str, str] = {
            "COMMENTS_JSON": str(comments_path),
            "REVIEWS_JSON": str(reviews_path),
            "ISSUE_COMMENTS_JSON": str(issue_comments_path),
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


# ── No open threads / reviews ────────────────────────────────────────────────


def test_no_comments_no_fire():
    """No comments, no reviews at all → nothing to address."""
    out = run(comments=[], reviews=[])
    assert out["has_unresolved_comments"] == "false"


def test_malformed_comments_json_fails_closed():
    """A malformed comments payload is FAIL-CLOSED (unresolved=true), not fail-open.

    v1 of this script (PR #2101) normalised malformed JSON to `[]` (fail-open,
    i.e. "nothing unresolved") — inconsistent with review-attestation.sh's
    fail-closed convention for this class of merge-blocking check, and a live
    footgun: a transient `gh api` hiccup would silently wave a PR through with
    real unaddressed comments.
    """
    out = run(raw_comments="not json")
    assert out["has_unresolved_comments"] == "true"
    assert "fail" in out["reason"].lower()


# ── PR #2094 replication (inline comments) ───────────────────────────────────


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


# ── Review bodies (no inline comment required) ───────────────────────────────


def test_review_body_only_no_inline_comments_fires():
    """rbg's criterion-substitution finding: a COMMENTED review with a substantive
    body and ZERO inline comments must still fire — this is the exact gap PR
    #2101's version of this script left open."""
    reviews = [_review(1, "copilot-pull-request-reviewer[bot]", state="COMMENTED")]
    out = run(comments=[], reviews=reviews)
    assert out["has_unresolved_comments"] == "true"
    assert "copilot-pull-request-reviewer[bot]" in out["reason"]


def test_changes_requested_review_body_fires_too():
    """CHANGES_REQUESTED reviews are covered, not just COMMENTED."""
    reviews = [_review(1, "some-reviewer", state="CHANGES_REQUESTED")]
    out = run(comments=[], reviews=reviews)
    assert out["has_unresolved_comments"] == "true"


def test_approved_review_body_never_fires():
    """An APPROVED review's body is never treated as unaddressed feedback."""
    reviews = [_review(1, "some-reviewer", state="APPROVED", body="LGTM, great work!")]
    out = run(comments=[], reviews=reviews)
    assert out["has_unresolved_comments"] == "false"


def test_empty_review_body_does_not_fire():
    """A COMMENTED review with an empty/whitespace-only body carries no feedback."""
    reviews = [_review(1, "some-reviewer", state="COMMENTED", body="   ")]
    out = run(comments=[], reviews=reviews)
    assert out["has_unresolved_comments"] == "false"


def test_review_body_addressed_by_later_pr_comment_no_fire():
    """A PR-level comment (the mechanic's `gh pr comment` triage summary in
    production) posted AFTER the review's submitted_at counts as addressed."""
    reviews = [_review(1, "Copilot", submitted_at="2026-07-04T03:41:53Z")]
    issue_comments = [_issue_comment("2026-07-04T03:50:00Z")]
    out = run(comments=[], reviews=reviews, issue_comments=issue_comments)
    assert out["has_unresolved_comments"] == "false"


def test_review_body_not_addressed_by_earlier_pr_comment():
    """A PR-level comment posted BEFORE the review doesn't count — it can't have
    been a response to feedback that didn't exist yet."""
    reviews = [_review(1, "Copilot", submitted_at="2026-07-04T03:41:53Z")]
    issue_comments = [_issue_comment("2026-07-04T03:00:00Z")]
    out = run(comments=[], reviews=reviews, issue_comments=issue_comments)
    assert out["has_unresolved_comments"] == "true"


def test_own_bot_review_excluded_no_fire():
    """A review body authored by our own automation doesn't count as third-party
    feedback needing triage."""
    reviews = [_review(1, "botnicbot", state="COMMENTED")]
    out = run(comments=[], reviews=reviews)
    assert out["has_unresolved_comments"] == "false"


def test_inline_comment_and_review_body_both_open_reports_both():
    """Both surfaces can be open simultaneously; the reason names both counts."""
    comments = [_root(1, "Copilot", path="a.py")]
    reviews = [_review(2, "some-other-bot", state="CHANGES_REQUESTED")]
    out = run(comments=comments, reviews=reviews)
    assert out["has_unresolved_comments"] == "true"
    assert "inline comment thread" in out["reason"]
    assert "review(s)" in out["reason"]
