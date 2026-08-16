"""The dispatch-completion notification: one line, two sinks, never fatal."""

import json
import os
import urllib.request
from pathlib import Path

CHANNEL_DIR = Path.home() / ".claude" / "channels" / "discord"


def format_line(record: dict) -> str:
    """One short line: what finished, and whether it succeeded."""
    return (
        f"polecat {record['agent']} "
        f"{record['task_id'] or record['session_id']} "
        f"{record['status']} (exit {record['exit_code']}, {record['duration_seconds']}s)"
    )


def _post_discord(line: str) -> None:
    """POST the line to the paired channel. A module-level seam the tests patch."""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        # `/discord:configure` writes one unquoted `DISCORD_BOT_TOKEN=<token>` line.
        env = (CHANNEL_DIR / ".env").read_text()
        token = env.partition("DISCORD_BOT_TOKEN=")[2].partition("\n")[0].strip()
    channel = os.environ.get("DISCORD_CHANNEL_ID")
    if not channel:
        groups = json.loads((CHANNEL_DIR / "access.json").read_text()).get("groups") or {}
        channel = next(iter(groups), "")
    if not (token and channel):
        return
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel}/messages",
        # `--task` reaches the line unsanitized, so parse no mentions out of it.
        data=json.dumps({"content": line, "allowed_mentions": {"parse": []}}).encode(),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            # Discord's edge rejects the default urllib agent with Cloudflare 1010.
            "User-Agent": "DiscordBot (https://github.com/nicsuzor/academicOps, 1.0)",
        },
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
