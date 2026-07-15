"""The two shipped example gates: one stateless, one stateful."""

from gates.block_rm_rf import block_rm_rf
from gates.event import Event
from gates.exit_reflection import exit_reflection_reminder
from gates.verdict import Verdict


def test_block_rm_rf_denies_matching_bash_command():
    e = Event(event="PreToolUse", tool="Bash", command="rm -rf /tmp/x")
    result = block_rm_rf(e, {})
    assert isinstance(result, Verdict)
    assert result.outcome == "deny"


def test_block_rm_rf_allows_other_bash_commands():
    e = Event(event="PreToolUse", tool="Bash", command="ls -la")
    assert block_rm_rf(e, {}) is None


def test_block_rm_rf_ignores_non_bash_tools():
    e = Event(event="PreToolUse", tool="Write", command="rm -rf /tmp/x")
    assert block_rm_rf(e, {}) is None


def test_block_rm_rf_ignores_non_pretooluse_events():
    e = Event(event="PostToolUse", tool="Bash", command="rm -rf /tmp/x")
    assert block_rm_rf(e, {}) is None


def test_block_rm_rf_is_stateless_state_untouched():
    e = Event(event="PreToolUse", tool="Bash", command="rm -rf /tmp/x")
    state = {}
    block_rm_rf(e, state)
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


def test_exit_reflection_ignores_non_stop_events():
    e = Event(event="PreToolUse", session_id="s1")
    assert exit_reflection_reminder(e, {}) is None
