"""
ntfy Push Notification Gate.

Sends push notifications via ntfy.sh for key session events.
Non-blocking: notification failures are logged but don't affect hook execution.

Events notified:
- SessionStart: Session began
- Stop: Session ended
- SubagentStop: Subagent completed (with verdict if available)

Configuration via environment variables (all required if NTFY_TOPIC is set):
- NTFY_TOPIC: Topic to publish to
- NTFY_SERVER: Server URL (e.g., "https://ntfy.sh")
- NTFY_PRIORITY: Priority 1-5
- NTFY_TAGS: Comma-separated tags
"""

from __future__ import annotations

import logging
import threading
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


def _send_notification_sync(
    config: dict[str, Any],
    title: str,
    message: str,
    priority: int | None = None,
    tags: str | None = None,
) -> bool:
    """
    Synchronous implementation of ntfy notification sending.
    Internal use only - use send_notification() for non-blocking calls.
    """
    try:
        url = f"{config['server']}/{config['topic']}"

        headers = {
            "Title": title,
            "Priority": str(priority if priority is not None else config["priority"]),
            "Tags": tags if tags is not None else config["tags"],
        }

        data = message.encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                logger.debug(f"ntfy notification sent: {title}")
                return True
            else:
                logger.warning(f"ntfy returned status {response.status}")
                return False

    except urllib.error.URLError as e:
        logger.warning(f"ntfy network error: {e}")
        return False
    except Exception as e:
        logger.warning(f"ntfy error: {e}")
        return False


def send_notification(
    config: dict[str, Any],
    title: str,
    message: str,
    priority: int | None = None,
    tags: str | None = None,
) -> bool:
    """
    Send a push notification via ntfy (non-blocking).

    Spawns a background thread to send the notification using urllib.
    This function returns True immediately once the thread is started.

    Args:
        config: ntfy configuration dict from get_ntfy_config()
        title: Notification title
        message: Notification body
        priority: Override default priority (1-5)
        tags: Override default tags (comma-separated)

    Returns:
        Always True (notification is sent in background)
    """
    thread = threading.Thread(
        target=_send_notification_sync,
        args=(config, title, message, priority, tags),
        daemon=True,
    )
    thread.start()
    return True


def notify_session_start(config: dict[str, Any], session_id: str) -> bool:
    """Send notification for session start."""
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    return send_notification(
        config,
        title="Session Started",
        message=f"AOPS session {short_id} began",
        tags="rocket,aops",
    )


def notify_session_stop(
    config: dict[str, Any], session_id: str, task_id: str | None = None
) -> bool:
    """Send notification for session stop."""
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    if task_id:
        message = f"Session {short_id} ended. Task: {task_id}"
    else:
        message = f"Session {short_id} ended"
    return send_notification(
        config,
        title="Session Ended",
        message=message,
        tags="checkered_flag,aops",
    )


def notify_subagent_stop(
    config: dict[str, Any],
    session_id: str,
    agent_type: str,
    verdict: str | None = None,
) -> bool:
    """Send notification for subagent completion."""
    short_id = session_id[:8] if len(session_id) > 8 else session_id

    if verdict:
        message = f"[{short_id}] {agent_type}: {verdict}"
        # Use warning tag for non-PASS verdicts
        tags = "warning,aops" if verdict.upper() != "PASS" else "white_check_mark,aops"
    else:
        message = f"[{short_id}] {agent_type} completed"
        tags = "robot,aops"

    return send_notification(
        config,
        title=f"Subagent: {agent_type}",
        message=message,
        tags=tags,
    )


def notify_task_bound(config: dict[str, Any], session_id: str, task_id: str) -> bool:
    """Send notification when task is bound to session."""
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    return send_notification(
        config,
        title="Task Claimed",
        message=f"[{short_id}] Working on: {task_id}",
        tags="pushpin,aops",
        priority=2,  # Lower priority for routine events
    )


def notify_task_completed(config: dict[str, Any], session_id: str, task_id: str) -> bool:
    """Send notification when task is completed."""
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    return send_notification(
        config,
        title="Task Completed",
        message=f"[{short_id}] Finished: {task_id}",
        tags="white_check_mark,aops",
    )


def notify_gate_blocked(
    config: dict[str, Any], session_id: str, gate_name: str, reason: str
) -> bool:
    """Send notification when a gate blocks an action."""
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    return send_notification(
        config,
        title=f"Gate Blocked: {gate_name}",
        message=f"[{short_id}] {reason[:100]}",
        tags="stop_sign,aops",
        priority=4,  # Higher priority for blocks
    )
