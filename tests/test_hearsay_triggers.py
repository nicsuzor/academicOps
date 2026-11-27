"""Tests for refactored hearsay triggers, naming, and trigger predicate alignment."""

from __future__ import annotations

import json
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


@pytest.fixture(autouse=True)
def _isolate_gate_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate"))


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

    ctx_batch = HookContext(
        client="claude",
        event="PostToolBatch",
        agent_type=agent,
        session_id=f"s-fg-batch-{agent}",
        hooks_dir=IDA_HOOKS,
        tool_calls=(
            {
                "tool_name": "Agent",
                "tool_use_id": "call-1",
                "tool_input": {"description": "fg subagent 1"},
                "tool_response": {
                    "status": "completed",
                    "content": [{"type": "text", "text": "result 1"}],
                },
            },
            {
                "tool_name": "Agent",
                "tool_use_id": "call-2",
                "tool_input": {"description": "fg subagent 2"},
                "tool_response": {
                    "status": "completed",
                    "content": [{"type": "text", "text": "result 2"}],
                },
            },
        ),
    )
    res_batch = handlers.post_tool_batch(ctx_batch)
    assert res_batch is not None, (
        f"hearsay should fire once on PostToolBatch fg completion for agent {agent}"
    )
    assert res_batch.kind is Kind.ADVISE


def test_shared_trigger_predicate_prevents_reminder_and_arming_drift():
    """AC2 & AC3: Shared trigger predicate aligns hearsay.md and gate arming on incoming reports."""
    import hearsay_gate  # type: ignore[import-not-found]

    # 1. Valid peer report -> predicate True, hearsay reminder and arming fire; honesty does not fire on receipt
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
    assert handlers.honest_output(ctx_valid) is None
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
    assert handlers.honest_output(ctx_notif) is None
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
    assert handlers.honest_output(ctx_ptr) is None
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
    assert handlers.honest_output(ctx_null) is None
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
    assert handlers.honest_output(ctx_user) is None
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


def test_honesty_fires_on_subagent_start_and_not_on_receiving_events():
    """Honesty (writing the report) fires on SubagentStart; receiving events only fire hearsay."""
    # 1. SubagentStart delivers honesty.md via warn (Kind.ADVISE)
    ctx_start = HookContext(
        client="claude",
        event="SubagentStart",
        agent_id="sub-alpha",
        agent_type="worker",
        session_id="s-sub-alpha",
        hooks_dir=IDA_HOOKS,
        raw={"agent_id": "sub-alpha"},
    )
    res_start = handlers.subagent_start(ctx_start)
    assert res_start is not None
    assert res_start.kind is Kind.ADVISE

    # 2. UserPromptSubmit does NOT deliver honesty.md
    ctx_init = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_id="sub-beta",
        agent_type="worker",
        session_id="s-sub-beta",
        hooks_dir=IDA_HOOKS,
        raw={"agent_id": "sub-beta", "prompt": "Implement AC1"},
    )
    assert handlers.honest_output(ctx_init) is None


def test_post_tool_hearsay_arm_handles_null_form_and_prose_reports_uniformly(tmp_path, monkeypatch):
    """PostToolUse auto-disarms null-form notices (fenced or standalone [no claim]) and arms prose reports uniformly."""
    import hearsay_gate
    import premise_check_gate as pcg

    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate"))

    # 1. PostToolUse with fenced null form clears gate with no-claim, should_arm_hearsay returns False
    session_null = "s-post-null"
    pcg.clear_state(session_null)
    ctx_post_null = HookContext(
        client="claude",
        event="PostToolUse",
        tool="Agent",
        agent_type="worker",
        session_id=session_null,
        hooks_dir=IDA_HOOKS,
        raw={
            "tool_input": {"prompt": "do work"},
            "tool_response": {
                "status": "completed",
                "content": [
                    {
                        "type": "text",
                        "text": "```argdown\n===\nasks: none\n===\n[no claim]\n```",
                    }
                ],
            },
        },
    )
    assert hearsay_gate.should_arm_hearsay(ctx_post_null) is False
    res_null = handlers.hearsay_arm(ctx_post_null)
    assert res_null is None
    assert pcg.is_armed(session_null) is False
    st_null = pcg.get_state(session_null)
    assert st_null.get("last_verdict", {}).get("verdict") == "no-claim"

    # 2. PostToolUse with standalone [no claim] body also auto-disarms
    session_bare_null = "s-post-bare-null"
    pcg.clear_state(session_bare_null)
    ctx_post_bare_null = HookContext(
        client="claude",
        event="PostToolUse",
        tool="Agent",
        agent_type="worker",
        session_id=session_bare_null,
        hooks_dir=IDA_HOOKS,
        raw={
            "tool_input": {"prompt": "ping"},
            "tool_response": {
                "status": "completed",
                "content": [{"type": "text", "text": "[no claim]"}],
            },
        },
    )
    assert hearsay_gate.should_arm_hearsay(ctx_post_bare_null) is False
    assert handlers.hearsay_arm(ctx_post_bare_null) is None
    assert pcg.is_armed(session_bare_null) is False

    # 3. PostToolUse with natural-language prose report (no fenced block) arms uniformly
    session_prose = "s-post-prose"
    pcg.clear_state(session_prose)
    ctx_post_prose = HookContext(
        client="claude",
        event="PostToolUse",
        tool="Agent",
        agent_type="worker",
        session_id=session_prose,
        hooks_dir=IDA_HOOKS,
        raw={
            "tool_input": {"prompt": "do work"},
            "tool_response": {
                "status": "completed",
                "content": [
                    {
                        "type": "text",
                        "text": "Completed task and verified output directly from test run.",
                    }
                ],
            },
        },
    )
    assert hearsay_gate.should_arm_hearsay(ctx_post_prose) is True
    res_prose = handlers.hearsay_arm(ctx_post_prose)
    assert res_prose is not None
    assert "--verdict <PASS|REVISE|FAIL>" in res_prose.inject_text
    assert "no argument block supplied" not in res_prose.inject_text
    assert pcg.is_armed(session_prose) is True


def test_agy_system_message_triggers_only_on_invocation_zero(tmp_path, monkeypatch):
    """agy SYSTEM_MESSAGE peer report triggers should_arm_hearsay/rule_against_hearsay/hearsay_arm only at invocationNum=0."""
    import hearsay_gate
    import premise_check_gate as pcg

    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate"))
    session_id = "s-agy-trigger-inv"
    pcg.clear_state(session_id)

    transcript = tmp_path / "transcript.jsonl"
    sys_msg = (
        "[Message] timestamp=2026-11-14T00:00:00Z sender=peer-agent-1 "
        "priority=MESSAGE_PRIORITY_HIGH content=### Check Report\n\nTask complete."
    )
    transcript.write_text(
        json.dumps({"step_index": 0, "type": "SYSTEM_MESSAGE", "content": sys_msg}) + "\n",
        encoding="utf-8",
    )

    ctx_0 = HookContext(
        client="agy",
        event="UserPromptSubmit",
        agent_type="ida:ida",
        session_id=session_id,
        hooks_dir=IDA_HOOKS,
        transcript_path=str(transcript),
        raw={"invocationNum": 0, "transcriptPath": str(transcript), "conversationId": session_id},
    )
    assert hearsay_gate.should_arm_hearsay(ctx_0) is True
    assert handlers.rule_against_hearsay(ctx_0) is not None
    assert handlers.hearsay_arm(ctx_0) is not None
    assert pcg.is_armed(session_id) is True

    pcg.disarm(
        session_id, claim_id=pcg.get_state(session_id)["claim_id"], verdict="PASS", reason="ok"
    )
    assert pcg.is_armed(session_id) is False

    ctx_1 = HookContext(
        client="agy",
        event="UserPromptSubmit",
        agent_type="ida:ida",
        session_id=session_id,
        hooks_dir=IDA_HOOKS,
        transcript_path=str(transcript),
        raw={"invocationNum": 1, "transcriptPath": str(transcript), "conversationId": session_id},
    )
    assert hearsay_gate.should_arm_hearsay(ctx_1) is False
    assert handlers.rule_against_hearsay(ctx_1) is None
    assert handlers.hearsay_arm(ctx_1) is None
    assert pcg.is_armed(session_id) is False


def _claims_from_result(result) -> list[str]:
    import shlex

    claims: list[str] = []
    for line in result.inject_text.splitlines()[1:]:
        tokens = shlex.split(line)
        if "--claim" in tokens:
            claims.append(tokens[tokens.index("--claim") + 1])
    return claims


def test_waiting_task_notification_suppresses_should_arm_and_hearsay_reminder():
    """Waiting <task-notification> never triggers should_arm_hearsay, rule_against_hearsay, or hearsay_arm."""
    import hearsay_gate

    ctx_wait = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="ida:ida",
        session_id="s-trigger-wait",
        hooks_dir=IDA_HOOKS,
        raw={
            "prompt": (
                "<task-notification>\n<task-id>a-wait</task-id>\n<status>running</status>\n"
                "<result>This agent has not reported yet: it is waiting on its own background work "
                "and will deliver its report through SubagentHandback when that finishes.</result>\n"
                "</task-notification>"
            )
        },
    )
    assert hearsay_gate.should_arm_hearsay(ctx_wait) is False
    assert handlers.rule_against_hearsay(ctx_wait) is None
    assert handlers.hearsay_arm(ctx_wait) is None


def test_active_unnotified_handback_triggers_should_arm_hearsay_once():
    """Unnotified SubagentHandback allows UserPromptSubmit notice once, then suppresses duplicates."""
    import hearsay_gate

    session_id = "s-trigger-active-hb"
    child_id = "child-active-trigger"
    report = (
        "```argdown\n===\nasks:\n  t1: check\nanswers:\n  t1: 2\n===\n"
        "(1) Obs `a:1`\n-- Rule --\n(2) Done.\n```"
    )
    handlers.post_tool(
        HookContext(
            client="claude",
            event="PostToolUse",
            tool="Agent",
            agent_type="ida:ida",
            session_id=session_id,
            hooks_dir=IDA_HOOKS,
            raw={
                "tool_use_id": "tu_spawn",
                "tool_input": {"description": "Check"},
                "tool_response": {"isAsync": True, "status": "async_launched", "agentId": child_id},
            },
        )
    )
    handlers.post_tool(
        HookContext(
            client="claude",
            event="PostToolUse",
            tool="SubagentHandback",
            agent_id=child_id,
            agent_type="worker",
            session_id=session_id,
            hooks_dir=IDA_HOOKS,
            raw={
                "agent_id": child_id,
                "tool_use_id": "tu_hb",
                "tool_input": {"message": report},
                "tool_response": {"success": True},
            },
        )
    )
    wrapped = (
        f'<agent-message from="{child_id}">\n'
        "[Subagent hand-back] The report follows:\n"
        + "\n".join(f"  {line}" for line in report.splitlines())
        + "\n</agent-message>"
    )
    ctx_ups = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="ida:ida",
        session_id=session_id,
        hooks_dir=IDA_HOOKS,
        raw={"prompt": wrapped},
    )
    assert hearsay_gate.should_arm_hearsay(ctx_ups) is True
    notice = handlers.hearsay_arm(ctx_ups)
    assert notice is not None and len(_claims_from_result(notice)) == 1
    assert hearsay_gate.should_arm_hearsay(ctx_ups) is False
    assert handlers.rule_against_hearsay(ctx_ups) is None


def test_post_verdict_delayed_agent_message_suppresses_should_arm_and_hearsay_reminder():
    """Judging a delivered foreground return suppresses a delayed <agent-message> twin, while unseen async SubagentHandback never pre-arms Root."""
    import hearsay_gate
    import premise_check_gate as pcg
    import premise_check_verdict as pcv

    session_id = "s-trigger-post-verdict"
    child_id = "child-verdict-trigger"
    report = (
        "```argdown\n===\nasks:\n  t1: check\nanswers:\n  t1: 2\n===\n"
        "(1) Obs `a:1`\n-- Rule --\n(2) Done.\n```"
    )
    handlers.post_tool(
        HookContext(
            client="claude",
            event="PostToolUse",
            tool="Agent",
            agent_type="ida:ida",
            session_id=session_id,
            hooks_dir=IDA_HOOKS,
            raw={
                "tool_use_id": "tu_spawn2",
                "tool_input": {"description": "Check"},
                "tool_response": {"isAsync": True, "status": "async_launched", "agentId": child_id},
            },
        )
    )
    handlers.post_tool(
        HookContext(
            client="claude",
            event="PostToolUse",
            tool="SubagentHandback",
            agent_id=child_id,
            agent_type="worker",
            session_id=session_id,
            hooks_dir=IDA_HOOKS,
            raw={
                "agent_id": child_id,
                "tool_use_id": "tu_hb2",
                "tool_input": {"message": report},
                "tool_response": {"success": True},
            },
        )
    )
    # Before delivery to Root, SendMessage must remain unblocked
    assert (
        handlers.pre_tool(
            HookContext(
                client="claude",
                event="PreToolUse",
                tool="SendMessage",
                agent_type="ida:ida",
                session_id=session_id,
                hooks_dir=IDA_HOOKS,
            )
        )
        is None
    )

    # Foreground metadata-only completion delivers buffered handback to Root
    fg_notice = handlers.post_tool(
        HookContext(
            client="claude",
            event="PostToolUse",
            tool="Agent",
            agent_type="ida:ida",
            session_id=session_id,
            hooks_dir=IDA_HOOKS,
            raw={
                "tool_use_id": "tu_fg2",
                "tool_input": {"description": "Check"},
                "tool_response": {"status": "completed", "agentId": child_id},
            },
        )
    )
    assert fg_notice is not None
    cid = _claims_from_result(fg_notice)[0]

    class _Tracer:
        def discover_config(self):
            return {"endpoint": "http://x"}

        def _new_trace_id(self):
            return "1" * 32

        def _new_span_id(self):
            return "2" * 16

        def _load_state(self, _session_id):
            return {}

        def _truncate(self, value: str, *_a, **_kw) -> str:
            return value

        def _build_tool_span_record(self, **kwargs):
            return {"attributes": {}}

        def _build_and_export_spans(self, **_kwargs):
            return True

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=cid,
        verdict="PASS",
        reason=f"Formal PASS {cid}: direct observation warrants conclusion.",
        tracer_mod=_Tracer(),
    )
    assert res["ok"] is True

    wrapped = (
        f'<agent-message from="{child_id}">\n'
        "[Subagent hand-back] The report follows:\n"
        + "\n".join(f"  {line}" for line in report.splitlines())
        + "\n</agent-message>"
    )
    ctx_ups = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="ida:ida",
        session_id=session_id,
        hooks_dir=IDA_HOOKS,
        raw={"prompt": wrapped},
    )
    assert hearsay_gate.should_arm_hearsay(ctx_ups) is False
    assert handlers.rule_against_hearsay(ctx_ups) is None
    assert handlers.hearsay_arm(ctx_ups) is None
    assert pcg.is_armed(session_id) is False
