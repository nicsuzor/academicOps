"""The gate registry: a plain list. Register a gate by appending to it."""

from __future__ import annotations

GATES = []

try:
    from .require_subagent_model import require_subagent_model
    GATES.append(require_subagent_model)
except ImportError:
    pass

try:
    from .exit_reflection import exit_reflection_reminder
    GATES.append(exit_reflection_reminder)
except ImportError:
    pass

try:
    from .require_aops_bot_gh_token import require_aops_bot_gh_token
    GATES.append(require_aops_bot_gh_token)
except ImportError:
    pass


