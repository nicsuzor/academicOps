"""Tests for ida hooks: hearsay, honesty, and quiet."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
_POLICY_FILE = REPO_ROOT / "tests" / "policy.toml"
_POLICY = tomllib.loads(_POLICY_FILE.read_text(encoding="utf-8")) if _POLICY_FILE.exists() else {}

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


def test_hearsay_registered_on_user_prompt_submit_and_post_tool_use():
    assert handlers.HANDLERS["UserPromptSubmit"] == [handlers.user_prompt_submit]
    assert handlers.HANDLERS["PostToolUse"] == [handlers.post_tool]
    assert "PostToolBatch" not in handlers.HANDLERS


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


@pytest.mark.parametrize("agent", ["ida:ida", "ida:sara", "sara"])
@pytest.mark.parametrize("bg_val", [None, False, "false"])
def test_hearsay_fires_on_foreground_subagent_post_tool_use(agent, bg_val):
    tool_input = {"description": "foreground subagent"}
    if bg_val is not None:
        tool_input["run_in_background"] = bg_val
    ctx = HookContext(
        client="claude",
        event="PostToolUse",
        tool="Agent",
        agent_type=agent,
        session_id="s-ida-fg",
        hooks_dir=IDA_HOOKS,
        raw={"tool_input": tool_input},
    )
    res = handlers.rule_against_hearsay(ctx)
    assert res is not None
    assert res.kind is Kind.ADVISE
    expected_inject, expected_user = load_message_pair(IDA_HOOKS, "hearsay")
    assert res.inject_text == expected_inject
    assert res.user_text == expected_user


@pytest.mark.parametrize("bg_val", [True, "true", "1", "yes"])
def test_hearsay_does_not_fire_on_background_subagent_post_tool_use(bg_val):
    ctx = HookContext(
        client="claude",
        event="PostToolUse",
        tool="Agent",
        agent_type="ida:ida",
        session_id="s-ida-bg",
        hooks_dir=IDA_HOOKS,
        raw={"tool_input": {"description": "bg subagent", "run_in_background": bg_val}},
    )
    assert handlers.rule_against_hearsay(ctx) is None


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
        ctx_post = HookContext(
            client="claude",
            event="PostToolUse",
            tool="Agent",
            agent_type=agent,
            session_id="s-other",
            hooks_dir=IDA_HOOKS,
            raw={"tool_input": {"description": "fg"}},
        )
        assert handlers.rule_against_hearsay(ctx_post) is None


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
        assert res1.inject_text == expected_quiet
        assert expected_honesty not in res1.inject_text
        assert handlers.quiet_channel_reply(ctx) is None


def test_quiet_channel_reply_uses_the_gate_predicate():
    import premise_check_gate

    assert handlers.is_channel_reply_tool is premise_check_gate.is_channel_reply_tool
    assert not hasattr(handlers, "_is_channel_reply_tool")
    assert not hasattr(handlers, "_CHANNEL_REPLY_TOOLS")
    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        agent_type="ida:ida",
        session_id="s-chan-pred",
        tool="Agent",
        hooks_dir=IDA_HOOKS,
    )
    handlers.clear_channel_gate_state("s-chan-pred")
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
    assert "user 1 user 2" == merged.user_text


def test_merge_combines_multiple_advisories():
    from dispatch import Kind, Result, _merge

    r1 = Result("first note", "user 1", Kind.ADVISE)
    r2 = Result("second note", "user 2", Kind.ADVISE)
    merged = _merge([r1, r2])
    assert merged is not None
    assert merged.kind is Kind.ADVISE
    assert "first note\n\nsecond note" == merged.inject_text
    assert "user 1 user 2" == merged.user_text


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
        mock_search.assert_called_once_with(expected_query, cwd="/workspace", session_id=session_id)
        assert search_res is not None
        assert "<academicOps PKB search results>" in search_res.inject_text

        # 2. Honesty and Hearsay do not fire on user messages
        assert handlers.honesty_on_peer_message(ctx) is None
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

        # 2. Honesty fires for peer messages
        honesty_res = handlers.honesty_on_peer_message(ctx)
        assert honesty_res is not None
        expected_honesty, _ = load_message_pair(IDA_HOOKS, "honesty")
        assert honesty_res.inject_text == expected_honesty

        # 3. Hearsay fires
        hearsay_res = handlers.rule_against_hearsay(ctx)
        assert hearsay_res is not None
        expected_hearsay, _ = load_message_pair(IDA_HOOKS, "hearsay")
        assert hearsay_res.inject_text == expected_hearsay

        # 4. Gate arms
        handlers.premise_check_arm(ctx)
        assert pcg.is_armed(session_id) is True


@pytest.mark.parametrize(
    "agent", ["ida", "ida:ida", "ida-prime", "sara", "ida:sara", "james", "aops:james", "worker"]
)
def test_no_honesty_fallback_when_search_empty(agent: str):
    """When PKB search yields no results on UserPromptSubmit, search_the_pkb returns None for all agents."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type=agent,
        hooks_dir=IDA_HOOKS,
        raw={"prompt": "what is the plan for today?"},
    )
    with patch.object(handlers, "_run_pkb_search", return_value=None):
        res = handlers.search_the_pkb(ctx)
        assert res is None


@pytest.mark.parametrize(
    "agent", ["ida:ida", "ida:sara", "aops:james", "worker", "pauli", "marsha", "rbg", ""]
)
@pytest.mark.parametrize(
    "peer_prompt",
    [
        '<cross-session-message from="twin-a">PR #12 merged</cross-session-message>',
        '<teammate-message teammate_id="worker">done</teammate-message>',
        "<task-notification>worker finished</task-notification>",
    ],
)
def test_honesty_on_peer_message_fires_for_all_agents(agent: str, peer_prompt: str):
    """When an incoming peer message arrives on UserPromptSubmit, honesty.md fires for all agents."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        agent_type=agent,
        hooks_dir=IDA_HOOKS,
        raw={"prompt": peer_prompt},
    )
    res = handlers.honesty_on_peer_message(ctx)
    assert res is not None
    expected_inject, expected_user = load_message_pair(IDA_HOOKS, "honesty")
    assert res.inject_text == expected_inject
    assert res.user_text == expected_user


def test_session_start_includes_premise_check_pointer(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PKB_MCP_URL", "https://pkb.example.com/mcp")
    ctx = HookContext(
        client="claude",
        event="SessionStart",
        session_id="s-session-start",
        hooks_dir=IDA_HOOKS,
    )
    res = handlers.session_start(ctx)
    assert res is not None
    assert (
        "Reports follow `premise-check`: written in its shape and checked on receipt."
        in res.inject_text
    )


@pytest.mark.parametrize("client", ["claude", "agy"])
@pytest.mark.parametrize("agent", ["ida:ida", "aops:james", "worker"])
def test_dispatch_honesty_reaches_all_agents_on_peer_message(
    staged_hooks: Path, client: str, agent: str
):
    """End-to-end dispatch confirms honesty.md is returned for all agents on incoming peer message."""
    event = "UserPromptSubmit" if client == "claude" else "PreInvocation"
    payload = {
        "hook_event_name": event,
        "agent_type": agent,
        "session_id": f"s-peer-{client}-{agent}",
        "prompt": "<task-notification>worker finished</task-notification>",
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
        assert expected_honesty in data["hookSpecificOutput"]["additionalContext"]
    else:
        assert any(
            expected_honesty in step.get("ephemeralMessage", "")
            for step in data.get("injectSteps", [])
        )


def test_each_hook_event_registers_single_handler():
    """Every hook event in HANDLERS runs through a single registered hook handler."""
    for event, registered in handlers.HANDLERS.items():
        assert len(registered) == 1, f"{event} registered {len(registered)} handlers: {registered}"


def test_peer_message_prompt_yields_single_user_prompt_submit_output(
    staged_hooks: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Replaying a peer-message prompt yields one UserPromptSubmit output carrying both the reminder and the gate notice, and no empty output."""
    import os

    gate_dir = tmp_path / "gate"
    gate_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["AOPS_PREMISE_GATE_DIR"] = str(gate_dir)

    sara_checkin_prompt = (
        '<cross-session-message from="uds:/tmp/cc-socks/118.sock" from-name="sara-1015-1338" from-mode="prompting">\n'
        "Check-in ~22:0xZ: both reviews of the observability spec PR approve it. https://github.com/nicsuzor/academicOps/pull/2938 (to dev) now waits only on merge.\n\n"
        "- **Alignment, aops_01ea867b (done):** PASS. US-1 at `specs/observability/observability.md:12-20` (AC-1.1–1.5) covers tonight's thread: how /reify composed tasks, how workers ran them, how supervisors received reports and caught mistakes, and pivots from session.id and verdict.id.\n"
        "- **Rules, aops_0bd385f0 (done):** APPROVE, posted on the PR at https://github.com/nicsuzor/academicOps/pull/2938#issuecomment-6202742967. The PR adds 109 lines and deletes 430, a net cut of 321. The spec has no links, implementation names or personal names. All 3 CI checks pass.\n"
        "- **Still running, 8 polecats:** dotfiles_c782766f, aops_59789df6, dotfiles_f2046116, aops_5c58fe03, aops_4e8bf75c, dotfiles_4ef13887, aops_3ffd32e4, aops_40ad3d18. None has released.\n"
        "- **Unacknowledged requests:** none. Pauli answered all six of tonight's reify requests.\n\n"
        "```argdown\n"
        "===\n"
        "title: Sara check-in ~22:00Z\n"
        "author: sara\n"
        "date: 2026-10-15\n"
        "abstract: Both reviews of PR #2938 pass; eight polecats running; no unacknowledged requests.\n"
        "granularity:\n"
        "  level: micro\n"
        '  floor: "Accept task-record verdicts with pointers and container listings as leaf nodes."\n'
        "model:\n"
        "  mode: strict\n"
        "===\n\n"
        "[Outcome]: PR academicOps#2938 has passed its alignment and rules reviews and awaits merge; eight tasks are still running; no peer request is unacknowledged.\n\n"
        "<Checkin>: Released review records and the container list establish the state.\n\n"
        '(1) [Alignment]: aops_01ea867b `status: done`, "Verdict: PASS (APPROVE) on PR #2938", US-1 at `observability.md:12-20`. {basis: "reported-by", pointer: "pkb aops_01ea867b released 2026-10-15T21:39:35Z"}\n'
        '(2) [Rules]: aops_0bd385f0 `status: done`, review posted `issuecomment-6202742967`, "APPROVE", CI `Lint/Type Check/Pytest: SUCCESS`. {basis: "reported-by", pointer: "pkb aops_0bd385f0 released 2026-10-15T21:35:43Z"}\n'
        '-- Form check: each verdict cites PR lines and acceptance items, so both reviews pass and the PR awaits merge only {uses: [1, 2], basis: "theory", pointer: "premise-check"} --\n'
        "(3) [PR ready]\n"
        '(4) [Running]: polecat_list_containers shows 8 task containers `running`, and every matching task is `in_progress`. {basis: "observed", pointer: "polecat_list_containers all:true"}\n'
        '-- Roll-up {uses: [3, 4], basis: "theory", pointer: "Sara: Status"} --\n'
        "(5) [Outcome]\n"
        "```\n"
        "</cross-session-message>"
    )
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "agent_type": "ida:ida",
        "session_id": "ff3bf890-046e-4d33-bc94-a4e33ac70e43",
        "prompt": sara_checkin_prompt,
    }
    proc = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "claude", "UserPromptSubmit"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    system_message = data.get("systemMessage", "")
    assert "\n" not in system_message
    assert system_message == (
        "Reminded to use `premise-check` when replying to a peer message. "
        "Premise-check gate armed by claim-59204fc6."
    )


def test_session_start_metadata_resolves_pkb(monkeypatch: pytest.MonkeyPatch):
    """pkb resolves to PKB_MCP_URL when configured per policy; the hook raises when unset."""
    policy_pkb_url = _POLICY.get("hooks", {}).get("session_start", {}).get("pkb_url")
    assert policy_pkb_url, "tests/policy.toml must define hooks.session_start.pkb_url"

    monkeypatch.setenv("PKB_MCP_URL", policy_pkb_url)
    ctx = HookContext(
        client="claude",
        event="SessionStart",
        session_id="s-pkb-test",
        hooks_dir=IDA_HOOKS,
    )
    res = handlers.session_start(ctx)
    assert res is not None
    assert f"pkb: {policy_pkb_url}" in res.inject_text
    assert "pkb: unknown" not in res.inject_text

    # When PKB_MCP_URL is unset, the hook raises (no guessing, no fallback)
    monkeypatch.delenv("PKB_MCP_URL", raising=False)
    with pytest.raises(RuntimeError, match="PKB_MCP_URL"):
        handlers.session_start(ctx)


def test_session_start_metadata_service_name(monkeypatch: pytest.MonkeyPatch):
    """tracing service reflects OTEL_SERVICE_NAME when configured, omitted when unset."""
    monkeypatch.setenv("GENAI_ENGINE_TRACE_ENDPOINT", "https://otel.example.com/v1/traces")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "custom-tracer-service")
    monkeypatch.setenv("PKB_MCP_URL", "https://pkb.example.com/mcp")
    ctx = HookContext(
        client="claude",
        event="SessionStart",
        session_id="s-svc-test",
        hooks_dir=IDA_HOOKS,
    )
    res = handlers.session_start(ctx)
    assert res is not None
    assert (
        "tracing: https://otel.example.com/v1/traces (service: custom-tracer-service)"
        in res.inject_text
    )

    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    res2 = handlers.session_start(ctx)
    assert res2 is not None
    assert "tracing: https://otel.example.com/v1/traces" in res2.inject_text
    assert "service:" not in res2.inject_text


def test_session_start_metadata_resolves_plugin_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """plugins field prints resolved version from installed plugin manifest."""
    monkeypatch.setenv("PKB_MCP_URL", "https://pkb.example.com/mcp")
    fake_plugin_root = tmp_path / "fake-plugin"
    fake_hooks_dir = fake_plugin_root / "hooks"
    fake_hooks_dir.mkdir(parents=True)
    manifest_dir = fake_plugin_root / ".claude-plugin"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "plugin.json").write_text(json.dumps({"name": "ida", "version": "0.10.24"}))

    ctx = HookContext(
        client="claude",
        event="SessionStart",
        session_id="s-ver-test",
        hooks_dir=fake_hooks_dir,
    )
    res = handlers.session_start(ctx)
    assert res is not None
    assert "plugins: 0.10.24" in res.inject_text
