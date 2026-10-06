"""Tests for the PKB hydration transport (plugins/ida/hooks/pkb_search_client.py).

The deployed endpoint ($PKB_MCP_URL) sits behind Cloudflare Access and is an
MCP portal: unauthenticated calls get HTTP 401, and with CF-Access headers it
lists only portal_* tools, so PKB search goes through portal_codemode_execute.
The client resolves credentials, picks a direct search tool when the server
exposes one, falls back to the portal otherwise, and returns plain text.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest
from fastmcp import Client, FastMCP

_HOOKS_DIR = Path(__file__).resolve().parent.parent / "plugins" / "ida" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import pkb_search_client as psc  # noqa: E402

URL = "https://pkb.example.test/mcp"


def _write_claude_json(path: Path, servers: dict, project_servers: dict | None = None) -> Path:
    data: dict = {"mcpServers": servers}
    if project_servers is not None:
        data["projects"] = {"/workspace": {"mcpServers": project_servers}}
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# --- credentials -----------------------------------------------------------


def test_cf_access_env_vars_win(tmp_path):
    cfg = _write_claude_json(
        tmp_path / "c.json",
        {"services": {"url": URL, "headers": {"CF-Access-Client-Id": "from-file"}}},
    )
    env = {"CF_ACCESS_CLIENT_ID": "id-env", "CF_ACCESS_CLIENT_SECRET": "secret-env"}
    assert psc.resolve_headers(URL, env, cfg) == {
        "CF-Access-Client-Id": "id-env",
        "CF-Access-Client-Secret": "secret-env",
    }


def test_headers_come_from_claude_json_entry_matching_the_url(tmp_path):
    cfg = _write_claude_json(
        tmp_path / "c.json",
        {
            "other": {"url": "https://elsewhere.test/mcp", "headers": {"X": "no"}},
            "services": {
                "url": URL + "/",
                "headers": {"CF-Access-Client-Id": "i", "CF-Access-Client-Secret": "s"},
            },
        },
    )
    assert psc.resolve_headers(URL, {}, cfg) == {
        "CF-Access-Client-Id": "i",
        "CF-Access-Client-Secret": "s",
    }


def test_headers_from_project_scoped_mcp_server(tmp_path):
    cfg = _write_claude_json(
        tmp_path / "c.json", {}, {"svc": {"url": URL, "headers": {"CF-Access-Client-Id": "p"}}}
    )
    assert psc.resolve_headers(URL, {}, cfg) == {"CF-Access-Client-Id": "p"}


def test_no_matching_entry_and_no_env_gives_no_headers(tmp_path):
    cfg = _write_claude_json(tmp_path / "c.json", {"x": {"url": "https://other.test/mcp"}})
    assert psc.resolve_headers(URL, {}, cfg) == {}
    assert psc.resolve_headers(URL, {}, tmp_path / "missing.json") == {}


def test_bearer_token_is_still_supported(tmp_path):
    headers = psc.resolve_headers(URL, {"PKB_MCP_TOKEN": "tok"}, tmp_path / "missing.json")
    assert headers == {"Authorization": "Bearer tok"}


# --- tool selection and call shape ----------------------------------------


@pytest.mark.parametrize("name", ["pkb__search", "pkb_search", "search"])
def test_direct_search_tool_is_preferred(name):
    tool, args = psc.build_call([name, "portal_codemode_execute"], "hello")
    assert tool == name
    assert args == {"query": "hello"}


def test_portal_codemode_fallback_embeds_query_as_a_json_literal():
    query = 'x"}); evil(); ({"a":"'
    tool, args = psc.build_call(["portal_list_servers", "portal_codemode_execute"], query)
    assert tool == "portal_codemode_execute"
    code = args["code"]
    assert code.startswith("async () => await codemode.pkb_search(")
    payload = code[len("async () => await codemode.pkb_search(") : -1]
    assert json.loads(payload) == {"query": query}


def test_no_usable_tool_raises():
    with pytest.raises(psc.NoSearchTool):
        psc.build_call(["portal_list_servers"], "q")


# --- result text -----------------------------------------------------------


def test_extract_text_unwraps_portal_content_blocks():
    # Shape observed from portal_codemode_execute -> pkb_search on 2026-10-06.
    raw = json.dumps([{"type": "text", "text": "**Found 1 results**\n### 1. A"}])
    assert psc.extract_text(raw) == "**Found 1 results**\n### 1. A"


def test_extract_text_unwraps_result_envelope():
    assert psc.extract_text(json.dumps({"result": "found it"})) == "found it"


def test_extract_text_passes_plain_text_through():
    assert psc.extract_text("1. Some doc\n   path.md") == "1. Some doc\n   path.md"


# --- against in-memory MCP servers -----------------------------------------


def test_search_calls_direct_tool_on_server():
    server = FastMCP("direct")

    @server.tool
    def pkb_search(query: str) -> str:
        return f"direct hit for {query}"

    out = asyncio.run(psc.search_with_client(Client(server), "axioms"))
    assert out == "direct hit for axioms"


def test_search_goes_through_portal_when_no_direct_tool():
    server = FastMCP("portal")

    @server.tool
    def portal_list_servers() -> str:
        return "[]"

    @server.tool
    def portal_codemode_execute(code: str) -> str:
        return json.dumps([{"type": "text", "text": f"portal ran: {code}"}])

    out = asyncio.run(psc.search_with_client(Client(server), "axioms"))
    assert out == 'portal ran: async () => await codemode.pkb_search({"query": "axioms"})'
