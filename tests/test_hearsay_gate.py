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
