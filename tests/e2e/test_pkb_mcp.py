"""Tests for pkb MCP server across stdio and HTTP/SSE transports.

Every test runs against BOTH transports via the `pkb_server` fixture.
HTTP-only tests use `pkb_http_server` directly.

Requires: pkb binary on PATH, ACA_DATA environment variable set.
"""

import http.client
import json
import os
import signal
import socket
import subprocess
import threading
import time
from abc import ABC, abstractmethod

import pytest


def _pkb_available() -> bool:
    """Check if pkb binary is on PATH and ACA_DATA is set."""
    try:
        result = subprocess.run(["pkb", "--version"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0 and bool(os.environ.get("ACA_DATA"))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _free_port() -> int:
    """Find a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _parse_sse_messages(body: str) -> list[dict]:
    """Extract JSON objects from SSE data: lines."""
    messages = []
    for line in body.split("\n"):
        if line.startswith("data: "):
            try:
                messages.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return messages


# ── JSON-RPC helpers ──────────────────────────────────────────────────────


def _initialize_request(id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pytest-e2e", "version": "0.1"},
        },
    }


def _notification(method: str) -> dict:
    return {"jsonrpc": "2.0", "method": method}


def _tool_call(id: int, name: str, args: dict | None = None) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": id,
        "method": "tools/call",
        "params": {"name": name, "arguments": args or {}},
    }


def _tools_list(id: int) -> dict:
    return {"jsonrpc": "2.0", "id": id, "method": "tools/list", "params": {}}


# ── Transport client abstraction ──────────────────────────────────────────


class PkbClient(ABC):
    """Unified MCP client interface for both transports."""

    @abstractmethod
    def initialize(self) -> dict:
        """Send initialize, return the result object."""
        ...

    @abstractmethod
    def call_tool(self, name: str, args: dict | None = None) -> dict:
        """Call a tool, return the result or error object."""
        ...

    @abstractmethod
    def list_tools(self) -> list[dict]:
        """List available tools."""
        ...

    @property
    @abstractmethod
    def transport_name(self) -> str: ...

    @abstractmethod
    def close(self) -> None: ...


class StdioPkbClient(PkbClient):
    """Sends JSON-RPC over stdin, reads from stdout."""

    def __init__(self):
        self._proc = subprocess.Popen(
            ["pkb", "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._next_id = 1
        self._initialized = False

    def _send_and_receive(self, message: dict) -> dict | None:
        """Send a message and read one response line (if message has id)."""
        line = json.dumps(message) + "\n"
        self._proc.stdin.write(line)
        self._proc.stdin.flush()

        if "id" not in message:
            # Notification — no response expected
            time.sleep(0.1)
            return None

        # Read one response line with timeout
        response_line = self._proc.stdout.readline()
        if not response_line:
            raise RuntimeError("pkb mcp closed stdout unexpectedly")
        return json.loads(response_line)

    def initialize(self) -> dict:
        resp = self._send_and_receive(_initialize_request(self._next_id))
        self._next_id += 1
        self._send_and_receive(_notification("notifications/initialized"))
        self._initialized = True
        return resp.get("result", resp)

    def call_tool(self, name: str, args: dict | None = None) -> dict:
        if not self._initialized:
            self.initialize()
        resp = self._send_and_receive(_tool_call(self._next_id, name, args))
        self._next_id += 1
        if resp and "result" in resp:
            return resp["result"]
        return resp or {}

    def list_tools(self) -> list[dict]:
        if not self._initialized:
            self.initialize()
        resp = self._send_and_receive(_tools_list(self._next_id))
        self._next_id += 1
        return resp.get("result", {}).get("tools", [])

    @property
    def transport_name(self) -> str:
        return "stdio"

    def close(self) -> None:
        if self._proc.poll() is None:
            self._proc.stdin.close()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()


class HttpPkbClient(PkbClient):
    """Sends JSON-RPC over HTTP, parses SSE responses.

    Each call_tool() creates a new http.client.HTTPConnection to validate
    session persistence across connections — this is THE key regression test.
    """

    def __init__(self, port: int, proc: subprocess.Popen):
        self.port = port
        self.proc = proc
        self._session_id: str | None = None
        self._next_id = 1
        self._initialized = False

    def _post(self, body: dict, session_id: str | None = None) -> tuple[int, dict, list[dict]]:
        """POST to /mcp, return (status, headers, parsed_sse_messages)."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=45)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        conn.request("POST", "/mcp", body=json.dumps(body), headers=headers)
        resp = conn.getresponse()
        status = resp.status
        resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        raw_body = resp.read().decode("utf-8")
        conn.close()
        messages = _parse_sse_messages(raw_body)
        return status, resp_headers, messages

    @property
    def session_id(self) -> str | None:
        return self._session_id

    def initialize(self) -> dict:
        status, headers, messages = self._post(_initialize_request(self._next_id))
        self._next_id += 1
        assert status == 200, f"initialize returned {status}"
        self._session_id = headers.get("mcp-session-id")
        assert self._session_id, "no Mcp-Session-Id in initialize response"
        assert messages, "no SSE data events in initialize response"

        # Send initialized notification
        self._post(
            _notification("notifications/initialized"),
            session_id=self._session_id,
        )
        self._initialized = True
        return messages[0].get("result", messages[0])

    def call_tool(self, name: str, args: dict | None = None) -> dict:
        if not self._initialized:
            self.initialize()
        status, _, messages = self._post(
            _tool_call(self._next_id, name, args),
            session_id=self._session_id,
        )
        self._next_id += 1
        assert status == 200, (
            f"tool call '{name}' returned status {status}. Session ID: {self._session_id}"
        )
        assert messages, f"no SSE data in tool call '{name}' response"
        resp = messages[0]
        if "result" in resp:
            return resp["result"]
        return resp

    def list_tools(self) -> list[dict]:
        if not self._initialized:
            self.initialize()
        _, _, messages = self._post(_tools_list(self._next_id), session_id=self._session_id)
        self._next_id += 1
        return messages[0].get("result", {}).get("tools", [])

    def raw_post(self, body: dict, session_id: str | None = None) -> tuple[int, dict, list[dict]]:
        """Expose raw POST for error handling tests."""
        return self._post(body, session_id)

    def raw_post_string(self, raw_body: str) -> tuple[int, dict, str]:
        """POST raw string (for malformed JSON tests)."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=45)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        conn.request("POST", "/mcp", body=raw_body, headers=headers)
        resp = conn.getresponse()
        resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        body_text = resp.read().decode("utf-8")
        conn.close()
        return resp.status, resp_headers, body_text

    @property
    def transport_name(self) -> str:
        return "http"

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()


# ── Fixtures ──────────────────────────────────────────────────────────────


def _start_http_server(port: int) -> subprocess.Popen:
    """Start pkb mcp --http on the given port and wait until it accepts connections."""
    proc = subprocess.Popen(
        ["pkb", "mcp", "--http", "--port", str(port)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=0.5)
            s.close()
            time.sleep(0.5)  # Give server a moment after port opens
            return proc
        except (ConnectionRefusedError, OSError):
            if proc.poll() is not None:
                stderr = proc.stderr.read().decode() if proc.stderr else ""
                pytest.fail(f"pkb mcp --http exited early: {stderr}")
            time.sleep(0.3)
    proc.kill()
    pytest.fail("pkb mcp --http did not start within 30s")


@pytest.fixture(params=["stdio", "http"])
def pkb_server(request):
    """MCP server running in either stdio or HTTP mode.

    Yields a PkbClient that abstracts the transport — callers
    send JSON-RPC dicts and get back parsed responses.
    """
    if not _pkb_available():
        pytest.skip("pkb binary not available or ACA_DATA not set")

    transport = request.param
    if transport == "stdio":
        client = StdioPkbClient()
        yield client
        client.close()
    else:
        port = _free_port()
        proc = _start_http_server(port)
        client = HttpPkbClient(port, proc)
        yield client
        client.close()


@pytest.fixture
def pkb_http_server():
    """HTTP-only server for HTTP-specific tests."""
    if not _pkb_available():
        pytest.skip("pkb binary not available or ACA_DATA not set")

    port = _free_port()
    proc = _start_http_server(port)
    client = HttpPkbClient(port, proc)
    yield client
    client.close()


# ── Tests: both transports ────────────────────────────────────────────────


@pytest.mark.slow
@pytest.mark.integration
class TestPkbMcp:
    """MCP server tests — each runs on both stdio and HTTP transports."""

    def test_initialize(self, pkb_server: PkbClient):
        """Server responds to initialize with serverInfo."""
        result = pkb_server.initialize()
        assert result["serverInfo"]["name"] == "pkb"

    def test_list_tools(self, pkb_server: PkbClient):
        """Server lists tools."""
        tools = pkb_server.list_tools()
        assert len(tools) >= 30, f"expected ≥30 tools, got {len(tools)}"

    def test_graph_stats(self, pkb_server: PkbClient):
        """graph_stats tool returns content."""
        result = pkb_server.call_tool("graph_stats")
        assert result.get("content"), (
            f"graph_stats missing content on {pkb_server.transport_name}: {result}"
        )

    def test_task_summary(self, pkb_server: PkbClient):
        """task_summary tool returns content."""
        result = pkb_server.call_tool("task_summary")
        assert result.get("content"), (
            f"task_summary missing content on {pkb_server.transport_name}: {result}"
        )

    def test_search(self, pkb_server: PkbClient):
        """search tool accepts query and returns without error."""
        result = pkb_server.call_tool("search", {"query": "test", "limit": 3})
        assert "content" in result, (
            f"search missing content on {pkb_server.transport_name}: {result}"
        )

    def test_list_tasks(self, pkb_server: PkbClient):
        """list_tasks returns content."""
        result = pkb_server.call_tool("list_tasks", {"limit": 3})
        assert result.get("content"), (
            f"list_tasks missing content on {pkb_server.transport_name}: {result}"
        )

    def test_multiple_sequential_calls(self, pkb_server: PkbClient):
        """Multiple tool calls on the same session all succeed."""
        for tool in ["graph_stats", "task_summary"]:
            result = pkb_server.call_tool(tool)
            assert result.get("content"), f"{tool} failed on {pkb_server.transport_name}: {result}"

    def test_unknown_tool_error(self, pkb_server: PkbClient):
        """Unknown tool returns error, doesn't crash."""
        result = pkb_server.call_tool("nonexistent_tool_xyz")
        assert result.get("error") or result.get("isError"), (
            f"expected error for unknown tool on {pkb_server.transport_name}: {result}"
        )


# ── Tests: HTTP-only ──────────────────────────────────────────────────────


@pytest.mark.slow
@pytest.mark.integration
class TestPkbHttpOnly:
    """HTTP-specific tests that don't apply to stdio."""

    def test_session_id_returned(self, pkb_http_server: HttpPkbClient):
        """Initialize returns Mcp-Session-Id header."""
        pkb_http_server.initialize()
        assert pkb_http_server.session_id, "no session ID after initialize"

    def test_missing_session_id_rejected(self, pkb_http_server: HttpPkbClient):
        """Request without session ID after init returns error."""
        pkb_http_server.initialize()
        status, _, _ = pkb_http_server.raw_post(_tool_call(99, "graph_stats"), session_id=None)
        assert 400 <= status < 500, f"expected 4xx for missing session ID, got {status}"
        assert pkb_http_server.proc.poll() is None, "server crashed"

    def test_invalid_session_id_rejected(self, pkb_http_server: HttpPkbClient):
        """Request with bogus session ID returns error."""
        pkb_http_server.initialize()
        status, _, _ = pkb_http_server.raw_post(
            _tool_call(99, "graph_stats"), session_id="bogus-id-12345"
        )
        assert 400 <= status < 500, f"expected 4xx for invalid session ID, got {status}"
        assert pkb_http_server.proc.poll() is None, "server crashed"

    def test_malformed_json_rejected(self, pkb_http_server: HttpPkbClient):
        """Malformed JSON returns error, server stays alive."""
        pkb_http_server.initialize()
        status, _, _ = pkb_http_server.raw_post_string("{not valid json!!")
        assert status >= 400, f"expected error for malformed JSON, got {status}"
        assert pkb_http_server.proc.poll() is None, "server crashed"

    def test_concurrent_sessions(self, pkb_http_server: HttpPkbClient):
        """Two independent sessions get different IDs, both work."""
        port = pkb_http_server.port

        results = {}

        def _run_session(name: str, tool: str):
            client = HttpPkbClient(port, pkb_http_server.proc)
            client.initialize()
            result = client.call_tool(tool)
            results[name] = {
                "session_id": client.session_id,
                "result": result,
            }

        t1 = threading.Thread(target=_run_session, args=("a", "graph_stats"))
        t2 = threading.Thread(target=_run_session, args=("b", "task_summary"))
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)

        assert "a" in results and "b" in results, f"sessions didn't complete: {results}"
        assert results["a"]["session_id"] != results["b"]["session_id"], (
            "concurrent sessions got the same session ID"
        )
        for name in ("a", "b"):
            assert results[name]["result"].get("content"), (
                f"session {name} tool call failed: {results[name]['result']}"
            )
