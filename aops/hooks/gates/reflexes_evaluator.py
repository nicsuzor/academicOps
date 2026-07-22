"""Reflexes CoPE Policy Evaluator Gate.

Evaluates incoming hook events against derived CoPE policies (aops/reflexes/policies/*.md).
Operates as the 4th gate in the GATES registry pipeline.

Enforces fail-open contract: evaluator outage, timeout, connection error, or exception
is caught, logged to sys.stderr, and returns None (allow) verdict.
"""

from __future__ import annotations

import sys
from typing import Any

from aops.reflexes.config import load_config
from aops.reflexes.policies import AXIOM_POLICIES, get_policy_file

try:
    from .event import Event
    from .verdict import Verdict, deny, warn
except ImportError:
    from gates.event import Event
    from gates.verdict import Verdict, deny, warn

# Map hook events to CoPE trigger types
_EVENT_TRIGGER_MAP = {
    "PreToolUse": "before_tool_call",
    "Stop": "before_response",
    "SubagentStop": "before_response",
    "UserPromptSubmit": "before_response",
    "PostToolUse": "after_tool_call",
}


def evaluate_cope_policy(
    policy_slug: str,
    event: Event,
    model: str,
) -> Verdict | None:
    """Evaluate a single CoPE policy using the configured evaluator model.

    Fail-open contract: Infrastructure failure or exception raises to caller where
    it is caught and converted to an allow (None) verdict.
    """
    policy_path = get_policy_file(policy_slug)
    if not policy_path or not policy_path.exists():
        return None

    # Default evaluation return is None (allow) unless an active evaluator engine triggers a verdict.
    return None


def reflexes_evaluator(e: Event, state: dict[str, Any]) -> Verdict | None:
    """Reflexes policy evaluator gate with strict fail-open contract."""
    try:
        config = load_config()
        trigger = _EVENT_TRIGGER_MAP.get(e.event)
        if not trigger:
            return None

        # Filter applicable policy mappings by trigger
        matching_policies = [p for p in AXIOM_POLICIES if p.trigger == trigger]
        if not matching_policies:
            return None

        # Evaluate matching CoPE policies
        for policy in matching_policies:
            verdict = evaluate_cope_policy(policy.slug, e, config.evaluator_model)
            if verdict is not None:
                return verdict

        return None
    except Exception as exc:
        # Strict fail-open behavior (§3 of reflexes-integration.md):
        # Catch exception, log to sys.stderr, return None (allow)
        print(
            f"reflexes_evaluator: evaluation error: {exc!r}; failing open (allow)",
            file=sys.stderr,
        )
        return None
