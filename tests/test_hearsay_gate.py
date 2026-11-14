"""Unit tests for hearsay gate tool matching and Antigravity turn-0 guard."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_ROOT = _REPO_ROOT / "plugins" / "ida"
_HOOKS_DIR = _PLUGIN_ROOT / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import dispatch
import hearsay_gate as hg
from dispatch import HookContext


def test_is_blocked_tool_matches_case_insensitively():
    """AC6: hearsay_gate._is_blocked_tool matches gated tools case-insensitively, including send_message and dump."""
    # Direct case-insensitive checks
    blocked = [
        "send_message",
        "SendMessage",
        "SEND_MESSAGE",
        "dump",
        "Dump",
        "DUMP",
        "agent",
        "Agent",
        "task",
        "Task",
        "invoke_subagent",
        "INVOKE_SUBAGENT",
        # Namespaced tool calls
        "mcp__services__send_message",
        "agy__dump",
        "custom__Agent",
    ]
    for tool_name in blocked:
        assert hg._is_blocked_tool(tool_name) is True, f"Expected {tool_name} to be blocked"

    # Non-gated tools must not be blocked
    not_blocked = ["read_file", "view_file", "grep_search", "run_command", "git_status"]
    for tool_name in not_blocked:
        assert hg._is_blocked_tool(tool_name) is False, f"Expected {tool_name} to not be blocked"


def test_gated_tools_definitions_include_send_message_and_dump():
    """AC6: _GATED_TOOLS in hearsay_gate and dispatch match case-insensitively and cover send_message and dump."""
    # Check hearsay_gate._GATED_TOOLS
    gated_hg = {t.lower() for t in hg._GATED_TOOLS}
    assert "send_message" in gated_hg
    assert "sendmessage" in gated_hg or "send_message" in gated_hg
    assert "dump" in gated_hg

    # Check dispatch._GATED_TOOLS
    assert hasattr(dispatch, "_GATED_TOOLS")
    gated_dispatch = {t.lower() for t in dispatch._GATED_TOOLS}
    assert "send_message" in gated_dispatch
    assert "dump" in gated_dispatch


def test_agy_turn_start_missing_transcript_guarded_against_file_not_found(tmp_path):
    """AC6: _agy_turn_start checks Path(path).is_file() so turn 0 does not raise FileNotFoundError."""
    missing_path = str(tmp_path / "does_not_exist.jsonl")
    ctx = HookContext(
        client="agy",
        event="UserPromptSubmit",
        session_id="turn0-test",
        raw={"invocationNum": 0, "transcriptPath": missing_path},
    )

    # Must return None without raising FileNotFoundError
    res = hg._agy_turn_start(ctx)
    assert res is None


def test_dispatch_instrument_send_message_case_insensitive():
    """AC6: dispatch._instrument_otel_events handles send_message case-insensitively."""
    mock_otel = MagicMock()
    mock_otel.resolve.return_value = {"endpoint": "mock"}
    mock_otel.detect_tool_plumbing_error.return_value = None
    mock_otel.detect_agent_idle_timeout.return_value = None

    with patch.object(dispatch, "_get_evaluator_otel_trace", return_value=mock_otel):
        # Case 1: ctx.tool = "send_message"
        ctx1 = HookContext(
            client="agy",
            event="PostToolUse",
            tool="send_message",
            session_id="s1",
        )
        dispatch._instrument_otel_events(ctx1)
        mock_otel.record_send_message.assert_called_with(ctx1, config={"endpoint": "mock"})

        mock_otel.record_send_message.reset_mock()

        # Case 2: ctx.tool_calls has tool_name = "send_message"
        ctx2 = HookContext(
            client="claude",
            event="PostToolBatch",
            session_id="s2",
            tool_calls=({"tool_name": "send_message", "tool_input": {}},),
        )
        dispatch._instrument_otel_events(ctx2)
        mock_otel.record_send_message.assert_called_with(ctx2, config={"endpoint": "mock"})


def test_evaluator_otel_trace_attributes_resolves_root_session_id(tmp_path, monkeypatch):
    """evaluator_otel_trace._attributes sets OpenInference session.id to root session and agent.id for subagents."""
    import json

    rbg_hooks = _REPO_ROOT / "plugins" / "rbg" / "hooks"
    if str(rbg_hooks) not in sys.path:
        sys.path.insert(0, str(rbg_hooks))
    import evaluator_otel_trace as eot

    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)

    root_uuid = "11111111-2222-3333-4444-555555555555"
    sub_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    state_dir = tmp_path / ".claude" / "tracer"
    state_dir.mkdir(parents=True)
    (state_dir / f"{sub_uuid}.json").write_text(
        json.dumps({"session_id": sub_uuid, "phoenix_session_id": root_uuid}),
        encoding="utf-8",
    )

    attrs = eot._attributes({"session_id": sub_uuid, "client": "agy", "event": "PostToolUse"})
    assert attrs["session.id"] == root_uuid
    assert attrs["agent.id"] == sub_uuid

    # Slash-suffixed session_id also strips suffix into agent.id
    attrs_slash = eot._attributes({"session_id": f"{root_uuid}/task-42", "client": "claude"})
    assert attrs_slash["session.id"] == root_uuid
    assert attrs_slash["agent.id"] == "task-42"


def _write_agy_transcripts(transcript_dir: Path, *entries: dict) -> Path:
    transcript_dir.mkdir(parents=True, exist_ok=True)
    compact = transcript_dir / "transcript.jsonl"
    full = transcript_dir / "transcript_full.jsonl"
    body = "".join(__import__("json").dumps(e) + "\n" for e in entries)
    compact.write_text(body, encoding="utf-8")
    full.write_text(body, encoding="utf-8")
    return compact


def _trap_transcript_reads(monkeypatch, transcript_dir: Path) -> None:
    import builtins

    real_open = builtins.open
    real_path_open = Path.open
    dir_prefix = str(transcript_dir)

    def guarded_open(file, *args, **kwargs):
        if hasattr(file, "__fspath__") or isinstance(file, str):
            if str(Path(file)).startswith(dir_prefix):
                raise AssertionError(f"Transcript file opened unexpectedly: {file}")
        return real_open(file, *args, **kwargs)

    def guarded_path_open(self, *args, **kwargs):
        if str(self).startswith(dir_prefix):
            raise AssertionError(f"Transcript file opened unexpectedly via Path.open: {self}")
        return real_path_open(self, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(Path, "open", guarded_path_open)


def test_agy_system_message_invocation_gt_0_exits_before_reading_transcripts(tmp_path, monkeypatch):
    """invocationNum >= 1 on agy SYSTEM_MESSAGE returns None/False without reading transcripts."""
    import handlers

    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate"))
    transcript_dir = tmp_path / "agy_conv"
    peer_sys_msg = (
        "[Message] timestamp=2026-11-14T00:00:00Z sender=peer-conv-uuid "
        "priority=MESSAGE_PRIORITY_HIGH content=### Check Report\n\nAll checks done."
    )
    transcript = _write_agy_transcripts(
        transcript_dir,
        {"step_index": 0, "type": "USER_INPUT", "content": "<USER_REQUEST>start</USER_REQUEST>"},
        {"step_index": 1, "type": "SYSTEM_MESSAGE", "content": peer_sys_msg},
    )

    session_id = "sess-agy-sys-guard"
    ctx_0 = HookContext(
        client="agy",
        event="UserPromptSubmit",
        session_id=session_id,
        hooks_dir=_HOOKS_DIR,
        transcript_path=str(transcript),
        raw={"invocationNum": 0, "transcriptPath": str(transcript), "conversationId": session_id},
    )
    assert hg.should_arm_hearsay(ctx_0) is True
    assert handlers.rule_against_hearsay(ctx_0) is not None
    assert hg.hearsay_arm(ctx_0) is not None
    assert hg.is_armed(session_id) is True

    # Disarm as verdict.py does, then verify subsequent model steps do not read transcripts or re-arm.
    claim_id = hg.get_state(session_id)["claim_id"]
    hg.disarm(session_id, claim_id=claim_id, verdict="PASS", reason="checked")
    assert hg.is_armed(session_id) is False

    _trap_transcript_reads(monkeypatch, transcript_dir)

    for inv in (1, 2):
        ctx_n = HookContext(
            client="agy",
            event="UserPromptSubmit",
            session_id=session_id,
            hooks_dir=_HOOKS_DIR,
            transcript_path=str(transcript),
            raw={
                "invocationNum": inv,
                "transcriptPath": str(transcript),
                "conversationId": session_id,
            },
        )
        assert hg._agy_turn_start(ctx_n) is None
        assert hg.prompt_text(ctx_n) == ""
        assert hg.is_peer_report(ctx_n) is False
        assert hg.extract_judged_content(ctx_n) is None
        assert hg.should_arm_hearsay(ctx_n) is False
        assert handlers.rule_against_hearsay(ctx_n) is None
        assert hg.hearsay_arm(ctx_n) is None
        assert hg.is_armed(session_id) is False


def test_agy_user_input_and_plan_review_invocation_gt_0_do_not_read_transcripts(
    tmp_path, monkeypatch
):
    """invocationNum >= 1 skips transcript parsing on both USER_INPUT and non-peer SYSTEM_MESSAGE turns."""
    import handlers

    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate"))

    # 1. USER_INPUT carrying a peer envelope
    user_dir = tmp_path / "user_conv"
    user_transcript = _write_agy_transcripts(
        user_dir,
        {
            "step_index": 0,
            "type": "USER_INPUT",
            "content": '<USER_REQUEST><cross-session-message from="peer">done</cross-session-message></USER_REQUEST>',
        },
    )
    _trap_transcript_reads(monkeypatch, user_dir)
    ctx_user_1 = HookContext(
        client="agy",
        event="UserPromptSubmit",
        session_id="sess-agy-user-1",
        hooks_dir=_HOOKS_DIR,
        transcript_path=str(user_transcript),
        raw={"invocationNum": 1, "transcriptPath": str(user_transcript)},
    )
    assert hg._agy_turn_start(ctx_user_1) is None
    assert hg.should_arm_hearsay(ctx_user_1) is False
    assert handlers.rule_against_hearsay(ctx_user_1) is None
    assert hg.hearsay_arm(ctx_user_1) is None
    assert hg.is_armed("sess-agy-user-1") is False

    # 2. [plan review] / system wake SYSTEM_MESSAGE
    wake_dir = tmp_path / "wake_conv"
    wake_transcript = _write_agy_transcripts(
        wake_dir,
        {
            "step_index": 0,
            "type": "SYSTEM_MESSAGE",
            "content": "[plan review] Review requested by harness.",
        },
    )
    _trap_transcript_reads(monkeypatch, wake_dir)
    ctx_wake_1 = HookContext(
        client="agy",
        event="UserPromptSubmit",
        session_id="sess-agy-wake-1",
        hooks_dir=_HOOKS_DIR,
        transcript_path=str(wake_transcript),
        raw={"invocationNum": 1, "transcriptPath": str(wake_transcript)},
    )
    assert hg._agy_turn_start(ctx_wake_1) is None
    assert hg.hearsay_arm(ctx_wake_1) is None
    assert handlers.rule_against_hearsay(ctx_wake_1) is None


def test_dispatch_agy_preinvocation_system_message_arms_once_then_ignores_later_invocations(
    tmp_path, monkeypatch
):
    """End-to-end dispatch.py agy PreInvocation arms on invocationNum=0 and stays disarmed at invocationNum=1."""
    import json
    import os
    import subprocess

    gate_dir = tmp_path / "gate"
    ptr_dir = tmp_path / "ptr"
    tracer_dir = tmp_path / "tracer"
    transcript = _write_agy_transcripts(
        tmp_path / "conv",
        {
            "step_index": 0,
            "type": "SYSTEM_MESSAGE",
            "content": (
                "[Message] timestamp=2026-11-14T00:00:00Z sender=peer-uuid-1 "
                "priority=MESSAGE_PRIORITY_HIGH content=### Subagent Report\n\nWork finished."
            ),
        },
    )

    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("OTEL_", "GENAI_", "BETA_TRACING_")) and k != "PKB_MCP_URL"
    }
    env.update(
        {
            "HOME": str(tmp_path),
            "AOPS_PREMISE_GATE_DIR": str(gate_dir),
            "AOPS_SESSION_POINTER_DIR": str(ptr_dir),
            "AOPS_TRACER_STATE_DIR": str(tracer_dir),
        }
    )

    session_id = "sess-dispatch-agy-sys"
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(gate_dir))

    def run_preinvocation(inv_num: int) -> subprocess.CompletedProcess[str]:
        payload = {
            "conversationId": session_id,
            "invocationNum": inv_num,
            "transcriptPath": str(transcript),
            "workspacePaths": [str(tmp_path)],
        }
        return subprocess.run(
            [sys.executable, str(_HOOKS_DIR / "dispatch.py"), "agy", "PreInvocation"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=15,
            env=env,
            cwd=str(tmp_path),
        )

    res0 = run_preinvocation(0)
    assert res0.returncode == 0
    out0 = json.loads(res0.stdout)
    expected_hearsay, _ = dispatch.load_message_pair(_HOOKS_DIR, "hearsay")
    assert any(
        expected_hearsay in step.get("ephemeralMessage", "") for step in out0.get("injectSteps", [])
    )
    assert hg.is_armed(session_id) is True

    claim_id = hg.get_state(session_id)["claim_id"]
    hg.disarm(session_id, claim_id=claim_id, verdict="REVISE", reason="no block")
    assert hg.is_armed(session_id) is False

    res1 = run_preinvocation(1)
    assert res1.returncode == 0
    assert res1.stdout.strip() == ""
    assert hg.is_armed(session_id) is False
