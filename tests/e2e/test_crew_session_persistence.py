"""Unit tests for crew session transcript persistence.

Verifies that _build_docker_cmd() configures a bind mount from the host
session_dir to the container's transcript directory (Claude/shell →
/home/worker/.claude/projects, Gemini → /home/worker/.gemini/tmp).

Live-visibility and end-to-end persistence are covered by the real-docker
suite in test_all_invocation_paths.py (TestAllInvocationPaths.test_session_persists).
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def build_docker_cmd():
    """Import _build_docker_cmd from polecat.

    Patches _is_remote_daemon to False so these unit tests exercise the
    local-daemon (bind-mount) code path without requiring Docker on PATH.
    """
    repo_root = Path(__file__).resolve().parents[2]
    polecat_dir = str(repo_root / "polecat")
    aops_core_dir = str(repo_root / "aops-core")
    if polecat_dir not in sys.path:
        sys.path.insert(0, polecat_dir)
    if aops_core_dir not in sys.path:
        sys.path.insert(0, aops_core_dir)
    from cli import _build_docker_cmd

    def _build_and_return_cmd(**kwargs):
        with patch("cli._is_remote_daemon", return_value=False):
            return _build_docker_cmd(**kwargs).cmd

    return _build_and_return_cmd


def test_session_dir_created_by_build(build_docker_cmd, tmp_path):
    """session_dir param creates the directory (extraction target for docker cp)."""
    session_dir = tmp_path / "test-sessions"
    build_docker_cmd(
        cli_tool="claude",
        work_dir=tmp_path,
        env={},
        agent_cmd=["claude", "-p", "hello"],
        is_interactive=False,
        session_dir=session_dir,
    )
    assert session_dir.exists(), "session_dir should be created by _build_docker_cmd"


@pytest.mark.parametrize(
    "cli_tool,is_interactive,agent_cmd,container_path",
    [
        ("claude", False, ["claude", "-p", "hello"], "/home/worker/.claude/projects/-workspace"),
        ("shell", True, ["bash"], "/home/worker/.claude/projects/-workspace"),
        ("gemini", False, ["gemini"], "/home/worker/.gemini/tmp/workspace"),
    ],
)
def test_session_dir_is_bind_mounted(
    build_docker_cmd, tmp_path, cli_tool, is_interactive, agent_cmd, container_path
):
    """session_dir is bind-mounted to the correct in-container transcript path."""
    session_dir = tmp_path / f"{cli_tool}-sessions"
    cmd = build_docker_cmd(
        cli_tool=cli_tool,
        work_dir=tmp_path,
        env={},
        agent_cmd=agent_cmd,
        is_interactive=is_interactive,
        session_dir=session_dir,
    )
    vol_idx = [i for i, x in enumerate(cmd) if x == "-v"]
    volumes = [cmd[i + 1] for i in vol_idx]
    expected_mount = f"{session_dir}:{container_path}"
    assert expected_mount in volumes, f"expected session bind-mount {expected_mount} in {volumes}"

    # Verify AOPS_SESSION_STATE_DIR is set to the same container path
    expected_env = f"AOPS_SESSION_STATE_DIR={container_path}"
    env_idx = [i for i, x in enumerate(cmd) if x == "-e"]
    envs = [cmd[i + 1] for i in env_idx]
    assert expected_env in envs, f"expected {expected_env} in {envs}"


def test_no_session_mount_without_param(build_docker_cmd, tmp_path):
    """Without session_dir, no .claude/projects or .gemini/tmp bind mount is added."""
    cmd = build_docker_cmd(
        cli_tool="claude",
        work_dir=tmp_path,
        env={},
        agent_cmd=["claude", "-p", "hello"],
        is_interactive=False,
    )
    vol_idx = [i for i, x in enumerate(cmd) if x == "-v"]
    volumes = [cmd[i + 1] for i in vol_idx]
    for vol in volumes:
        assert ".claude/projects" not in vol
        assert ".gemini/tmp" not in vol
