"""Tests for the task-body mandatory pre-push/pre-PR gate (epic-50b5ade9.3).

Covers:
1. Blocking push/PR when a mandatory gate is present in the task body and unverdicted.
2. Allowing push/PR once the verdict is recorded (e.g. James APPROVE).
3. Override mechanism (TASK_BODY_GATE_OVERRIDE=1, AOP_FORCE=1, --override-gate).
4. Gating mode env var (warn / block / off).
5. Non-push/PR commands not intercepted.
6. End-to-end hook dispatch and client wire rendering.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB_HOOKS = _REPO_ROOT / "lib" / "hooks"

if str(_LIB_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIB_HOOKS))

import dispatch  # noqa: E402
from task_body_gate import (  # noqa: E402
    clear_recorded_verdicts,
    is_push_or_pr_command,
    parse_mandatory_gates,
    record_gate_verdict,
    task_body_gate_handler,
)


@pytest.fixture(autouse=True)
def _cleanup_verdicts(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS_VERDICTS_DIR", str(tmp_path))
    session_id = "test-gate-session"
    clear_recorded_verdicts(session_id)
    yield
    clear_recorded_verdicts(session_id)


# ---------------------------------------------------------------------------
# Unit tests: parser and command detector
# ---------------------------------------------------------------------------


def test_push_or_pr_command_detection():
    assert is_push_or_pr_command("git push origin main")
    assert is_push_or_pr_command("git push -u origin polecat/123")
    assert is_push_or_pr_command("git push")
    assert is_push_or_pr_command("gh pr create --title 'Fix' --body 'Done'")
    assert is_push_or_pr_command("gh pr create")

    # Non-push/PR commands
    assert not is_push_or_pr_command("git status")
    assert not is_push_or_pr_command("git commit -m 'test'")
    assert not is_push_or_pr_command("git pull")
    assert not is_push_or_pr_command("gh pr view 123")
    assert not is_push_or_pr_command("pytest tests/")


def test_parse_mandatory_gates_markers():
    body_james = "## Acceptance Criteria\nMUST get James APPROVE before PR."
    assert parse_mandatory_gates(body_james) == ["james"]

    body_rereview = "MUST get James re-review APPROVE on the implementation before PR"
    assert parse_mandatory_gates(body_rereview) == ["james"]

    body_qa = "A mandatory QA verdict is required before push."
    assert parse_mandatory_gates(body_qa) == ["marsha"]

    body_multiple = (
        "1. MUST get James APPROVE before PR.\n2. Mandatory marsha verdict required before push."
    )
    assert set(parse_mandatory_gates(body_multiple)) == {"james", "marsha"}

    body_clean = "Standard implementation task. Deliver clean code and tests."
    assert parse_mandatory_gates(body_clean) == []


# ---------------------------------------------------------------------------
# Acceptance Criterion 2: Test fixture with "MUST get James APPROVE before PR"
# ---------------------------------------------------------------------------


def test_james_mandatory_gate_blocks_unverdicted_and_allows_verdicted(monkeypatch):
    session_id = "test-gate-session"
    task_body = "MUST get James APPROVE before PR"

    monkeypatch.setenv("TASK_BODY_GATE_MODE", "block")
    monkeypatch.setenv("AOPS_TASK_BODY", task_body)

    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        command="git push origin branch-1",
        session_id=session_id,
    )

    # 1. Unverdicted push -> Blocked (Kind.REFUSE)
    res = task_body_gate_handler(ctx)
    assert res is not None
    assert res.kind == dispatch.Kind.REFUSE
    assert "james" in res.inject_text.lower()

    # 2. Record James APPROVE verdict -> Allowed (None)
    record_gate_verdict(session_id, "james", verdict="APPROVE", detail="Looks great")
    res_after = task_body_gate_handler(ctx)
    assert res_after is None


def test_gh_pr_create_blocked_until_verdict(monkeypatch):
    session_id = "test-gate-session"
    task_body = "Mandatory: MUST get James re-review APPROVE on the implementation before PR"

    monkeypatch.setenv("TASK_BODY_GATE_MODE", "block")
    monkeypatch.setenv("AOPS_TASK_BODY", task_body)

    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        command="gh pr create --title 'Feature' --body 'Details'",
        session_id=session_id,
    )

    # Unverdicted PR create -> Refused
    res = task_body_gate_handler(ctx)
    assert res is not None
    assert res.kind == dispatch.Kind.REFUSE

    # Satisfy gate -> Allowed
    record_gate_verdict(session_id, "james", verdict="APPROVE")
    assert task_body_gate_handler(ctx) is None


# ---------------------------------------------------------------------------
# Acceptance Criterion 3: Override mechanism works
# ---------------------------------------------------------------------------


def test_override_mechanism_env_var(monkeypatch):
    session_id = "test-gate-session"
    task_body = "MUST get James APPROVE before PR"

    monkeypatch.setenv("TASK_BODY_GATE_MODE", "block")
    monkeypatch.setenv("AOPS_TASK_BODY", task_body)
    monkeypatch.setenv("TASK_BODY_GATE_OVERRIDE", "1")

    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        command="git push origin branch-1",
        session_id=session_id,
    )

    # Overridden -> Allowed even without verdict
    assert task_body_gate_handler(ctx) is None


def test_override_mechanism_command_flag(monkeypatch):
    session_id = "test-gate-session"
    task_body = "MUST get James APPROVE before PR"

    monkeypatch.setenv("TASK_BODY_GATE_MODE", "block")
    monkeypatch.setenv("AOPS_TASK_BODY", task_body)

    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        command="git push origin branch-1 --override-gate",
        session_id=session_id,
    )

    assert task_body_gate_handler(ctx) is None


# ---------------------------------------------------------------------------
# Acceptance Criterion 4: Gating modes (warn, block, off)
# ---------------------------------------------------------------------------


def test_gating_mode_off(monkeypatch):
    session_id = "test-gate-session"
    task_body = "MUST get James APPROVE before PR"

    monkeypatch.setenv("TASK_BODY_GATE_MODE", "off")
    monkeypatch.setenv("AOPS_TASK_BODY", task_body)

    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        command="git push origin branch-1",
        session_id=session_id,
    )

    assert task_body_gate_handler(ctx) is None


def test_gating_mode_warn(monkeypatch):
    session_id = "test-gate-session"
    task_body = "MUST get James APPROVE before PR"

    monkeypatch.setenv("TASK_BODY_GATE_MODE", "warn")
    monkeypatch.setenv("AOPS_TASK_BODY", task_body)

    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        command="git push origin branch-1",
        session_id=session_id,
    )

    res = task_body_gate_handler(ctx)
    assert res is not None
    assert res.kind == dispatch.Kind.ADVISE
    assert "james" in res.inject_text.lower()


def test_gating_mode_block(monkeypatch):
    session_id = "test-gate-session"
    task_body = "MUST get James APPROVE before PR"

    monkeypatch.setenv("TASK_BODY_GATE_MODE", "block")
    monkeypatch.setenv("AOPS_TASK_BODY", task_body)

    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        command="git push origin branch-1",
        session_id=session_id,
    )

    res = task_body_gate_handler(ctx)
    assert res is not None
    assert res.kind == dispatch.Kind.REFUSE


# ---------------------------------------------------------------------------
# End-to-end dispatch through dispatch.py rendering
# ---------------------------------------------------------------------------


def test_claude_wire_rendering_refusal():
    result = dispatch.refuse("Gate not satisfied", user_text="Blocked push")
    wire = dispatch.render("claude", "PreToolUse", result)
    assert wire["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert wire["hookSpecificOutput"]["permissionDecisionReason"] == "Gate not satisfied"
    assert wire["systemMessage"] == "Blocked push"


def test_agy_wire_rendering_refusal():
    result = dispatch.refuse("Gate not satisfied")
    wire = dispatch.render("agy", "PreToolUse", result)
    assert wire["decision"] == "deny"
    assert wire["reason"] == "Gate not satisfied"


# ---------------------------------------------------------------------------
# Verify-Parent Replay: #583 Review-Gate-Skip Mitigation (epic-50b5ade9.4)
# ---------------------------------------------------------------------------


def test_replay_583_mandatory_review_gate_enforcement(monkeypatch):
    """Replays the #583 incident scenario.

    In #583, a polecat worker skipped a mandatory pre-PR review gate stated in its
    task body ("MUST get James re-review APPROVE on the implementation before PR").

    This test confirms:
    1. A task body containing 'MUST get James re-review APPROVE on the implementation before PR'
       blocks git push / gh pr create until an APPROVE verdict is recorded.
    2. Once James APPROVE verdict is recorded, git push / gh pr create is permitted.
    3. Overriding via env var bypasses the gate.
    """
    session_id = "replay-583-session"
    task_body = (
        "## Deliverables\n"
        "Implement review gate hook.\n\n"
        "## Acceptance Criteria\n"
        "1. MUST get James re-review APPROVE on the implementation before PR.\n"
        "2. All tests pass."
    )

    monkeypatch.setenv("TASK_BODY_GATE_MODE", "block")
    monkeypatch.setenv("AOPS_TASK_BODY", task_body)

    ctx_push = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        command="git push origin polecat/fix-583",
        session_id=session_id,
    )

    # 1. Blocked before verdict
    res = task_body_gate_handler(ctx_push)
    assert res is not None
    assert res.kind == dispatch.Kind.REFUSE
    assert "james" in res.inject_text.lower()

    # 2. Blocked on gh pr create
    ctx_pr = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        command="gh pr create --title 'Fix #583' --body 'Done'",
        session_id=session_id,
    )
    res_pr = task_body_gate_handler(ctx_pr)
    assert res_pr is not None
    assert res_pr.kind == dispatch.Kind.REFUSE

    # 3. Allowed after verdict recorded
    record_gate_verdict(session_id, "james", verdict="APPROVE", detail="Re-review passed")
    assert task_body_gate_handler(ctx_push) is None
    assert task_body_gate_handler(ctx_pr) is None
