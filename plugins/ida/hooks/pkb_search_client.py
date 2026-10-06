"""PKB search over MCP for the UserPromptSubmit hydration hook.

Run as ``python3 pkb_search_client.py <query>`` by handlers._run_pkb_search,
which owns the timeout and output cap. Prints the search result text on
stdout and exits 0; on any failure prints a one-line reason (never a
credential) on stderr and exits 1.

The deployed $PKB_MCP_URL is an MCP portal behind Cloudflare Access:
unauthenticated requests get HTTP 401, and it lists only ``portal_*`` tools,
so search goes through ``portal_codemode_execute`` calling ``pkb_search``.
A server that exposes a search tool directly is called directly.

Credentials, in order: ``CF_ACCESS_CLIENT_ID``/``CF_ACCESS_CLIENT_SECRET``
env vars; else the headers of the ``~/.claude.json`` mcpServers entry
(top-level or project-scoped) whose url matches; plus an
``Authorization: Bearer`` from ``PKB_MCP_TOKEN`` if set.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

_DIRECT_TOOLS = ("pkb__search", "pkb_search", "search")
_PORTAL_TOOL = "portal_codemode_execute"
_PORTAL_PREFIX = "async () => await codemode.pkb_search("


class NoSearchTool(RuntimeError):
    pass


def _norm(url: str) -> str:
    return url.strip().rstrip("/")


def _mcp_servers(config: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    yield from (config.get("mcpServers") or {}).values()
    for project in (config.get("projects") or {}).values():
        if isinstance(project, Mapping):
            yield from (project.get("mcpServers") or {}).values()


def resolve_headers(url: str, env: Mapping[str, str], claude_json: Path) -> dict[str, str]:
    headers: dict[str, str] = {}
    cf_id, cf_secret = env.get("CF_ACCESS_CLIENT_ID"), env.get("CF_ACCESS_CLIENT_SECRET")
    if cf_id and cf_secret:
        headers = {"CF-Access-Client-Id": cf_id, "CF-Access-Client-Secret": cf_secret}
    else:
        try:
            config = json.loads(claude_json.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            config = {}
        for server in _mcp_servers(config):
            if isinstance(server, Mapping) and _norm(str(server.get("url") or "")) == _norm(url):
                headers = {str(k): str(v) for k, v in (server.get("headers") or {}).items()}
                break
    token = env.get("PKB_MCP_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def build_call(tool_names: Iterable[str], query: str) -> tuple[str, dict[str, str]]:
    names = set(tool_names)
    for name in _DIRECT_TOOLS:
        if name in names:
            return name, {"query": query}
    if _PORTAL_TOOL in names:
        # json.dumps yields a valid JS object literal, so the query cannot
        # break out of the string it is embedded in.
        return _PORTAL_TOOL, {"code": f"{_PORTAL_PREFIX}{json.dumps({'query': query})})"}
    raise NoSearchTool(f"server exposes no PKB search tool (tools: {sorted(names)})")


def extract_text(text: str) -> str:
    try:
        data = json.loads(text)
    except ValueError:
        return text.strip()
    if isinstance(data, list):
        parts = [b.get("text", "") for b in data if isinstance(b, Mapping)]
        if any(parts):
            return "\n".join(p for p in parts if p).strip()
    if isinstance(data, Mapping) and isinstance(data.get("result"), str):
        return data["result"].strip()
    return text.strip()


async def search_with_client(client: Any, query: str) -> str:
    async with client:
        tools = await client.list_tools()
        tool, args = build_call((t.name for t in tools), query)
        result = await client.call_tool(tool, args)
    text = "\n".join(getattr(b, "text", "") for b in result.content).strip()
    return extract_text(text)


async def search(url: str, query: str, headers: Mapping[str, str]) -> str:
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport

    return await search_with_client(
        Client(StreamableHttpTransport(url, headers=dict(headers))), query
    )


def main(argv: list[str]) -> int:
    url = os.environ.get("PKB_MCP_URL")
    if not url or len(argv) < 2 or not argv[1].strip():
        print("pkb search: PKB_MCP_URL and a query are required", file=sys.stderr)
        return 1
    headers = resolve_headers(url, os.environ, Path.home() / ".claude.json")
    try:
        out = asyncio.run(search(url, argv[1], headers))
    except Exception as exc:  # message only; headers are never formatted into it
        print(f"pkb search failed: {type(exc).__name__}: {str(exc)[:200]}", file=sys.stderr)
        return 1
    if not out:
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
