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

# Measured 2026-09-12 (scripts/measure_pkb_injection.py, n=30 live fires
# across two prompt families): backend search latency p95 ~1.35s, median
# ~1.29s. 5s clears that with >3x margin while cutting the worst-case block
# on a stalled backend from 15s to 5s -- this hook is synchronous ahead of
# every prompt, so a hang here is a hang for the whole turn.
_SEARCH_TIMEOUT_SECONDS = 5

# Same measurement run: payload size for 5 results was 3.5-6.4KB (p95). This
# hook fires on every single UserPromptSubmit -- the highest-frequency
# injection point in the framework -- and had no ceiling of its own,
# inheriting whatever the `pkb` CLI's default result count/format produced.
# Set well above the measured p95 so normal output is never touched; it only
# bites if the backend's output grows unexpectedly large.
_MAX_INJECT_CHARS = 8000
_TRUNCATION_MARKER = "\n[...truncated, output exceeded injection budget...]"


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


def _cap_output(out: str) -> str:
    """Bound injected payload size, independent of what the backend returns.

    A per-turn hook has no natural upper limit from its caller -- the CLI's
    own result count and formatting decide payload size today. This is the
    hook's own ceiling, not a substitute for the backend returning a
    reasonable number of results.
    """
    if len(out) <= _MAX_INJECT_CHARS:
        return out
    cutoff = _MAX_INJECT_CHARS - len(_TRUNCATION_MARKER)
    return out[:cutoff].rstrip() + _TRUNCATION_MARKER


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
            timeout=_SEARCH_TIMEOUT_SECONDS,
            cwd=str(cwd) if cwd and Path(cwd).is_dir() else None,
            env=env,
        )
        if proc.returncode == 0:
            out = proc.stdout.strip()
            out = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", out).strip()
            if out:
                return _cap_output(out)
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
