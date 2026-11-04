"""aops-debug hook handlers.

A purely debugging plugin that intercepts and logs all canonical and unmapped
events sent to the framework.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from dispatch import HookContext, Result

log = logging.getLogger("aops.debug")

_HOOKS_DIR = Path(__file__).resolve().parent
_IDA_HOOKS_DIR = _HOOKS_DIR.parent.parent / "ida" / "hooks"
for _p in (_HOOKS_DIR, _IDA_HOOKS_DIR):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    import claude_code_tracer
except ImportError as exc:
    claude_code_tracer = None
    log.warning("claude_code_tracer did not import (%s) — debug OTel tracing disabled", exc)


def _prepare_tracer_data(ctx: HookContext) -> dict[str, Any]:
    data = dict(ctx.raw) if isinstance(ctx.raw, dict) else {}
    payload_key = "conversationId" if ctx.client == "agy" else "session_id"
    if ctx.session_id:
        data.setdefault(payload_key, ctx.session_id)
        data.setdefault("session_id", ctx.session_id)
    if ctx.cwd:
        data.setdefault("cwd", ctx.cwd)
    if ctx.agent_type:
        data.setdefault("agent_type", ctx.agent_type)
    if ctx.agent_id:
        data.setdefault("agent_id", ctx.agent_id)
    if getattr(ctx, "prompt_id", None):
        data.setdefault("prompt_id", ctx.prompt_id)
    if ctx.tool:
        data.setdefault("tool_name", ctx.tool)
    if ctx.hook_event_name:
        data.setdefault("hook_event_name", ctx.hook_event_name)
    return data


def dump_payload(ctx: HookContext) -> Result | None:
    """Debug hook: dump the raw payload to a temp file and export the full debug trace to OTel."""
    data = _prepare_tracer_data(ctx)
    payload_key = "conversationId" if ctx.client == "agy" else "session_id"
    resolved_session_id = (
        claude_code_tracer.resolve_session_id(data, payload_key, prefer_env=False)
        if claude_code_tracer is not None
        else None
    )

    ident = resolved_session_id or ctx.session_id or str(os.getpid())
    temp_dir = tempfile.gettempdir()
    os.makedirs(temp_dir, exist_ok=True)
    log_path = os.path.join(temp_dir, f"aops_debug_hooks_{ident}.jsonl")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(ctx.raw) + "\n")

    if claude_code_tracer is not None:
        try:
            config = claude_code_tracer.discover_config(data)
            if config is not None:
                claude_code_tracer.emit_debug_hook_span(
                    data,
                    config,
                    client=ctx.client,
                    event=ctx.event,
                    raw_payload=ctx.raw,
                )
        except Exception as exc:
            log.warning("aops-debug OTel trace export failed (%s): %s", ctx.event, exc)

    return None


HANDLERS: dict[str, list] = {"*": [dump_payload]}
