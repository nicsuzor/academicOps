"""Tests for Reflexes evaluator gate and configuration integration."""

from __future__ import annotations

from gates.event import Event
from gates.reflexes_evaluator import evaluate_cope_policy, reflexes_evaluator
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


def test_fail_open_on_exception(capsys, monkeypatch):
    """Verify fail-open contract: backend exception returns None and logs to stderr."""

    def faulting_evaluator(slug, event, model):
        raise RuntimeError("Evaluator endpoint unreachable / timeout")

    monkeypatch.setattr("gates.reflexes_evaluator.evaluate_cope_policy", faulting_evaluator)

    event = Event(event="PreToolUse", tool="Bash", command="ls", session_id="test-session")
    verdict = reflexes_evaluator(event, {})
    assert verdict is None

    captured = capsys.readouterr()
    assert "reflexes_evaluator: evaluation error:" in captured.err
    assert "failing open (allow)" in captured.err


def test_unmatched_event_returns_none():
    """Verify events without policy triggers return None without error."""
    event = Event(event="UnknownEvent", session_id="test-session")
    verdict = reflexes_evaluator(event, {})
    assert verdict is None


def test_evaluator_verdict_propagation(monkeypatch):
    """Verify evaluator verdicts propagate when returned."""
    mock_verdict = deny("CoPE policy violation detected: BE-01")

    def mock_evaluator(slug, event, model):
        return mock_verdict

    monkeypatch.setattr("gates.reflexes_evaluator.evaluate_cope_policy", mock_evaluator)

    event = Event(event="PreToolUse", tool="Bash", command="tail -f /var/log/syslog")
    verdict = reflexes_evaluator(event, {})
    assert verdict == mock_verdict
