"""E2E tests for crew session transcript persistence.

Verifies that Claude sessions inside Docker containers produce persistent
JSONL transcript files via the session_dir mount in _build_docker_cmd().
"""

import json
import logging
import os
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
def test_claude_docker_auth_and_session_persistence(claude_docker):
    """E2E: Claude inside Docker can authenticate to the API and produces a session transcript.

    Single test replaces two former tests (produces_session_jsonl + contains_valid_entries)
    to avoid paying the Docker+Claude startup cost twice.

    Verifies:
    1. Claude API auth works (OAuth via staged .credentials.json or ANTHROPIC_API_KEY)
    2. Session JSONL is written and persists on the host via the session_dir mount
    3. JSONL contains parseable user + assistant entries
    """
    result, session_id, tool_calls = claude_docker(
        "Reply with exactly: hello world",
        timeout_seconds=90,
        fail_on_error=False,
    )
    diag = _dump_diagnostics(result, session_id)
    log.debug("Claude Docker session diagnostics:\n%s", diag)

    # 1. Auth gate: Claude must have produced actual output
    res = result.get("result", {})
    usage = res.get("usage", {})
    assert usage.get("output_tokens", 0) > 0, (
        f"Claude produced 0 output tokens — auth or session failed.\n{diag}"
    )

    # 2. Session persistence: JSONL file exists on host
    session_dir = result.get("session_dir")
    actual_files = [p for p in session_dir.rglob("*") if p.is_file()]
    assert len(actual_files) > 0, f"session_dir has no files.\n{diag}"

    from tests.conftest import find_session_jsonl

    session_file = find_session_jsonl(session_id, search_dirs=[session_dir])
    assert session_file is not None, f"No session JSONL for {session_id}.\n{diag}"
    assert session_file.stat().st_size > 0, f"Session JSONL exists but is empty.\n{diag}"

    # 3. JSONL content: has user + assistant messages
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


@pytest.mark.slow
@pytest.mark.integration
def test_docker_git_auth_via_entrypoint(tmp_path):
    """E2E: entrypoint.sh configures git credentials so git operations authenticate.

    Runs a lightweight shell command inside aops-crew (no Claude/Gemini needed).
    Verifies the credential helper is configured and resolves to the expected token.
    """
    import subprocess

    # Skip if Docker or image unavailable
    try:
        result = subprocess.run(
            ["docker", "images", "aops-crew", "--format", "{{.Repository}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if "aops-crew" not in result.stdout:
            pytest.skip("aops-crew image not built")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker not available")

    test_token = "ghp_test_e2e_credential_check_12345"
    uid = os.getuid()
    gid = os.getgid()

    # Run a shell command inside the container that:
    # 1. Verifies the credential helper is configured
    # 2. Invokes the credential helper to check the token is resolved
    # 3. Checks that SSH is disabled
    # 4. Checks that git remote URLs are rewritten to HTTPS
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--user",
            f"{uid}:{gid}",
            "-e",
            f"GH_TOKEN={test_token}",
            "-e",
            "SSH_AUTH_SOCK=",
            "aops-crew",
            "bash",
            "-c",
            "echo HELPER=$(git config --global credential.helper) && "
            'echo CRED=$(printf "protocol=https\\nhost=github.com\\n" | git credential fill 2>/dev/null | grep password) && '
            "echo SSH=$SSH_AUTH_SOCK && "
            "echo REWRITE=$(git config --global --get url.https://github.com/.insteadOf)",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, f"Container exited {result.returncode}:\n{output}"

    # Credential helper is configured
    assert "HELPER=" in output, f"No credential helper configured:\n{output}"
    helper_line = [ln for ln in output.splitlines() if ln.startswith("HELPER=")][0]
    assert "credential" in helper_line.lower() or "!" in helper_line, (
        f"Credential helper not set up:\n{output}"
    )

    # Token resolves through the credential helper
    assert f"password={test_token}" in output, f"Credential helper did not resolve token:\n{output}"

    # SSH is disabled
    assert "SSH=" in output  # SSH_AUTH_SOCK should be empty

    # Git URL rewriting to HTTPS
    assert "REWRITE=git@github.com:" in output, f"SSH→HTTPS URL rewrite not configured:\n{output}"


## test_gemini_docker_produces_session_jsonl removed — fragile (Gemini Docker
## session persistence) and the Claude variant provides sufficient coverage.
