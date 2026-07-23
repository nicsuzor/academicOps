"""The two shipped example gates: one stateless, one stateful."""

from gates.event import Event
from gates.exit_reflection import exit_reflection_reminder
from gates.require_subagent_model import require_subagent_model
from gates.verdict import Verdict


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


def test_exit_reflection_warns_once_per_session():
    e = Event(event="Stop", session_id="s1")
    state = {}
    first = exit_reflection_reminder(e, state)
    assert isinstance(first, Verdict)
    assert first.outcome == "warn"
    assert state["exit_reflection_reminded"] is True

    second = exit_reflection_reminder(e, state)
    assert second is None


def test_exit_reflection_injects_handover_template():
    # The consolidated Stop reminder carries the full handover.md content
    # (formerly injected by router.py's Stop branch), plus the short
    # user-visible line.
    e = Event(event="Stop", session_id="s1")
    result = exit_reflection_reminder(e, {})
    assert "academicOps handover reminder" in result.inject_text
    assert result.user_text


def test_exit_reflection_skips_while_background_tasks_pending():
    # Pending background tasks: no reminder yet, and state stays unmarked so
    # the reminder still fires on the session's next clean Stop.
    e = Event(
        event="Stop",
        session_id="s1",
        raw={"background_tasks": [{"id": "bg1"}]},
    )
    state = {}
    assert exit_reflection_reminder(e, state) is None
    assert state == {}


def test_exit_reflection_ignores_non_stop_events():
    e = Event(event="PreToolUse", session_id="s1")
    assert exit_reflection_reminder(e, {}) is None
