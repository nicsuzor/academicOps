"""UserPromptSubmit routing by prompt origin.

Nic's messages (console, Telegram) get PKB hydration, no hearsay reminder, and
do not arm the premise-check gate. Agent messages (cross-session, teammate,
task-notification) get the hearsay reminder and arm the gate, and are not
hydrated. A prompt carrying both gets both. Wrapper samples are the real Phoenix spans in test_prompt_origin.py.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_HOOKS_DIR = Path(__file__).resolve().parent.parent / "plugins" / "ida" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_spec = importlib.util.spec_from_file_location(
    "origin_routing_handlers", _HOOKS_DIR / "handlers.py"
)
assert _spec is not None and _spec.loader is not None
handlers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(handlers)

import premise_check_gate as pcg  # noqa: E402
from dispatch import HookContext, _merge, load_message_pair  # noqa: E402

from tests.test_prompt_origin import (  # noqa: E402
    CONSOLE,
    CROSS_SESSION_BARE,
    CROSS_SESSION_WRAPPED,
    TASK_NOTIFICATION,
    TEAMMATE,
    TELEGRAM,
)

NIC_PROMPTS = {"console": CONSOLE, "telegram": TELEGRAM}
AGENT_PROMPTS = {
    "cross-session-bare": CROSS_SESSION_BARE,
    "cross-session-wrapped": CROSS_SESSION_WRAPPED,
    "teammate": TEAMMATE,
    "task-notification": TASK_NOTIFICATION,
}


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate_state"))
    monkeypatch.setenv("AOPS_CHANNEL_GATE_DIR", str(tmp_path / "channel_gate"))
    (tmp_path / "channel_gate").mkdir()


def _ctx(prompt: str, session_id: str = "s-route", agent_type: str = "ida:ida") -> HookContext:
    return HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id=session_id,
        agent_type=agent_type,
        raw={"prompt": prompt},
        hooks_dir=_HOOKS_DIR,
        cwd="/workspace",
    )


# --- hydration -------------------------------------------------------------


def test_console_prompt_is_hydrated_with_the_prompt():
    with patch.object(handlers, "_run_pkb_search", return_value="hit") as search:
        res = handlers.search_the_pkb(_ctx(CONSOLE))
    search.assert_called_once_with(CONSOLE)
    assert res is not None and "hit" in res.inject_text


def test_telegram_prompt_is_hydrated_with_the_message_body_not_the_wrapper():
    with patch.object(handlers, "_run_pkb_search", return_value="hit") as search:
        res = handlers.search_the_pkb(_ctx(TELEGRAM))
    search.assert_called_once_with("use /craft to redo the daily skill edits.")
    assert res is not None and "hit" in res.inject_text


@pytest.mark.parametrize("name", AGENT_PROMPTS)
def test_agent_prompt_is_not_hydrated(name):
    with patch.object(handlers, "_run_pkb_search", return_value="hit") as search:
        res = handlers.search_the_pkb(_ctx(AGENT_PROMPTS[name]))
    search.assert_not_called()
    assert res is None


# --- hearsay reminder ------------------------------------------------------


@pytest.mark.parametrize("name", NIC_PROMPTS)
def test_nic_prompt_gets_no_hearsay_reminder(name):
    assert handlers.rule_against_hearsay(_ctx(NIC_PROMPTS[name])) is None


@pytest.mark.parametrize("name", AGENT_PROMPTS)
def test_agent_prompt_gets_hearsay_reminder(name):
    res = handlers.rule_against_hearsay(_ctx(AGENT_PROMPTS[name]))
    assert res is not None
    assert res.inject_text == load_message_pair(_HOOKS_DIR, "hearsay")[0]


# --- premise-check gate ----------------------------------------------------


@pytest.mark.parametrize("name", NIC_PROMPTS)
def test_nic_prompt_does_not_arm_the_gate(name):
    sid = f"s-nic-{name}"
    pcg.premise_check_arm(_ctx(NIC_PROMPTS[name], session_id=sid))
    assert pcg.is_armed(sid) is False


@pytest.mark.parametrize("name", AGENT_PROMPTS)
def test_agent_prompt_arms_the_gate(name):
    sid = f"s-agent-{name}"
    pcg.premise_check_arm(_ctx(AGENT_PROMPTS[name], session_id=sid))
    assert pcg.is_armed(sid) is True


def test_nic_prompt_leaves_an_already_armed_gate_armed():
    """Nic speaking does not discharge a pending verdict on an earlier agent claim."""
    sid = "s-pending"
    pcg.premise_check_arm(_ctx(CROSS_SESSION_BARE, session_id=sid))
    pcg.premise_check_arm(_ctx(CONSOLE, session_id=sid))
    assert pcg.is_armed(sid) is True


# --- mixed -----------------------------------------------------------------


def test_mixed_prompt_hydrates_nic_part_and_arms_for_agent_part():
    prompt = TELEGRAM + "\n" + CROSS_SESSION_BARE
    sid = "s-mixed"
    with patch.object(handlers, "_run_pkb_search", return_value="hit") as search:
        handlers.search_the_pkb(_ctx(prompt, session_id=sid))
    search.assert_called_once_with("use /craft to redo the daily skill edits.")
    assert handlers.rule_against_hearsay(_ctx(prompt, session_id=sid)) is not None
    pcg.premise_check_arm(_ctx(prompt, session_id=sid))
    assert pcg.is_armed(sid) is True


@pytest.mark.parametrize("nic", [CONSOLE, TELEGRAM], ids=["console", "telegram"])
def test_mixed_prompt_delivers_both_the_hydration_and_the_hearsay_reminder(nic):
    """Every registered UserPromptSubmit handler, merged as dispatch merges them."""
    ctx = _ctx(nic + "\n" + CROSS_SESSION_WRAPPED, session_id="s-mixed-merge")
    with patch.object(handlers, "_run_pkb_search", return_value="hit"):
        merged = _merge([h(ctx) for h in handlers.HANDLERS["UserPromptSubmit"]])
    assert merged is not None
    assert "<academicOps PKB search results>\nhit" in merged.inject_text
    assert load_message_pair(_HOOKS_DIR, "hearsay")[0] in merged.inject_text
    assert pcg.is_armed("s-mixed-merge") is True
