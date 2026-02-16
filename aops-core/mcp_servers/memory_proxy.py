#!/usr/bin/env python3
"""Stdio proxy for the remote HTTP memory MCP server.

Claude Code's HTTP transport attempts OAuth negotiation which fails against
our Bearer-token memory server. This proxy bridges via stdio transport.

Usage:
    uv run python mcp_servers/memory_proxy.py
"""

import os

from fastmcp import Client, FastMCP
from fastmcp.client.auth import BearerAuth

MEMORY_URL = os.environ.get(
    "MEMORY_SERVER_URL",
    "http://services.stoat-musical.ts.net:8026/mcp",
)
API_KEY = os.environ.get("MCP_MEMORY_API_KEY", "")

client = Client(MEMORY_URL, auth=BearerAuth(token=API_KEY))
proxy = FastMCP.as_proxy(client, name="memory-proxy")

if __name__ == "__main__":
    proxy.run()
