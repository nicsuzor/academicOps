"""Tests for ida hooks: hearsay, honesty, and quiet."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

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


_PEER_REPORT = '<cross-session-message from="twin-a">PR #12 merged</cross-session-message>'
_USER_MESSAGE = '<channel source="plugin:telegram:telegram" user="nic">ship it</channel>'


@pytest.mark.parametrize("agent", ["ida:ida", "ida:sara"])
def test_hearsay_fires_on_a_peer_report(agent):
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type=agent,
        session_id="s-ida-1",
        hooks_dir=IDA_HOOKS,
        raw={"prompt": _PEER_REPORT},
    )
    res = handlers.rule_against_hearsay(ctx)
    assert res is not None
    assert res.kind is Kind.ADVISE
    expected_inject, expected_user = load_message_pair(IDA_HOOKS, "hearsay")
    assert res.inject_text == expected_inject
    assert res.user_text == expected_user


@pytest.mark.parametrize("prompt", [_USER_MESSAGE, "what's next?"])
def test_hearsay_does_not_fire_on_the_users_own_messages(prompt):
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="ida:ida",
        session_id="s-ida-2",
        hooks_dir=IDA_HOOKS,
        raw={"prompt": prompt},
    )
    assert handlers.rule_against_hearsay(ctx) is None


def test_hearsay_does_not_fire_for_non_ida_agents():
    for agent in ("aops:james", "james", "worker", "pauli", "rbg"):
        ctx = HookContext(
            client="claude",
            event="UserPromptSubmit",
            agent_type=agent,
            session_id="s-other",
            hooks_dir=IDA_HOOKS,
            raw={"prompt": _PEER_REPORT},
        )
        res = handlers.rule_against_hearsay(ctx)
        assert res is None, f"hearsay fired for non-ida agent {agent}"


# ---------------------------------------------------------------------------
# 2. Honesty hook on Stop for all agents (blocking once)
# ---------------------------------------------------------------------------


def test_honesty_not_registered_on_stop():
    assert "Stop" in handlers.HANDLERS
    assert handlers.honest_output not in handlers.HANDLERS["Stop"]


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


@pytest.mark.parametrize("client", ["claude", "agy"])
@pytest.mark.parametrize("agent", ["worker", "ida:ida"])
def test_stop_passes_through_end_to_end(staged_hooks: Path, client: str, agent: str):
    payload = {
        "hook_event_name": "Stop",
        "agent_type": agent,
        "session_id": f"s-stop-{client}-{agent}",
    }
    proc = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), client, "Stop"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc.returncode == 0
    expected_honesty, _ = load_message_pair(staged_hooks, "honesty")
    expected_quiet, _ = load_message_pair(staged_hooks, "quiet")
    assert expected_honesty not in proc.stdout
    assert expected_quiet not in proc.stdout
    assert '"block"' not in proc.stdout


# ---------------------------------------------------------------------------
# 3. Quiet hook on Stop and PreToolUse for Ida Prime
# ---------------------------------------------------------------------------


def test_quiet_not_registered_on_stop_or_pretooluse():
    assert "Stop" in handlers.HANDLERS
    assert handlers.be_quiet not in handlers.HANDLERS["Stop"]
    assert "PreToolUse" in handlers.HANDLERS
    assert handlers.quiet_channel_reply not in handlers.HANDLERS["PreToolUse"]


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


def test_quiet_channel_reply_denies_once_for_ida():
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
    expected_honesty, _ = load_message_pair(IDA_HOOKS, "honesty")
    expected_quiet, _ = load_message_pair(IDA_HOOKS, "quiet")
    for tool in channel_tools:
        handlers.clear_channel_gate_state("s-chan-1")
        ctx = HookContext(
            client="claude",
            event="PreToolUse",
            agent_type="ida:ida",
            session_id="s-chan-1",
            tool=tool,
            hooks_dir=IDA_HOOKS,
        )
        res1 = handlers.quiet_channel_reply(ctx)
        assert res1 is not None, f"gate did not fire for {tool}"
        assert res1.kind is Kind.REFUSE
        assert expected_honesty in res1.inject_text
        assert expected_quiet in res1.inject_text
        assert handlers.quiet_channel_reply(ctx) is None


@pytest.mark.parametrize("client", ["claude", "agy"])
def test_pretooluse_channel_reply_passes_through_for_ida(staged_hooks: Path, client: str):
    payload = {
        "hook_event_name": "PreToolUse",
        "agent_type": "ida:ida",
        "session_id": f"s-chan-{client}",
        "tool_name": "telegram_reply",
    }
    proc = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), client, "PreToolUse"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc.returncode == 0
    expected_quiet, _ = load_message_pair(staged_hooks, "quiet")
    assert expected_quiet not in proc.stdout
    assert '"deny"' not in proc.stdout


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
    ctx_reply = HookContext(
        client="claude",
        event="PreToolUse",
        agent_type="ida:ida",
        session_id=session_id,
        tool="telegram_reply",
        hooks_dir=IDA_HOOKS,
    )
    # Turn 1: 1st call denied, 2nd allowed
    res1 = handlers.quiet_channel_reply(ctx_reply)
    assert res1 is not None and res1.kind is Kind.REFUSE
    assert handlers.quiet_channel_reply(ctx_reply) is None

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
    res3 = handlers.quiet_channel_reply(ctx_reply)
    assert res3 is not None and res3.kind is Kind.REFUSE


def test_is_ida_variants():
    from dispatch import HookContext

    for valid_agent in ("ida", "ida:ida", "plugin:ida", "ida-prime", "ida_prime"):
        ctx = HookContext(client="claude", event="Stop", agent_type=valid_agent)
        assert handlers._is_ida(ctx) is True, f"failed for {valid_agent}"
        assert handlers.is_ida(ctx) is True, f"failed for {valid_agent}"
        assert handlers.is_agent(ctx, "ida") is True, f"failed for {valid_agent}"

    for invalid_agent in ("aops:james", "james", "pauli", "marsha", "rbg", "ida:custom", ""):
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


def test_merge_combines_multiple_advisories():
    from dispatch import Kind, Result, _merge

    r1 = Result("first note", "user 1", Kind.ADVISE)
    r2 = Result("second note", "user 2", Kind.ADVISE)
    merged = _merge([r1, r2])
    assert merged is not None
    assert merged.kind is Kind.ADVISE
    assert "first note\n\nsecond note" == merged.inject_text
    assert "user 1\n\nuser 2" == merged.user_text


@pytest.mark.parametrize(
    ("prompt", "expected_query"),
    [
        ("what are the axioms of academicOps?", "what are the axioms of academicOps?"),
        ('<channel source="plugin:telegram:telegram" user="nic">ship it</channel>', "ship it"),
    ],
)
def test_user_messages_get_pkb_hydration_and_no_hearsay_or_gate(prompt, expected_query):
    import premise_check_gate as pcg

    session_id = f"s-test-user-{abs(hash(prompt))}"
    pcg.clear_state(session_id)

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="ida:ida",
        session_id=session_id,
        hooks_dir=IDA_HOOKS,
        cwd="/workspace",
        raw={"prompt": prompt},
    )

    with patch.object(handlers, "_run_pkb_search", return_value="1. Match in pkb") as mock_search:
        # 1. PKB search runs with the unwrapped query
        search_res = handlers.search_the_pkb(ctx)
        mock_search.assert_called_once_with(expected_query, cwd="/workspace")
        assert search_res is not None
        assert "<academicOps PKB search results>" in search_res.inject_text

        # 2. Hearsay does not fire
        hearsay_res = handlers.rule_against_hearsay(ctx)
        assert hearsay_res is None

        # 3. Gate is not armed
        handlers.premise_check_arm(ctx)
        assert pcg.is_armed(session_id) is False


@pytest.mark.parametrize(
    "peer_prompt",
    [
        '<cross-session-message from="twin-a">PR #12 merged</cross-session-message>',
        '<teammate-message teammate_id="worker">done</teammate-message>',
        "<task-notification>worker finished</task-notification>",
    ],
)
def test_agent_messages_get_hearsay_and_arm_gate_without_hydration(peer_prompt):
    import premise_check_gate as pcg

    session_id = f"s-test-peer-{abs(hash(peer_prompt))}"
    pcg.clear_state(session_id)

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type="ida:ida",
        session_id=session_id,
        hooks_dir=IDA_HOOKS,
        cwd="/workspace",
        raw={"prompt": peer_prompt},
    )

    with patch.object(handlers, "_run_pkb_search") as mock_search:
        # 1. Hydration skips peer reports
        search_res = handlers.search_the_pkb(ctx)
        mock_search.assert_not_called()
        assert search_res is None

        # 2. Hearsay fires
        hearsay_res = handlers.rule_against_hearsay(ctx)
        assert hearsay_res is not None
        expected_hearsay, _ = load_message_pair(IDA_HOOKS, "hearsay")
        assert hearsay_res.inject_text == expected_hearsay

        # 3. Gate arms
        handlers.premise_check_arm(ctx)
        assert pcg.is_armed(session_id) is True


@pytest.mark.parametrize("agent", ["ida", "ida:ida", "ida-prime"])
def test_honesty_reaches_ida_prime_when_search_empty(agent: str):
    """When PKB search yields no results on UserPromptSubmit, honesty.md applies to Ida Prime."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type=agent,
        hooks_dir=IDA_HOOKS,
        raw={"prompt": "what is the plan for today?"},
    )
    with patch.object(handlers, "_run_pkb_search", return_value=None):
        res = handlers.search_the_pkb(ctx)
        assert res is not None
        expected_inject, expected_user = load_message_pair(IDA_HOOKS, "honesty")
        assert res.inject_text == expected_inject
        assert res.user_text == expected_user


@pytest.mark.parametrize("agent", ["sara", "ida:sara", "james", "aops:james"])
def test_honesty_exemption_preserved_for_sara_and_james(agent: str):
    """Sara and James remain exempted from honesty.md fallback on UserPromptSubmit."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type=agent,
        hooks_dir=IDA_HOOKS,
        raw={"prompt": "execute task"},
    )
    with patch.object(handlers, "_run_pkb_search", return_value=None):
        res = handlers.search_the_pkb(ctx)
        assert res is None


@pytest.mark.parametrize("client", ["claude", "agy"])
def test_dispatch_honesty_reaches_ida_prime(staged_hooks: Path, client: str):
    """End-to-end dispatch confirms honesty.md is returned for Ida Prime on prompt submit."""
    event = "UserPromptSubmit" if client == "claude" else "PreInvocation"
    payload = {
        "hook_event_name": event,
        "agent_type": "ida:ida",
        "session_id": f"s-ida-{client}",
        "prompt": "general user inquiry without pkb match",
    }
    proc = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), client, event],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    expected_honesty, _ = load_message_pair(staged_hooks, "honesty")
    if client == "claude":
        assert data["hookSpecificOutput"]["additionalContext"] == expected_honesty
    else:
        assert any(
            expected_honesty == step.get("ephemeralMessage") for step in data.get("injectSteps", [])
        )
