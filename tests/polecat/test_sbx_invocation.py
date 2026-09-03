"""Unit tests for Docker Sandboxes (sbx) command invocation in polecat CLI."""

from pathlib import Path
import subprocess
from click.testing import CliRunner
from lib.polecat import cli

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_resolve_sbx_command_default_and_override(monkeypatch):
    monkeypatch.delenv("POLECAT_SBX_BIN", raising=False)
    cmd = cli.resolve_sbx_command()
    assert cmd in (["sbx"], ["docker", "sbx"])

    monkeypatch.setenv("POLECAT_SBX_BIN", "/opt/custom/sbx")
    assert cli.resolve_sbx_command() == ["/opt/custom/sbx"]


def test_resolve_kit_path_builtin_and_custom(tmp_path):
    claude_kit = cli.resolve_kit_path("claude")
    assert claude_kit is not None
    assert (claude_kit / "spec.yaml").is_file()

    agy_kit = cli.resolve_kit_path("agy")
    assert agy_kit is not None
    assert (agy_kit / "spec.yaml").is_file()

    shell_kit = cli.resolve_kit_path("shell")
    assert shell_kit is None

    # Custom kit path
    custom = tmp_path / "my-custom-kit"
    custom.mkdir()
    (custom / "spec.yaml").write_text("schemaVersion: '2'")
    resolved = cli.resolve_kit_path("claude", custom_kit=custom)
    assert resolved == custom.resolve()


def test_build_sbx_command_claude_headless_task(tmp_path):
    cmd = cli.build_sbx_command(
        agent_cmd="claude",
        workspace_dir=tmp_path / "ws",
        session_name="session-123",
        kit_path=Path("/path/to/claude-kit"),
        task="aops_test",
        interactive=False,
    )
    assert cmd[:3] == ["docker", "sbx", "run"] or cmd[:2] == ["sbx", "run"]
    assert "--name" in cmd
    assert cmd[cmd.index("--name") + 1] == "session-123"
    assert "--kit" in cmd
    assert cmd[cmd.index("--kit") + 1] == "/path/to/claude-kit"
    assert "claude" in cmd
    assert str(tmp_path / "ws") in cmd
    assert "--" in cmd
    inner = cmd[cmd.index("--") + 1 :]
    assert "--print" in inner
    assert "/pull aops_test" in inner


def test_build_sbx_command_agy_explicit_prompt(tmp_path):
    cmd = cli.build_sbx_command(
        agent_cmd="agy",
        workspace_dir=tmp_path / "ws",
        prompt="Analyze data",
        interactive=False,
    )
    assert "agy" in cmd
    inner = cmd[cmd.index("--") + 1 :]
    assert "--print" in inner
    assert "Analyze data" in inner


def test_build_sbx_command_interactive_no_print(tmp_path):
    cmd = cli.build_sbx_command(
        agent_cmd="claude",
        workspace_dir=tmp_path / "ws",
        prompt="Analyze data",
        interactive=True,
    )
    if "--" in cmd:
        inner = cmd[cmd.index("--") + 1 :]
        assert "--print" not in inner


def test_build_sbx_command_detached_and_ports(tmp_path):
    cmd = cli.build_sbx_command(
        agent_cmd="claude",
        workspace_dir=tmp_path / "ws",
        detach=True,
        ports=("8080", "3000:3000"),
    )
    assert "-d" in cmd
    assert "-p" in cmd
    assert "8080" in cmd
    assert "3000:3000" in cmd


def test_build_sbx_command_env_vars_and_model(tmp_path):
    cmd = cli.build_sbx_command(
        agent_cmd="claude",
        workspace_dir=tmp_path / "ws",
        env_vars={"FOO": "bar", "BAZ": ""},
        model="claude-3-7-sonnet",
    )
    assert "-e" in cmd
    assert "FOO=bar" in cmd
    assert "BAZ" in cmd
    inner = cmd[cmd.index("--") + 1 :]
    assert "--model" in inner
    assert "claude-3-7-sonnet" in inner
