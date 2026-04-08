"""Unit tests for crew session transcript persistence.

Verifies that _build_docker_cmd() correctly configures session handling
for Claude and Gemini modes. No Docker or LLM required.

Session transcripts are extracted via docker cp (not bind mounts) because
bind mounts silently fail on WSL2/Docker Desktop. The session_dir param
creates the directory on the host; callers pass extract_paths to
_run_docker_container() for post-run extraction.

E2E session persistence tests are in test_all_invocation_paths.py
(TestAllInvocationPaths.test_session_persists).
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


def test_no_session_bind_mount_for_claude(build_docker_cmd, tmp_path):
    """Claude mode does NOT bind-mount session_dir (uses docker cp extraction)."""
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
    assert ".claude/projects" not in cmd_str


def test_no_session_bind_mount_for_shell(build_docker_cmd, tmp_path):
    """Shell mode does NOT bind-mount session_dir (uses docker cp extraction)."""
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
    assert ".claude/projects" not in cmd_str


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
