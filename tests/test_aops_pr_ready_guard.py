"""Tests for the own-PR-ready guard in plugins/aops/hooks/handlers.py.

A polecat run must not be able to mark its own PR ready for review --
"independent review = a different run" has to be a mechanical fact the
worker side enforces, not dispatch discipline alone (aops_3c133222,
aops_d8085e5b). The guard compares the PR's head branch against this
session's own checked-out branch: same branch means the session is trying to
ready its own PR; a different branch means it isn't.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_HOOKS = REPO_ROOT / "lib" / "hooks"
AOPS_HOOKS = REPO_ROOT / "plugins" / "aops" / "hooks"

if str(LIB_HOOKS) not in sys.path:
    sys.path.insert(0, str(LIB_HOOKS))
if str(AOPS_HOOKS) not in sys.path:
    sys.path.insert(0, str(AOPS_HOOKS))

handlers_spec = importlib.util.spec_from_file_location("aops_handlers", AOPS_HOOKS / "handlers.py")
assert handlers_spec is not None and handlers_spec.loader is not None
handlers = importlib.util.module_from_spec(handlers_spec)
# Deliberately NOT registered as sys.modules["handlers"]: that name collides
# with plugins/rbg/hooks/handlers.py, which other test files (test_cope.py)
# import under the bare name "handlers". Under pytest-xdist, whichever file
# runs first in a worker process wins that global slot for every test after
# it -- this exact collision made tests/test_cope.py fail with
# `AttributeError: module 'aops_handlers' has no attribute 'evaluate'` once
# this file was added (it shifted xdist's grouping). Nothing in this file
# patches via the string "handlers.*", so no registration is needed.
handlers_spec.loader.exec_module(handlers)

from dispatch import HookContext, Kind  # type: ignore[import-not-found]


def _ctx(command: str, tool: str = "Bash", cwd: str = "/workspace") -> HookContext:
    return HookContext(
        client="claude",
        event="PreToolUse",
        tool=tool,
        command=command,
        cwd=cwd,
        raw={"tool_input": {"command": command}},
        hooks_dir=AOPS_HOOKS,
    )


# ---------------------------------------------------------------------------
# registration
# ---------------------------------------------------------------------------


def test_guard_registered_on_pre_tool_use():
    assert handlers.guard_own_pr_ready in handlers.HANDLERS["PreToolUse"]


# ---------------------------------------------------------------------------
# scope: which tool calls it even looks at
# ---------------------------------------------------------------------------


def test_ignores_non_shell_tools():
    ctx = _ctx("gh pr ready 5", tool="Read")
    assert handlers.guard_own_pr_ready(ctx) is None


def test_ignores_unrelated_bash_commands():
    ctx = _ctx("gh pr view 5")
    with patch.object(handlers, "_own_git_branch") as mock_branch:
        assert handlers.guard_own_pr_ready(ctx) is None
    mock_branch.assert_not_called()


def test_ignores_empty_command():
    ctx = _ctx("")
    assert handlers.guard_own_pr_ready(ctx) is None


# ---------------------------------------------------------------------------
# the raw GraphQL mutation: refused outright, no lookup
# ---------------------------------------------------------------------------


def test_refuses_raw_graphql_mutation_outright():
    command = (
        "gh api graphql -f query='mutation { markPullRequestReadyForReview("
        'input: {pullRequestId: "PR_kwABC"}) { clientMutationId } }\''
    )
    ctx = _ctx(command)
    with patch.object(handlers, "_own_git_branch") as mock_branch:
        res = handlers.guard_own_pr_ready(ctx)
    mock_branch.assert_not_called()
    assert res is not None
    assert res.kind is Kind.REFUSE
    assert "aops_3c133222" in res.inject_text
    assert "gh pr ready" in res.inject_text


# ---------------------------------------------------------------------------
# gh pr ready --undo: reverting to draft is not a review bypass
# ---------------------------------------------------------------------------


def test_undo_is_never_blocked():
    ctx = _ctx("gh pr ready 5 --undo")
    with patch.object(handlers, "_own_git_branch") as mock_branch:
        assert handlers.guard_own_pr_ready(ctx) is None
    mock_branch.assert_not_called()


# ---------------------------------------------------------------------------
# no explicit ref: gh defaults to the current branch's own PR
# ---------------------------------------------------------------------------


def test_no_argument_refuses_using_current_branch_pr():
    ctx = _ctx("gh pr ready")
    with patch.object(handlers, "_own_git_branch", return_value="polecat/s1"):
        res = handlers.guard_own_pr_ready(ctx)
    assert res is not None
    assert res.kind is Kind.REFUSE
    assert "no argument" in res.inject_text


def test_no_argument_refuses_when_own_branch_unknown():
    ctx = _ctx("gh pr ready")
    with patch.object(handlers, "_own_git_branch", return_value=None):
        res = handlers.guard_own_pr_ready(ctx)
    assert res is not None
    assert res.kind is Kind.REFUSE
    assert "could not determine" in res.inject_text


# ---------------------------------------------------------------------------
# explicit branch-name ref: no API lookup needed
# ---------------------------------------------------------------------------


def test_ref_matching_own_branch_name_is_refused_without_lookup():
    ctx = _ctx("gh pr ready polecat/s1")
    with (
        patch.object(handlers, "_own_git_branch", return_value="polecat/s1"),
        patch.object(handlers, "_pr_head_branch") as mock_head,
    ):
        res = handlers.guard_own_pr_ready(ctx)
    mock_head.assert_not_called()
    assert res is not None
    assert res.kind is Kind.REFUSE


def test_ref_naming_a_different_branch_is_allowed_without_lookup():
    ctx = _ctx("gh pr ready someone-elses-branch")
    with (
        patch.object(handlers, "_own_git_branch", return_value="polecat/s1"),
        patch.object(handlers, "_pr_head_branch") as mock_head,
    ):
        res = handlers.guard_own_pr_ready(ctx)
    mock_head.assert_not_called()
    assert res is None


# ---------------------------------------------------------------------------
# explicit PR number / URL: resolved via `gh pr view`
# ---------------------------------------------------------------------------


def test_pr_number_resolving_to_own_branch_is_refused():
    ctx = _ctx("gh pr ready 2653")
    with (
        patch.object(handlers, "_own_git_branch", return_value="polecat/s1"),
        patch.object(handlers, "_pr_head_branch", return_value="polecat/s1") as mock_head,
    ):
        res = handlers.guard_own_pr_ready(ctx)
    mock_head.assert_called_once_with("2653", "/workspace")
    assert res is not None
    assert res.kind is Kind.REFUSE
    assert "2653" in res.inject_text


def test_pr_number_resolving_to_a_different_branch_is_allowed():
    ctx = _ctx("gh pr ready 2654")
    with (
        patch.object(handlers, "_own_git_branch", return_value="polecat/s1"),
        patch.object(handlers, "_pr_head_branch", return_value="polecat/s2-review"),
    ):
        res = handlers.guard_own_pr_ready(ctx)
    assert res is None


def test_pr_url_ref_is_treated_as_opaque_and_resolved():
    ctx = _ctx("gh pr ready https://github.com/nicsuzor/academicOps/pull/2653")
    with (
        patch.object(handlers, "_own_git_branch", return_value="polecat/s1"),
        patch.object(handlers, "_pr_head_branch", return_value="polecat/s1") as mock_head,
    ):
        res = handlers.guard_own_pr_ready(ctx)
    mock_head.assert_called_once()
    assert res is not None
    assert res.kind is Kind.REFUSE


def test_unresolvable_pr_ref_refuses_fail_closed():
    ctx = _ctx("gh pr ready 2653")
    with (
        patch.object(handlers, "_own_git_branch", return_value="polecat/s1"),
        patch.object(handlers, "_pr_head_branch", return_value=None),
    ):
        res = handlers.guard_own_pr_ready(ctx)
    assert res is not None
    assert res.kind is Kind.REFUSE
    assert "could not resolve" in res.inject_text


# ---------------------------------------------------------------------------
# agy's shell tool name
# ---------------------------------------------------------------------------


def test_applies_to_agy_run_command_tool_too():
    ctx = _ctx("gh pr ready", tool="run_command")
    with patch.object(handlers, "_own_git_branch", return_value="polecat/s1"):
        res = handlers.guard_own_pr_ready(ctx)
    assert res is not None
    assert res.kind is Kind.REFUSE


# ---------------------------------------------------------------------------
# ref parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command,expected_ref,expected_undo",
    [
        ("gh pr ready", None, False),
        ("gh pr ready 123", "123", False),
        ("gh pr ready --undo", None, True),
        ("gh pr ready 123 --undo", "123", True),
        ("gh pr ready https://github.com/o/r/pull/9", "https://github.com/o/r/pull/9", False),
        ("gh pr ready feature-x", "feature-x", False),
    ],
)
def test_pr_ready_ref_parsing(command, expected_ref, expected_undo):
    ref, is_undo = handlers._pr_ready_ref(command)
    assert ref == expected_ref
    assert is_undo == expected_undo


# ---------------------------------------------------------------------------
# subprocess-facing helpers, mocked at the subprocess boundary
# ---------------------------------------------------------------------------


def test_own_git_branch_reads_head_via_git(monkeypatch):
    captured = {}

    class FakeResult:
        returncode = 0
        stdout = "polecat/s1\n"

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return FakeResult()

    monkeypatch.setattr(handlers.subprocess, "run", fake_run)
    assert handlers._own_git_branch("/workspace") == "polecat/s1"
    assert captured["args"][:2] == ["git", "-C"]
    assert captured["kwargs"]["timeout"] == 10


def test_own_git_branch_returns_none_on_empty_cwd():
    assert handlers._own_git_branch("") is None


def test_own_git_branch_returns_none_on_nonzero_exit(monkeypatch):
    class FakeResult:
        returncode = 128
        stdout = ""

    monkeypatch.setattr(handlers.subprocess, "run", lambda *a, **k: FakeResult())
    assert handlers._own_git_branch("/workspace") is None


def test_pr_head_branch_reads_via_gh_pr_view(monkeypatch):
    captured = {}

    class FakeResult:
        returncode = 0
        stdout = "polecat/s2-review\n"

    def fake_run(args, **kwargs):
        captured["args"] = args
        return FakeResult()

    monkeypatch.setattr(handlers.subprocess, "run", fake_run)
    assert handlers._pr_head_branch("2653", "/workspace") == "polecat/s2-review"
    assert captured["args"][:3] == ["gh", "pr", "view"]


def test_pr_head_branch_returns_none_on_failure(monkeypatch):
    def raising_run(*a, **k):
        raise OSError("gh not found")

    monkeypatch.setattr(handlers.subprocess, "run", raising_run)
    assert handlers._pr_head_branch("2653", "/workspace") is None


# ---------------------------------------------------------------------------
# session-identity-keyed branch, recorded at SessionStart
#
# A branch-only check is defeated by a second clone at a different path in
# the same session (observed on #2658: the authoring run flipped its own PR
# ready from an "independent v0.10 clone" that was, in fact, its own second
# checkout). `AOPS_SESSION_STATE_DIR` is set once per container, before any
# such cwd-switching, so a branch recorded there at SessionStart is a fact
# about the session, not about whichever directory a later command happens
# to run in.
# ---------------------------------------------------------------------------


def test_record_session_own_branch_writes_state_file_at_session_start(monkeypatch, tmp_path):
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))
    ctx = HookContext(
        client="claude",
        event="SessionStart",
        cwd="/workspace",
        raw={},
        hooks_dir=AOPS_HOOKS,
    )
    with patch.object(handlers, "_own_git_branch", return_value="polecat/own-pr-ready-block-s1"):
        handlers.session_start(ctx)
    state_file = tmp_path / handlers._OWN_BRANCH_STATE_FILENAME
    assert state_file.read_text().strip() == "polecat/own-pr-ready-block-s1"


def test_record_session_own_branch_is_a_noop_without_state_dir(monkeypatch):
    monkeypatch.delenv("AOPS_SESSION_STATE_DIR", raising=False)
    ctx = HookContext(client="claude", event="SessionStart", cwd="/workspace", raw={})
    with patch.object(handlers, "_own_git_branch", return_value="polecat/s1"):
        handlers.session_start(ctx)  # must not raise


def test_record_session_own_branch_is_a_noop_when_branch_unknown(monkeypatch, tmp_path):
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))
    ctx = HookContext(client="claude", event="SessionStart", cwd="/workspace", raw={})
    with patch.object(handlers, "_own_git_branch", return_value=None):
        handlers.session_start(ctx)
    assert not (tmp_path / handlers._OWN_BRANCH_STATE_FILENAME).exists()


def test_recorded_session_own_branch_reads_state_file(monkeypatch, tmp_path):
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))
    (tmp_path / handlers._OWN_BRANCH_STATE_FILENAME).write_text("polecat/own-pr-ready-block-s1\n")
    assert handlers._recorded_session_own_branch() == "polecat/own-pr-ready-block-s1"


def test_recorded_session_own_branch_is_none_without_state_dir(monkeypatch):
    monkeypatch.delenv("AOPS_SESSION_STATE_DIR", raising=False)
    assert handlers._recorded_session_own_branch() is None


def test_recorded_session_own_branch_is_none_when_file_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))
    assert handlers._recorded_session_own_branch() is None


def test_guard_refuses_the_second_clone_bypass_observed_on_2658(monkeypatch, tmp_path):
    """The exact incident this task exists to close.

    The session's *current* cwd is a second, independent-looking clone on
    `v0.10` -- a bare `_own_git_branch(ctx.cwd)` check would allow this, as
    it did on the real #2658 incident. The branch recorded at this
    session's SessionStart (before the second clone existed) is the PR's
    actual head branch, so the guard must catch it anyway.
    """
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))
    (tmp_path / handlers._OWN_BRANCH_STATE_FILENAME).write_text("polecat/own-pr-ready-block-s1")

    ctx = _ctx("gh pr ready 2658", cwd="/tmp/aops-review-sim")
    with (
        patch.object(handlers, "_own_git_branch", return_value="v0.10"),
        patch.object(handlers, "_pr_head_branch", return_value="polecat/own-pr-ready-block-s1"),
    ):
        res = handlers.guard_own_pr_ready(ctx)

    assert res is not None
    assert res.kind is Kind.REFUSE
    assert "polecat/own-pr-ready-block-s1" in res.inject_text


def test_guard_still_allows_a_genuinely_different_session(monkeypatch, tmp_path):
    """No recorded branch, and cwd's branch differs from the PR: allowed."""
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))
    # This session never opened polecat/own-pr-ready-block-s1 -- nothing recorded.

    ctx = _ctx("gh pr ready 2658", cwd="/tmp/aops-review-sim")
    with (
        patch.object(handlers, "_own_git_branch", return_value="v0.10"),
        patch.object(handlers, "_pr_head_branch", return_value="polecat/own-pr-ready-block-s1"),
    ):
        res = handlers.guard_own_pr_ready(ctx)

    assert res is None
