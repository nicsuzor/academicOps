"""The aops MCP server's three tools (dispatch/inspect/stop): request shaping
and response shaping, with `execute_run` and `docker` themselves mocked out —
no container, no docker daemon required. Runtime proof that a real dispatch
through the server produces a running polecat container belongs to a live
field test (specs/polecat/polecat-mcp-server.md), not this suite.

Tool functions are `async def` (fastmcp tools), driven here with
`asyncio.run()` rather than pytest-asyncio — not a project dependency, and
one more than this file needs.
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

import pytest

from lib.polecat import server
from lib.polecat.cli import PolecatError


def _run(coro):
    return asyncio.run(coro)


@dataclass
class _FakeRunResult:
    detached: bool = False
    returncode: int = 0
    session_id: str = "session-abc123"
    session_dir: Path = Path("/tmp/sessions/session-abc123")
    workspace_dir: Path = Path("/tmp/workspace")
    container_id: str | None = "deadbeef"
    container_name: str = "polecat-session-abc123"
    run_record_path: Path = Path("/tmp/sessions/session-abc123/run.json")
    seeded_prompt: str | None = "/pkb:pull aops_123"
    delivery_ok: bool = True
    delivery_err: str | None = None
    image: str = "ghcr.io/nicsuzor/aops-crew:latest"
    task_id: str | None = "aops_123"


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------


def test_dispatch_calls_execute_run_and_shapes_the_result():
    fake = _FakeRunResult()
    with mock.patch.object(server, "execute_run", return_value=fake) as mocked:
        result = _run(server.dispatch(task="aops_123", project="aops"))

    assert mocked.call_args.kwargs["task"] == "aops_123"
    assert mocked.call_args.kwargs["project"] == "aops"
    # Path fields come back as strings — plain-tool results must be JSON-able.
    json.dumps(result)
    assert result["session_id"] == "session-abc123"
    assert result["delivery_ok"] is True
    assert result["task_id"] == "aops_123"


def test_dispatch_defaults_agent_cmd_to_claude():
    with mock.patch.object(server, "execute_run", return_value=_FakeRunResult()) as mocked:
        _run(server.dispatch(task="aops_123"))
    assert mocked.call_args.kwargs["agent_cmd"] == "claude"


def test_dispatch_repo_dir_is_forwarded_as_a_path():
    with mock.patch.object(server, "execute_run", return_value=_FakeRunResult()) as mocked:
        _run(server.dispatch(task="aops_123", repo_dir="/home/nic/src/academicOps"))
    assert mocked.call_args.kwargs["repo_dir"] == Path("/home/nic/src/academicOps")


def test_dispatch_propagates_polecat_error():
    """A resolution failure inside execute_run (missing POLECAT_HOME, an
    unresolvable workspace, ...) must reach the MCP caller as an error, not
    silently vanish or crash the server process."""
    with mock.patch.object(
        server, "execute_run", side_effect=PolecatError("no polecat home configured")
    ):
        with pytest.raises(PolecatError, match="no polecat home configured"):
            _run(server.dispatch(task="aops_123"))


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


def test_inspect_reports_not_found_when_nothing_matches():
    with (
        mock.patch.object(server, "_docker_inspect", return_value=None),
        mock.patch.object(server, "_find_run_record", return_value=None),
    ):
        result = _run(server.inspect(session_id="never-dispatched"))
    assert result["found"] is False
    assert result["container"] is None
    assert result["run_record"] is None


def test_inspect_reports_a_running_container():
    container = {"Id": "deadbeef", "State": {"Running": True, "ExitCode": 0}}
    with (
        mock.patch.object(server, "_docker_inspect", return_value=container),
        mock.patch.object(server, "_find_run_record", return_value=None),
    ):
        result = _run(server.inspect(session_id="session-abc123"))
    assert result["found"] is True
    assert result["running"] is True
    assert result["container"]["id"] == "deadbeef"


def test_inspect_reports_a_finished_run_with_no_live_container():
    run_record = {"status": "success", "exit_code": 0}
    with (
        mock.patch.object(server, "_docker_inspect", return_value=None),
        mock.patch.object(server, "_find_run_record", return_value=run_record),
    ):
        result = _run(server.inspect(session_id="session-abc123"))
    assert result["found"] is True
    assert result["running"] is False
    assert result["container"] is None
    assert result["run_record"] == run_record


def test_inspect_uses_the_same_container_name_dispatch_would():
    with (
        mock.patch.object(server, "_docker_inspect", return_value=None) as mocked,
        mock.patch.object(server, "_find_run_record", return_value=None),
    ):
        _run(server.inspect(session_id="session-abc123"))
    mocked.assert_called_once_with("polecat-session-abc123")


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------


def test_stop_is_a_noop_when_not_running():
    with mock.patch.object(server, "_docker_inspect", return_value=None):
        result = _run(server.stop(session_id="session-abc123"))
    assert result["stopped"] is False
    assert result["reason"] == "not running"


def test_stop_stops_a_running_container():
    container = {"State": {"Running": True}}
    completed = mock.Mock(returncode=0, stderr="")
    with (
        mock.patch.object(server, "_docker_inspect", return_value=container),
        mock.patch("subprocess.run", return_value=completed) as mocked_run,
    ):
        result = _run(server.stop(session_id="session-abc123"))
    assert result["stopped"] is True
    mocked_run.assert_called_once_with(
        ["docker", "stop", "polecat-session-abc123"], capture_output=True, text=True
    )


def test_stop_raises_on_docker_failure():
    container = {"State": {"Running": True}}
    completed = mock.Mock(returncode=1, stderr="no such container")
    with (
        mock.patch.object(server, "_docker_inspect", return_value=container),
        mock.patch("subprocess.run", return_value=completed),
    ):
        with pytest.raises(PolecatError, match="no such container"):
            _run(server.stop(session_id="session-abc123"))


# ---------------------------------------------------------------------------
# _resolve_bind: no default port, per the "no defaults" constraint
# ---------------------------------------------------------------------------


def test_resolve_bind_requires_port(monkeypatch):
    monkeypatch.delenv("POLECAT_MCP_PORT", raising=False)
    with pytest.raises(PolecatError, match="POLECAT_MCP_PORT"):
        server._resolve_bind()


def test_resolve_bind_reads_host_and_port(monkeypatch):
    monkeypatch.setenv("POLECAT_MCP_PORT", "8033")
    monkeypatch.setenv("POLECAT_MCP_HOST", "127.0.0.1")
    assert server._resolve_bind() == ("127.0.0.1", 8033)


def test_resolve_bind_defaults_host_to_all_interfaces(monkeypatch):
    monkeypatch.setenv("POLECAT_MCP_PORT", "8033")
    monkeypatch.delenv("POLECAT_MCP_HOST", raising=False)
    assert server._resolve_bind() == ("0.0.0.0", 8033)


def test_resolve_bind_rejects_a_non_integer_port(monkeypatch):
    monkeypatch.setenv("POLECAT_MCP_PORT", "not-a-number")
    with pytest.raises(PolecatError, match="integer"):
        server._resolve_bind()
