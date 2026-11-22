"""Modular headless hook handlers for low-context agy agents.

Delivers the canonical handback reminder (`messages/honesty.md`) and the
`premise-check` skill body once per conversation on first `PreInvocation`,
alongside OTel tracing (`agy_tracer`), without loading `CORE.md`, workspace
rules, PKB search, or requiring `PKB_MCP_URL`.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from dispatch import HookContext, Result, load_message_pair, warn
from handlers import (
    _session_pointer_dir,
    agy_post_tool,
    agy_pre_tool,
    agy_stop,
    agy_user_prompt_submit,
)

_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n?", re.DOTALL)


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1).strip()


def _load_premise_check_skill(hooks_dir: Path) -> str:
    plugin_root = (
        hooks_dir.parent
        if hooks_dir and str(hooks_dir) != "."
        else Path(__file__).resolve().parent.parent
    )
    skill_path = plugin_root / "skills" / "premise-check" / "SKILL.md"
    if not skill_path.is_file():
        raise FileNotFoundError(f"headless hook: missing required skill {skill_path}")
    return _strip_frontmatter(skill_path.read_text(encoding="utf-8"))


def headless_handback_reminder(ctx: HookContext) -> Result | None:
    """Deliver `honesty.md` and `premise-check/SKILL.md` once per headless agy conversation."""
    if ctx.client != "agy":
        return None

    if ctx.session_id:
        safe_session = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", ctx.session_id)
        marker = _session_pointer_dir() / f"{safe_session}.headless.delivered"
        if marker.exists():
            return None
        try:
            with marker.open("x", encoding="utf-8") as fh:
                fh.write(datetime.now().astimezone().isoformat())
        except FileExistsError:
            return None

    hooks_dir = (
        ctx.hooks_dir
        if ctx.hooks_dir and str(ctx.hooks_dir) != "."
        else Path(__file__).resolve().parent
    )
    honesty_agent, honesty_user = load_message_pair(hooks_dir, "honesty")
    skill_body = _load_premise_check_skill(hooks_dir)

    parts = [p for p in (honesty_agent, skill_body) if p]
    if not parts:
        return None
    return warn("\n\n".join(parts), honesty_user or honesty_agent or None)


HANDLERS: dict[str, list] = {
    "UserPromptSubmit": [agy_user_prompt_submit, headless_handback_reminder],
    "PreToolUse": [agy_pre_tool],
    "PostToolUse": [agy_post_tool],
    "Stop": [agy_stop],
}
