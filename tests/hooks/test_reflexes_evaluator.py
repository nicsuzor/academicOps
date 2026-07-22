"""Tests for Reflexes evaluator gate and configuration integration."""

from __future__ import annotations

from gates.event import Event
from gates.reflexes_evaluator import reflexes_evaluator, set_evaluator_backend
from gates.registry import GATES
from gates.verdict import deny

from aops.reflexes.config import load_config


def test_registry_contains_reflexes_evaluator():
    """Verify reflexes_evaluator is registered in GATES alongside existing gates."""
    assert reflexes_evaluator in GATES
    assert len(GATES) == 4


def test_evaluator_config_loading():
    """Verify evaluator configuration loads and specifies cheapest model."""
    config = load_config()
    assert config.evaluator_model == "claude-3-5-haiku-20241022"
    assert config.evaluator_provider == "anthropic"
    assert config.fail_open is True


def test_fail_open_on_exception(capsys):
    """Verify fail-open contract: backend exception returns None and logs to stderr."""

    def faulting_backend(e, policies, config):
        raise RuntimeError("Evaluator endpoint unreachable / timeout")

    set_evaluator_backend(faulting_backend)
    try:
        event = Event(event="PreToolUse", tool="Bash", command="ls", session_id="test-session")
        verdict = reflexes_evaluator(event, {})
        assert verdict is None

        captured = capsys.readouterr()
        assert "reflexes_evaluator: policy evaluation raised" in captured.err
        assert "failing open (allow)" in captured.err
    finally:
        set_evaluator_backend(None)


def test_unmatched_event_returns_none():
    """Verify events without policy triggers return None without error."""
    event = Event(event="UnknownEvent", session_id="test-session")
    verdict = reflexes_evaluator(event, {})
    assert verdict is None


def test_evaluator_backend_verdict_propagation():
    """Verify custom/mock evaluator backend verdicts propagate when returned."""
    mock_verdict = deny("CoPE policy violation detected: BE-01")

    def mock_backend(e, policies, config):
        assert len(policies) > 0
        return mock_verdict

    set_evaluator_backend(mock_backend)
    try:
        event = Event(event="PreToolUse", tool="Bash", command="tail -f /var/log/syslog")
        verdict = reflexes_evaluator(event, {})
        assert verdict == mock_verdict
    finally:
        set_evaluator_backend(None)
