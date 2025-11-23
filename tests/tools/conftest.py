"""FastMCP proxy fixture for Basic Memory (bmem) MCP testing."""

import pytest
from fastmcp import FastMCP


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "tool: mark test as a tool integration test (requires MCP servers)"
    )


@pytest.fixture
def anyio_backend():
    """Use asyncio backend only (trio not installed)."""
    return "asyncio"


@pytest.fixture(scope="session")
def bmem_server():
    """FastMCP proxy connecting to Basic Memory stdio server.

    Creates a proxy that bridges to the Basic Memory MCP server
    running via `uvx basic-memory mcp`.

    Returns:
        FastMCP: Proxy server instance connected to bmem
    """
    config = {
        "mcpServers": {
            "bmem": {
                "command": "uvx",
                "args": ["basic-memory", "mcp"],
            }
        }
    }
    return FastMCP.as_proxy(config, name="bmem_test_proxy")
