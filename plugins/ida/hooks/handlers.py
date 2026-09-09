"""ida hook handlers."""

from __future__ import annotations

from collections.abc import Callable

from citation_enforcement import citation_enforcement_gate
from dispatch import HookContext, Result
from premise_check_gate import premise_check_handler
from scratchpad_gate import scratchpad_write_gate

Handler = Callable[[HookContext], Result | None]

HANDLERS: dict[str, list] = {
    "PreToolUse": [scratchpad_write_gate, premise_check_handler],
    "Stop": [citation_enforcement_gate],
    # "PostToolBatch": [premise_check_arm],
}
