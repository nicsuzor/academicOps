"""Tests for `polecat ping-pkb` — the supervisor's pre-dispatch readiness gate.

The probe must fail loudly with distinct exit codes so the supervisor can
distinguish "config missing" (4) from "service unreachable" (5). See issues
#598 (host-check) and #600 (PKB unreachable from nicwin's WSL2).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from cli import main  # noqa: E402


@pytest.fixture
def runner():
    return CliRunner()


def test_ping_pkb_exits_4_when_url_unset(runner, monkeypatch):
    """No PKB_MCP_URL → exit 4 with a remediation message."""
    monkeypatch.delenv("PKB_MCP_URL", raising=False)
    result = runner.invoke(main, ["ping-pkb"], catch_exceptions=False)
    assert result.exit_code == 4
    assert "PKB_MCP_URL is not set" in result.output


def test_ping_pkb_exits_5_on_connection_refused(runner, monkeypatch):
    """ConnectionRefusedError mirrors the worker-boot crash (#600) → exit 5."""
    monkeypatch.setenv("PKB_MCP_URL", "http://localhost:65535/mcp")

    with patch("polecat.pkb_bridge.PkbClient") as mock_client_cls:
        mock_client_cls.side_effect = ConnectionRefusedError(
            "Connection refused — same fault that crashes PkbClient._initialize()"
        )
        result = runner.invoke(main, ["ping-pkb"], catch_exceptions=False)

    assert result.exit_code == 5
    assert "FAILED" in result.output


def test_ping_pkb_exits_5_on_handshake_tools_call_none(runner, monkeypatch):
    """TCP/handshake OK but tools/call returns None → exit 5."""
    monkeypatch.setenv("PKB_MCP_URL", "http://localhost:8026/mcp")

    fake_client = MagicMock()
    fake_client.call_tool.return_value = None
    with patch("polecat.pkb_bridge.PkbClient", return_value=fake_client):
        result = runner.invoke(main, ["ping-pkb"], catch_exceptions=False)

    assert result.exit_code == 5
    assert "list_tasks returned no" in result.output


def test_ping_pkb_exits_0_on_success(runner, monkeypatch):
    """Successful handshake + tools/call → exit 0 with OK message."""
    monkeypatch.setenv("PKB_MCP_URL", "http://localhost:8026/mcp")

    fake_client = MagicMock()
    fake_client.call_tool.return_value = "| # | ID | ... |"  # list_tasks markdown
    with patch("polecat.pkb_bridge.PkbClient", return_value=fake_client):
        result = runner.invoke(main, ["ping-pkb"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "OK" in result.output
    fake_client.call_tool.assert_called_once_with("list_tasks", {"limit": 1})
