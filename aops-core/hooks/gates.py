"""
Gate Configuration - DEPRECATED.

This module previously contained ACTIVE_GATES but that was never used.
All gate configuration is now in gate_config.py.

This file is kept for backwards compatibility and re-exports from gate_config.
"""

# Re-export everything from gate_config for backwards compatibility
from hooks.gate_config import (
    TOOL_CATEGORIES,
    TOOL_GATE_REQUIREMENTS,
    GATE_EXECUTION_ORDER,
    MAIN_AGENT_ONLY_GATES,
    GATE_MODE_DEFAULTS,
    GATE_MODE_ENV_VARS,
    get_tool_category,
    get_required_gates,
    get_gates_for_event,
    is_main_agent_only,
)

__all__ = [
    "TOOL_CATEGORIES",
    "TOOL_GATE_REQUIREMENTS",
    "GATE_EXECUTION_ORDER",
    "MAIN_AGENT_ONLY_GATES",
    "GATE_MODE_DEFAULTS",
    "GATE_MODE_ENV_VARS",
    "get_tool_category",
    "get_required_gates",
    "get_gates_for_event",
    "is_main_agent_only",
]
