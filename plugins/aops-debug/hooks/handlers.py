"""aops-debug hook handlers.

A purely debugging plugin that intercepts and logs all canonical and unmapped
events sent to the framework.
"""

from __future__ import annotations

from dispatch import HookContext, Result


def dump_payload(ctx: HookContext) -> Result | None:
    """Debug hook: dump the raw payload to a temp file."""
    import json
    import os
    import tempfile

    # Use session_id so we don't conflict across concurrent sessions,
    # but still keep all events for a single session in one file.
    ident = ctx.session_id or str(os.getpid())
    temp_dir = tempfile.gettempdir()
    os.mkdirs(temp_dir, exist_ok=True)
    log_path = os.path.join(temp_dir, f"aops_debug_hooks_{ident}.jsonl")

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ctx.raw) + "\n")
    except OSError:
        pass
    return None


HANDLERS: dict[str, list] = {"*": [dump_payload]}
