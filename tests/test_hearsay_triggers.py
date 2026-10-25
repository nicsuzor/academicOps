"""Tests for refactored hearsay triggers, naming, and trigger predicate alignment."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"

if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import handlers  # type: ignore[import-not-found]
from dispatch import HookContext, Kind  # type: ignore[import-not-found]

_PEER_REPORT_VALID = (
    '<cross-session-message from="twin-a">\n'
    "Check complete.\n"
    "```argdown\n"
    "=== \n"
    "asks: [aops_1234]\n"
    "=== \n"
    '(1) [P1]: data verified {basis: "observed", pointer: "file.txt:10"}\n'
    "-- w --\n"
    "(2) [C1]: conclusion\n"
    "```\n"
    "</cross-session-message>"
)

_NULL_FORM_MSG = (
    '<cross-session-message from="twin-a">\n'
    "Status ping.\n"
    "```argdown\n"
    "===\n"
    "asks: none\n"
    "===\n\n"
    "[no claim]\n"
    "```\n"
    "</cross-session-message>"
)

_NOTIFICATION_NO_REPORT = (
    "<task-notification>\n"
    "<task-id>b0000001</task-id>\n"
    "<tool-use-id>toolu_bg_command</tool-use-id>\n"
    "<output-file>/tmp/tasks/b0000001.output</output-file>\n"
    "<status>completed</status>\n"
    '<summary>Background command "Run the tests" completed (exit code 0)</summary>\n'
    "</task-notification>"
)

_HANDBACK_POINTER_MSG = (
    "<task-notification>\n"
    "<task-id>a1b2c3d4e5f600112</task-id>\n"
    "<status>completed</status>\n"
    '<summary>Agent "Check the claim" finished</summary>\n'
    "<result>This agent's report was delivered to you as a message from "
    '"a1b2c3d4e5f600112" (its SubagentHandback call). Read it there; it is not repeated here.\n'
    "</result>\n"
    "</task-notification>"
)


def test_hearsay_gate_module_and_naming_compatibility():
    """Hearsay gate module exists and exposes hearsay_arm / hearsay_handler with backward compatibility."""
    import hearsay_gate  # type: ignore[import-not-found]

    assert hasattr(hearsay_gate, "hearsay_arm")
    assert hasattr(hearsay_gate, "hearsay_handler")
    assert hasattr(hearsay_gate, "should_arm_hearsay")
    assert hasattr(handlers, "hearsay_arm")
    assert hasattr(handlers, "hearsay_handler")

    # Backward compatibility aliases
    assert handlers.premise_check_arm is handlers.hearsay_arm
    assert handlers.premise_check_handler is handlers.hearsay_handler
    assert hearsay_gate.premise_check_arm is hearsay_gate.hearsay_arm
    assert hearsay_gate.premise_check_handler is hearsay_gate.hearsay_handler


@pytest.mark.parametrize(
    "agent",
    ["ida:ida", "ida:sara", "aops:james", "james", "worker", "pauli", "rbg", "marsha"],
)
def test_hearsay_fires_uniformly_across_all_agents(agent: str):
    """AC4: Hooks fire on all agents whenever event conditions match, without persona distinction."""
    ctx_prompt = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type=agent,
        session_id=f"s-peer-{agent}",
        hooks_dir=IDA_HOOKS,
        raw={"prompt": _PEER_REPORT_VALID},
    )
    res_prompt = handlers.rule_against_hearsay(ctx_prompt)
    assert res_prompt is not None, f"hearsay should fire on peer report for agent {agent}"
    assert res_prompt.kind is Kind.ADVISE

    ctx_post = HookContext(
        client="claude",
        event="PostToolUse",
        tool="Agent",
        agent_type=agent,
        session_id=f"s-fg-{agent}",
        hooks_dir=IDA_HOOKS,
        raw={
            "tool_input": {"description": "fg subagent"},
            "tool_response": {
                "status": "completed",
                "content": [{"type": "text", "text": "result"}],
            },
        },
    )
    res_post = handlers.rule_against_hearsay(ctx_post)
    assert res_post is not None, f"hearsay should fire on fg subagent completion for agent {agent}"
    assert res_post.kind is Kind.ADVISE


def test_shared_trigger_predicate_prevents_reminder_and_arming_drift():
    """AC2 & AC3: Shared trigger predicate aligns hearsay.md, honesty.md, and gate arming."""
    import hearsay_gate  # type: ignore[import-not-found]

    # 1. Valid peer report -> predicate True, all reminders and arming fire
    ctx_valid = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="worker",
        session_id="s-drift-valid",
        hooks_dir=IDA_HOOKS,
        raw={"prompt": _PEER_REPORT_VALID},
    )
    assert hearsay_gate.should_arm_hearsay(ctx_valid) is True
    assert handlers.rule_against_hearsay(ctx_valid) is not None
    assert handlers.honesty_on_peer_message(ctx_valid) is not None
    assert handlers.hearsay_arm(ctx_valid) is not None

    # 2. Mere notification without report -> predicate False, none fire
    ctx_notif = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="worker",
        session_id="s-drift-notif",
        hooks_dir=IDA_HOOKS,
        raw={"prompt": _NOTIFICATION_NO_REPORT},
    )
    assert hearsay_gate.should_arm_hearsay(ctx_notif) is False
    assert handlers.rule_against_hearsay(ctx_notif) is None
    assert handlers.honesty_on_peer_message(ctx_notif) is None
    assert handlers.hearsay_arm(ctx_notif) is None

    # 3. Handback pointer -> predicate False, none fire
    ctx_ptr = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="worker",
        session_id="s-drift-ptr",
        hooks_dir=IDA_HOOKS,
        raw={"prompt": _HANDBACK_POINTER_MSG},
    )
    assert hearsay_gate.should_arm_hearsay(ctx_ptr) is False
    assert handlers.rule_against_hearsay(ctx_ptr) is None
    assert handlers.honesty_on_peer_message(ctx_ptr) is None
    assert handlers.hearsay_arm(ctx_ptr) is None

    # 4. Null form argument -> predicate False, reminders suppressed and gate not armed
    ctx_null = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="worker",
        session_id="s-drift-null",
        hooks_dir=IDA_HOOKS,
        raw={"prompt": _NULL_FORM_MSG},
    )
    assert hearsay_gate.should_arm_hearsay(ctx_null) is False
    assert handlers.rule_against_hearsay(ctx_null) is None
    assert handlers.honesty_on_peer_message(ctx_null) is None
    assert handlers.hearsay_arm(ctx_null) is None

    # 5. User prompt -> predicate False, none fire
    ctx_user = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="worker",
        session_id="s-drift-user",
        hooks_dir=IDA_HOOKS,
        raw={"prompt": "run tests"},
    )
    assert hearsay_gate.should_arm_hearsay(ctx_user) is False
    assert handlers.rule_against_hearsay(ctx_user) is None
    assert handlers.honesty_on_peer_message(ctx_user) is None
    assert handlers.hearsay_arm(ctx_user) is None


def test_suppressed_premature_reminders_on_subagent_dispatch():
    """AC6: Eliminate premature reminders when gates are not yet armed."""
    import hearsay_gate  # type: ignore[import-not-found]

    # PreToolUse dispatching subagent
    ctx_pre_dispatch = HookContext(
        client="claude",
        event="PreToolUse",
        tool="Agent",
        agent_type="ida:ida",
        session_id="s-pre-dispatch",
        hooks_dir=IDA_HOOKS,
        raw={"tool_input": {"prompt": "research topic"}},
    )
    assert hearsay_gate.should_arm_hearsay(ctx_pre_dispatch) is False
    assert handlers.rule_against_hearsay(ctx_pre_dispatch) is None
    # PreToolUse handler does not inject reminder text when disarmed
    assert handlers.pre_tool(ctx_pre_dispatch) is None

    # PostToolUse with background subagent launch
    ctx_post_bg = HookContext(
        client="claude",
        event="PostToolUse",
        tool="Agent",
        agent_type="ida:ida",
        session_id="s-post-bg",
        hooks_dir=IDA_HOOKS,
        raw={
            "tool_input": {"prompt": "research topic", "run_in_background": True},
            "tool_response": {"isAsync": True, "status": "async_launched", "agentId": "bg-1"},
        },
    )
    assert hearsay_gate.should_arm_hearsay(ctx_post_bg) is False
    assert handlers.rule_against_hearsay(ctx_post_bg) is None
    assert handlers.hearsay_arm(ctx_post_bg) is None


def test_hearsay_arm_emits_otel_trace_on_incoming_message(tmp_path, monkeypatch):
    """AC5: Incoming messages arm hearsay checking and emit OTel trace without task file mutation."""
    import hearsay_gate  # type: ignore[import-not-found]
    import premise_check_gate as pcg

    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate"))
    session_id = "s-otel-trace-test"
    pcg.clear_state(session_id)

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="worker",
        session_id=session_id,
        hooks_dir=IDA_HOOKS,
        raw={"prompt": _PEER_REPORT_VALID},
    )

    fake_tracer = MagicMock()
    fake_config = {"endpoint": "http://collector.invalid:4318", "project_name": "test"}
    fake_tracer.discover_config.return_value = fake_config

    with (
        patch.object(hearsay_gate, "claude_code_tracer", fake_tracer, create=True),
        patch.object(hearsay_gate, "emit_hearsay_span") as mock_emit,
    ):
        res = handlers.hearsay_arm(ctx)
        assert res is not None
        assert pcg.is_armed(session_id) is True
        mock_emit.assert_called_once()
