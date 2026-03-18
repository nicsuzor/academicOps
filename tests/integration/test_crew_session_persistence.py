"""E2E tests for crew session transcript persistence.

Verifies that Claude sessions inside Docker containers produce persistent
JSONL transcript files via the session_dir mount in _build_docker_cmd().
"""

import json
import logging
import sys
from pathlib import Path

import pytest

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unit tests — no Docker required
# ---------------------------------------------------------------------------


@pytest.fixture
def build_docker_cmd():
    """Import _build_docker_cmd from polecat."""
    repo_root = Path(__file__).resolve().parents[2]
    polecat_dir = str(repo_root / "polecat")
    aops_core_dir = str(repo_root / "aops-core")
    if polecat_dir not in sys.path:
        sys.path.insert(0, polecat_dir)
    if aops_core_dir not in sys.path:
        sys.path.insert(0, aops_core_dir)
    from cli import _build_docker_cmd

    return _build_docker_cmd


def test_session_dir_mount_in_docker_cmd(build_docker_cmd, tmp_path):
    """session_dir param adds a -v mount for .claude/projects."""
    session_dir = tmp_path / "test-sessions"
    cmd = build_docker_cmd(
        cli_tool="claude",
        work_dir=tmp_path,
        env={},
        agent_cmd=["claude", "-p", "hello"],
        is_interactive=False,
        session_dir=session_dir,
    )
    cmd_str = " ".join(cmd)
    assert f"{session_dir.resolve()}:/home/worker/.claude/projects" in cmd_str
    assert session_dir.exists(), "session_dir should be created by _build_docker_cmd"


def test_shell_mode_gets_session_mount(build_docker_cmd, tmp_path):
    """shell mode also gets the session_dir mount."""
    session_dir = tmp_path / "shell-sessions"
    cmd = build_docker_cmd(
        cli_tool="shell",
        work_dir=tmp_path,
        env={},
        agent_cmd=["bash"],
        is_interactive=True,
        session_dir=session_dir,
    )
    cmd_str = " ".join(cmd)
    assert f"{session_dir.resolve()}:/home/worker/.claude/projects" in cmd_str


def test_no_session_mount_without_param(build_docker_cmd, tmp_path):
    """Without session_dir, no .claude/projects mount is added."""
    cmd = build_docker_cmd(
        cli_tool="claude",
        work_dir=tmp_path,
        env={},
        agent_cmd=["claude", "-p", "hello"],
        is_interactive=False,
    )
    cmd_str = " ".join(cmd)
    assert ".claude/projects" not in cmd_str


def test_no_session_mount_for_gemini(build_docker_cmd, tmp_path):
    """Gemini mode does not get a session_dir mount (Gemini manages its own)."""
    session_dir = tmp_path / "gemini-sessions"
    cmd = build_docker_cmd(
        cli_tool="gemini",
        work_dir=tmp_path,
        env={},
        agent_cmd=["gemini"],
        is_interactive=False,
        session_dir=session_dir,
    )
    cmd_str = " ".join(cmd)
    assert ".claude/projects" not in cmd_str


# ---------------------------------------------------------------------------
# Debug helpers for E2E tests
# ---------------------------------------------------------------------------


def _dump_diagnostics(result: dict, session_id: str) -> str:
    """Build a diagnostic string showing everything about a Docker Claude run."""
    lines = [
        f"session_id: {session_id}",
        f"success: {result.get('success')}",
        f"error: {result.get('error', 'none')}",
    ]

    # Init message — shows apiKeySource, model, mcp_servers
    init = result.get("init", {})
    if init:
        lines.append(f"apiKeySource: {init.get('apiKeySource', 'MISSING')}")
        lines.append(f"model: {init.get('model', 'MISSING')}")
        lines.append(f"permissionMode: {init.get('permissionMode', 'MISSING')}")
        failed_mcps = [
            s["name"] for s in init.get("mcp_servers", []) if s.get("status") == "failed"
        ]
        if failed_mcps:
            lines.append(f"failed MCP servers: {failed_mcps}")

    # Result message — shows tokens, duration, actual result
    res = result.get("result", {})
    if res:
        lines.append(f"result text: {str(res.get('result', ''))[:200]}")
        lines.append(f"duration_api_ms: {res.get('duration_api_ms', 'MISSING')}")
        lines.append(f"num_turns: {res.get('num_turns', 'MISSING')}")
        usage = res.get("usage", {})
        lines.append(
            f"tokens: in={usage.get('input_tokens', 0)} out={usage.get('output_tokens', 0)}"
        )

    # Raw stdout (first 1000 chars)
    raw = result.get("output", "")
    lines.append(f"raw stdout (first 1000): {raw[:1000]}")

    # Stderr
    stderr = result.get("stderr", "")
    if stderr:
        lines.append(f"stderr (last 500): {stderr[-500:]}")

    # Session dir contents
    session_dir = result.get("session_dir")
    if session_dir and session_dir.exists():
        all_entries = list(session_dir.rglob("*"))
        files = [p for p in all_entries if p.is_file()]
        dirs = [p for p in all_entries if p.is_dir()]
        lines.append(f"session_dir files: {files}")
        lines.append(f"session_dir dirs: {dirs}")
    else:
        lines.append(
            f"session_dir: {session_dir} (exists={session_dir.exists() if session_dir else 'None'})"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# E2E tests — require Docker + Claude auth
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.integration
def test_claude_docker_produces_session_jsonl(claude_docker):
    """Claude writes a session JSONL transcript that persists via the session_dir mount."""
    result, session_id, tool_calls = claude_docker(
        "Use the Bash tool to run: echo hello-world",
        timeout_seconds=90,
        fail_on_error=False,
    )
    diag = _dump_diagnostics(result, session_id)
    log.debug("Claude Docker session diagnostics:\n%s", diag)

    # Gate: Claude must have produced actual output (proves auth worked).
    # Note: apiKeySource may report "none" even with working OAuth — check tokens instead.
    res = result.get("result", {})
    usage = res.get("usage", {})
    assert usage.get("output_tokens", 0) > 0, (
        f"Claude produced 0 output tokens — session did not execute.\n{diag}"
    )

    # Verify tool calls were captured (consolidated from test_docker_session.py)
    bash_calls = [c for c in tool_calls if c["name"] == "Bash"]
    assert len(bash_calls) >= 1, (
        f"Expected Bash tool call, got: {[c['name'] for c in tool_calls]}.\n{diag}"
    )

    # Now check session persistence
    session_dir = result.get("session_dir")
    actual_files = [p for p in session_dir.rglob("*") if p.is_file()]
    assert len(actual_files) > 0, f"session_dir has no files.\n{diag}"

    # Find the session JSONL specifically
    from tests.conftest import find_session_jsonl

    session_file = find_session_jsonl(session_id, search_dirs=[session_dir])
    assert session_file is not None, f"No session JSONL for {session_id}.\n{diag}"
    assert session_file.stat().st_size > 0, f"Session JSONL exists but is empty.\n{diag}"


@pytest.mark.slow
@pytest.mark.integration
def test_session_jsonl_contains_valid_entries(claude_docker):
    """Session JSONL contains parseable entries with user + assistant messages."""
    result, session_id, _ = claude_docker(
        "Reply with exactly: test persistence",
        timeout_seconds=90,
        fail_on_error=False,
    )
    diag = _dump_diagnostics(result, session_id)
    log.debug("Claude Docker session diagnostics:\n%s", diag)

    # Gate: Claude must have produced actual output (proves auth worked)
    res = result.get("result", {})
    assert res.get("usage", {}).get("output_tokens", 0) > 0, (
        f"Claude produced 0 output tokens.\n{diag}"
    )

    # Find JSONL
    session_dir = result.get("session_dir")
    from tests.conftest import find_session_jsonl

    session_file = find_session_jsonl(session_id, search_dirs=[session_dir])
    assert session_file is not None, f"No session JSONL for {session_id}.\n{diag}"

    entries = []
    with session_file.open() as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    assert len(entries) > 0, f"Session JSONL has no entries.\n{diag}"

    types = {e.get("type") for e in entries}
    assert "user" in types or "human" in types, f"No user message found. Types: {types}\n{diag}"
    assert "assistant" in types, f"No assistant message found. Types: {types}\n{diag}"
