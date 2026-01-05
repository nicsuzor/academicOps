"""FastMCP proxy fixture for Memory MCP testing."""

import pytest
from fastmcp import FastMCP


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "tool: mark test as a tool integration test (requires MCP servers)"
    )


@pytest.fixture
def anyio_backend():
    """Use asyncio backend only (trio not installed)."""
    return "asyncio"


@pytest.fixture(scope="session")
def memory_server():
    """FastMCP proxy connecting to Memory stdio server.

    Creates a proxy that bridges to the Memory MCP server
    running via `uvx basic-memory mcp`.

    Returns:
        FastMCP: Proxy server instance connected to memory server
    """
    config = {
        "mcpServers": {
            "memory": {
                "command": "uvx",
                "args": ["basic-memory", "mcp"],
            }
        }
    }
    return FastMCP.as_proxy(config, name="memory_test_proxy")
