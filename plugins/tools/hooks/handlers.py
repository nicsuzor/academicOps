"""tools hook handlers."""

from __future__ import annotations

from pathlib import Path

from dispatch import HookContext, Result, warn


def session_start(ctx: HookContext) -> Result | None:
    core_path = (
        ctx.hooks_dir.parent
        if ctx.hooks_dir and str(ctx.hooks_dir) != "."
        else Path(__file__).resolve().parent.parent
    ) / "CORE.md"
    if core_path.is_file():
        content = core_path.read_text(encoding="utf-8").strip()
        if content:
            return warn(content)
    return None


HANDLERS: dict[str, list] = {
    "SessionStart": [session_start],
}
