"""Tests for re-enabled ida hooks: hearsay, honesty, and quiet."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
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


@pytest.fixture
def staged_hooks(tmp_path: Path) -> Path:
    """A plugin hooks/ directory assembled with dispatch.py and handlers.py."""
    hooks = tmp_path / "hooks"
    shutil.copytree(IDA_HOOKS, hooks, ignore=shutil.ignore_patterns("__pycache__"))
    return hooks


@pytest.fixture(autouse=True)
def clean_gate_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    state_dir = tmp_path / "aops_channel_gate"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AOPS_CHANNEL_GATE_DIR", str(state_dir))
    yield
    handlers.clear_channel_gate_state()


# ---------------------------------------------------------------------------
# 1. Hearsay hook on UserPromptSubmit for Ida
# ---------------------------------------------------------------------------


def test_hearsay_registered_on_user_prompt_submit():
    assert "UserPromptSubmit" in handlers.HANDLERS
    assert handlers.rule_against_hearsay in handlers.HANDLERS["UserPromptSubmit"]


def test_hearsay_fires_for_ida_on_user_prompt_submit():
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="ida:ida",
        session_id="s-ida-1",
        hooks_dir=IDA_HOOKS,
    )
    res = handlers.rule_against_hearsay(ctx)
    assert res is not None
    assert res.kind is Kind.ADVISE
    expected_inject, expected_user = load_message_pair(IDA_HOOKS, "hearsay")
    assert res.inject_text == expected_inject
    assert res.user_text == expected_user


def test_hearsay_does_not_fire_for_non_ida_agents():
    for agent in ("aops:james", "james", "worker", "pauli", "rbg"):
        ctx = HookContext(
            client="claude",
            event="UserPromptSubmit",
            agent_type=agent,
            session_id="s-other",
            hooks_dir=IDA_HOOKS,
        )
        res = handlers.rule_against_hearsay(ctx)
        assert res is None, f"hearsay fired for non-ida agent {agent}"


def test_hearsay_dispatch_claude_end_to_end(staged_hooks: Path):
    proc = subprocess.run(
        [
            sys.executable,
            str(staged_hooks / "dispatch.py"),
            "claude",
            "UserPromptSubmit",
        ],
        input=json.dumps(
            {
                "hook_event_name": "UserPromptSubmit",
                "agent_type": "ida:ida",
                "session_id": "s-ida-e2e",
                "prompt": "Here is the subagent report.",
            }
        ),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    expected_inject, _ = load_message_pair(staged_hooks, "hearsay")
    assert expected_inject in data["hookSpecificOutput"]["additionalContext"]


def test_hearsay_dispatch_agy_end_to_end(staged_hooks: Path):
    proc = subprocess.run(
        [
            sys.executable,
            str(staged_hooks / "dispatch.py"),
            "agy",
            "PreInvocation",
        ],
        input=json.dumps(
            {
                "agent_type": "ida:ida",
                "session_id": "s-ida-agy",
                "prompt": "Twin message arriving.",
            }
        ),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    expected_inject, _ = load_message_pair(staged_hooks, "hearsay")
    assert any(
        step.get("ephemeralMessage") == expected_inject for step in data.get("injectSteps", [])
    )


# ---------------------------------------------------------------------------
# 2. Honesty hook on Stop for all agents (blocking once)
# ---------------------------------------------------------------------------


def test_honesty_registered_on_stop():
    assert "Stop" in handlers.HANDLERS
    assert handlers.honest_output in handlers.HANDLERS["Stop"]


def test_honesty_fires_for_all_agents_on_stop():
    for agent in ("ida:ida", "aops:james", "worker", "pauli", "marsha", ""):
        ctx = HookContext(
            client="claude",
            event="Stop",
            agent_type=agent,
            session_id=f"s-{agent}",
            hooks_dir=IDA_HOOKS,
        )
        res = handlers.honest_output(ctx)
        assert res is not None, f"honesty did not fire for {agent}"
        assert res.kind is Kind.BLOCK
        expected_inject, _ = load_message_pair(IDA_HOOKS, "honesty")
        assert res.inject_text == expected_inject


def test_honesty_does_not_fire_when_background_tasks_running():
    ctx = HookContext(
        client="claude",
        event="Stop",
        agent_type="worker",
        raw={"background_tasks": [{"id": "bg-1"}]},
        hooks_dir=IDA_HOOKS,
    )
    res = handlers.honest_output(ctx)
    assert res is None


def test_honesty_blocks_once_on_claude_end_to_end(staged_hooks: Path):
    # First attempt: blocks and returns decision: "block"
    payload = {
        "hook_event_name": "Stop",
        "agent_type": "worker",
        "session_id": "s-stop-1",
    }
    proc1 = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "Stop"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc1.returncode == 0
    data1 = json.loads(proc1.stdout)
    assert data1["decision"] == "block"
    expected_inject, _ = load_message_pair(staged_hooks, "honesty")
    assert expected_inject in data1["reason"]

    # Second attempt (continuation): stop_hook_active allows stop through cleanly
    payload["stop_hook_active"] = True
    proc2 = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "Stop"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc2.returncode == 0
    assert proc2.stdout.strip() == ""


def test_honesty_degrades_to_advisory_on_agy(staged_hooks: Path):
    payload = {
        "agent_type": "worker",
        "session_id": "s-stop-agy",
    }
    proc = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "agy", "Stop"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "decision" not in data or data["decision"] != "deny"
    expected_inject, _ = load_message_pair(staged_hooks, "honesty")
    assert any(
        step.get("ephemeralMessage") == expected_inject for step in data.get("injectSteps", [])
    )


# ---------------------------------------------------------------------------
# 3. Quiet hook on Stop and PreToolUse for Ida Prime (blocking once)
# ---------------------------------------------------------------------------


def test_quiet_registered_on_stop_and_pretooluse():
    assert "Stop" in handlers.HANDLERS
    assert handlers.be_quiet in handlers.HANDLERS["Stop"]
    assert "PreToolUse" in handlers.HANDLERS
    assert handlers.quiet_channel_reply in handlers.HANDLERS["PreToolUse"]


def test_quiet_stop_fires_only_for_ida():
    ctx_ida = HookContext(
        client="claude",
        event="Stop",
        agent_type="ida:ida",
        session_id="s-ida-stop",
        hooks_dir=IDA_HOOKS,
    )
    res_ida = handlers.be_quiet(ctx_ida)
    assert res_ida is not None
    assert res_ida.kind is Kind.BLOCK
    expected_quiet, _ = load_message_pair(IDA_HOOKS, "quiet")
    assert res_ida.inject_text == expected_quiet

    ctx_other = HookContext(
        client="claude",
        event="Stop",
        agent_type="aops:james",
        session_id="s-james-stop",
        hooks_dir=IDA_HOOKS,
    )
    assert handlers.be_quiet(ctx_other) is None


def test_ida_prime_stop_combines_honesty_and_quiet(staged_hooks: Path):
    payload = {
        "hook_event_name": "Stop",
        "agent_type": "ida:ida",
        "session_id": "s-ida-combined",
    }
    proc = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "Stop"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["decision"] == "block"
    expected_honesty, _ = load_message_pair(staged_hooks, "honesty")
    expected_quiet, _ = load_message_pair(staged_hooks, "quiet")
    assert expected_honesty in data["reason"]
    assert expected_quiet in data["reason"]


def test_quiet_pretooluse_channel_reply_denies_once_for_ida(staged_hooks: Path):
    channel_tools = (
        "telegram_reply",
        "telegram_send_message",
        "mcp__plugin_telegram_telegram__reply",
        "mcp__telegram__reply",
        "mcp__telegram__send_message",
        "discord_reply",
        "AskUserQuestion",
        "ask_question",
    )
    for tool in channel_tools:
        handlers.clear_channel_gate_state("s-chan-1")
        payload = {
            "hook_event_name": "PreToolUse",
            "agent_type": "ida:ida",
            "session_id": "s-chan-1",
            "tool_name": tool,
        }

        # Attempt 1: Denied once with honesty and quiet
        proc1 = subprocess.run(
            [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "PreToolUse"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=15,
            cwd=str(staged_hooks),
        )
        assert proc1.returncode == 0
        data1 = json.loads(proc1.stdout)
        specific1 = data1["hookSpecificOutput"]
        assert specific1["permissionDecision"] == "deny"
        expected_honesty, _ = load_message_pair(staged_hooks, "honesty")
        expected_quiet, _ = load_message_pair(staged_hooks, "quiet")
        assert expected_honesty in specific1["permissionDecisionReason"]
        assert expected_quiet in specific1["permissionDecisionReason"]

        # Attempt 2: Permitted
        proc2 = subprocess.run(
            [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "PreToolUse"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=15,
            cwd=str(staged_hooks),
        )
        assert proc2.returncode == 0
        assert proc2.stdout.strip() == ""


def test_pretooluse_channel_reply_degrades_to_advisory_on_agy(staged_hooks: Path):
    handlers.clear_channel_gate_state("s-chan-agy")
    payload = {
        "hook_event_name": "PreToolUse",
        "agent_type": "ida:ida",
        "session_id": "s-chan-agy",
        "tool_name": "telegram_reply",
    }
    proc = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "agy", "PreToolUse"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "decision" not in data or data["decision"] != "deny"
    expected_honesty, _ = load_message_pair(staged_hooks, "honesty")
    expected_quiet, _ = load_message_pair(staged_hooks, "quiet")
    assert any(
        expected_honesty in step.get("ephemeralMessage", "")
        and expected_quiet in step.get("ephemeralMessage", "")
        for step in data.get("injectSteps", [])
    )


def test_quiet_pretooluse_ignores_non_channel_tools(staged_hooks: Path):
    payload = {
        "hook_event_name": "PreToolUse",
        "agent_type": "ida:ida",
        "session_id": "s-non-chan",
        "tool_name": "Bash",
    }
    proc = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "PreToolUse"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_quiet_pretooluse_ignores_non_ida_agents(staged_hooks: Path):
    payload = {
        "hook_event_name": "PreToolUse",
        "agent_type": "worker",
        "session_id": "s-worker-chan",
        "tool_name": "telegram_reply",
    }
    proc = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "PreToolUse"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_user_prompt_submit_clears_channel_reply_gate_state(staged_hooks: Path):
    session_id = "s-reset-test"
    payload_reply = {
        "hook_event_name": "PreToolUse",
        "agent_type": "ida:ida",
        "session_id": session_id,
        "tool_name": "telegram_reply",
    }
    # Turn 1: 1st call denied
    proc1 = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "PreToolUse"],
        input=json.dumps(payload_reply),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert json.loads(proc1.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"

    # Turn 1: 2nd call allowed
    proc2 = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "PreToolUse"],
        input=json.dumps(payload_reply),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc2.stdout.strip() == ""

    # New turn arrives (UserPromptSubmit)
    proc_submit = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "UserPromptSubmit"],
        input=json.dumps(
            {
                "hook_event_name": "UserPromptSubmit",
                "agent_type": "ida:ida",
                "session_id": session_id,
                "prompt": "new instruction",
            }
        ),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc_submit.returncode == 0

    # Turn 2: 1st call denied again!
    proc3 = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "PreToolUse"],
        input=json.dumps(payload_reply),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert json.loads(proc3.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_is_ida_variants():
    from dispatch import HookContext

    for valid_agent in ("ida", "ida:ida", "plugin:ida", "ida-prime", "ida_prime", "ida:custom"):
        ctx = HookContext(client="claude", event="Stop", agent_type=valid_agent)
        assert handlers._is_ida(ctx) is True, f"failed for {valid_agent}"
        assert handlers.is_ida(ctx) is True, f"failed for {valid_agent}"
        assert handlers.is_agent(ctx, "ida") is True, f"failed for {valid_agent}"

    for invalid_agent in ("aops:james", "james", "pauli", "marsha", "rbg", ""):
        ctx = HookContext(client="claude", event="Stop", agent_type=invalid_agent)
        assert handlers._is_ida(ctx) is False, f"falsely matched for {invalid_agent}"
        assert handlers.is_ida(ctx) is False, f"falsely matched for {invalid_agent}"


def test_is_agent_variants():
    from dispatch import HookContext

    for valid_james in (
        "james",
        "aops:james",
        "james:james",
        "james-prime",
        "james_prime",
        "plugin:james",
    ):
        ctx = HookContext(client="claude", event="Stop", agent_type=valid_james)
        assert handlers.is_agent(ctx, "james") is True, f"failed for {valid_james}"
        assert handlers.is_agent(ctx, "ida", "james") is True, (
            f"failed for multi target {valid_james}"
        )
        assert handlers.is_ida(ctx, "james") is True, (
            f"failed for is_ida extra target {valid_james}"
        )

    # Also string directly and None handling
    assert handlers.is_agent("aops:james", "james") is True
    assert handlers.is_agent("ida", "ida") is True
    assert handlers.is_agent(None, "ida") is False


def test_normalize_resolves_agent_from_aliases_and_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from dispatch import normalize

    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()

    # 1. From agent_name
    ctx1 = normalize("claude", "Stop", {"agent_name": "ida"}, hooks_dir)
    assert ctx1.agent_type == "ida"

    # 2. From agent
    ctx2 = normalize("claude", "Stop", {"agent": "ida-prime"}, hooks_dir)
    assert ctx2.agent_type == "ida-prime"

    # 3. From environment variable
    monkeypatch.setenv("CLAUDE_AGENT_NAME", "ida")
    ctx3 = normalize("claude", "Stop", {}, hooks_dir)
    assert ctx3.agent_type == "ida"


def test_merge_combines_multiple_refusals():
    from dispatch import Kind, Result, _merge

    r1 = Result("first reason", "user 1", Kind.REFUSE)
    r2 = Result("second reason", "user 2", Kind.REFUSE)
    merged = _merge([r1, r2])
    assert merged is not None
    assert merged.kind is Kind.REFUSE
    assert "first reason\n\nsecond reason" == merged.inject_text
    assert "user 1\n\nuser 2" == merged.user_text
