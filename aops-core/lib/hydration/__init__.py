"""Hydration module - context building for prompt hydration.

This module provides utilities for building hydration context and checking
whether a prompt should skip hydration. It is imported by gates (lib/gates/)
to avoid circular dependencies with hooks/.
"""

from lib.hydration.builder import build_hydration_instruction
from lib.hydration.skip_check import should_skip_hydration

__all__ = ["build_hydration_instruction", "should_skip_hydration"]
