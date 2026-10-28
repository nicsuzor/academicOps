"""Tests for polecat worker completion event delivery to listening sessions (#3148).

Verifies:
1. AC1: A polecat exit produces an event that a listening session receives and acknowledges.
2. AC2: No recorded completion event stays undelivered while a listener is attached.
3. Event formatting and socket resolution across dispatcher variants.
4. Failures on transport/send do not acknowledge events.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

import pytest

from scripts.polecat_notify_relay import (
    fetch_events_from_file,
    find_target_sockets,
    format_notification,
    relay_single_pass,
)


class MockUdsListener:
    """Mock Unix Domain Socket listener simulating an attached agent session."""

    def __init__(self, sock_path: Path):
        self.sock_path = sock_path
        self.received_messages: list[dict] = []
        self._stop = threading.Event()
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None

    def start(self):
        if self.sock_path.exists():
            self.sock_path.unlink()
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(str(self.sock_path))
        self._server.listen(5)
        self._server.settimeout(0.5)

        def _listen():
            while not self._stop.is_set():
                try:
                    conn, _ = self._server.accept()
                except TimeoutError:
                    continue
                except Exception:
                    break
                try:
                    conn.settimeout(1.0)
                    data = b""
                    while True:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                    for line in data.decode("utf-8", errors="replace").splitlines():
                        line = line.strip()
                        if line:
                            self.received_messages.append(json.loads(line))
                except Exception:
                    pass
                finally:
                    conn.close()

        self._thread = threading.Thread(target=_listen, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1.0)
        if self.sock_path.exists():
            try:
                self.sock_path.unlink()
            except Exception:
                pass


@pytest.fixture
def relay_env(tmp_path: Path):
    events_file = tmp_path / "polecat-events.jsonl"
    socks_dir = tmp_path / "cc-socks"
    socks_dir.mkdir(parents=True, exist_ok=True)
    return events_file, socks_dir


def test_polecat_exit_produces_event_received_and_acknowledged(relay_env):
    """AC1: A polecat exit produces an event that a listening session receives and acknowledges."""
    events_file, socks_dir = relay_env
    sara_sock = socks_dir / "sara-1015-1338.sock"
    listener = MockUdsListener(sara_sock)
    listener.start()

    try:
        # 1. Arrange: Recorded polecat exit completion event
        event = {
            "seq": 1,
            "task_id": "mock_task_test_task_1",
            "container_name": "polecat-worker-1",
            "exit_code": 0,
            "task_status": "review",
            "pr_url": "https://github.com/nicsuzor/academicOps/pull/3200",
            "duration_s": 42.5,
            "dispatcher": "sara",
            "acked": False,
        }
        events_file.write_text(json.dumps(event) + "\n", encoding="utf-8")

        # 2. Act: Run relay single pass while listener is attached
        delivered = relay_single_pass(
            mcp_url=None,
            events_file=events_file,
            socks_dir=socks_dir,
        )

        # 3. Assert: Listening session received the completion event
        assert delivered == 1
        time.sleep(0.05)
        assert len(listener.received_messages) == 1
        content = listener.received_messages[0]["message"]["content"]
        assert "[polecat-exit]" in content
        assert "task=mock_task_test_task_1" in content
        assert "container=polecat-worker-1" in content
        assert "status=review" in content
        assert "pr_url=https://github.com/nicsuzor/academicOps/pull/3200" in content

        # 4. Assert: Event is acknowledged in the event store
        unacked = fetch_events_from_file(events_file)
        assert len(unacked) == 0

    finally:
        listener.stop()


def test_no_recorded_completion_event_stays_undelivered_while_listener_attached(relay_env):
    """AC2: No recorded completion event stays undelivered while a listener is attached."""
    events_file, socks_dir = relay_env

    # 1. Arrange: Multiple recorded completion events while NO listener is attached
    ev1 = {
        "seq": 1,
        "task_id": "mock_task_unreleased_1",
        "container_name": "polecat-unrel-1",
        "exit_code": 1,
        "task_status": "partial",
        "unreleased": True,
        "dispatcher": "sara",
        "acked": False,
    }
    ev2 = {
        "seq": 2,
        "task_id": "mock_task_normal_2",
        "container_name": "polecat-normal-2",
        "exit_code": 0,
        "task_status": "done",
        "dispatcher": "sara",
        "acked": False,
    }
    events_file.write_text(json.dumps(ev1) + "\n" + json.dumps(ev2) + "\n", encoding="utf-8")

    # Pass while no listener attached: events must NOT be marked delivered or acknowledged
    delivered_unattached = relay_single_pass(
        mcp_url=None,
        events_file=events_file,
        socks_dir=socks_dir,
    )
    assert delivered_unattached == 0
    # Must stay unacknowledged
    unacked_before = fetch_events_from_file(events_file)
    assert len(unacked_before) == 2

    # 2. Act: Attach listener and run relay pass
    sara_sock = socks_dir / "sara.sock"
    listener = MockUdsListener(sara_sock)
    listener.start()

    try:
        delivered_attached = relay_single_pass(
            mcp_url=None,
            events_file=events_file,
            socks_dir=socks_dir,
        )

        # 3. Assert: All events delivered to the attached listener
        assert delivered_attached == 2
        time.sleep(0.05)
        assert len(listener.received_messages) == 2
        msg1 = listener.received_messages[0]["message"]["content"]
        msg2 = listener.received_messages[1]["message"]["content"]
        assert "task=mock_task_unreleased_1" in msg1
        assert "unreleased=true" in msg1
        assert "task=mock_task_normal_2" in msg2

        # 4. Assert: No completion events stay undelivered or unacknowledged
        unacked_after = fetch_events_from_file(events_file)
        assert len(unacked_after) == 0

    finally:
        listener.stop()


def test_format_notification_handles_all_fields():
    """format_notification produces canonical [polecat-exit] format with all attributes."""
    event = {
        "task_id": "mock_task_foo",
        "container_name": "worker-bar",
        "exit_code": 0,
        "task_status": "done",
        "unreleased": True,
        "pr_url": "https://example.com/pr/1",
        "duration_s": 12.3,
        "dispatcher": "sara",
    }
    msg = format_notification(event)
    assert (
        msg
        == "[polecat-exit] task=mock_task_foo container=worker-bar exit_code=0 status=done unreleased=true pr_url=https://example.com/pr/1 duration=12.3s dispatcher=sara"
    )

    minimal = {}
    msg_min = format_notification(minimal)
    assert msg_min == "[polecat-exit] task=unknown container=unknown exit_code=0 status=unknown"


def test_find_target_sockets(tmp_path: Path):
    """find_target_sockets matches exact, prefix, role-based, and fallback sockets."""
    sara_exact = tmp_path / "sara.sock"
    sara_prefix = tmp_path / "sara-20261028.sock"
    prime_sock = tmp_path / "ida-prime.sock"

    sara_exact.touch()
    sara_prefix.touch()
    prime_sock.touch()

    # Exact match
    assert find_target_sockets(tmp_path, "sara") == [sara_exact]

    # Prefix match
    sara_exact.unlink()
    assert find_target_sockets(tmp_path, "sara") == [sara_prefix]

    # Prime match
    assert find_target_sockets(tmp_path, "ida-prime") == [prime_sock]

    # Fallback to sara when unmatched
    assert find_target_sockets(tmp_path, "unknown-disp") == [sara_prefix]


def test_undelivered_event_remains_unacked_when_socket_fails(relay_env):
    """If socket message delivery fails, event is not marked delivered and remains unacked."""
    events_file, socks_dir = relay_env
    # Create dead socket path (no server listening)
    dead_sock = socks_dir / "sara.sock"
    dead_sock.touch()

    event = {
        "seq": 1,
        "task_id": "mock_task_failed_sock",
        "exit_code": 0,
        "task_status": "done",
        "dispatcher": "sara",
        "acked": False,
    }
    events_file.write_text(json.dumps(event) + "\n", encoding="utf-8")

    delivered = relay_single_pass(
        mcp_url=None,
        events_file=events_file,
        socks_dir=socks_dir,
    )
    assert delivered == 0
    unacked = fetch_events_from_file(events_file)
    assert len(unacked) == 1
    assert unacked[0]["task_id"] == "mock_task_failed_sock"
