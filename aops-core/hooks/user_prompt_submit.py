#!/usr/bin/env -S uv run python
"""
UserPromptSubmit hook for Claude Code.

Re-exports from lib/hydration/ for backwards compatibility.
Gate logic lives in lib/gates/; hydration skip-check lives in lib/hydration/.
"""

from lib.hydration import should_skip_hydration

__all__ = ["should_skip_hydration"]
