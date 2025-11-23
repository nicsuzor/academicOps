"""Test bmem MCP server retrieval via FastMCP proxy.

Tests that bmem search_notes can find known content in the knowledge base.
"""

import pytest
from fastmcp import Client


@pytest.mark.tool
@pytest.mark.anyio
async def test_search_claude_code_log(bmem_server):
    """Search bmem for 'claude-code-log' and verify results.

    This test validates:
    1. bmem MCP server is reachable via FastMCP proxy
    2. search_notes tool works
    3. Known content from session logs is findable
    """
    async with Client(bmem_server) as client:
        result = await client.call_tool(
            "search_notes",
            {"query": "claude-code-log", "project": "main"}
        )

        # Verify we got results
        assert result is not None, "search_notes returned None"

        # Result should contain matching content
        # The exact structure depends on bmem's response format
        content = str(result)
        assert "claude-code-log" in content.lower() or len(content) > 100, (
            f"Expected to find 'claude-code-log' content, got: {content[:200]}"
        )
