#!/usr/bin/env python3
import http.client
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from polecat.pkb_bridge import PkbClient


def _make_client() -> PkbClient:
    """Build a PkbClient without firing the real initialize() handshake."""
    with patch.object(PkbClient, "_initialize", lambda self: None):
        return PkbClient("http://unit-test.invalid/mcp")


def test_post_retry_on_timeout(capsys):
    client = _make_client()

    # Mock urllib.request.urlopen to fail twice then succeed
    mock_resp = MagicMock()
    mock_resp.headers = {}
    mock_resp.read.return_value = (
        b'data: {"jsonrpc": "2.0", "id": 1, "result": {"success": true}}\n'
    )
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [
            TimeoutError("timed out"),
            urllib.error.URLError("timed out"),
            mock_resp,
        ]

        with patch("time.sleep") as mock_sleep:
            result = client._post({"test": "body"})

            assert result == {"jsonrpc": "2.0", "id": 1, "result": {"success": True}}
            assert mock_urlopen.call_count == 3
            assert mock_sleep.call_count == 2

            captured = capsys.readouterr()
            assert "PKB PKB timeout (attempt 1/4): retrying" in captured.err
            assert "PKB PKB timeout (attempt 2/4): retrying" in captured.err


def test_post_exhaust_retries(capsys):
    client = _make_client()

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = TimeoutError("timed out")

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(TimeoutError):
                client._post({"test": "body"})

            assert mock_urlopen.call_count == 4
            assert mock_sleep.call_count == 3

            captured = capsys.readouterr()
            assert "PKB PKB timeout (attempt 4/4)" not in captured.err
            assert "PKB PKB timeout (attempt 3/4): retrying" in captured.err


def test_post_retry_on_chunked_read_timeout(capsys):
    """Regression for aops-aaa98cf7: chunked-read TimeoutError raised mid-resp.read()
    must trigger a retry rather than fail dispatch silently."""
    client = _make_client()

    # First response raises TimeoutError on .read() (simulating the chunked-read
    # timeout from the bug report). Second response succeeds.
    failing_resp = MagicMock()
    failing_resp.headers = {}
    failing_resp.read.side_effect = TimeoutError("timed out")
    failing_resp.__enter__.return_value = failing_resp

    success_resp = MagicMock()
    success_resp.headers = {}
    success_resp.read.return_value = (
        b'data: {"jsonrpc": "2.0", "id": 1, "result": {"success": true}}\n'
    )
    success_resp.__enter__.return_value = success_resp

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [failing_resp, success_resp]

        with patch("time.sleep") as mock_sleep:
            result = client._post({"test": "body"})

            assert result == {"jsonrpc": "2.0", "id": 1, "result": {"success": True}}
            assert mock_urlopen.call_count == 2
            assert mock_sleep.call_count == 1

            captured = capsys.readouterr()
            assert "PKB PKB timeout (attempt 1/4): retrying" in captured.err


def test_post_retry_on_incomplete_read(capsys):
    """IncompleteRead during chunked decoding should also trigger a retry."""
    client = _make_client()

    failing_resp = MagicMock()
    failing_resp.headers = {}
    failing_resp.read.side_effect = http.client.IncompleteRead(b"")
    failing_resp.__enter__.return_value = failing_resp

    success_resp = MagicMock()
    success_resp.headers = {}
    success_resp.read.return_value = b'data: {"jsonrpc": "2.0", "id": 1, "result": {"ok": true}}\n'
    success_resp.__enter__.return_value = success_resp

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [failing_resp, success_resp]

        with patch("time.sleep") as mock_sleep:
            result = client._post({"test": "body"})

            assert result == {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
            assert mock_urlopen.call_count == 2
            assert mock_sleep.call_count == 1
