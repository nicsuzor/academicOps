"""One-line dispatch-completion notification: Discord, plus an appended log file.

Deliberately minimal. It formats a single line from the run record and writes it
to two places. Nothing here may ever break or block a dispatch, so every failure
is swallowed.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

CHANNEL_DIR = Path.home() / ".claude" / "channels" / "discord"


def _discord_config() -> tuple[str, str] | None:
    """Bot token and channel id, from the environment or the provisioned files."""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        for raw in (CHANNEL_DIR / ".env").read_text().splitlines():
            key, _, value = raw.partition("=")
            if key.strip() == "DISCORD_BOT_TOKEN":
                token = value.strip().strip("\"'")
    channel = os.environ.get("DISCORD_CHANNEL_ID")
    if not channel:
        groups = json.loads((CHANNEL_DIR / "access.json").read_text()).get("groups") or {}
        channel = next(iter(groups), "")
    return (token, channel) if token and channel else None


def format_line(record: dict) -> str:
    """One short line: what finished, and whether it succeeded."""
    seconds = record.get("duration_seconds")
    duration = f", {int(seconds)}s" if isinstance(seconds, int | float) else ""
    return (
        f"polecat {record.get('agent') or '?'} "
        f"{record.get('task_id') or record.get('session_id') or '?'} "
        f"{record.get('status') or '?'} (exit {record.get('exit_code')}{duration})"
    )


def _post_discord(line: str) -> None:
    config = _discord_config()
    if not config:
        return
    token, channel = config
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel}/messages",
        data=json.dumps({"content": line}).encode(),
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(request, timeout=10).close()  # noqa: S310


def notify_run_complete(run_record: Path | str, sessions_base: Path | str) -> str | None:
    """Emit the completion line to Discord and append it to the runs log."""
    try:
        record = json.loads(Path(run_record).read_text())
        line = format_line(record)
    except Exception:
        return None
    try:
        log_path = Path(sessions_base) / "state" / "polecat_runs.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as handle:
            handle.write(f"{record.get('ended_at', '')} {line}\n")
    except Exception:
        pass
    try:
        _post_discord(line)
    except Exception:
        pass
    return line
