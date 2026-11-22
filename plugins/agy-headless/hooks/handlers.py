"""Hook handlers for isolated low-context headless agy agents.

Delivers the plugin's concise `CORE.md`, canonical handback reminder
(`messages/honesty.md`), and `premise-check` skill body once on `SessionStart`,
alongside OTel tracing (`agy_tracer`) on invocation, tool, and stop events,
without ambient workspace rules, PKB search, or `PKB_MCP_URL`.
"""

from __future__ import annotations

import re
from pathlib import Path

import agy_tracer
from dispatch import HookContext, Result, load_message_pair, warn

_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n?", re.DOTALL)


def _plugin_root(ctx: HookContext) -> Path:
    hooks_dir = (
        ctx.hooks_dir
        if ctx.hooks_dir and str(ctx.hooks_dir) != "."
        else Path(__file__).resolve().parent
    )
    return hooks_dir.parent


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1).strip()


def session_start(ctx: HookContext) -> Result | None:
    """Deliver CORE.md, honesty.md, and premise-check/SKILL.md once on SessionStart."""
    plugin_root = _plugin_root(ctx)
    hooks_dir = plugin_root / "hooks"

    core_path = plugin_root / "CORE.md"
    if not core_path.is_file():
        raise FileNotFoundError(f"agy-headless hook: missing required CORE.md {core_path}")
    core_text = core_path.read_text(encoding="utf-8").strip()
    if not core_text:
        raise ValueError(f"agy-headless hook: required CORE.md is empty: {core_path}")

    honesty_path = hooks_dir / "messages" / "honesty.md"
    if not honesty_path.is_file():
        raise FileNotFoundError(f"agy-headless hook: missing required reminder {honesty_path}")
    honesty_agent, _ = load_message_pair(hooks_dir, "honesty")
    if not honesty_agent:
        raise ValueError(f"agy-headless hook: required reminder is empty: {honesty_path}")

    skill_path = plugin_root / "bundled-skills" / "premise-check" / "SKILL.md"
    if not skill_path.is_file():
        raise FileNotFoundError(f"agy-headless hook: missing required skill {skill_path}")
    skill_body = _strip_frontmatter(skill_path.read_text(encoding="utf-8"))
    if not skill_body:
        raise ValueError(f"agy-headless hook: required skill body is empty: {skill_path}")

    return warn("\n\n".join((core_text, honesty_agent, skill_body)))


HANDLERS: dict[str, list] = {
    "SessionStart": [session_start],
    "UserPromptSubmit": [agy_tracer.pre_invocation_hook],
    "PreToolUse": [agy_tracer.pre_tool_hook],
    "PostToolUse": [agy_tracer.post_tool_hook],
    "Stop": [agy_tracer.stop_hook],
}
