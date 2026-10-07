"""PKB search over MCP for the UserPromptSubmit hydration hook.

$PKB_MCP_URL is the services MCP portal behind Cloudflare Access. It exposes
PKB tools only through ``portal_codemode_execute``, so the search runs as a
code-mode call to ``pkb_search``.

Credentials come from ``CF_ACCESS_CLIENT_ID``/``CF_ACCESS_CLIENT_SECRET``.
Without them, the hook borrows the headers of whichever client config
(Claude Code's ``~/.claude.json`` or agy's ``~/.gemini/config/mcp_config.json``)
registers the same URL. ``PKB_MCP_TOKEN``, if set, is sent as a bearer token.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path

RESULT_LIMIT = 5

MCP_CONFIGS = (
    Path.home() / ".claude.json",
    Path.home() / ".gemini" / "config" / "mcp_config.json",
)


def headers_for(
    url: str, env: Mapping[str, str], configs: tuple[Path, ...] = MCP_CONFIGS
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if env.get("CF_ACCESS_CLIENT_ID") and env.get("CF_ACCESS_CLIENT_SECRET"):
        headers = {
            "CF-Access-Client-Id": env["CF_ACCESS_CLIENT_ID"],
            "CF-Access-Client-Secret": env["CF_ACCESS_CLIENT_SECRET"],
        }
    else:
        headers = _config_headers(url, configs)
    if env.get("PKB_MCP_TOKEN"):
        headers["Authorization"] = f"Bearer {env['PKB_MCP_TOKEN']}"
    return headers


def _config_headers(url: str, configs: tuple[Path, ...]) -> dict[str, str]:
    for path in configs:
        try:
            servers = json.loads(path.read_text(encoding="utf-8")).get("mcpServers") or {}
        except (OSError, ValueError, AttributeError):
            continue
        for server in servers.values():
            if not isinstance(server, dict):
                continue
            server_url = str(server.get("url") or server.get("serverUrl") or "")
            if server_url.rstrip("/") == url.rstrip("/"):
                return {str(k): str(v) for k, v in (server.get("headers") or {}).items()}
    return {}


def search_code(query: str) -> str:
    # json.dumps yields a valid JS object literal, so the query cannot break
    # out of the code it is embedded in.
    return f"async () => await codemode.pkb_search({json.dumps({'query': query, 'limit': RESULT_LIMIT})})"


def result_text(text: str) -> str:
    """The portal returns the tool's content blocks as JSON text; unwrap them."""
    try:
        data = json.loads(text)
    except ValueError:
        return text.strip()
    if isinstance(data, list):
        return "\n".join(str(b.get("text", "")) for b in data if isinstance(b, dict)).strip()
    return text.strip()


async def _search(url: str, query: str, headers: dict[str, str]) -> str:
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport

    async with Client(StreamableHttpTransport(url, headers=headers)) as client:
        result = await client.call_tool("portal_codemode_execute", {"code": search_code(query)})
    return result_text("\n".join(getattr(b, "text", "") for b in result.content))


def search(url: str, query: str, headers: dict[str, str], timeout: float) -> str:
    return asyncio.run(asyncio.wait_for(_search(url, query, headers), timeout))
