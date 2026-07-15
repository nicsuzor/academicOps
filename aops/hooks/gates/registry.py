"""The gate registry: a plain list. Register a gate by appending to it."""

from __future__ import annotations

from .block_rm_rf import block_rm_rf
from .exit_reflection import exit_reflection_reminder

GATES = [
    block_rm_rf,
    exit_reflection_reminder,
]
