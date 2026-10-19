"""Tests for scripts/measure_pkb_injection.py."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import measure_pkb_injection


def test_measure_backend_authenticates_with_hook_headers():
    """Measurement script sends the same credential headers the hook does."""
    captured_transports = []

    class MockClientContext:
        def __init__(self, *args, **kwargs):
            self.transport = kwargs.get("transport")
            captured_transports.append(self.transport)

        async def __aenter__(self):
            mock_client = AsyncMock()
            mock_client.call_tool = AsyncMock(
                return_value=MagicMock(content=[MagicMock(text='{"results": []}')])
            )
            return mock_client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    test_headers = {"CF-Access-Client-Id": "id1", "CF-Access-Client-Secret": "sec1"}

    import asyncio

    with (
        patch.dict(os.environ, {"PKB_MCP_URL": "https://pkb.example.com"}),
        patch("fastmcp.Client", side_effect=MockClientContext),
        patch.object(measure_pkb_injection, "_resolve_mcp_headers", return_value=test_headers),
        patch.dict(
            measure_pkb_injection.PROMPT_FAMILIES, {"test_family": ["test prompt"]}, clear=True
        ),
        patch.dict(measure_pkb_injection.FAMILY_KEYWORDS, {"test_family": ["test"]}, clear=True),
    ):
        asyncio.run(measure_pkb_injection.measure_backend(repeats=1))

    assert len(captured_transports) > 0
    transport = captured_transports[0]
    assert transport is not None
    assert getattr(transport, "headers", None) == test_headers
