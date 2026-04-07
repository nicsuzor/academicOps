"""Unit tests for crew session transcript persistence.

Verifies that _build_docker_cmd() correctly configures session_dir mounts
for Claude and Gemini modes. No Docker or LLM required.

E2E session persistence tests are in test_crew_docker_session.py
(TestCrewDockerSession.test_session_persists).
"""

import sys
from pathlib import Path

import pytest


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

    def _build_and_return_cmd(**kwargs):
        return _build_docker_cmd(**kwargs).cmd

    return _build_and_return_cmd


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
