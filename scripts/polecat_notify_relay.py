#!/usr/bin/env python3
"""Polecat Worker Finish Notification Relay.

Drains unacknowledged container completion events from polecat-mcp (or state file)
and delivers structured notifications over the cross-session bus (/tmp/cc-socks/)
to the dispatching agent session (e.g. sara, ida-prime).

Guarantees:
- Every recorded completion event reaches an attached listening session.
- Events are acknowledged ONLY when successfully delivered to a listening session.
- No recorded completion event is prematurely acknowledged or dropped while no listener is attached.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import socket
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [polecat-notify-relay] %(levelname)s: %(message)s",
)
log = logging.getLogger("polecat-notify-relay")


def format_notification(event: dict[str, Any]) -> str:
    """Format structured notification message from a completion event."""
    task_id = event.get("task_id") or "unknown"
    container = event.get("container_name") or event.get("container_id", "unknown")[:12]
    exit_code = event.get("exit_code", 0)
    status = event.get("task_status") or "unknown"
    dispatcher = event.get("dispatcher") or "unknown"

    parts = [
        f"[polecat-exit] task={task_id}",
        f"container={container}",
        f"exit_code={exit_code}",
        f"status={status}",
    ]
    if event.get("unreleased"):
        parts.append("unreleased=true")
    if event.get("pr_url"):
        parts.append(f"pr_url={event['pr_url']}")
    if event.get("duration_s") is not None:
        parts.append(f"duration={event['duration_s']}s")
    if dispatcher and dispatcher != "unknown":
        parts.append(f"dispatcher={dispatcher}")

    return " ".join(parts)


def get_socks_dirs(configured_dir: str | Path | None = None) -> list[Path]:
    """Find candidates for cc-socks directories."""
    dirs: list[Path] = []
    if configured_dir:
        dirs.append(Path(configured_dir))
    env_dir = os.environ.get("CC_SOCKS_DIR")
    if env_dir:
        dirs.append(Path(env_dir))
    dirs.append(Path("/tmp/cc-socks"))

    uid = os.getuid() if hasattr(os, "getuid") else None
    if uid is not None:
        dirs.append(Path(f"/tmp/cc-socks-{uid}"))
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if xdg:
        dirs.append(Path(xdg) / "cc-socks")

    seen = set()
    valid: list[Path] = []
    for d in dirs:
        resolved = str(d.resolve()) if d.exists() else str(d)
        if resolved not in seen:
            seen.add(resolved)
            valid.append(d)
    return valid


def find_target_sockets(socks_dir: str | Path, dispatcher: str) -> list[Path]:
    """Resolve target socket paths on socks_dir matching the dispatcher."""
    sd = Path(socks_dir)
    if not sd.is_dir():
        return []

    socks = sorted(list(sd.glob("*.sock")))
    if not socks:
        return []

    # 1. Exact match: <dispatcher>.sock
    exact = sd / f"{dispatcher}.sock"
    if exact.exists():
        return [exact]

    # 2. Prefix match: <dispatcher>*.sock
    prefix_matches = [s for s in socks if s.stem.startswith(dispatcher)]
    if prefix_matches:
        return prefix_matches

    disp_lower = dispatcher.lower()

    # 3. If dispatcher is sara* or dashboard: try sara*, fallback to ida-prime* or prime*
    if disp_lower.startswith("sara") or disp_lower == "dashboard":
        sara_socks = [s for s in socks if "sara" in s.stem.lower()]
        if sara_socks:
            return sara_socks
        prime_socks = [s for s in socks if "prime" in s.stem.lower()]
        if prime_socks:
            return prime_socks

    # 4. If dispatcher is ida-prime* or prime: try ida-prime* or prime*
    if "prime" in disp_lower:
        prime_socks = [s for s in socks if "prime" in s.stem.lower()]
        if prime_socks:
            return prime_socks

    # 5. Non-bus or unmatched dispatcher (host-cli, cloud, or dead session):
    # Route to active coordinator (sara -> ida-prime)
    sara_socks = [s for s in socks if "sara" in s.stem.lower()]
    if sara_socks:
        return sara_socks
    prime_socks = [s for s in socks if "prime" in s.stem.lower()]
    if prime_socks:
        return prime_socks

    # Fallback to first live socket if none of the above matched
    return socks[:1]


def send_bus_message(sock_path: Path | str, message: str) -> bool:
    """Send structured message into a session UDS socket."""
    sock_str = str(sock_path)
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(sock_str)
        payload = (
            json.dumps({"type": "user", "message": {"role": "user", "content": message}}) + "\n"
        )
        s.sendall(payload.encode("utf-8"))
        s.close()
        log.info("delivered notification to socket %s: %s", sock_str, message)
        return True
    except Exception as e:
        log.warning("failed to deliver notification to socket %s: %r", sock_str, e)
        return False


def fetch_events_from_mcp_sync(mcp_url: str) -> list[dict[str, Any]] | None:
    """Fetch unacknowledged events from polecat-mcp via MCP streamable HTTP client."""
    try:
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async def _call():
            async with streamable_http_client(mcp_url) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    res = await session.call_tool("polecat_events", {"unacked_only": True})
                    if not res or not res.content:
                        return []
                    return [json.loads(c.text) for c in res.content]

        return asyncio.run(_call())
    except Exception as e:
        log.debug("MCP fetch from %s failed: %r", mcp_url, e)
        return None


def ack_events_via_mcp_sync(mcp_url: str, ack_up_to: int) -> bool:
    """Acknowledge events up to seq via MCP streamable HTTP client."""
    try:
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async def _call():
            async with streamable_http_client(mcp_url) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    await session.call_tool("polecat_events", {"ack_up_to": ack_up_to})
                    return True

        return asyncio.run(_call())
    except Exception as e:
        log.debug("MCP ack to %s failed: %r", mcp_url, e)
        return False


def fetch_events_from_file(file_path: Path | str) -> list[dict[str, Any]]:
    """Fetch unacknowledged events directly from JSONL state file."""
    p = Path(file_path)
    if not p.is_file():
        return []
    unacked: list[dict[str, Any]] = []
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    if not ev.get("acked"):
                        unacked.append(ev)
                except Exception:
                    continue
    except Exception as e:
        log.warning("error reading events file %s: %r", p, e)
    return unacked


def ack_events_in_file(file_path: Path | str, ack_up_to: int) -> None:
    """Mark events up to ack_up_to as acked in the JSONL state file."""
    p = Path(file_path)
    if not p.is_file():
        return
    try:
        all_events = []
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    if ev.get("seq", 0) <= ack_up_to:
                        ev["acked"] = True
                    all_events.append(ev)
                except Exception:
                    continue
        tmp = p.with_suffix(f".tmp.{os.getpid()}")
        with open(tmp, "w", encoding="utf-8") as f:
            for ev in all_events:
                f.write(json.dumps(ev) + "\n")
        tmp.replace(p)
    except Exception as e:
        log.warning("error updating events file %s: %r", p, e)


def append_to_daily_list(event: dict[str, Any], socks_dirs: list[Path] | None = None) -> None:
    """Record unhandled or abnormal completions to the daily list via pauli socket."""
    log.info(
        "routing abnormal or unreleased event to daily list: task=%s status=%s",
        event.get("task_id"),
        event.get("task_status"),
    )
    if socks_dirs:
        msg = format_notification(event)
        for sd in socks_dirs:
            if sd.is_dir():
                pauli_socks = [s for s in sd.glob("*.sock") if "pauli" in s.stem.lower()]
                for ps in pauli_socks:
                    send_bus_message(ps, f"[daily-list-triage] {msg}")


def relay_single_pass(
    mcp_url: str | None = None,
    events_file: Path | str | None = None,
    socks_dir: Path | str | None = None,
) -> int:
    """Run one polling pass: fetch unacked events, deliver to listening sockets, and ack.

    Only events that were successfully delivered to a listening session are acknowledged.
    If no listener is attached, events remain unacknowledged for the next pass.

    Returns the count of delivered events.
    """
    mcp_url = mcp_url or os.environ.get("POLECAT_MCP_URL")
    events_file = events_file or os.environ.get("POLECAT_EVENTS_FILE", "/tmp/polecat-events.jsonl")

    # 1. Fetch unacked events
    events = None
    used_mcp = False
    if mcp_url:
        events = fetch_events_from_mcp_sync(mcp_url)
        if events is not None:
            used_mcp = True

    if events is None and events_file:
        events = fetch_events_from_file(events_file)

    if not events:
        return 0

    log.info("found %d unacknowledged polecat completion event(s)", len(events))
    socks_dirs = get_socks_dirs(str(socks_dir) if socks_dir else None)

    delivered_count = 0
    delivered_seqs: list[int] = []

    for ev in events:
        seq = ev.get("seq", 0)
        finished_at = ev.get("finished_at")
        arrival_time = datetime.now(UTC).isoformat()
        log.info(
            "processing event seq=%d task=%s finished_at=%s arrival_time=%s",
            seq,
            ev.get("task_id"),
            finished_at,
            arrival_time,
        )

        msg = format_notification(ev)
        dispatcher = ev.get("dispatcher") or "sara"

        # Find target sockets
        targets: list[Path] = []
        for sd in socks_dirs:
            targets = find_target_sockets(sd, dispatcher)
            if targets:
                break

        delivered = False
        for target in targets:
            if send_bus_message(target, msg):
                delivered = True

        if delivered:
            delivered_count += 1
            if seq > 0:
                delivered_seqs.append(seq)
        else:
            log.warning(
                "no listening session received event seq=%d task=%s; keeping unacknowledged",
                seq,
                ev.get("task_id"),
            )

        # If abnormal exit or unreleased, log to daily list
        if ev.get("unreleased") or ev.get("exit_code", 0) != 0:
            append_to_daily_list(ev, socks_dirs=socks_dirs)

    # 2. Acknowledge events ONLY if they were delivered to a listening session
    if delivered_seqs:
        max_delivered = max(delivered_seqs)
        log.info("acknowledging delivered events up to seq=%d", max_delivered)
        if used_mcp and mcp_url:
            ack_events_via_mcp_sync(mcp_url, max_delivered)
        elif events_file:
            ack_events_in_file(events_file, max_delivered)

    return delivered_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Polecat worker finish notification relay")
    parser.add_argument("--once", action="store_true", help="Run a single poll pass and exit")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds")
    parser.add_argument("--mcp-url", default=None, help="Polecat MCP streamable HTTP URL")
    parser.add_argument("--events-file", default=None, help="Path to polecat-events.jsonl")
    parser.add_argument("--socks-dir", default=None, help="Directory containing cc-socks")
    args = parser.parse_args()

    if args.once:
        relay_single_pass(
            mcp_url=args.mcp_url,
            events_file=args.events_file,
            socks_dir=args.socks_dir,
        )
        return

    log.info("starting polecat finish notification relay loop (interval=%.1fs)", args.interval)
    while True:
        try:
            relay_single_pass(
                mcp_url=args.mcp_url,
                events_file=args.events_file,
                socks_dir=args.socks_dir,
            )
        except Exception as e:
            log.error("error in relay loop: %r", e)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
