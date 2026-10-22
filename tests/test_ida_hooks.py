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
        raw={
            "tool_input": tool_input,
            "tool_response": {"status": "completed", "content": [{"type": "text", "text": "X"}]},
        },
    )
    res = handlers.rule_against_hearsay(ctx)
    assert res is not None
    assert res.kind is Kind.ADVISE
    expected_inject, expected_user = load_message_pair(IDA_HOOKS, "hearsay")
    assert res.inject_text == expected_inject
    assert res.user_text == expected_user


@pytest.mark.parametrize("bg_val", [None, True, "true", "1", "yes"])
def test_hearsay_does_not_fire_on_background_subagent_post_tool_use(bg_val):
    tool_input = {"description": "bg subagent"}
    if bg_val is not None:
        tool_input["run_in_background"] = bg_val
    ctx = HookContext(
        client="claude",
        event="PostToolUse",
        tool="Agent",
        agent_type="ida:ida",
        session_id="s-ida-bg",
        hooks_dir=IDA_HOOKS,
        raw={
            "tool_input": tool_input,
            "tool_response": {"isAsync": True, "status": "async_launched", "agentId": "a1"},
        },
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


# ---------------------------------------------------------------------------
# 3. Quiet hook on Stop and PreToolUse for Ida Prime
# ---------------------------------------------------------------------------


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
        '<cross-session-message from="twin-a">PR #12 merged\n```argdown\n(1) p -- fact\n-- w --\n(2) c\n```\n</cross-session-message>',
        '<teammate-message teammate_id="worker">done\n```argdown\n(1) p -- fact\n-- w --\n(2) c\n```\n</teammate-message>',
        "<task-notification>worker finished\n```argdown\n(1) p -- fact\n-- w --\n(2) c\n```\n</task-notification>",
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


def test_session_start_raises_when_pkb_mcp_url_unset(monkeypatch: pytest.MonkeyPatch):
    """SessionStart fails loudly when PKB_MCP_URL is unset (no guessing, no fallback)."""
    monkeypatch.delenv("PKB_MCP_URL", raising=False)
    ctx = HookContext(
        client="claude",
        event="SessionStart",
        session_id="s-pkb-test",
        hooks_dir=IDA_HOOKS,
    )
    with pytest.raises(RuntimeError, match="PKB_MCP_URL"):
        handlers.session_start(ctx)


# ---------------------------------------------------------------------------
# agy: recorded hook payload shapes
# ---------------------------------------------------------------------------

_AGY_PAYLOADS = json.loads(
    (REPO_ROOT / "tests" / "fixtures" / "agy_hook_payloads.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize(
    ("event", "payload"),
    [
        ("PreToolUse", "pre_tool_invoke_subagent"),
        ("PostToolUse", "post_tool_invoke_subagent"),
        ("PostToolUse", "post_tool_wait"),
    ],
)
def test_normalize_reads_agy_nested_tool_call(event: str, payload: str, tmp_path: Path):
    from dispatch import normalize

    raw = _AGY_PAYLOADS[payload]
    ctx = normalize("agy", event, raw, tmp_path)
    assert ctx.tool == raw["toolCall"]["name"]
    assert ctx.tool_input == raw["toolCall"]["args"]


def _session_start_parts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
    monkeypatch.setenv("PKB_MCP_URL", "http://localhost:8000")
    ctx = HookContext(client="claude", event="SessionStart", session_id="claude-sess")
    result = handlers.session_start(ctx)
    assert result is not None
    return result.inject_text.split("\n\n")


@pytest.fixture
def pointer_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "session_pointer"
    monkeypatch.setenv("AOPS_SESSION_POINTER_DIR", str(state))
    return state


def test_agy_first_pre_invocation_delivers_the_session_start_pointer_once(
    pointer_state: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from dispatch import normalize

    parts = _session_start_parts(monkeypatch)
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(json.dumps({"type": "SYSTEM_MESSAGE", "content": "started"}) + "\n")

    payload = dict(_AGY_PAYLOADS["pre_invocation_first"], transcriptPath=str(transcript))
    first = handlers.user_prompt_submit(normalize("agy", "UserPromptSubmit", payload, IDA_HOOKS))
    assert first is not None
    assert first.inject_text in parts

    for later in ("pre_invocation_later", "pre_invocation_next_turn"):
        payload_later = dict(_AGY_PAYLOADS[later], transcriptPath=str(transcript))
        ctx = normalize("agy", "UserPromptSubmit", payload_later, IDA_HOOKS)
        assert handlers.user_prompt_submit(ctx) is None


def test_agy_pointer_is_per_conversation(pointer_state: Path, tmp_path: Path):
    from dispatch import normalize

    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(json.dumps({"type": "SYSTEM_MESSAGE", "content": "started"}) + "\n")

    one = dict(_AGY_PAYLOADS["pre_invocation_first"], transcriptPath=str(transcript))
    other = dict(one, conversationId="agy-conv-2")
    assert handlers.user_prompt_submit(normalize("agy", "UserPromptSubmit", one, IDA_HOOKS))
    assert handlers.user_prompt_submit(normalize("agy", "UserPromptSubmit", other, IDA_HOOKS))


def test_claude_user_prompt_submit_carries_no_session_start_pointer(
    pointer_state: Path, monkeypatch: pytest.MonkeyPatch
):
    from dispatch import normalize

    parts = _session_start_parts(monkeypatch)
    raw = {"session_id": "claude-sess", "prompt": "hello"}
    result = handlers.user_prompt_submit(normalize("claude", "UserPromptSubmit", raw, IDA_HOOKS))
    assert result is None or not set(result.inject_text.split("\n\n")) & set(parts)
