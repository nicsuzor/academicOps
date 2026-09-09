"""pkb hook handlers."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from dispatch import HookContext, Result, load_message_pair, warn

log = logging.getLogger("pkb.handlers")

Handler = Callable[[HookContext], Result | None]


def honest_output(ctx: HookContext) -> Result | None:
    """Remind agents to present substantiating evidence with their claims."""
    if ctx.agent_type in (
        "aops:ida",
        "aops:james",
        "orchestrate:james",
        "pkb:ida",
    ) or (ctx.agent_type and ctx.agent_type.endswith((":ida", ":james"))):
        return None

    if ctx.raw.get("background_tasks"):
        return None

    return warn(*load_message_pair(ctx.hooks_dir, "honesty"))


def _find_pkb_bin(cwd: str | Path | None = None) -> str | None:
    pkb_bin = shutil.which("pkb")
    if pkb_bin:
        return pkb_bin
    candidates: list[Path] = []
    if cwd:
        candidates.append(Path(cwd) / "pkb")
    candidates.append(Path.cwd() / "pkb")
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
    return None


def _run_pkb_search(prompt: str, cwd: str | Path | None = None) -> str | None:
    query = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", prompt).strip()[:200]
    if not query:
        return None
    pkb_bin = _find_pkb_bin(cwd)
    if not pkb_bin:
        log.warning("pkb binary not found for UserPromptSubmit hook")
        return None
    try:
        env = dict(os.environ)
        env["NO_COLOR"] = "1"
        proc = subprocess.run(
            [pkb_bin, "search", query],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(cwd) if cwd and Path(cwd).is_dir() else None,
            env=env,
        )
        if proc.returncode == 0:
            out = proc.stdout.strip()
            out = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", out).strip()
            if out:
                return out
        else:
            log.warning("pkb search exited with returncode %s: %s", proc.returncode, proc.stderr)
    except Exception as exc:
        log.warning("pkb search execution failed: %s", exc)
    return None


def search_the_pkb(ctx: HookContext) -> Result | None:
    """Ground every prompt in the PKB before the agent acts on it.

    Tries first to return the output of `pkb search {prompt:200}` wrapped in
    `<academicOps PKB search results>` tags; if that fails, returns the
    existing messages.
    """
    # Ida is COO and commissions graph operations to Pauli; suppress unprompted snippets
    if ctx.agent_type in (
        "aops:ida",
        "pkb:ida",
        "ida",
        "ida:ida",
    ) or (ctx.agent_type and ctx.agent_type.endswith(":ida")):
        return None

    raw_prompt = ctx.raw.get("prompt")
    if raw_prompt is None and hasattr(ctx, "prompt"):
        raw_prompt = ctx.prompt
    if isinstance(raw_prompt, dict):
        raw_prompt = raw_prompt.get("text") or raw_prompt.get("content") or ""
    prompt_str = str(raw_prompt or "").strip()

    if prompt_str:
        output = _run_pkb_search(prompt_str, cwd=ctx.cwd)
        if output:
            msg = f"<academicOps PKB search results>\n{output}\n</academicOps PKB search results>"
            return warn(msg)

    return honest_output(ctx)


HANDLERS: dict[str, list] = {
    "UserPromptSubmit": [search_the_pkb],
}
