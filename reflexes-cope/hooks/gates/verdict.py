"""Verdict: the outcome result of a gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Outcome = Literal["warn", "deny"]


@dataclass(frozen=True)
class Verdict:
    outcome: Outcome
    inject_text: str  # injected into the agent's context
    user_text: str | None = None  # optional short line shown to the user


def warn(message: str, user_text: str | None = None) -> Verdict:
    """Non-blocking: surface message to the agent, let it proceed."""
    return Verdict("warn", message, user_text)


def deny(reason: str, user_text: str | None = None) -> Verdict:
    """Blocking: refuse the action, tell the agent why."""
    return Verdict("deny", reason, user_text)


_RANK: dict[Outcome, int] = {"warn": 1, "deny": 2}


def merge(verdicts: list[Verdict | None]) -> Verdict | None:
    result: Verdict | None = None
    for v in verdicts:
        if v is None:
            continue
        if result is None or _RANK[v.outcome] > _RANK[result.outcome]:
            result = v
    return result
