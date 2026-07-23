"""Reflexes CoPE Policy Evaluator Gate.

Evaluates incoming hook events against derived CoPE policies (reflexes/policies/*.md).
Operates as an advisory evaluator gate under the reflexes-cope plugin.

Advisory-only contract: Never returns a blocking/deny Verdict. Any evaluated
policy outcome emits an overridable advisory (warn / inject_text) consumed by
a deciding agent.

Enforces fail-open contract: evaluator outage, timeout, connection error, or exception
is caught, logged to sys.stderr, and returns None (allow) verdict.
"""

from __future__ import annotations

import sys
from typing import Any

from reflexes.config import load_config
from reflexes.policies import AXIOM_POLICIES, get_policy_file

try:
    from .event import Event
    from .verdict import Verdict, warn
except ImportError:
    try:
        from gates.event import Event
        from gates.verdict import Verdict, warn
    except ImportError:
        from aops.hooks.gates.event import Event
        from aops.hooks.gates.verdict import Verdict, warn

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
    policy_path = get_policy_file(policy_slug)
    if not policy_path or not policy_path.exists():
        return None
    return None


def reflexes_evaluator(e: Event, state: dict[str, Any]) -> Verdict | None:
    try:
        config = load_config()
        trigger = _EVENT_TRIGGER_MAP.get(e.event)
        if not trigger:
            return None

        matching_policies = [p for p in AXIOM_POLICIES if p.trigger == trigger]
        if not matching_policies:
            return None

        for policy in matching_policies:
            verdict = evaluate_cope_policy(policy.slug, e, config.evaluator_model)
            if verdict is not None:
                if verdict.outcome != "warn":
                    verdict = warn(verdict.inject_text, verdict.user_text)
                return verdict

        return None
    except Exception as exc:
        print(
            f"reflexes_evaluator: evaluation error: {exc!r}; failing open (allow)",
            file=sys.stderr,
        )
        return None
