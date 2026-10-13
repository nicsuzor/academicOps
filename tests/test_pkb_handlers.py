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
        "PKB_MCP_HEADERS",
        "PKB_MCP_TOKEN",
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
    """Verify that search_the_pkb is wired to UserPromptSubmit."""
    assert "UserPromptSubmit" in handlers.HANDLERS
    registered = handlers.HANDLERS["UserPromptSubmit"]
    assert handlers.search_the_pkb in registered


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
        patch("shutil.which", return_value="/usr/bin/mcp"),
        patch("subprocess.run") as mock_run,
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        mock_proc = subprocess.CompletedProcess(
            args=["/usr/bin/mcp", "search", "a" * 200],
            returncode=0,
            stdout="result line\n",
            stderr="",
        )
        mock_run.return_value = mock_proc
        out = handlers._run_pkb_search(long_prompt)
        assert out == "result line"
        assert mock_run.call_args[0][0][:2] == ["/usr/bin/mcp", "call"]
    assert mock_run.call_args[0][0][3:5] == ["pkb_search", "--input-json"]
    assert "a" * 200 in mock_run.call_args[0][0][5]


def test_user_prompt_submit_strips_ansi_from_prompt():
    """ANSI escape sequences in prompt are stripped before passing to pkb search."""
    ansi_prompt = "\x1b[31mred text\x1b[0m with \x1b[1mbold\x1b[0m"
    with (
        patch("shutil.which", return_value="/usr/bin/mcp"),
        patch("subprocess.run") as mock_run,
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        mock_proc = subprocess.CompletedProcess(
            args=["/usr/bin/mcp", "search", "red text with bold"],
            returncode=0,
            stdout="result line\n",
            stderr="",
        )
        mock_run.return_value = mock_proc
        out = handlers._run_pkb_search(ansi_prompt)
        assert out == "result line"
        assert mock_run.call_args[0][0][:2] == ["/usr/bin/mcp", "call"]
    assert mock_run.call_args[0][0][3:5] == ["pkb_search", "--input-json"]
    assert "red text with bold" in mock_run.call_args[0][0][5]


def test_run_pkb_search_uses_measured_timeout():
    """subprocess timeout matches the measured backend-latency ceiling, not the old 15s guess."""
    with (
        patch("shutil.which", return_value="/usr/bin/mcp"),
        patch("subprocess.run") as mock_run,
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["/usr/bin/mcp", "search", "q"], returncode=0, stdout="result\n", stderr=""
        )
        handlers._run_pkb_search("q")
        assert mock_run.call_args.kwargs["timeout"] == handlers._SEARCH_TIMEOUT_SECONDS
        assert handlers._SEARCH_TIMEOUT_SECONDS < 15


def test_run_pkb_search_caps_oversized_output():
    """Output larger than the injection budget is truncated with a marker, regardless of source."""
    huge = "x" * (handlers._MAX_INJECT_CHARS * 2)
    with (
        patch("shutil.which", return_value="/usr/bin/mcp"),
        patch("subprocess.run") as mock_run,
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["/usr/bin/mcp", "search", "q"], returncode=0, stdout=huge, stderr=""
        )
        out = handlers._run_pkb_search("q")
        assert out is not None
        assert len(out) == handlers._MAX_INJECT_CHARS
        assert out.endswith(handlers._TRUNCATION_MARKER)


def test_run_pkb_search_leaves_normal_output_untouched():
    """Output well under the cap passes through byte-for-byte."""
    normal = "1. Some doc (score: 0.08)\n   path/to/doc.md\n   an extract of the match."
    with (
        patch("shutil.which", return_value="/usr/bin/mcp"),
        patch("subprocess.run") as mock_run,
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["/usr/bin/mcp", "search", "q"], returncode=0, stdout=normal, stderr=""
        )
        out = handlers._run_pkb_search("q")
        assert out == normal


def test_user_prompt_submit_fallback_when_prompt_is_empty():
    """When prompt is empty, search_the_pkb falls back to existing messages (honesty)."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": ""},
        hooks_dir=PKB_HOOKS,
        agent_type="worker",
    )

    expected_inject, expected_user = load_message_pair(PKB_HOOKS, "honesty")

    res = handlers.search_the_pkb(ctx)
    assert res is not None
    assert "<academicOps PKB search results>" not in res.inject_text
    assert res.inject_text == expected_inject
    assert res.user_text == expected_user


def test_user_prompt_submit_fallback_when_pkb_search_fails():
    """When pkb search returns None (binary missing or failure), falls back to existing messages."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": "check status"},
        hooks_dir=PKB_HOOKS,
        agent_type="worker",
    )

    expected_inject, _ = load_message_pair(PKB_HOOKS, "honesty")

    with patch.object(handlers, "_run_pkb_search", return_value=None):
        res = handlers.search_the_pkb(ctx)
        assert res is not None
        assert "<academicOps PKB search results>" not in res.inject_text
        assert res.inject_text == expected_inject


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
    """End-to-end dispatch for Claude Code UserPromptSubmit with search success."""
    proc = subprocess.run(
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
    assert proc.returncode == 0
    assert proc.stdout.strip(), "hook produced empty stdout"
    data = json.loads(proc.stdout)
    specific = data.get("hookSpecificOutput", {})
    assert specific.get("hookEventName") == "UserPromptSubmit"
    content = specific.get("additionalContext", "")
    # Either PKB search result or the fallback honesty message, byte-for-byte
    # the file as staged for this run — not a literal restated here.
    expected_inject, _ = load_message_pair(staged_hooks, "honesty")
    assert content.startswith("<academicOps PKB search results>") or content == expected_inject


def test_dispatch_agy_preinvocation_end_to_end(staged_hooks: Path):
    """End-to-end dispatch for AGY PreInvocation (mapped to UserPromptSubmit) with search success."""
    proc = subprocess.run(
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
    assert proc.returncode == 0
    assert proc.stdout.strip(), "hook produced empty stdout"
    data = json.loads(proc.stdout)
    steps = data.get("injectSteps", [])
    assert len(steps) > 0
    msg = steps[0].get("ephemeralMessage", "")
    expected_inject, _ = load_message_pair(staged_hooks, "honesty")
    assert msg.startswith("<academicOps PKB search results>") or msg == expected_inject


@pytest.mark.parametrize("agent", ["ida:ida", "ida:sara", "james"])
def test_no_honesty_fallback_for_coordinators_when_search_fails(agent):
    """Ida and Sara get the hearsay reminder on a peer report; the honesty
    fallback would displace it, since only the first advisory is delivered."""
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


def test_run_pkb_search_with_headers_never_falls_back_to_unauthenticated_cli():
    """With headers configured, a failed HTTP search returns None; it does not
    retry unauthenticated through the CLI and double the prompt's wait."""
    with (
        patch.object(handlers, "_resolve_mcp_headers", return_value={"X-Auth": "t"}),
        patch.object(handlers, "_search_via_fastmcp_client", return_value=None) as mock_http,
        patch("subprocess.run") as mock_subproc,
        patch.dict("os.environ", {"PKB_MCP_URL": "https://mcp.example.com"}),
    ):
        assert handlers._run_pkb_search("query text") is None
        mock_http.assert_called_once_with("https://mcp.example.com", "query text", {"X-Auth": "t"})
        mock_subproc.assert_not_called()


def test_search_via_fastmcp_client_is_bounded_by_timeout():
    """A stalled backend cannot hold the prompt past the search timeout."""
    import asyncio
    import time

    async def stall(*_args):
        await asyncio.sleep(30)

    with (
        patch.object(handlers, "_call_pkb_search", stall),
        patch.object(handlers, "_SEARCH_TIMEOUT_SECONDS", 0.2),
    ):
        start = time.monotonic()
        assert handlers._search_via_fastmcp_client("https://x", "q", {"A": "b"}) is None
        assert time.monotonic() - start < 5
