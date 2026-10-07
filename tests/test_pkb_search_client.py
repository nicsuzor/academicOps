"""Tests for the PKB hydration transport (plugins/ida/hooks/pkb_search_client.py).

The deployed endpoint ($PKB_MCP_URL) is the services MCP portal behind
Cloudflare Access: unauthenticated calls get HTTP 401, and PKB tools are only
reachable through portal_codemode_execute. The live round trip is exercised
by running the real hook (see the PR); these tests cover credentials, the
generated code, unwrapping and the timeout.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parent.parent / "plugins" / "ida" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import pkb_search_client as psc  # noqa: E402

URL = "https://pkb.example.test/mcp"


def _config(path: Path, servers: dict) -> Path:
    path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")
    return path


# --- credentials -----------------------------------------------------------


def test_cf_access_env_vars_win(tmp_path):
    cfg = _config(tmp_path / "c.json", {"s": {"url": URL, "headers": {"X": "from-file"}}})
    env = {"CF_ACCESS_CLIENT_ID": "id", "CF_ACCESS_CLIENT_SECRET": "secret"}
    assert psc.headers_for(URL, env, (cfg,)) == {
        "CF-Access-Client-Id": "id",
        "CF-Access-Client-Secret": "secret",
    }


def test_headers_come_from_claude_code_config(tmp_path):
    cfg = _config(
        tmp_path / ".claude.json", {"services": {"url": URL + "/", "headers": {"X": "1"}}}
    )
    assert psc.headers_for(URL, {}, (cfg,)) == {"X": "1"}


def test_headers_come_from_agy_config(tmp_path):
    """agy's mcp_config.json names the endpoint ``serverUrl``."""
    missing = tmp_path / "absent.json"
    cfg = _config(
        tmp_path / "mcp_config.json", {"services": {"serverUrl": URL, "headers": {"X": "2"}}}
    )
    assert psc.headers_for(URL, {}, (missing, cfg)) == {"X": "2"}


def test_no_matching_entry_gives_no_headers(tmp_path):
    cfg = _config(
        tmp_path / "c.json", {"other": {"url": "https://elsewhere/mcp", "headers": {"X": "1"}}}
    )
    assert psc.headers_for(URL, {}, (cfg,)) == {}


def test_bearer_token_is_added(tmp_path):
    assert psc.headers_for(URL, {"PKB_MCP_TOKEN": "t"}, ()) == {"Authorization": "Bearer t"}


# --- call and result -------------------------------------------------------


def test_query_is_embedded_as_a_json_literal_with_a_result_limit():
    query = 'a"); evil(); ("'
    code = psc.search_code(query)
    prefix = "async () => await codemode.pkb_search("
    assert code.startswith(prefix) and code.endswith(")")
    assert json.loads(code[len(prefix) : -1]) == {"query": query, "limit": psc.RESULT_LIMIT}


def test_result_text_unwraps_portal_content_blocks():
    blocks = json.dumps([{"type": "text", "text": "**Found 5 results**"}])
    assert psc.result_text(blocks) == "**Found 5 results**"


def test_result_text_passes_plain_text_through():
    assert psc.result_text("  plain  ") == "plain"


def test_search_is_cut_off_at_the_timeout(monkeypatch):
    async def stalled(url, query, headers):
        await asyncio.sleep(5)
        return "late"

    monkeypatch.setattr(psc, "_search", stalled)
    with pytest.raises(TimeoutError):
        psc.search(URL, "q", {}, timeout=0.05)
