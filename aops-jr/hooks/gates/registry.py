"""The gate registry: a plain list. Register a gate by appending to it."""

from __future__ import annotations

from .require_subagent_model import require_subagent_model

GATES = [
    require_subagent_model,
]
