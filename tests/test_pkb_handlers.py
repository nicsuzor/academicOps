"""Tests for the UserPromptSubmit / PKB-search hook in plugins/ida/hooks/handlers.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PKB_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"

if str(PKB_HOOKS) not in sys.path:
    sys.path.insert(0, str(PKB_HOOKS))

import importlib.util

handlers_spec = importlib.util.spec_from_file_location("pkb_handlers", PKB_HOOKS / "handlers.py")
assert handlers_spec is not None and handlers_spec.loader is not None
handlers = importlib.util.module_from_spec(handlers_spec)
# Deliberately NOT registered as sys.modules["handlers"]: that name collides
# with plugins/rbg/hooks/handlers.py, which tests/test_cope.py imports under
# the bare name "handlers". Under pytest-xdist, whichever module registers
# that slot first wins it for every test in the worker, so a bare "handlers"
# registration here causes test_cope.py's handlers.evaluate(...) calls to
# raise AttributeError against the wrong module.
sys.modules["pkb_handlers"] = handlers
handlers_spec.loader.exec_module(handlers)

from dispatch import HookContext, load_message_pair  # type: ignore[import-not-found]


@pytest.fixture(autouse=True)
def no_ambient_pkb_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's real PKB credentials out of every test.

    With credentials in the environment the hook takes the authenticated HTTP
    path, so tests of the CLI path would silently test the wrong branch.
    """
    for var in (
        "PKB_MCP_URL",
        "PKB_MCP_HEADERS",
        "DISPATCHER_MCP_TOKEN",
        "WORKER_MCP_TOKEN",
        "CF_ACCESS_CLIENT_ID",
        "CF_ACCESS_CLIENT_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def staged_hooks(tmp_path: Path) -> Path:
    """A plugin hooks/ directory assembled with dispatch.py and handlers.py."""
    hooks = tmp_path / "hooks"
    shutil.copytree(PKB_HOOKS, hooks, ignore=shutil.ignore_patterns("__pycache__"))
    return hooks


def test_search_the_pkb_registered_in_handlers():
    """Verify that UserPromptSubmit registers the single user_prompt_submit handler."""
    assert handlers.HANDLERS["UserPromptSubmit"] == [handlers.user_prompt_submit]


def test_user_prompt_submit_pkb_search_success():
    """When pkb search succeeds, output is wrapped in <academicOps PKB search results> tags."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": "what are the axioms of academicOps?"},
        hooks_dir=PKB_HOOKS,
        cwd="/workspace",
    )

    mock_search_results = (
        "1. Rule sets and axioms ████████ 0.85\n   specs/AXIOMS.md\n   Found 1 match."
    )

    with patch.object(handlers, "_run_pkb_search", return_value=mock_search_results) as mock_search:
        res = handlers.search_the_pkb(ctx)
        mock_search.assert_called_once_with("what are the axioms of academicOps?", cwd="/workspace")
        assert res is not None
        expected_text = (
            "<academicOps PKB search results>\n"
            f"{mock_search_results}\n"
            "</academicOps PKB search results>"
        )
        assert res.inject_text == expected_text
        assert res.user_text is None


def test_user_prompt_submit_truncates_prompt_to_200():
    """Prompt query is truncated to 200 characters when passed to pkb search."""
    long_prompt = "a" * 350
    with (
        patch.object(
            handlers, "_search_via_fastmcp_client", return_value="result line"
        ) as mock_client,
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        out = handlers._run_pkb_search(long_prompt)
        assert out == "result line"
        mock_client.assert_called_once_with("http://test", "a" * 200, {})


def test_user_prompt_submit_strips_ansi_from_prompt():
    """ANSI escape sequences in prompt are stripped before passing to pkb search."""
    ansi_prompt = "\x1b[31mred text\x1b[0m with \x1b[1mbold\x1b[0m"
    with (
        patch.object(
            handlers, "_search_via_fastmcp_client", return_value="result line"
        ) as mock_client,
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        out = handlers._run_pkb_search(ansi_prompt)
        assert out == "result line"
        mock_client.assert_called_once_with("http://test", "red text with bold", {})


def test_run_pkb_search_uses_measured_timeout():
    """FastMCP client search timeout matches the measured backend-latency ceiling, not the old 15s guess."""
    assert handlers._SEARCH_TIMEOUT_SECONDS < 15
    assert handlers._SEARCH_TIMEOUT_SECONDS > 0


def test_run_pkb_search_caps_oversized_output():
    """Output larger than the injection budget is truncated with a marker, regardless of source."""
    huge = "x" * (handlers._MAX_INJECT_CHARS * 2)
    with (
        patch.object(
            handlers, "_search_via_fastmcp_client", return_value=handlers._cap_output(huge)
        ),
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        out = handlers._run_pkb_search("q")
        assert out is not None
        assert len(out) == handlers._MAX_INJECT_CHARS
        assert out.endswith(handlers._TRUNCATION_MARKER)


def test_run_pkb_search_leaves_normal_output_untouched():
    """Output well under the cap passes through byte-for-byte."""
    normal = "1. Some doc (score: 0.08)\n   path/to/doc.md\n   an extract of the match."
    with (
        patch.object(handlers, "_search_via_fastmcp_client", return_value=normal),
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        out = handlers._run_pkb_search("q")
        assert out == normal


def test_user_prompt_submit_returns_none_when_prompt_is_empty():
    """When prompt is empty, search_the_pkb returns None (no honesty fallback)."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": ""},
        hooks_dir=PKB_HOOKS,
        agent_type="worker",
    )

    res = handlers.search_the_pkb(ctx)
    assert res is None


def test_user_prompt_submit_returns_none_when_pkb_search_returns_none():
    """When pkb search returns None, search_the_pkb returns None (no honesty fallback)."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": "check status"},
        hooks_dir=PKB_HOOKS,
        agent_type="worker",
    )

    with patch.object(handlers, "_run_pkb_search", return_value=None):
        res = handlers.search_the_pkb(ctx)
        assert res is None


def test_user_prompt_submit_ida_injects_pkb_search():
    """Verify that search_the_pkb injects PKB search results for Ida (agent_type 'ida:ida' and 'ida')."""
    for agent in ("ida:ida", "ida"):
        ctx = HookContext(
            client="claude",
            event="UserPromptSubmit",
            raw={"prompt": "what are the axioms of academicOps?"},
            hooks_dir=PKB_HOOKS,
            cwd="/workspace",
            agent_type=agent,
        )
        mock_search_results = "specs/AXIOMS.md: Found 1 match."
        with patch.object(handlers, "_run_pkb_search", return_value=mock_search_results):
            res = handlers.search_the_pkb(ctx)
            assert res is not None
            expected_text = (
                "<academicOps PKB search results>\n"
                f"{mock_search_results}\n"
                "</academicOps PKB search results>"
            )
            assert res.inject_text == expected_text
            assert res.user_text is None


def test_dispatch_claude_userpromptsubmit_end_to_end(staged_hooks: Path):
    """End-to-end dispatch for Claude Code UserPromptSubmit: no fallback on user prompt without PKB, honesty on peer report."""
    proc_user = subprocess.run(
        [
            sys.executable,
            str(staged_hooks / "dispatch.py"),
            "claude",
            "UserPromptSubmit",
        ],
        input=json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "survey release"}),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc_user.returncode == 0
    assert proc_user.stdout.strip() == ""

    proc_peer = subprocess.run(
        [
            sys.executable,
            str(staged_hooks / "dispatch.py"),
            "claude",
            "UserPromptSubmit",
        ],
        input=json.dumps(
            {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "<task-notification>survey release</task-notification>",
            }
        ),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc_peer.returncode == 0
    assert proc_peer.stdout.strip(), "hook produced empty stdout on peer report"
    data = json.loads(proc_peer.stdout)
    specific = data.get("hookSpecificOutput", {})
    assert specific.get("hookEventName") == "UserPromptSubmit"
    content = specific.get("additionalContext", "")
    expected_inject, _ = load_message_pair(staged_hooks, "honesty")
    assert content == expected_inject


def test_dispatch_agy_preinvocation_end_to_end(staged_hooks: Path):
    """End-to-end dispatch for AGY PreInvocation: no fallback on user prompt without PKB, honesty on peer report."""
    proc_user = subprocess.run(
        [
            sys.executable,
            str(staged_hooks / "dispatch.py"),
            "agy",
            "PreInvocation",
        ],
        input=json.dumps({"hook_event_name": "PreInvocation", "prompt": "survey release"}),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc_user.returncode == 0
    assert proc_user.stdout.strip() == ""

    proc_peer = subprocess.run(
        [
            sys.executable,
            str(staged_hooks / "dispatch.py"),
            "agy",
            "PreInvocation",
        ],
        input=json.dumps(
            {
                "hook_event_name": "PreInvocation",
                "prompt": "<task-notification>survey release</task-notification>",
            }
        ),
        text=True,
        capture_output=True,
        timeout=15,
        cwd=str(staged_hooks),
    )
    assert proc_peer.returncode == 0
    assert proc_peer.stdout.strip(), "hook produced empty stdout on peer report"
    data = json.loads(proc_peer.stdout)
    steps = data.get("injectSteps", [])
    assert len(steps) > 0
    msg = steps[0].get("ephemeralMessage", "")
    expected_inject, _ = load_message_pair(staged_hooks, "honesty")
    assert msg == expected_inject


@pytest.mark.parametrize("agent", ["ida:ida", "ida:sara", "james", "worker"])
def test_no_honesty_fallback_for_coordinators_when_search_fails(agent):
    """search_the_pkb never returns an honesty fallback for any agent."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": "<cross-session-message>report</cross-session-message>"},
        hooks_dir=PKB_HOOKS,
        agent_type=agent,
    )
    with patch.object(handlers, "_run_pkb_search", return_value=None):
        assert handlers.search_the_pkb(ctx) is None


def test_user_prompt_submit_unwraps_telegram_channel_message():
    """Telegram channel prompts are unwrapped so PKB search queries the inner user text."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={
            "prompt": (
                '<channel source="plugin:telegram:telegram" user="nic">'
                "what are the axioms of academicOps?"
                "</channel>"
            )
        },
        hooks_dir=PKB_HOOKS,
        cwd="/workspace",
        agent_type="ida:ida",
    )
    mock_search_results = "specs/AXIOMS.md: Found 1 match."
    with patch.object(handlers, "_run_pkb_search", return_value=mock_search_results) as mock_search:
        res = handlers.search_the_pkb(ctx)
        mock_search.assert_called_once_with("what are the axioms of academicOps?", cwd="/workspace")
        assert res is not None
        assert "<academicOps PKB search results>" in res.inject_text


@pytest.mark.parametrize(
    "peer_prompt",
    [
        '<cross-session-message from="twin-a">PR #12 merged</cross-session-message>',
        '<teammate-message teammate_id="worker">done</teammate-message>',
        "<task-notification>worker finished</task-notification>",
    ],
)
def test_search_the_pkb_skips_peer_reports(peer_prompt):
    """search_the_pkb does not run on peer reports, leaving hearsay to fire and gate to arm."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": peer_prompt},
        hooks_dir=PKB_HOOKS,
        cwd="/workspace",
        agent_type="ida:ida",
    )
    with patch.object(handlers, "_run_pkb_search") as mock_search:
        res = handlers.search_the_pkb(ctx)
        mock_search.assert_not_called()
        assert res is None


def test_extract_prompt_query_unwraps_channels_and_strips_ansi():
    raw = '<channel source="telegram" user="nic">\x1b[32mhello world\x1b[0m</channel>'
    assert handlers.extract_prompt_query(raw) == "hello world"
    assert handlers.extract_prompt_query("plain prompt") == "plain prompt"
    assert handlers.extract_prompt_query("") == ""


def test_extract_prompt_query_keeps_typed_prompt_that_quotes_a_channel_tag():
    """A typed prompt that mentions a channel envelope mid-text is searched whole,
    not truncated to the quoted fragment."""
    typed = 'why does <channel source="telegram">hi</channel> skip hydration?'
    assert handlers.extract_prompt_query(typed) == typed


def test_resolve_mcp_headers_reads_environment():
    with patch.dict(os.environ, {"PKB_MCP_HEADERS": json.dumps({"X-Custom": "val"})}, clear=True):
        assert handlers._resolve_mcp_headers() == {"X-Custom": "val"}

    with patch.dict(
        os.environ,
        {"CF_ACCESS_CLIENT_ID": "id123", "CF_ACCESS_CLIENT_SECRET": "sec456"},
        clear=True,
    ):
        assert handlers._resolve_mcp_headers() == {
            "CF-Access-Client-Id": "id123",
            "CF-Access-Client-Secret": "sec456",
        }


def test_resolve_mcp_headers_ignores_client_config_files(tmp_path: Path):
    """Headers come from the environment only, never from a client's own config file."""
    (tmp_path / ".claude.json").write_text(
        json.dumps({"mcpServers": {"s": {"url": "https://x", "headers": {"A": "b"}}}}),
        encoding="utf-8",
    )
    with patch.dict(os.environ, {"HOME": str(tmp_path)}, clear=True):
        assert handlers._resolve_mcp_headers() == {}


def test_resolve_mcp_headers_logs_malformed_json(caplog):
    with patch.dict(os.environ, {"PKB_MCP_HEADERS": "{not json"}, clear=True):
        with caplog.at_level("WARNING"):
            assert handlers._resolve_mcp_headers() == {}
    assert any("PKB_MCP_HEADERS" in r.getMessage() for r in caplog.records)


def test_search_over_http_with_no_auth_headers_set():
    """PKB search uses in-process HTTP client even when no auth headers are set in the environment."""
    with (
        patch.dict("os.environ", {"PKB_MCP_URL": "https://pkb.example.com"}, clear=True),
        patch.object(
            handlers, "_search_via_fastmcp_client", return_value="1. Match in PKB"
        ) as mock_http,
    ):
        assert handlers._resolve_mcp_headers() == {}
        out = handlers._run_pkb_search("query text")
        assert out == "1. Match in PKB"
        mock_http.assert_called_once_with("https://pkb.example.com", "query text", {})


def test_run_pkb_search_has_no_subprocess_or_cli_route():
    """_run_pkb_search reaches the PKB over HTTP only and has no CLI or subprocess route."""
    with (
        patch.object(handlers, "_search_via_fastmcp_client", return_value="result") as mock_http,
        patch.dict("os.environ", {"PKB_MCP_URL": "https://mcp.example.com"}),
    ):
        out = handlers._run_pkb_search("query text")
        assert out == "result"
        mock_http.assert_called_once_with("https://mcp.example.com", "query text", {})
        # Handlers module must not import or use subprocess for searching
        assert not hasattr(handlers, "subprocess")


def test_http_failure_surfaces_as_hook_failure_naming_the_error():
    """When HTTP access fails, the hook raises the failure naming the error rather than returning honesty."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": "what is the plan?"},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    with (
        patch.dict("os.environ", {"PKB_MCP_URL": "https://pkb.example.com"}),
        patch.object(
            handlers,
            "_search_via_fastmcp_client",
            side_effect=RuntimeError("connection refused to https://pkb.example.com"),
        ),
    ):
        with pytest.raises(RuntimeError, match="connection refused to https://pkb.example.com"):
            handlers.search_the_pkb(ctx)


def test_dispatch_http_failure_surfaces_error_in_hook_output(staged_hooks: Path):
    """End-to-end dispatch confirms an HTTP failure surfaces naming the error, not returning honesty."""
    env = dict(os.environ)
    env["PKB_MCP_URL"] = "http://127.0.0.1:9"  # Unreachable port ensures HTTP connection failure
    for var in (
        "PKB_MCP_HEADERS",
        "DISPATCHER_MCP_TOKEN",
        "WORKER_MCP_TOKEN",
        "CF_ACCESS_CLIENT_ID",
        "CF_ACCESS_CLIENT_SECRET",
    ):
        env.pop(var, None)

    proc = subprocess.run(
        [
            sys.executable,
            str(staged_hooks / "dispatch.py"),
            "claude",
            "UserPromptSubmit",
        ],
        input=json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "check status"}),
        text=True,
        capture_output=True,
        timeout=60,
        cwd=str(staged_hooks),
        env=env,
    )
    assert proc.returncode == 0
    # The failure must be reported in stderr naming the handler and error
    assert "search_the_pkb" in proc.stderr
    # The output must NOT be the honesty message
    expected_honesty, _ = load_message_pair(staged_hooks, "honesty")
    data = json.loads(proc.stdout)
    content = data.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert expected_honesty not in content
    # The failure is surfaced naming the error
    assert "search_the_pkb" in content and "failed with" in content


def test_search_via_fastmcp_client_is_bounded_by_timeout():
    """A stalled backend raises TimeoutError rather than returning None and falling back."""
    import asyncio
    import time

    async def stall(*_args, **_kwargs):
        await asyncio.sleep(30)

    with (
        patch.object(handlers, "_call_pkb_search", stall),
        patch.object(handlers, "_SEARCH_TIMEOUT_SECONDS", 0.2),
    ):
        start = time.monotonic()
        with pytest.raises(TimeoutError):
            handlers._search_via_fastmcp_client("https://x", "q", {"A": "b"})
        assert time.monotonic() - start < 5
