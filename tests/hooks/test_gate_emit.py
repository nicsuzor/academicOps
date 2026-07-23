"""Verdict -> wire format, per event and per client."""

from gates.emit import emit
from gates.event import Event
from gates.verdict import deny, warn


def test_allow_produces_no_output_any_client():
    e = Event(event="PreToolUse", tool="Bash")
    assert emit(None, e, "claude") == {}
    assert emit(None, e, "agy") == {}


def test_claude_pretooluse_deny_uses_permission_decision():
    e = Event(event="PreToolUse", tool="Bash", command="rm -rf /")
    out = emit(deny("nope"), e, "claude")
    assert out == {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "nope",
        }
    }


def test_claude_pretooluse_warn_uses_additional_context_not_permission_decision():
    e = Event(event="PreToolUse", tool="Bash")
    out = emit(warn("careful"), e, "claude")
    assert "permissionDecision" not in out.get("hookSpecificOutput", {})
    assert out["hookSpecificOutput"]["additionalContext"] == "careful"


def test_claude_stop_deny_uses_top_level_decision():
    e = Event(event="Stop")
    out = emit(deny("nope"), e, "claude")
    assert out == {"decision": "block", "reason": "nope"}


def test_claude_posttooluse_deny_uses_top_level_decision():
    e = Event(event="PostToolUse", tool="Write")
    out = emit(deny("nope"), e, "claude")
    assert out == {"decision": "block", "reason": "nope"}


def test_claude_stop_warn_uses_additional_context():
    e = Event(event="Stop")
    out = emit(warn("reflect first"), e, "claude")
    assert out == {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": "reflect first",
        }
    }
    assert "decision" not in out


def test_claude_warn_with_user_text_adds_system_message():
    e = Event(event="Stop")
    out = emit(warn("reflect first", user_text="≡ heads up"), e, "claude")
    assert out["systemMessage"] == "≡ heads up"
    assert out["hookSpecificOutput"]["additionalContext"] == "reflect first"
    assert "decision" not in out


def test_agy_warn_uses_inject_steps():
    e = Event(event="PreInvocation")
    out = emit(warn("careful"), e, "agy")
    assert out == {"injectSteps": [{"ephemeralMessage": "careful"}]}


def test_agy_deny_falls_back_to_context_injection_pending_confirmed_format():
    # No confirmed agy blocking wire format exists yet (tracked as a
    # follow-up); deny degrades to the same non-blocking shape as warn.
    e = Event(event="PreInvocation")
    out = emit(deny("nope"), e, "agy")
    assert out == {"injectSteps": [{"ephemeralMessage": "nope"}]}


def test_emit_unknown_client_raises():
    e = Event(event="Stop")
    try:
        emit(warn("x"), e, "gemini")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown client")
