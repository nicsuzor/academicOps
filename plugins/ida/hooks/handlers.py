"""ida hook handlers."""

from __future__ import annotations

from collections.abc import Callable

from dispatch import HookContext, Result
from premise_check_gate import premise_check_handler

Handler = Callable[[HookContext], Result | None]

HANDLERS: dict[str, list] = {
    "PreToolUse": [premise_check_handler],
    "Stop": [],
    # "PostToolBatch": [premise_check_arm],
}
