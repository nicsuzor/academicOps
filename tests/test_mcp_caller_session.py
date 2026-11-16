"""Tests for PreToolUse hook injecting caller ``session_id`` into PKB MCP calls."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
HOOK_SCRIPT = IDA_HOOKS / "mcp_caller_session.py"
if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

_POLICY = tomllib.loads((REPO_ROOT / "tests" / "policy.toml").read_text(encoding="utf-8"))
SESSION_SERVERS = frozenset(_POLICY["hooks"]["mcp_caller_session"]["session_servers"])


def _clean_env(**extra: str) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "CLAUDE_CODE_SESSION_ID",
            "CLAUDE_SESSION_ID",
            "ANTIGRAVITY_CONVERSATION_ID",
        }
    }
    env.update(extra)
    return env


def test_claude_direct_pkb_injects_top_level_session_id():
    """Claude direct PKB tool receives top-level session_id and preserves original args."""
    from mcp_caller_session import inject_caller_session

    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__pkb__get_task",
        "session_id": "sess-uuid-main",
        "prompt_id": "prompt-uuid-main",
        "tool_use_id": "toolu-01",
        "tool_input": {"id": "task-fixture-01"},
    }

    result = inject_caller_session(payload, session_servers=SESSION_SERVERS, environ={})
    specific = result["hookSpecificOutput"]
    assert specific.get("hookEventName") == "PreToolUse"
    assert "permissionDecision" not in specific

    updated = specific["updatedInput"]
    assert updated["id"] == "task-fixture-01"
    assert updated["session_id"] == "sess-uuid-main"
    assert "_session" not in updated


def test_claude_env_vars_take_precedence_over_stdin():
    """CLAUDE_CODE_SESSION_ID > CLAUDE_SESSION_ID > stdin session_id."""
    from mcp_caller_session import inject_caller_session

    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__pkb__search",
        "session_id": "stdin-sess",
        "tool_input": {"query": "test"},
    }

    res_primary = inject_caller_session(
        payload,
        session_servers=SESSION_SERVERS,
        environ={
            "CLAUDE_CODE_SESSION_ID": "env-cc-sess",
            "CLAUDE_SESSION_ID": "env-c-sess",
        },
    )
    assert res_primary["hookSpecificOutput"]["updatedInput"]["session_id"] == "env-cc-sess"

    res_fallback = inject_caller_session(
        payload,
        session_servers=SESSION_SERVERS,
        environ={"CLAUDE_SESSION_ID": "env-c-sess"},
    )
    assert res_fallback["hookSpecificOutput"]["updatedInput"]["session_id"] == "env-c-sess"


def test_claude_skips_portal_codemode_and_portal_tools():
    """portal_codemode_execute and portal_* tools must NOT receive top-level session_id."""
    from mcp_caller_session import inject_caller_session

    for tool_name in (
        "mcp__services__portal_codemode_execute",
        "mcp__services__portal_list_servers",
        "mcp__plugin_aops_services__portal_codemode_execute",
        "mcp__aops:services__portal_codemode_execute",
        "portal_codemode_execute",
    ):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "session_id": "sess-uuid-parent",
            "tool_input": {"code": "return await codemode.pkb_get_task({ id: 'x' });"},
        }
        result = inject_caller_session(payload, session_servers=SESSION_SERVERS, environ={})
        assert result == {}, f"Expected no modification for {tool_name}, got {result}"


def test_claude_call_mcp_tool_injects_into_arguments_only_for_pkb():
    """call_mcp_tool targeting ServerName == 'pkb' injects session_id into Arguments."""
    from mcp_caller_session import inject_caller_session

    pkb_payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__services__call_mcp_tool",
        "session_id": "sess-call-tool",
        "tool_input": {
            "ServerName": "pkb",
            "ToolName": "search",
            "Arguments": {"query": "hello", "limit": 5},
        },
    }
    result = inject_caller_session(pkb_payload, session_servers=SESSION_SERVERS, environ={})
    updated = result["hookSpecificOutput"]["updatedInput"]
    assert "session_id" not in updated
    assert "_session" not in updated
    assert updated["Arguments"] == {"query": "hello", "limit": 5, "session_id": "sess-call-tool"}

    other_payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__services__call_mcp_tool",
        "session_id": "sess-call-tool",
        "tool_input": {
            "ServerName": "telegram",
            "ToolName": "reply",
            "Arguments": {"text": "hi"},
        },
    }
    assert inject_caller_session(other_payload, session_servers=SESSION_SERVERS, environ={}) == {}


def test_agy_direct_pkb_and_call_mcp_tool_overwrite():
    """AGY emits overwrite only when missing/different, using ANTIGRAVITY_CONVERSATION_ID first."""
    from mcp_caller_session import inject_caller_session

    # Missing session_id on mcp_pkb_search, env overrides stdin conversationId
    agy_direct = {
        "toolCall": {"name": "mcp_pkb_search", "args": {"query": "observability"}},
        "conversationId": "conv-stdin",
    }
    res_env = inject_caller_session(
        agy_direct,
        session_servers=SESSION_SERVERS,
        client="agy",
        environ={"ANTIGRAVITY_CONVERSATION_ID": "conv-env"},
    )
    assert res_env == {"overwrite": {"session_id": "conv-env"}}

    # Fallback to stdin conversationId when env var absent
    res_stdin = inject_caller_session(
        agy_direct, session_servers=SESSION_SERVERS, client="agy", environ={}
    )
    assert res_stdin == {"overwrite": {"session_id": "conv-stdin"}}

    # Already matching -> no-op
    agy_already = {
        "toolCall": {
            "name": "mcp__pkb__get_task",
            "args": {"id": "t1", "session_id": "conv-env"},
        },
        "conversationId": "conv-stdin",
    }
    assert (
        inject_caller_session(
            agy_already,
            session_servers=SESSION_SERVERS,
            client="agy",
            environ={"ANTIGRAVITY_CONVERSATION_ID": "conv-env"},
        )
        == {}
    )

    # Different session_id -> overwrite
    agy_wrong = {
        "toolCall": {
            "name": "mcp_pkb_get_task",
            "args": {"id": "t1", "session_id": "wrong-id"},
        },
    }
    assert inject_caller_session(
        agy_wrong,
        session_servers=SESSION_SERVERS,
        client="agy",
        environ={"ANTIGRAVITY_CONVERSATION_ID": "conv-env"},
    ) == {"overwrite": {"session_id": "conv-env"}}

    # call_mcp_tool targeting pkb -> overwrite Arguments preserving existing keys
    agy_call_mcp = {
        "toolCall": {
            "name": "call_mcp_tool",
            "args": {
                "ServerName": "pkb",
                "ToolName": "pkb_search",
                "Arguments": {"query": "spec", "limit": 3},
            },
        },
        "conversationId": "conv-call",
    }
    assert inject_caller_session(
        agy_call_mcp, session_servers=SESSION_SERVERS, client="agy", environ={}
    ) == {"overwrite": {"Arguments": {"query": "spec", "limit": 3, "session_id": "conv-call"}}}

    # call_mcp_tool with matching session_id in Arguments -> no-op
    agy_call_mcp_same = {
        "toolCall": {
            "name": "call_mcp_tool",
            "args": {
                "ServerName": "pkb",
                "ToolName": "pkb_search",
                "Arguments": {"query": "spec", "session_id": "conv-call"},
            },
        },
        "conversationId": "conv-call",
    }
    assert (
        inject_caller_session(
            agy_call_mcp_same, session_servers=SESSION_SERVERS, client="agy", environ={}
        )
        == {}
    )


@pytest.mark.integration
def test_hook_subprocess_execution():
    """End-to-end execution for Claude and AGY subprocess invocations."""
    claude_payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__pkb__search",
        "session_id": "sess-e2e",
        "tool_use_id": "toolu-03",
        "tool_input": {"query": "observability"},
    }
    proc = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(claude_payload),
        text=True,
        capture_output=True,
        env=_clean_env(),
    )
    assert proc.returncode == 0, f"Hook failed with stderr: {proc.stderr}"
    updated = json.loads(proc.stdout)["hookSpecificOutput"]["updatedInput"]
    assert updated["query"] == "observability"
    assert updated["session_id"] == "sess-e2e"
    assert "_session" not in updated

    agy_payload = {
        "toolCall": {"name": "mcp_pkb_search", "args": {"query": "observability"}},
        "conversationId": "conv-e2e",
    }
    agy_proc = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT), "agy"],
        input=json.dumps(agy_payload),
        text=True,
        capture_output=True,
        env=_clean_env(ANTIGRAVITY_CONVERSATION_ID="conv-env-e2e"),
    )
    assert agy_proc.returncode == 0, f"AGY hook failed with stderr: {agy_proc.stderr}"
    assert json.loads(agy_proc.stdout) == {"overwrite": {"session_id": "conv-env-e2e"}}


@pytest.mark.integration
def test_hook_subprocess_fails_on_malformed_stdin():
    """Verify that malformed JSON on stdin fails fast with a non-zero exit code."""
    proc = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input="invalid json {",
        text=True,
        capture_output=True,
    )
    assert proc.returncode != 0


def test_hook_omits_session_for_non_session_servers():
    """Calls to servers other than pkb (e.g. telegram, konnect) receive no session_id."""
    from mcp_caller_session import inject_caller_session

    for tool_name in (
        "mcp__telegram__reply",
        "mcp__aops:telegram__reply",
        "mcp__konnect__get_board",
        "mcp__playwright__browser_click",
        "mcp__plugin_aops_external_services__fetch",
        "mcp__aops:external_services__fetch",
        "mcp__external_services__fetch",
    ):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "session_id": "sess-uuid-main",
            "tool_input": {"arg1": "val1"},
        }
        result = inject_caller_session(payload, session_servers=SESSION_SERVERS, environ={})
        assert result == {}, f"Expected no modification for {tool_name}, got {result}"


def test_hook_injects_session_for_pkb_tool_name_formats():
    """Direct PKB tool calls receive top-level session_id across tool name formats."""
    from mcp_caller_session import inject_caller_session

    for tool_name in (
        "mcp__pkb__search",
        "mcp__pkb__get_task",
        "mcp__plugin_aops_pkb__get_task",
        "mcp__aops:pkb__get_task",
    ):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "session_id": "sess-ac2",
            "tool_input": {"key": "val"},
        }
        result = inject_caller_session(payload, session_servers=SESSION_SERVERS, environ={})
        updated = result["hookSpecificOutput"]["updatedInput"]
        assert updated == {"key": "val", "session_id": "sess-ac2"}


def test_hook_resolves_root_session_id_from_tracer_state(tmp_path, monkeypatch):
    """Out-of-process subagent MCP call resolves root phoenix_session_id as session_id."""
    from mcp_caller_session import inject_caller_session

    monkeypatch.setenv("HOME", str(tmp_path))
    tracer_dir = tmp_path / ".claude" / "tracer"
    tracer_dir.mkdir(parents=True, exist_ok=True)
    (tracer_dir / "subagent-sess-99.json").write_text(
        json.dumps(
            {
                "session_id": "subagent-sess-99",
                "phoenix_session_id": "root-sess-00",
                "parent_session_id": "root-sess-00",
            }
        ),
        encoding="utf-8",
    )

    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__pkb__get_task",
        "session_id": "subagent-sess-99",
        "tool_input": {"id": "task-fixture-01"},
    }
    result = inject_caller_session(payload, session_servers=SESSION_SERVERS, environ={})
    assert result["hookSpecificOutput"]["updatedInput"]["session_id"] == "root-sess-00"

    payload_suffixed = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__pkb__get_task",
        "session_id": "root-sess-00/task-1",
        "tool_input": {"id": "task-fixture-01"},
    }
    res_suffixed = inject_caller_session(
        payload_suffixed, session_servers=SESSION_SERVERS, environ={}
    )
    assert res_suffixed["hookSpecificOutput"]["updatedInput"]["session_id"] == "root-sess-00"


def test_dispatch_normalize_env_session_id_precedence(monkeypatch):
    """dispatch.normalize prioritizes CLAUDE_CODE_SESSION_ID / CLAUDE_SESSION_ID / ANTIGRAVITY_CONVERSATION_ID over stdin."""
    from dispatch import normalize

    claude_raw = {"session_id": "stdin-claude", "prompt": "hi"}
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "env-cc-1")
    monkeypatch.setenv("CLAUDE_SESSION_ID", "env-c-2")
    assert normalize("claude", "UserPromptSubmit", claude_raw, IDA_HOOKS).session_id == "env-cc-1"

    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID")
    assert normalize("claude", "UserPromptSubmit", claude_raw, IDA_HOOKS).session_id == "env-c-2"

    monkeypatch.delenv("CLAUDE_SESSION_ID")
    assert (
        normalize("claude", "UserPromptSubmit", claude_raw, IDA_HOOKS).session_id == "stdin-claude"
    )

    agy_raw = {"conversationId": "stdin-agy"}
    monkeypatch.setenv("ANTIGRAVITY_CONVERSATION_ID", "env-agy-1")
    assert normalize("agy", "PreToolUse", agy_raw, IDA_HOOKS).session_id == "env-agy-1"

    monkeypatch.delenv("ANTIGRAVITY_CONVERSATION_ID")
    assert normalize("agy", "PreToolUse", agy_raw, IDA_HOOKS).session_id == "stdin-agy"
