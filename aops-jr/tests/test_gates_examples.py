"""The shipped gate example test for require_subagent_model."""

import sys
from pathlib import Path

_JR_HOOKS = str(Path(__file__).resolve().parent.parent / "hooks")
if _JR_HOOKS not in sys.path:
    sys.path.insert(0, _JR_HOOKS)

from hooks.gates.event import Event
from hooks.gates.require_subagent_model import require_subagent_model
from hooks.gates.verdict import Verdict


def test_require_subagent_model_warns_when_model_missing():
    e = Event(event="PreToolUse", tool="Agent", raw={"tool_input": {"subagent_type": "james"}})
    result = require_subagent_model(e, {})
    assert isinstance(result, Verdict)
    assert result.outcome == "warn"


def test_require_subagent_model_allows_when_model_set():
    e = Event(
        event="PreToolUse",
        tool="Agent",
        raw={"tool_input": {"subagent_type": "james", "model": "haiku"}},
    )
    assert require_subagent_model(e, {}) is None


def test_require_subagent_model_exempts_forks():
    e = Event(event="PreToolUse", tool="Agent", raw={"tool_input": {"subagent_type": "fork"}})
    assert require_subagent_model(e, {}) is None


def test_require_subagent_model_ignores_other_tools():
    e = Event(event="PreToolUse", tool="Bash", raw={"tool_input": {"command": "ls"}})
    assert require_subagent_model(e, {}) is None


def test_require_subagent_model_ignores_non_pretooluse_events():
    e = Event(event="PostToolUse", tool="Agent", raw={"tool_input": {}})
    assert require_subagent_model(e, {}) is None


def test_require_subagent_model_tolerates_missing_tool_input():
    e = Event(event="PreToolUse", tool="Agent", raw={})
    result = require_subagent_model(e, {})
    assert isinstance(result, Verdict)
    assert result.outcome == "warn"


def test_require_subagent_model_is_stateless_state_untouched():
    e = Event(event="PreToolUse", tool="Agent", raw={"tool_input": {"subagent_type": "james"}})
    state = {}
    require_subagent_model(e, state)
    assert state == {}
