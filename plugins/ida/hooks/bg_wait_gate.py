#!/usr/bin/env python3
"""Stop gate: a headless session may not end while its background Bash job runs.

In an interactive session, ending a turn while a ``run_in_background`` Bash
command is still running is safe: the completion notification re-invokes the
agent. In a headless session (``claude -p``, the Agent SDK) the run ends with
the turn, so the notification never arrives, the process exits 0, and the
claimed task stays ``in_progress`` with nothing verified (academicOps#2750).

``bg_wait_gate`` reads the session transcript, finds every background Bash job
the session launched, drops the ones that have reported back or whose output
file carries the ``[exited with code N]`` trailer, and blocks the stop while
any remain. The block reason tells the agent to wait for them and finish.

It fires on continuation stops too (``fires_on_continuation``): a second
text-only stop while the job still runs is the same failure. ``_MAX_BLOCKS``
consecutive blocks bound the loop if the agent never waits.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from dispatch import HookContext, Result, block, warn

# Entry points with no one to re-invoke the agent after its turn ends.
_HEADLESS_ENTRYPOINTS = ("sdk-cli", "sdk-ts", "sdk-py")

_MAX_BLOCKS = 20

_BACKGROUND_TOOLS = ("Bash",)

_NOTIFICATION_RE = re.compile(
    r"<task-notification>.*?<task-id>([^<]+)</task-id>.*?<status>([^<]+)</status>",
    re.DOTALL,
)
_OUTPUT_PATH_RE = re.compile(r"Output is being written to: (\S+?\.output)")
_EXIT_TRAILER = "[exited with code"


def is_headless() -> bool:
    """True when ending the turn ends the run.

    ``AOPS_BG_WAIT_GATE=1``/``0`` forces the gate on or off.
    """
    override = os.environ.get("AOPS_BG_WAIT_GATE", "").strip().lower()
    if override in ("1", "on", "true"):
        return True
    if override in ("0", "off", "false"):
        return False
    return os.environ.get("CLAUDE_CODE_ENTRYPOINT", "") in _HEADLESS_ENTRYPOINTS


def _tool_result_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


def _has_exited(output_file: str) -> bool:
    """True if the job's output file ends with Claude Code's exit trailer.

    A missing or unreadable file counts as exited: the gate blocks only on
    positive evidence that the job is still running.
    """
    if not output_file:
        return False
    try:
        with open(output_file, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 512))
            tail = f.read().decode("utf-8", "replace")
    except OSError:
        return True
    return _EXIT_TRAILER in tail


def pending_background_jobs(transcript_path: str) -> list[dict[str, str]]:
    """Background Bash jobs launched in this transcript that are still running."""
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    tool_names: dict[str, str] = {}
    commands: dict[str, str] = {}
    launched: dict[str, dict[str, str]] = {}
    finished: set[str] = set()

    for line in lines:
        for task_id, _status in _NOTIFICATION_RE.findall(line):
            finished.add(task_id.strip())
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict) or entry.get("isSidechain"):
            continue
        message = entry.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use":
                tool_names[item.get("id", "")] = item.get("name", "")
                tool_input = item.get("input")
                if isinstance(tool_input, dict):
                    commands[item.get("id", "")] = str(tool_input.get("command", ""))
            elif item.get("type") == "tool_result":
                result = entry.get("toolUseResult")
                task_id = result.get("backgroundTaskId") if isinstance(result, dict) else None
                use_id = item.get("tool_use_id", "")
                if not task_id or tool_names.get(use_id) not in _BACKGROUND_TOOLS:
                    continue
                match = _OUTPUT_PATH_RE.search(_tool_result_text(item.get("content")))
                launched[task_id] = {
                    "id": task_id,
                    "output_file": match.group(1) if match else "",
                    "command": commands.get(use_id, ""),
                }

    return [
        job
        for task_id, job in launched.items()
        if task_id not in finished and not _has_exited(job["output_file"])
    ]


# ---------------------------------------------------------------------------
# Consecutive-block counter, so a session that never waits still ends.
# ---------------------------------------------------------------------------


def _state_path(session_id: str) -> Path:
    override = os.environ.get("AOPS_BG_WAIT_GATE_DIR")
    base = Path(override) if override else Path(tempfile.gettempdir()) / "aops_bg_wait_gate"
    base.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", session_id or "default")
    return base / f"{safe}.count"


def _read_count(session_id: str) -> int:
    try:
        return int(_state_path(session_id).read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def _write_count(session_id: str, count: int) -> None:
    try:
        _state_path(session_id).write_text(str(count), encoding="utf-8")
    except OSError:
        pass


def _describe(job: dict[str, str]) -> str:
    command = " ".join(job["command"].split())
    if len(command) > 120:
        command = command[:117] + "..."
    where = f", output `{job['output_file']}`" if job["output_file"] else ""
    return f"- `{job['id']}`{where}: `{command}`"


def bg_wait_gate(ctx: HookContext) -> Result | None:
    if ctx.client != "claude" or not is_headless() or not ctx.transcript_path:
        return None

    pending = pending_background_jobs(ctx.transcript_path)
    if not pending:
        _write_count(ctx.session_id, 0)
        return None

    count = _read_count(ctx.session_id) + 1
    if count > _MAX_BLOCKS:
        _write_count(ctx.session_id, 0)
        return warn(
            f"bg_wait_gate: {len(pending)} background job(s) still running after "
            f"{_MAX_BLOCKS} blocked stops; letting the run end."
        )
    _write_count(ctx.session_id, count)

    jobs = "\n".join(_describe(job) for job in pending)
    return block(
        "This is a headless run: when your turn ends, the run ends. No completion "
        "notification will wake you, and any work after this point will not happen. "
        f"These background jobs are still running:\n{jobs}\n\n"
        "Do not end your turn yet. Wait for each job with a blocking tool call "
        "(for example, Monitor its output file until it ends with "
        "`[exited with code N]`, or a foreground Bash loop that polls for that line). "
        "Then read the result, finish the task, and release it before you stop. "
        "If a job cannot finish, stop it and release the task with the reason.",
        user_text=f"bg_wait_gate: blocked stop; {len(pending)} background job(s) still running",
    )


bg_wait_gate.fires_on_continuation = True  # type: ignore[attr-defined]
