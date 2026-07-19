"""Verdict: the three-outcome result of a gate.

allow (``None``) < warn(msg) < deny(reason). A gate returns ``None`` to allow,
or a ``Verdict`` to warn or deny. One merge rule: deny beats warn beats allow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Outcome = Literal["warn", "deny"]


@dataclass(frozen=True)
class Verdict:
    outcome: Outcome
    inject_text: str
    user_text: str | None


def warn(message: str) -> Verdict:
    """Non-blocking: surface ``message`` to the agent, let it proceed."""
    return Verdict("warn", message)


def deny(reason: str) -> Verdict:
    """Blocking: refuse the action, tell the agent why."""
    return Verdict("deny", reason)


_RANK: dict[Outcome, int] = {"warn": 1, "deny": 2}


def merge(verdicts: list[Verdict | None]) -> Verdict | None:
    """Merge every gate's verdict: deny > warn > allow (``None``).

    Ties at the same outcome keep the first verdict seen, so gate order in
    the registry is a stable tiebreak.
    """
    result: Verdict | None = None
    for v in verdicts:
        if v is None:
            continue
        if result is None or _RANK[v.outcome] > _RANK[result.outcome]:
            result = v
    return result
