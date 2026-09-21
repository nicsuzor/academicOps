"""Tests for container-side seed command construction in entrypoint.sh.

Verifies:
1. When POLECAT_TARGET_TASK is set, entrypoint.sh constructs and appends
   /pkb:pull <task-id> for both agy and claude.
2. Under agy with NONINTERACTIVE=1 / CI=1, entrypoint.sh uses --print /pkb:pull <task-id>.
3. Under agy in interactive mode (NONINTERACTIVE unset), entrypoint.sh uses --prompt-interactive /pkb:pull <task-id>.
4. Under claude, entrypoint.sh appends /pkb:pull <task-id> as trailing positional.
5. When an explicit prompt is provided on argv, entrypoint.sh does not overwrite or duplicate it.
6. When POLECAT_TARGET_TASK is unset, entrypoint.sh leaves argv untouched.
"""

import os
import stat
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ENTRYPOINT_SH = _REPO_ROOT / "lib" / "polecat" / "entrypoint.sh"


def _run_entrypoint_with_mock_bin(tmp_path, agent_name, argv, env_vars=None):
    """Creates a mock agent binary in tmp_path/bin that echoes its invocation args."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    agent_bin = bin_dir / agent_name
    agent_bin.write_text('#!/bin/sh\necho "$0" "$@"\n')
    agent_bin.chmod(agent_bin.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    base_env = {
        "GIT_AUTHOR_NAME": "Test Agent",
        "GIT_AUTHOR_EMAIL": "agent@test.com",
        "AOPS_BOT_GH_TOKEN": "token-123",
        "GENAI_ENGINE_TRACE_ENDPOINT": "http://localhost:4317",
        "HOME": str(tmp_path),
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '/bin:/usr/bin')}",
    }
    if env_vars:
        base_env.update(env_vars)

    proc = subprocess.run(
        ["bash", str(_ENTRYPOINT_SH), agent_name, *argv],
        env=base_env,
        capture_output=True,
        text=True,
    )
    return proc


def test_entrypoint_claude_seed_construction(tmp_path):
    """claude dispatch with POLECAT_TARGET_TASK gets /pkb:pull <task-id> appended."""
    proc = _run_entrypoint_with_mock_bin(
        tmp_path,
        "claude",
        ["--dangerously-skip-permissions", "--setting-sources=user,project", "--print"],
        env_vars={"POLECAT_TARGET_TASK": "aops_9160e382"},
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    assert "--print /pkb:pull aops_9160e382" in out


def test_entrypoint_agy_headless_seed_construction(tmp_path):
    """agy headless dispatch with POLECAT_TARGET_TASK gets --print /pkb:pull <task-id> appended."""
    proc = _run_entrypoint_with_mock_bin(
        tmp_path,
        "agy",
        ["--dangerously-skip-permissions", "--log-file", "/tmp/cli.log", "--print-timeout", "30m"],
        env_vars={"POLECAT_TARGET_TASK": "aops_9160e382", "NONINTERACTIVE": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    assert "--print-timeout 30m --print /pkb:pull aops_9160e382" in out


def test_entrypoint_agy_interactive_seed_construction(tmp_path):
    """agy interactive dispatch with POLECAT_TARGET_TASK gets --prompt-interactive /pkb:pull <task-id> appended."""
    proc = _run_entrypoint_with_mock_bin(
        tmp_path,
        "agy",
        ["--dangerously-skip-permissions", "--log-file", "/tmp/cli.log"],
        env_vars={"POLECAT_TARGET_TASK": "aops_9160e382", "NONINTERACTIVE": "0", "CI": "0"},
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    assert "--prompt-interactive /pkb:pull aops_9160e382" in out


def test_entrypoint_leaves_explicit_prompt_untouched(tmp_path):
    """When an explicit prompt is already on argv, POLECAT_TARGET_TASK does not override it."""
    proc = _run_entrypoint_with_mock_bin(
        tmp_path,
        "agy",
        ["--dangerously-skip-permissions", "--prompt", "my custom prompt"],
        env_vars={"POLECAT_TARGET_TASK": "aops_9160e382"},
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    assert "--prompt my custom prompt" in out
    assert "/pkb:pull" not in out


def test_entrypoint_leaves_non_agent_command_untouched(tmp_path):
    """bash or other commands do not get seed prompts appended."""
    proc = _run_entrypoint_with_mock_bin(
        tmp_path,
        "bash",
        ["-c", "echo hello"],
        env_vars={"POLECAT_TARGET_TASK": "aops_9160e382"},
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    assert "-c echo hello" in out
    assert "/pkb:pull" not in out


def test_entrypoint_no_task_leaves_argv_untouched(tmp_path):
    """When POLECAT_TARGET_TASK is unset, entrypoint leaves argv unchanged."""
    proc = _run_entrypoint_with_mock_bin(
        tmp_path,
        "claude",
        ["--print", "hello"],
        env_vars={"POLECAT_TARGET_TASK": ""},
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    assert "--print hello" in out
