"""Tests for Reflexes evaluator gate and configuration integration (reflexes-cope plugin)."""

from __future__ import annotations

import sys
from pathlib import Path

pkg_root = Path(__file__).resolve().parent.parent
if str(pkg_root) not in sys.path:
    sys.path.insert(0, str(pkg_root))

from reflexes.config import load_config
from hooks.gates.reflexes_evaluator import evaluate_cope_policy, reflexes_evaluator

try:
    from gates.event import Event
    from gates.verdict import Verdict, deny, warn
except ImportError:
    from aops.hooks.gates.event import Event
    from aops.hooks.gates.verdict import Verdict, deny, warn


def test_evaluator_config_loading():
    config = load_config()
    assert config.evaluator_model == "claude-3-5-haiku-20241022"
    assert config.evaluator_provider == "anthropic"
    assert config.fail_open is True


def test_fail_open_on_exception(capsys, monkeypatch):
    def faulting_evaluator(slug, event, model):
        raise RuntimeError("Evaluator endpoint unreachable / timeout")

    monkeypatch.setattr(
        "hooks.gates.reflexes_evaluator.evaluate_cope_policy", faulting_evaluator
    )

    event = Event(event="PreToolUse", tool="Bash", command="ls", session_id="test-session")
    verdict = reflexes_evaluator(event, {})
    assert verdict is None

    captured = capsys.readouterr()
    assert "reflexes_evaluator: evaluation error:" in captured.err
    assert "failing open (allow)" in captured.err


def test_unmatched_event_returns_none():
    event = Event(event="UnknownEvent", session_id="test-session")
    verdict = reflexes_evaluator(event, {})
    assert verdict is None


def test_advisory_only_verdict_propagation(monkeypatch):
    mock_verdict = deny("CoPE policy violation detected: BE-01")

    def mock_evaluator(slug, event, model):
        return mock_verdict

    monkeypatch.setattr(
        "hooks.gates.reflexes_evaluator.evaluate_cope_policy", mock_evaluator
    )

    event = Event(event="PreToolUse", tool="Bash", command="tail -f /var/log/syslog")
    verdict = reflexes_evaluator(event, {})
    assert verdict is not None
    assert verdict.outcome == "warn"
    assert "CoPE policy violation" in verdict.inject_text
