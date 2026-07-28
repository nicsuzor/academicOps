"""Result: what a handler has to say about one hook event.

There are two shapes, and the distinction between them is load-bearing.

An **advisory** (``warn``) is text injected into the agent's context. Nothing
in-session blocks on a rule verdict (specs/ARCHITECTURE.md, Enforcement) — real
enforcement is a separate merge-stage check, and ``autoMode`` and ``cope`` both
run advisory-only, on purpose.

A **refusal** (``refuse``) blocks the call, and is reserved for exactly one
thing: *structural impossibility*. The session, as configured, physically
cannot carry the call out, so letting it through produces a hang rather than an
outcome. The only instance is an interactive prompt in a headless session —
nobody is there to answer, so the call never returns.

Refusal is never a rule verdict. "This looks non-compliant", "an axiom says not
to", "this is unwise", "the agent should do X first" are all advisories, however
confident the handler is. If the reason names a rule, or contains *should* or
*must not*, it is a ``warn``. The test is not how bad the call is; it is
whether the call can succeed at all.

A handler returns ``None`` (nothing to say), a ``warn``, or a ``refuse``.
``merge`` combines every handler's results for one event: a refusal wins over
any advisory, whatever the registration order — a session that cannot proceed
must not have that fact hidden behind an earlier suggestion — and within one
kind the first wins, with handler registration order as the tiebreak.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    inject_text: str  # injected into the agent's context; the reason, on a refusal
    user_text: str | None = None  # optional short line shown to the user
    is_refusal: bool = False  # structural impossibility ONLY — see the module docstring


def warn(message: str, user_text: str | None = None) -> Result:
    """Surface ``message`` to the agent as a non-blocking advisory."""
    return Result(message, user_text)


def refuse(reason: str, user_text: str | None = None) -> Result:
    """Block the call: this session structurally cannot carry it out.

    Not for rule compliance, and not for judgment about whether the call is a
    good idea — see the module docstring. ``reason`` reaches the agent as the
    denial reason, so it must say what is impossible here and what to do
    instead.
    """
    return Result(reason, user_text, is_refusal=True)


def merge(results: list[Result | None]) -> Result | None:
    """A refusal beats any advisory; within one kind, the first wins."""
    present = [r for r in results if r is not None]
    for r in present:
        if r.is_refusal:
            return r
    return present[0] if present else None
