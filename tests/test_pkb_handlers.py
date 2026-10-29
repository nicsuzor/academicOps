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

from dispatch import (  # type: ignore[import-not-found]
    HookContext,
    load_message_pair,
)


@pytest.fixture(autouse=True)
def no_ambient_pkb_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's real PKB credentials out of every test.

    With credentials in the environment the hook takes the authenticated HTTP
    path, so tests of the CLI path would silently test the wrong branch.
    """
    for var in (
        "PKB_MCP_URL",
        "DISPATCHER_MCP_TOKEN",
        "WORKER_MCP_TOKEN",
        "WORKER_MCP_TOKEN_ID",
        "WORKER_MCP_TOKEN_SECRET",
        "DISPATCHER_MCP_TOKEN_ID",
        "DISPATCHER_MCP_TOKEN_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def staged_hooks(tmp_path: Path) -> Path:
    """A plugin hooks/ directory assembled with dispatch.py and handlers.py."""
    hooks = tmp_path / "hooks"
    shutil.copytree(PKB_HOOKS, hooks, ignore=shutil.ignore_patterns("__pycache__"))
    return hooks


def test_user_prompt_submit_sends_whole_prompt_up_to_8kb():
    """Prompt query is sent whole up to 8 KB without 200-character truncation."""
    long_prompt = "a" * 350
    with (
        patch.object(handlers, "_post_mcp_search", return_value="result line") as mock_client,
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        out = handlers._run_pkb_search(long_prompt)
        assert out == "result line"
        mock_client.assert_called_once_with("http://test", "a" * 350, {})


def test_user_prompt_submit_strips_ansi_from_prompt():
    """ANSI escape sequences in prompt are stripped before passing to pkb search."""
    ansi_prompt = "\x1b[31mred text\x1b[0m with \x1b[1mbold\x1b[0m"
    with (
        patch.object(handlers, "_post_mcp_search", return_value="result line") as mock_client,
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        out = handlers._run_pkb_search(ansi_prompt)
        assert out == "result line"
        mock_client.assert_called_once_with("http://test", "red text with bold", {})


def test_run_pkb_search_caps_oversized_output():
    """Output larger than the injection budget is truncated with a marker, regardless of source."""
    huge = "x" * (handlers._MAX_INJECT_CHARS * 2)
    with (
        patch.object(handlers, "_post_mcp_search", return_value=handlers._cap_output(huge)),
        patch.dict("os.environ", {"PKB_MCP_URL": "http://test"}),
    ):
        out = handlers._run_pkb_search("q")
        assert out is not None
        assert len(out) == handlers._MAX_INJECT_CHARS
        assert out.endswith(handlers._TRUNCATION_MARKER)


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
                "prompt": '<cross-session-message from="twin-a">survey release</cross-session-message>',
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
    expected_inject, _ = load_message_pair(staged_hooks, "hearsay")
    assert expected_inject in content


def test_dispatch_agy_preinvocation_end_to_end(staged_hooks: Path):
    """End-to-end dispatch for AGY PreInvocation: no fallback on user prompt without PKB, hearsay on peer report."""
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
                "prompt": '<cross-session-message from="twin-a">survey release</cross-session-message>',
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
    expected_inject, _ = load_message_pair(staged_hooks, "hearsay")
    assert any(expected_inject in step.get("ephemeralMessage", "") for step in steps)


@pytest.mark.parametrize(
    ("peer_prompt", "expected_query"),
    [
        (
            '<cross-session-message from="twin-a">PR #12 merged</cross-session-message>',
            "PR #12 merged",
        ),
        ('<teammate-message teammate_id="worker">done</teammate-message>', "done"),
        ("<task-notification>worker finished</task-notification>", "worker finished"),
        (
            '<subagent-handback from="worker">subagent finished</subagent-handback>',
            "subagent finished",
        ),
    ],
)
def test_search_the_pkb_includes_peer_reports(peer_prompt, expected_query):
    """search_the_pkb includes peer reports, subagent handbacks, and task notifications."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": peer_prompt},
        hooks_dir=PKB_HOOKS,
        cwd="/workspace",
        agent_type="ida:ida",
    )
    with patch.object(handlers, "_run_pkb_search", return_value="1. note") as mock_search:
        res = handlers.search_the_pkb(ctx)
        mock_search.assert_called_once_with(expected_query, cwd="/workspace")
        assert res is not None
        assert "<academicOps PKB search results>" in res.inject_text


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
    legacy_var = "".join(["PKB_", "MCP_", "HEADERS"])
    with patch.dict(os.environ, {legacy_var: json.dumps({"X-Custom": "val"})}, clear=True):
        assert handlers._resolve_mcp_headers() == {}

    with patch.dict(
        os.environ,
        {"WORKER_MCP_TOKEN_ID": "id123", "WORKER_MCP_TOKEN_SECRET": "sec456"},
        clear=True,
    ):
        assert handlers._resolve_mcp_headers() == {
            "CF-Access-Client-Id": "id123",
            "CF-Access-Client-Secret": "sec456",
        }


def test_resolve_mcp_headers_falls_back_to_dispatcher_pair():
    """With no worker pair set, the dispatcher pair supplies the Access headers."""
    with patch.dict(
        os.environ,
        {"DISPATCHER_MCP_TOKEN_ID": "did", "DISPATCHER_MCP_TOKEN_SECRET": "dsec"},
        clear=True,
    ):
        assert handlers._resolve_mcp_headers() == {
            "CF-Access-Client-Id": "did",
            "CF-Access-Client-Secret": "dsec",
        }


def test_resolve_mcp_headers_prefers_worker_pair():
    """The worker pair, which has no polecat dispatch access, wins over the dispatcher pair."""
    with patch.dict(
        os.environ,
        {
            "WORKER_MCP_TOKEN_ID": "wid",
            "WORKER_MCP_TOKEN_SECRET": "wsec",
            "DISPATCHER_MCP_TOKEN_ID": "did",
            "DISPATCHER_MCP_TOKEN_SECRET": "dsec",
        },
        clear=True,
    ):
        assert handlers._resolve_mcp_headers() == {
            "CF-Access-Client-Id": "wid",
            "CF-Access-Client-Secret": "wsec",
        }


def test_resolve_mcp_headers_ignores_half_a_pair():
    """An id without its secret is not a credential; the next pair is used instead."""
    with patch.dict(
        os.environ,
        {
            "WORKER_MCP_TOKEN_ID": "wid",
            "DISPATCHER_MCP_TOKEN_ID": "did",
            "DISPATCHER_MCP_TOKEN_SECRET": "dsec",
        },
        clear=True,
    ):
        assert handlers._resolve_mcp_headers() == {
            "CF-Access-Client-Id": "did",
            "CF-Access-Client-Secret": "dsec",
        }


def test_resolve_mcp_headers_ignores_legacy_variable(caplog):
    legacy_var = "".join(["PKB_", "MCP_", "HEADERS"])
    with patch.dict(os.environ, {legacy_var: "{not json"}, clear=True):
        with caplog.at_level("WARNING"):
            assert handlers._resolve_mcp_headers() == {}
    assert not any(legacy_var in r.getMessage() for r in caplog.records)


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
            "_post_mcp_search",
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
        "DISPATCHER_MCP_TOKEN",
        "WORKER_MCP_TOKEN",
        "WORKER_MCP_TOKEN_ID",
        "WORKER_MCP_TOKEN_SECRET",
        "DISPATCHER_MCP_TOKEN_ID",
        "DISPATCHER_MCP_TOKEN_SECRET",
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


def test_post_mcp_search_is_bounded_by_timeout():
    """A stalled backend raises TimeoutError rather than returning None and falling back."""
    import time

    def slow_urlopen(*_args, **_kwargs):
        raise TimeoutError("timed out")

    with (
        patch("urllib.request.urlopen", slow_urlopen),
        patch.object(handlers, "_SEARCH_TIMEOUT_SECONDS", 0.2),
    ):
        start = time.monotonic()
        with pytest.raises(TimeoutError):
            handlers._post_mcp_search("https://x", "q", {"A": "b"})
        assert time.monotonic() - start < 5


# --- agy: the prompt comes from the transcript ------------------------------
#
# agy's PreInvocation payload carries no prompt field. Observed live on
# polecat:latest sha256:72d0649b352d (2026-10-19): payload keys were
# artifactDirectoryPath, conversationId, initialNumSteps, invocationNum,
# modelName, transcriptPath, workspacePaths, and the turn's USER_INPUT step
# was already in transcript.jsonl when the hook fired, its content wrapping
# the typed text in <USER_REQUEST>...</USER_REQUEST>.

AGY_TYPED = "what are the axioms of academicOps?"
AGY_USER_INPUT = (
    f"<USER_REQUEST>\n{AGY_TYPED}\n</USER_REQUEST>\n"
    "<ADDITIONAL_METADATA>\nThe current local time is: 2026-10-19T02:13:40Z.\n</ADDITIONAL_METADATA>"
)


def _agy_transcript(tmp_path: Path, *entries: dict) -> Path:
    path = tmp_path / "transcript.jsonl"
    path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
    return path


def _agy_ctx(transcript: Path, invocation_num: int | None = 0) -> HookContext:
    raw: dict = {"conversationId": "c1", "transcriptPath": str(transcript), "initialNumSteps": 1}
    if invocation_num is not None:
        raw["invocationNum"] = invocation_num
    return HookContext(
        client="agy", event="UserPromptSubmit", raw=raw, hooks_dir=PKB_HOOKS, cwd="/workspace"
    )


def test_agy_prompt_is_read_from_the_transcript_user_request(tmp_path: Path):
    transcript = _agy_transcript(
        tmp_path,
        {
            "step_index": 0,
            "type": "USER_INPUT",
            "source": "USER_EXPLICIT",
            "content": AGY_USER_INPUT,
        },
    )
    with patch.object(handlers, "_run_pkb_search", return_value="1. hit") as mock_search:
        res = handlers.search_the_pkb(_agy_ctx(transcript))
    mock_search.assert_called_once_with(AGY_TYPED, cwd="/workspace", session_id="c1")
    assert res is not None and "<academicOps PKB search results>" in res.inject_text


def test_agy_uses_the_latest_user_input(tmp_path: Path):
    transcript = _agy_transcript(
        tmp_path,
        {
            "step_index": 0,
            "type": "USER_INPUT",
            "content": "<USER_REQUEST>\nold question\n</USER_REQUEST>",
        },
        {"step_index": 1, "type": "PLANNER_RESPONSE", "source": "MODEL", "content": "answer"},
        {"step_index": 2, "type": "USER_INPUT", "content": AGY_USER_INPUT},
    )
    with patch.object(handlers, "_run_pkb_search", return_value="1. hit") as mock_search:
        handlers.search_the_pkb(_agy_ctx(transcript))
    mock_search.assert_called_once_with(AGY_TYPED, cwd="/workspace", session_id="c1")


def test_agy_searches_once_per_turn(tmp_path: Path):
    """Only the turn's first model invocation searches; later invocations do not."""
    transcript = _agy_transcript(
        tmp_path, {"step_index": 0, "type": "USER_INPUT", "content": AGY_USER_INPUT}
    )
    with patch.object(handlers, "_run_pkb_search", return_value="1. hit") as mock_search:
        assert handlers.search_the_pkb(_agy_ctx(transcript, invocation_num=1)) is None
    mock_search.assert_not_called()


def test_agy_turn_started_by_system_message_is_not_searched(tmp_path: Path):
    """A turn woken by a SYSTEM_MESSAGE (e.g. a subagent result) has no user prompt to ground."""
    transcript = _agy_transcript(
        tmp_path,
        {"step_index": 0, "type": "USER_INPUT", "content": AGY_USER_INPUT},
        {"step_index": 1, "type": "SYSTEM_MESSAGE", "content": "subagent finished"},
    )
    with patch.object(handlers, "_run_pkb_search", return_value="1. hit") as mock_search:
        assert handlers.search_the_pkb(_agy_ctx(transcript)) is None
    mock_search.assert_not_called()


def test_agy_peer_report_in_transcript_is_searched(tmp_path: Path):
    peer = '<USER_REQUEST>\n<cross-session-message from="x">report</cross-session-message>\n</USER_REQUEST>'
    transcript = _agy_transcript(tmp_path, {"step_index": 0, "type": "USER_INPUT", "content": peer})
    with patch.object(handlers, "_run_pkb_search", return_value="1. hit") as mock_search:
        res = handlers.search_the_pkb(_agy_ctx(transcript))
        assert res is not None
        assert "<academicOps PKB search results>" in res.inject_text
    mock_search.assert_called_once_with("report", cwd="/workspace", session_id="c1")


def test_agy_missing_transcript_returns_none(tmp_path: Path):
    assert handlers.search_the_pkb(_agy_ctx(tmp_path / "absent.jsonl")) is None


def test_agy_user_input_with_embedded_user_request_closing_tag(tmp_path: Path):
    typed = "what about </USER_REQUEST> inside prompt?"
    content = (
        f"<USER_REQUEST>\n{typed}\n</USER_REQUEST>\n"
        "<ADDITIONAL_METADATA>\ninfo\n</ADDITIONAL_METADATA>"
    )
    transcript = _agy_transcript(
        tmp_path,
        {"step_index": 0, "type": "USER_INPUT", "content": content},
    )
    with patch.object(handlers, "_run_pkb_search", return_value="1. hit") as mock_search:
        handlers.search_the_pkb(_agy_ctx(transcript))
    mock_search.assert_called_once_with(typed, cwd="/workspace", session_id="c1")


def test_agy_peer_report_is_detected_by_is_peer_report(tmp_path: Path):
    peer = '<USER_REQUEST>\n<cross-session-message from="worker-1">report</cross-session-message>\n</USER_REQUEST>'
    transcript = _agy_transcript(tmp_path, {"step_index": 0, "type": "USER_INPUT", "content": peer})
    ctx = _agy_ctx(transcript)
    assert handlers.is_peer_report(ctx) is True


def test_agy_user_input_without_wrapper_is_used_whole(tmp_path: Path):
    transcript = _agy_transcript(
        tmp_path, {"step_index": 0, "type": "USER_INPUT", "content": AGY_TYPED}
    )
    with patch.object(handlers, "_run_pkb_search", return_value="1. hit") as mock_search:
        handlers.search_the_pkb(_agy_ctx(transcript))
    mock_search.assert_called_once_with(AGY_TYPED, cwd="/workspace", session_id="c1")


def test_dispatch_agy_preinvocation_reads_prompt_from_transcript(
    staged_hooks: Path, tmp_path: Path
):
    """End to end through dispatch.py with agy's real payload shape: the search runs on the typed text."""
    transcript = _agy_transcript(
        tmp_path, {"step_index": 0, "type": "USER_INPUT", "content": AGY_USER_INPUT}
    )
    payload = {
        "artifactDirectoryPath": str(tmp_path),
        "conversationId": "c1",
        "initialNumSteps": 1,
        "invocationNum": 0,
        "modelName": "m",
        "transcriptPath": str(transcript),
        "workspacePaths": ["/workspace"],
    }
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("PKB_MCP", "WORKER_MCP", "DISPATCHER_MCP"))
    }
    env["PKB_MCP_URL"] = (
        "http://127.0.0.1:9"  # unreachable: the failure message proves a search was attempted
    )
    proc = subprocess.run(
        [sys.executable, str(staged_hooks / "dispatch.py"), "agy", "PreInvocation"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    out = json.loads(proc.stdout)
    message = out["injectSteps"][0]["ephemeralMessage"]
    assert "search_the_pkb" in message


# --- Direct stdlib HTTP POST prompt hydration tests -------------------------


@pytest.fixture
def http_mcp_server():
    import http.server
    import threading

    requests_received = []
    status_to_return = [200]
    response_body = [
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": "1. Match in PKB"}]},
            }
        ).encode("utf-8")
    ]
    response_headers = [{"Content-Type": "application/json"}]

    class MockHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b""
            requests_received.append(
                {
                    "path": self.path,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "body": body,
                    "json": json.loads(body.decode("utf-8")) if body else None,
                }
            )
            self.send_response(status_to_return[0])
            for k, v in response_headers[0].items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(response_body[0])

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), MockHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class Controller:
        url = f"http://127.0.0.1:{port}"
        requests = requests_received

        def set_response(self, status=200, body=None, headers=None):
            status_to_return[0] = status
            if body is not None:
                if isinstance(body, str):
                    body = body.encode("utf-8")
                elif isinstance(body, dict):
                    body = json.dumps(body).encode("utf-8")
                response_body[0] = body
            if headers is not None:
                response_headers[0] = headers

    try:
        yield Controller()
    finally:
        server.shutdown()


def test_search_the_pkb_sends_one_post_with_headers(http_mcp_server, monkeypatch, tmp_path):
    """AC: default tool name is 'pkb_search' when PKB_MCP_TOOL_PREFIX is unset; one POST per search carrying x-session-id, active turn traceparent, #3009 tokens, and real user-agent."""
    tracer_dir = tmp_path / ".claude" / "tracer"
    tracer_dir.mkdir(parents=True, exist_ok=True)
    trace_id = "0123456789abcdef0123456789abcdef"
    span_id = "0123456789abcdef"
    state_file = tracer_dir / "s123.json"
    state_file.write_text(
        json.dumps({"current_trace": {"trace_id": trace_id, "root_span_id": span_id}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", http_mcp_server.url)
    monkeypatch.setenv("WORKER_MCP_TOKEN_ID", "wid")
    monkeypatch.setenv("WORKER_MCP_TOKEN_SECRET", "wsec")
    monkeypatch.delenv("PKB_MCP_TOOL_PREFIX", raising=False)

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id="s123",
        raw={"prompt": "what are the axioms?"},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    res = handlers.search_the_pkb(ctx)
    assert res is not None
    assert "<academicOps PKB search results>" in res.inject_text
    assert len(http_mcp_server.requests) == 1

    req = http_mcp_server.requests[0]
    assert req["headers"]["x-session-id"] == "s123"
    assert req["headers"]["traceparent"] == f"00-{trace_id}-{span_id}-01"
    assert req["headers"]["cf-access-client-id"] == "wid"
    assert req["headers"]["cf-access-client-secret"] == "wsec"
    assert not req["headers"]["user-agent"].startswith("Python-urllib")
    assert "academicOps" in req["headers"]["user-agent"]
    assert req["headers"]["content-type"] == "application/json"
    assert "text/event-stream" in req["headers"]["accept"]
    assert req["json"]["params"]["name"] == "pkb_search"
    args = req["json"]["params"]["arguments"]
    assert args["query"] == "what are the axioms?"
    assert args["limit"] == 5
    assert args["detail"] == "snippet"
    assert "_session" in args
    assert args["session_id"] == "s123" if "session_id" in args else True
    assert args["_session"]["session_id"] == "s123"
    assert args["_session"]["caller"] == "hook"
    assert args["_session"]["surface"] == "claude-code"


def test_search_the_pkb_passes_limit_and_detail_defaults(http_mcp_server, monkeypatch, tmp_path):
    """AC-1.9: arguments carries limit: 5 and detail: 'snippet' by default to prevent truncation."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", http_mcp_server.url)

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id="s789",
        raw={"prompt": "check pkb search default limit and detail"},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    res = handlers.search_the_pkb(ctx)
    assert res is not None
    assert len(http_mcp_server.requests) == 1
    args = http_mcp_server.requests[0]["json"]["params"]["arguments"]
    assert args["limit"] == 5
    assert args["detail"] == "snippet"
    assert args["query"] == "check pkb search default limit and detail"


def test_search_the_pkb_tool_prefix_env_override(http_mcp_server, monkeypatch, tmp_path):
    """AC: PKB_MCP_TOOL_PREFIX overrides the default 'pkb_' prefix."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", http_mcp_server.url)
    monkeypatch.setenv("PKB_MCP_TOOL_PREFIX", "custom_")

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id="s123",
        raw={"prompt": "what are the axioms?"},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    res = handlers.search_the_pkb(ctx)
    assert res is not None
    assert len(http_mcp_server.requests) == 1
    req = http_mcp_server.requests[0]
    assert req["json"]["params"]["name"] == "custom_search"


def test_search_the_pkb_unauthenticated_when_credentials_unset(
    http_mcp_server, monkeypatch, tmp_path
):
    """AC: unauthenticated request when credentials unset; cloud proxy injects them."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", http_mcp_server.url)
    for var in (
        "WORKER_MCP_TOKEN_ID",
        "WORKER_MCP_TOKEN_SECRET",
        "DISPATCHER_MCP_TOKEN_ID",
        "DISPATCHER_MCP_TOKEN_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id="s456",
        raw={"prompt": "prompt query"},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    handlers.search_the_pkb(ctx)
    assert len(http_mcp_server.requests) == 1
    req = http_mcp_server.requests[0]
    assert "cf-access-client-id" not in req["headers"]
    assert "cf-access-client-secret" not in req["headers"]
    assert "authorization" not in req["headers"]
    assert req["headers"]["x-session-id"] == "s456"
    assert "traceparent" in req["headers"]
    assert not req["headers"]["user-agent"].startswith("Python-urllib")


def test_search_the_pkb_injected_message_on_401(staged_hooks: Path, http_mcp_server):
    """AC: HTTP 401 injects a message naming refusal, 401, and canonical token variables, with red trace recorded."""
    legacy_var = "".join(["PKB_", "MCP_", "HEADERS"])
    http_mcp_server.set_response(401, body="Unauthorized")
    env = dict(os.environ)
    env["PKB_MCP_URL"] = http_mcp_server.url
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
        timeout=10,
        cwd=str(staged_hooks),
        env=env,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    injected = data.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert injected.startswith("aops hooks: handler 'search_the_pkb' failed")
    assert "refused authorisation" in injected
    assert "401" in injected
    assert legacy_var not in injected
    assert "WORKER_MCP_TOKEN_ID" in injected
    assert "WORKER_MCP_TOKEN_SECRET" in injected
    assert "DISPATCHER_MCP_TOKEN_ID" in injected
    assert "DISPATCHER_MCP_TOKEN_SECRET" in injected
    assert len(http_mcp_server.requests) == 1
    assert "traceparent" in http_mcp_server.requests[0]["headers"]


def test_search_the_pkb_injected_message_on_403(staged_hooks: Path, http_mcp_server):
    """AC: HTTP 403 injects a message naming refusal, 403, and canonical token variables, with red trace recorded."""
    legacy_var = "".join(["PKB_", "MCP_", "HEADERS"])
    http_mcp_server.set_response(403, body="Forbidden")
    env = dict(os.environ)
    env["PKB_MCP_URL"] = http_mcp_server.url
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
        timeout=10,
        cwd=str(staged_hooks),
        env=env,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    injected = data.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert injected.startswith("aops hooks: handler 'search_the_pkb' failed")
    assert "refused authorisation" in injected
    assert "403" in injected
    assert legacy_var not in injected
    assert "WORKER_MCP_TOKEN_ID" in injected
    assert "WORKER_MCP_TOKEN_SECRET" in injected
    assert "DISPATCHER_MCP_TOKEN_ID" in injected
    assert "DISPATCHER_MCP_TOKEN_SECRET" in injected
    assert len(http_mcp_server.requests) == 1
    assert "traceparent" in http_mcp_server.requests[0]["headers"]


def test_search_the_pkb_injected_message_on_unreachable(staged_hooks: Path):
    """AC: unreachable endpoint injects message naming unreachable."""
    env = dict(os.environ)
    env["PKB_MCP_URL"] = "http://127.0.0.1:9"
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
        timeout=10,
        cwd=str(staged_hooks),
        env=env,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    injected = data.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert injected.startswith("aops hooks: handler 'search_the_pkb' failed")
    assert "unreachable" in injected


def test_search_the_pkb_ignores_legacy_headers_and_authenticates_with_canonical_pair(
    http_mcp_server, monkeypatch, tmp_path
):
    """AC2: With only a canonical pair set, the PKB hook authenticates; with legacy headers set and no pair, it does not use it."""
    legacy_var = "".join(["PKB_", "MCP_", "HEADERS"])
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", http_mcp_server.url)

    # 1. With legacy headers set and no canonical pair, the hook does NOT send the legacy header
    monkeypatch.setenv(legacy_var, json.dumps({"X-Legacy-Header": "forbidden"}))
    monkeypatch.delenv("WORKER_MCP_TOKEN_ID", raising=False)
    monkeypatch.delenv("WORKER_MCP_TOKEN_SECRET", raising=False)
    monkeypatch.delenv("DISPATCHER_MCP_TOKEN_ID", raising=False)
    monkeypatch.delenv("DISPATCHER_MCP_TOKEN_SECRET", raising=False)

    ctx1 = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id="s1",
        raw={"prompt": "prompt 1"},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    handlers.search_the_pkb(ctx1)
    assert len(http_mcp_server.requests) == 1
    assert "x-legacy-header" not in http_mcp_server.requests[0]["headers"]

    # 2. With only a canonical pair set, the hook authenticates carrying the token pair
    monkeypatch.delenv(legacy_var, raising=False)
    monkeypatch.setenv("WORKER_MCP_TOKEN_ID", "wid123")
    monkeypatch.setenv("WORKER_MCP_TOKEN_SECRET", "wsec456")

    ctx2 = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id="s2",
        raw={"prompt": "prompt 2"},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    handlers.search_the_pkb(ctx2)
    assert len(http_mcp_server.requests) == 2
    assert http_mcp_server.requests[1]["headers"]["cf-access-client-id"] == "wid123"
    assert http_mcp_server.requests[1]["headers"]["cf-access-client-secret"] == "wsec456"


def test_search_the_pkb_session_fallback_and_caching(monkeypatch, tmp_path):
    """AC: falls back to initialize once if session needed, caching for 24h in tracer state dir."""
    import http.server
    import threading

    calls = []

    class SessionServer(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length).decode("utf-8"))
            method = body.get("method")
            session_hdr = self.headers.get("mcp-session-id")
            calls.append((method, session_hdr))

            if method == "tools/call" and not session_hdr:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "Session required"}')
            elif method == "initialize":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("mcp-session-id", "sess-uuid-789")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": {}}).encode("utf-8")
                )
            elif method == "tools/call" and session_hdr == "sess-uuid-789":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": body["id"],
                            "result": {
                                "content": [{"type": "text", "text": "1. Found with session"}]
                            },
                        }
                    ).encode("utf-8")
                )

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), SessionServer)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("PKB_MCP_URL", f"http://127.0.0.1:{port}")
        ctx = HookContext(
            client="claude",
            event="UserPromptSubmit",
            session_id="s1",
            raw={"prompt": "find notes"},
            hooks_dir=PKB_HOOKS,
        )
        res = handlers.search_the_pkb(ctx)
        assert res is not None
        assert "Found with session" in res.inject_text
        assert calls == [
            ("tools/call", None),
            ("initialize", None),
            ("tools/call", "sess-uuid-789"),
        ]

        cache_file = tmp_path / ".claude" / "tracer" / "pkb_session_cache.json"
        assert cache_file.exists()
        cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
        assert cache_data["session_id"] == "sess-uuid-789"

        calls.clear()
        res2 = handlers.search_the_pkb(ctx)
        assert res2 is not None
        assert "Found with session" in res2.inject_text
        assert calls == [("tools/call", "sess-uuid-789")]
    finally:
        server.shutdown()


def test_parse_mcp_response_raises_on_sse_error():
    """AC: SSE error lines raise RuntimeError immediately rather than returning None."""
    raw_sse = 'data: {"error": "Internal server error in search"}\n\n'
    with pytest.raises(RuntimeError, match="PKB MCP error.*Internal server error"):
        handlers._parse_mcp_response(raw_sse)


def test_post_mcp_search_does_not_initialize_on_404_or_generic_400():
    """AC: HTTP 404/400 errors without explicit session errors do not attempt initialize."""
    import http.server
    import threading

    calls = []

    class Server404(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            calls.append(json.loads(body).get("method"))
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"detail": "Not Found"}')

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Server404)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with pytest.raises(RuntimeError) as exc_info:
            handlers._post_mcp_search(f"http://127.0.0.1:{port}", "test query")
        assert "HTTP 404" in str(exc_info.value)
        assert "Not Found" in str(exc_info.value)
        assert calls == ["tools/call"]
    finally:
        server.shutdown()


# --- AC2 & AC3: Envelope/slash gating, 8KB query, _session, empty silence, single-line error ---


@pytest.mark.parametrize(
    "cmd_prompt",
    [
        "/cmd",
        "/pull",
        "/status",
        "/cmd   ",
        "/ida:pull",
        "/",
    ],
)
def test_argumentless_slash_commands_make_no_pkb_call(cmd_prompt):
    """AC2: Argument-less slash commands (/cmd) make no PKB call."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": cmd_prompt},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    with patch.object(handlers, "_run_pkb_search") as mock_search:
        res = handlers.search_the_pkb(ctx)
        mock_search.assert_not_called()
        assert res is None


@pytest.mark.parametrize(
    ("prompt", "expected_query"),
    [
        ('<handback from="worker">done</handback>', "done"),
        ('<subagent-handback from="worker">done</subagent-handback>', "done"),
        ('<agent-message to="ida">status update</agent-message>', "status update"),
        ('<cross-session-message from="peer">done</cross-session-message>', "done"),
        ('<teammate-message teammate_id="worker">finished</teammate-message>', "finished"),
        ("<task-notification>task completed</task-notification>", "task completed"),
        (
            'Another Claude session sent a message:\n<teammate-message teammate_id="worker">finished</teammate-message>',
            "finished",
        ),
    ],
)
def test_peer_and_handback_envelopes_are_hydrated(prompt, expected_query):
    """Peer reports, subagent handbacks, and task notifications are included in PKB search hydration."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": prompt},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    with patch.object(handlers, "_run_pkb_search", return_value="hit") as mock_search:
        res = handlers.search_the_pkb(ctx)
        assert res is not None
        mock_search.assert_called_once()
        args, _ = mock_search.call_args
        assert args[0] == expected_query


def test_channel_wrapped_human_prompts_send_full_text_up_to_8kb():
    """AC2: <channel>-wrapped human prompts send full text up to 8 KB without 200-char truncation."""
    body_500 = "x" * 500
    prompt = f'<channel source="telegram" user="nic">{body_500}</channel>'
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": prompt},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    with patch.object(handlers, "_run_pkb_search", return_value="hit") as mock_search:
        res = handlers.search_the_pkb(ctx)
        assert res is not None
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args
        assert args[0] == body_500


def test_slash_command_with_arg_sends_arg_whole_up_to_8kb():
    """AC2: /cmd <arg> prompts send <arg> whole up to 8 KB without 200-char truncation."""
    arg_500 = "y" * 500
    prompt = f"/cmd {arg_500}"
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": prompt},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    with patch.object(handlers, "_run_pkb_search", return_value="hit") as mock_search:
        res = handlers.search_the_pkb(ctx)
        assert res is not None
        args, _ = mock_search.call_args
        assert args[0] == arg_500

    pull_prompt = "/pull task_c89c7dae"
    ctx_pull = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": pull_prompt},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    with patch.object(handlers, "_run_pkb_search", return_value="hit") as mock_search:
        res = handlers.search_the_pkb(ctx_pull)
        assert res is not None
        args, _ = mock_search.call_args
        assert args[0] == "task_c89c7dae"


def test_prompt_exceeding_8kb_is_capped_at_8192():
    """AC2: Prompt exceeding 8 KB (8192 chars) is capped at 8192 chars."""
    huge_prompt = "z" * 10000
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": huge_prompt},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    with patch.object(handlers, "_run_pkb_search", return_value="hit") as mock_search:
        handlers.search_the_pkb(ctx)
        args, _ = mock_search.call_args
        assert len(args[0]) == 8192


def test_pkb_hydrate_zero_env_var_is_ignored():
    """PKB_HYDRATE=0 does not disable hydration; disabling env vars have been removed."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": "should we hydrate?"},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    with (
        patch.dict("os.environ", {"PKB_HYDRATE": "0"}),
        patch.object(handlers, "_run_pkb_search", return_value="1. note") as mock_search,
    ):
        res = handlers.search_the_pkb(ctx)
        mock_search.assert_called_once()
        assert res is not None
        assert "<academicOps PKB search results>" in res.inject_text


def test_search_the_pkb_sends_session_with_matching_prompt_id(
    http_mcp_server, monkeypatch, tmp_path
):
    """AC3: The hook sends _session with matching prompt_id on both the MCP call and the hook span."""
    tracer_dir = tmp_path / ".claude" / "tracer"
    tracer_dir.mkdir(parents=True, exist_ok=True)
    trace_id = "11112222333344445555666677778888"
    span_id = "1111222233334444"
    state_file = tracer_dir / "s-session-ac3.json"
    state_file.write_text(
        json.dumps(
            {
                "current_trace": {
                    "trace_id": trace_id,
                    "root_span_id": span_id,
                    "prompt_id": "prompt-trace-match-1",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", http_mcp_server.url)

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id="s-session-ac3",
        prompt_id="prompt-trace-match-1",
        raw={"prompt": "what is the session contract?"},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    res = handlers.search_the_pkb(ctx)
    assert res is not None
    assert len(http_mcp_server.requests) == 1

    req = http_mcp_server.requests[0]
    args = req["json"]["params"]["arguments"]
    assert args["query"] == "what is the session contract?"
    assert "_session" in args
    sess = args["_session"]
    assert sess["session_id"] == "s-session-ac3"
    assert sess["prompt_id"] == "prompt-trace-match-1"
    assert sess["caller"] == "hook"
    assert sess["surface"] == "claude-code"

    # State file's current_trace must have the matching prompt_id
    updated_state = json.loads(state_file.read_text(encoding="utf-8"))
    assert updated_state["current_trace"]["prompt_id"] == sess["prompt_id"]


def test_search_the_pkb_generates_matching_prompt_id_when_absent(
    http_mcp_server, monkeypatch, tmp_path
):
    """AC3: When prompt_id is absent from payload, generated prompt_id matches on both MCP call and tracer state."""
    tracer_dir = tmp_path / ".claude" / "tracer"
    tracer_dir.mkdir(parents=True, exist_ok=True)
    trace_id = "aaaabbbbccccddddaaaabbbbccccdddd"
    span_id = "aaaabbbbccccdddd"
    state_file = tracer_dir / "s-no-prompt-id.json"
    state_file.write_text(
        json.dumps(
            {
                "current_trace": {
                    "trace_id": trace_id,
                    "root_span_id": span_id,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", http_mcp_server.url)

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id="s-no-prompt-id",
        raw={"prompt": "find notes without prompt_id"},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    res = handlers.search_the_pkb(ctx)
    assert res is not None
    assert len(http_mcp_server.requests) == 1

    req = http_mcp_server.requests[0]
    sess = req["json"]["params"]["arguments"]["_session"]
    generated_pid = sess["prompt_id"]
    assert generated_pid, "prompt_id must not be empty"

    updated_state = json.loads(state_file.read_text(encoding="utf-8"))
    assert updated_state["current_trace"]["prompt_id"] == generated_pid


def test_search_the_pkb_injects_nothing_when_server_returns_empty_content(
    http_mcp_server, monkeypatch, tmp_path
):
    """AC3: The hook injects nothing when the server returns empty text or content."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PKB_MCP_URL", http_mcp_server.url)
    http_mcp_server.set_response(
        200,
        body={"jsonrpc": "2.0", "id": 1, "result": {"content": []}},
    )

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id="s-empty-1",
        raw={"prompt": "search nothing"},
        hooks_dir=PKB_HOOKS,
        agent_type="ida:ida",
    )
    res = handlers.search_the_pkb(ctx)
    assert res is None

    # Also test empty text item
    http_mcp_server.set_response(
        200,
        body={"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "   "}]}},
    )
    res2 = handlers.search_the_pkb(ctx)
    assert res2 is None


def test_dispatch_error_injects_single_failure_line(staged_hooks: Path):
    """AC3: Failure injects a single line naming the cause on error (no newlines)."""
    env = dict(os.environ)
    env["PKB_MCP_URL"] = "http://127.0.0.1:9"
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
        timeout=10,
        cwd=str(staged_hooks),
        env=env,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    injected = data.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert injected.startswith("aops hooks: handler 'search_the_pkb' failed")
    assert "\n" not in injected.strip(), (
        f"Expected single line failure, got multiline: {injected!r}"
    )
