#!/usr/bin/env python3
"""
Unified hook logger for Claude Code and Gemini CLI.

Logs ALL hook events to:
1. Session state file (operational metrics via SessionState)
2. Per-session JSONL hook log (audit trail)
"""

import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any

import psutil
from lib.gate_model import GateResult
from lib.session_paths import get_hook_log_path
from lib.session_state import SessionState

from hooks.internal_models import HookLogEntry
from hooks.schemas import CanonicalHookOutput, HookContext

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _json_serializer(obj: Any) -> str:
    """Convert non-serializable objects to strings for JSON serialization."""
    return str(obj)


def log_hook_event(
    ctx: HookContext,
    output: CanonicalHookOutput | None = None,
    exit_code: int = 0,
) -> None:
    """
    Log a hook event to the per-session hooks log file.
    """
    session_id = ctx.session_id
    # Fail-safe: empty session_id = skip (don't crash hook)
    if not session_id or session_id == "unknown":
        return

    try:
        # Build per-session hook log path
        input_data = ctx.raw_input
        date = input_data.get("date")
        if date is None:
            date = datetime.now(UTC).strftime("%Y-%m-%d")

        log_path = get_hook_log_path(session_id, input_data, date)

        # Gather process metrics
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()

        # Create log entry from superclass fields + new metadata
        log_entry = HookLogEntry(
            session_id=session_id,
            logged_at=datetime.now().astimezone().replace(microsecond=0).isoformat(),
            exit_code=exit_code,
            output=output.model_dump() if output else None,
            **ctx.model_dump(exclude={"framework_content", "session_id"}),
        )

        # Add debug metrics to metadata
        log_dict = log_entry.model_dump()
        log_dict["debug"] = {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "mem_rss_mb": mem_info.rss / (1024 * 1024),
            "mem_vms_mb": mem_info.vms / (1024 * 1024),
            "process_uptime": time.time() - process.create_time(),
        }

        # Append to JSONL file
        with log_path.open("a") as f:
            json.dump(
                log_dict,
                f,
                separators=(",", ":"),
                default=_json_serializer,
            )
            f.write("\n")

    except Exception as e:
        # Log error to stderr but don't crash the hook
        print(f"[unified_logger] Error logging hook event: {e}", file=sys.stderr)


def log_event_to_session(
    session_id: str, hook_event: str, input_data: dict[str, Any], state: SessionState | None = None
) -> GateResult | None:
    """Update session state for a hook event.

    This is now a thin wrapper. Most state logic is in Gates.
    We might update basic metrics here if needed, or rely on Gates.
    For now, we keep it as a no-op placeholder for the registry if called.

    Args:
        session_id: Session ID
        hook_event: Name of the hook event
        input_data: Full input data from the hook
        state: SessionState object (optional, if passed by new router)

    Returns:
        None
    """
    # Logic moved to Gate implementations (HydrationGate, CustodietGate, etc.)
    return None
