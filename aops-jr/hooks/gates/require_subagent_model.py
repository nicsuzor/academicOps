"""Stateless gate: remind the agent to pin a cheap model on subagent dispatch.

Structural signal only: ``PreToolUse`` + ``tool_name == "Agent"`` + whether
the structured ``tool_input.model`` field is present — never the content of
the dispatched prompt. This directly enforces a documented framework
practice ("If any subagents are spawned, pass them an explicit cheap
model" — see e.g. the multi-agent-review dispatch instructions) the same
way ``router.py``'s real gates key off structured fields like
``tool_name`` and ``background_tasks`` length rather than parsing free text.

``subagent_type == "fork"`` is exempt: a forked agent always inherits the
parent's model (a `model` override is ignored for forks), so there is
nothing meaningful to set.
"""

from __future__ import annotations

import os

from .event import Event
from .verdict import Verdict, warn

_REMINDER = (
    "Dispatching a subagent without an explicit `model` field lets it "
    "inherit an expensive default. Pass a cheap model explicitly for "
    "routine subagent work."
)


def _enabled() -> bool:
    """Read the `require_subagent_model` userConfig knob.

    Same convention as the sibling `AOPS_GATE_STATE_DIR` knob in this same
    plugin (state.py): a plain process env var, defaulting on. Set
    `AOPS_REQUIRE_SUBAGENT_MODEL=false` to disable the reminder.
    """
    return os.environ.get("AOPS_REQUIRE_SUBAGENT_MODEL", "true").strip().lower() not in (
        "false",
        "0",
        "no",
    )


def require_subagent_model(e: Event, state: dict) -> Verdict | None:
    if not _enabled():
        return None
    if e.event != "PreToolUse" or e.tool != "Agent":
        return None
    tool_input = e.raw.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    if tool_input.get("subagent_type") == "fork":
        return None
    if not tool_input.get("model"):
        return warn(_REMINDER)
    return None
