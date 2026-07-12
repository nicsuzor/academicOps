#!/usr/bin/env -S uv run python
"""
Unified hook logger for Claude Code and Gemini CLI.

Logs ALL hook events to:
1. Session state file (operational metrics via SessionState)
2. Per-session JSONL hook log (audit trail)
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
from lib.hook_context import HookContext
from lib.session_paths import get_hook_log_path

from hooks.internal_models import HookLogEntry
from hooks.schemas import CanonicalHookOutput, ResolvedDecision

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _json_serializer(obj: Any) -> str:
    """Convert non-serializable objects to strings for JSON serialization."""
    return str(obj)


def _fallback_log_path() -> Path:
    """Global sink for hook events with no resolvable session_id.

    ``get_hook_log_path`` needs a real session_id to build the per-session
    on-disk anchor (short-hash filename); it cannot place an event that has
    none. Previously ``log_hook_event`` just returned in that case, silently
    dropping the event — invisible in exactly the scenario (a crash before
    ``normalize_input`` could resolve a session_id) where the log is most
    needed (aops_2597b5ff scope D, item 2). This is a single flat file, not
    the per-session naming scheme, since there is no session to anchor to.
    ``AOPS_HOOK_FALLBACK_LOG`` overrides it (tests; operator debugging).
    """
    override = os.environ.get("AOPS_HOOK_FALLBACK_LOG")
    path = Path(override) if override else Path.home() / ".claude" / "hooks-fallback.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def log_hook_event(
    ctx: HookContext,
    output: CanonicalHookOutput | None = None,
    resolved: ResolvedDecision | None = None,
    exit_code: int = 0,
    error: str | None = None,
) -> None:
    """
    Log a hook event to the per-session hooks log file.

    ``output`` is the gate layer's internal ``CanonicalHookOutput`` (the true
    gate verdict). ``resolved`` is the ``ResolvedDecision`` produced by
    ``resolve_policy()`` AFTER all verdict-changing policy has run — logging
    both together means the entry shows both "what the gates decided" and
    "what will actually be sent to the client", with nothing lost in between.
    Callers are responsible for wrapping this call in its own try/except: a
    logging failure must never be the reason a hook fails to deliver its real
    payload to the client.
    """
    session_id = ctx.session_id
    # A missing/"unknown" session_id can't anchor the per-session filename
    # (get_hook_log_path needs a real short-hash) — route to the global
    # fallback sink instead of dropping the event. This is the narrow gap:
    # normalize_input() always synthesizes a non-"unknown" id
    # ("unknown-<uuid>") for the NORMAL pipeline, so this path is reached
    # only by main()'s crash handler (ctx built before normalize_input ran)
    # or a direct/test caller — exactly the case where losing the log entry
    # would hide a real router failure (aops_2597b5ff scope D, item 2).
    session_id_missing = not session_id or session_id == "unknown"

    if session_id_missing:
        log_path = _fallback_log_path()
    else:
        # Path resolution — fail fast (no silent swallowing)
        date = ctx.raw_input.get("date")
        if date is None:
            date = datetime.now().astimezone().strftime("%Y-%m-%d")

        log_path = get_hook_log_path(
            session_id, transcript_path=ctx.transcript_path, date=date, client_type=ctx.client_type
        )

    # Process metrics — best-effort (psutil may fail in sandboxed envs)
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        debug_metrics = {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "mem_rss_mb": mem_info.rss / (1024 * 1024),
            "mem_vms_mb": mem_info.vms / (1024 * 1024),
            "process_uptime": time.time() - process.create_time(),
        }
    except Exception:
        debug_metrics = {"pid": os.getpid(), "ppid": os.getppid()}

    # Build and write entry — fail fast
    log_entry = HookLogEntry(
        session_id=session_id,
        logged_at=datetime.now().astimezone().replace(microsecond=0).isoformat(),
        exit_code=exit_code,
        output=output.model_dump() if output else None,
        resolved=resolved.model_dump() if resolved else None,
        **ctx.model_dump(exclude={"session_id"}),
    )

    log_dict = log_entry.model_dump()
    log_dict["debug"] = debug_metrics
    if error:
        log_dict["error"] = error
    if session_id_missing:
        log_dict["session_id_missing"] = True

    with log_path.open("a") as f:
        json.dump(
            log_dict,
            f,
            separators=(",", ":"),
            default=_json_serializer,
        )
        f.write("\n")
