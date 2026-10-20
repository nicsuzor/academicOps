"""Tests for degraded capability detection on PostToolUse (#3021, #3022).

Covers:
1. PostToolUse detects degraded capability flags in tool results (voiceSent: false, voiceError, *_error) and warns.
2. Normal tool responses pass without warning.
3. Stringified JSON and invalid inputs are handled safely.
4. End-to-end dispatch of PostToolUse with degraded results returns expected advisory warning.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"

if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import importlib.util

handlers_spec = importlib.util.spec_from_file_location("ida_handlers", IDA_HOOKS / "handlers.py")
assert handlers_spec is not None and handlers_spec.loader is not None
handlers = importlib.util.module_from_spec(handlers_spec)
handlers_spec.loader.exec_module(handlers)

from dispatch import HookContext, Kind, load_message_pair  # type: ignore[import-not-found]

_POLICY_FILE = REPO_ROOT / "tests" / "policy.toml"
_policy = tomllib.loads(_POLICY_FILE.read_text(encoding="utf-8")) if _POLICY_FILE.exists() else {}
_DEGRADED_KEYS = _policy.get("hooks", {}).get("degraded_capability", {}).get(
    "degraded_keys", ["voiceError", "transcript_error"]
)


def test_post_tool_surfaces_degraded_voice_error():
    """PostToolUse detects voiceError in tool response dict and emits an advisory warning."""
    sample_error = "ENOENT: no such file or directory, posix_spawn 'speak.sh'"
    ctx = HookContext(
        client="claude",
        event="PostToolUse",
        tool="reply",
        agent_type="ida:ida",
        session_id="s-degraded-voice-1",
        hooks_dir=IDA_HOOKS,
        cwd=str(REPO_ROOT),
        raw={
            "tool_name": "reply",
            "tool_response": {
                "success": True,
                "messageId": 1234,
                "voiceSent": False,
                "voiceError": sample_error,
            },
        },
    )

    res = handlers.post_tool_degraded_check(ctx)
    assert res is not None, "post_tool_degraded_check should detect degraded result"
    assert res.kind is Kind.ADVISE
    expected_inject, expected_user = load_message_pair(IDA_HOOKS, "degraded_capability")
    assert expected_inject in res.inject_text
    assert sample_error in res.inject_text
    assert res.user_text == expected_user


@pytest.mark.parametrize("err_key", _DEGRADED_KEYS)
def test_post_tool_surfaces_configured_error_keys(err_key: str):
    """PostToolUse detects error fields declared in policy and warns."""
    sample_err = f"Failed to execute operation on {err_key}"
    ctx = HookContext(
        client="claude",
        event="PostToolUse",
        tool="channel_tool",
        agent_type="ida:ida",
        session_id="s-degraded-policy-1",
        hooks_dir=IDA_HOOKS,
        cwd=str(REPO_ROOT),
        raw={
            "tool_name": "channel_tool",
            "tool_response": {
                "ok": False,
                err_key: sample_err,
            },
        },
    )

    res = handlers.post_tool_degraded_check(ctx)
    assert res is not None
    assert res.kind is Kind.ADVISE
    assert sample_err in res.inject_text


def test_post_tool_handles_stringified_json_tool_response():
    """PostToolUse parses stringified JSON responses to check for degradation."""
    sample_err = "TTS daemon timeout"
    payload = json.dumps({"voiceSent": False, "voiceError": sample_err})
    ctx = HookContext(
        client="claude",
        event="PostToolUse",
        tool="reply",
        agent_type="ida:ida",
        session_id="s-degraded-json-1",
        hooks_dir=IDA_HOOKS,
        cwd=str(REPO_ROOT),
        raw={
            "tool_name": "reply",
            "tool_response": payload,
        },
    )

    res = handlers.post_tool_degraded_check(ctx)
    assert res is not None
    assert res.kind is Kind.ADVISE
    assert sample_err in res.inject_text


def test_post_tool_passes_clean_response():
    """PostToolUse returns None when response has no degraded capability flags."""
    ctx = HookContext(
        client="claude",
        event="PostToolUse",
        tool="reply",
        agent_type="ida:ida",
        session_id="s-clean-1",
        hooks_dir=IDA_HOOKS,
        cwd=str(REPO_ROOT),
        raw={
            "tool_name": "reply",
            "tool_response": {"success": True, "messageId": 5678, "voiceSent": True},
        },
    )

    res = handlers.post_tool_degraded_check(ctx)
    assert res is None


def test_post_tool_handles_invalid_or_missing_response():
    """PostToolUse safely ignores non-JSON strings or missing response payloads."""
    ctx_invalid = HookContext(
        client="claude",
        event="PostToolUse",
        tool="reply",
        agent_type="ida:ida",
        session_id="s-invalid-1",
        hooks_dir=IDA_HOOKS,
        cwd=str(REPO_ROOT),
        raw={"tool_name": "reply", "tool_response": "not-valid-json"},
    )
    assert handlers.post_tool_degraded_check(ctx_invalid) is None

    ctx_none = HookContext(
        client="claude",
        event="PostToolUse",
        tool="reply",
        agent_type="ida:ida",
        session_id="s-none-1",
        hooks_dir=IDA_HOOKS,
        cwd=str(REPO_ROOT),
        raw={"tool_name": "reply"},
    )
    assert handlers.post_tool_degraded_check(ctx_none) is None


def test_dispatch_post_tool_degraded_flow():
    """End-to-end hook dispatch: PostToolUse with degraded response triggers advisory warning."""
    sample_err = "Voice note encoder failed"
    payload = {
        "hook_event_name": "PostToolUse",
        "agent_type": "ida:ida",
        "session_id": "s-dispatch-degraded-1",
        "tool_name": "reply",
        "tool_response": {
            "success": True,
            "voiceSent": False,
            "voiceError": sample_err,
        },
    }
    proc = subprocess.run(
        [sys.executable, str(IDA_HOOKS / "dispatch.py"), "claude", "PostToolUse"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(IDA_HOOKS),
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert "hookSpecificOutput" in data
    additional_context = data["hookSpecificOutput"].get("additionalContext", "")
    assert sample_err in additional_context
    assert "degraded" in additional_context.lower() or "voiceerror" in additional_context.lower()
