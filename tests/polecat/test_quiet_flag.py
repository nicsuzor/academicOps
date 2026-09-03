"""`polecat run --quiet` suppresses polecat's own progress prose on stderr.

Polecat's own output is confined to stderr so stdout stays clean for piping.
`--quiet` silences the progress and workspace-discovery prose; error output from
`fail()` is deliberately exempt, because an exit code alone is not a reliable
failure signal here (agy can exit 0 on internal error).

Without the flag defined, click's `ignore_unknown_options` plus the
`extra_args` UNPROCESSED catch-all swallow `--quiet` and forward it to the inner
agent binary, and every echo still fires — that is the red these tests pin.
"""

import subprocess

import pytest
from click.testing import CliRunner

from lib.polecat import cli

# Bound before any monkeypatching: `cli.subprocess` is the stdlib module itself,
# so patching `cli.subprocess.run` patches it globally and a fake that delegates
# to `subprocess.run` would recurse into itself.
_REAL_RUN = subprocess.run

# One fragment per gated echo site reachable through `run` with an explicit
# --repo-dir. The `resolve_isolated_workspace` warning is not among them: cli.py
# skips isolation entirely when --repo-dir is given, so it is covered by a
# direct call below.
PROGRESS_PROSE = (
    "Running: ",  # container invocation announcement
    "Workspace: ",  # session-discovery line
    "Session logs: ",  # session-discovery line
)


def _base_mocks(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_image_available_locally", lambda image: True)
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {
            "git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}
        },
    )
    monkeypatch.setattr(cli, "load_local_overlay", lambda home: {})
    monkeypatch.setattr(
        cli, "setup_staging", lambda staging_dir, mcp_url, agent_home, agent_cmd=None: None
    )
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")
    monkeypatch.setenv("PKB_MCP_URL", "http://test-pkb.invalid:8026/mcp")
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)


def _invoke(monkeypatch, tmp_path, argv):
    """Run `polecat run ...` against stubbed docker, returning (result, docker_argv)."""
    _base_mocks(monkeypatch, tmp_path)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 0)
        return _REAL_RUN(cmd, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, argv)
    assert len(captured) == 1, f"expected one docker run, got {len(captured)}: {result.output}"
    return result, captured[0]


def test_progress_prose_on_stderr_without_quiet(monkeypatch, tmp_path):
    """Non-regression: the default run still narrates to stderr, not stdout."""
    result, _ = _invoke(
        monkeypatch, tmp_path, ["run", "claude", "--repo-dir", str(tmp_path / "repo")]
    )
    assert result.exit_code == 0, result.output
    for fragment in PROGRESS_PROSE:
        assert fragment in result.stderr, f"{fragment!r} missing from stderr:\n{result.stderr}"
    assert result.stdout == "", f"stdout must stay clean, got:\n{result.stdout}"


@pytest.mark.parametrize("flag", ["--quiet", "-q"])
def test_quiet_suppresses_progress_prose(monkeypatch, tmp_path, flag):
    result, docker_cmd = _invoke(
        monkeypatch, tmp_path, ["run", "claude", flag, "--repo-dir", str(tmp_path / "repo")]
    )
    assert result.exit_code == 0, result.output
    for fragment in PROGRESS_PROSE:
        assert fragment not in result.stderr, (
            f"{flag} left {fragment!r} on stderr:\n{result.stderr}"
        )


@pytest.mark.parametrize("flag", ["--quiet", "-q"])
def test_quiet_is_consumed_not_forwarded_to_the_agent(monkeypatch, tmp_path, flag):
    """The flag must be parsed as polecat's own option, not swallowed by the
    UNPROCESSED catch-all and passed through to the inner agent binary."""
    _, docker_cmd = _invoke(
        monkeypatch, tmp_path, ["run", "claude", flag, "--repo-dir", str(tmp_path / "repo")]
    )
    inner_cmd = docker_cmd[docker_cmd.index("test-image:latest") + 1 :]
    assert flag not in inner_cmd, f"{flag} leaked into the inner invocation: {inner_cmd}"


def _invoke_failing(monkeypatch, tmp_path, argv):
    """As `_invoke`, but the container exits nonzero — the preserve-workspace path."""
    _base_mocks(monkeypatch, tmp_path)

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            return subprocess.CompletedProcess(cmd, 3)
        return _REAL_RUN(cmd, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)
    return CliRunner().invoke(cli.main, argv)


@pytest.mark.parametrize("quiet,expected", [(False, True), (True, False)])
def test_quiet_gates_the_non_git_workspace_warning(tmp_path, capsys, quiet, expected):
    plain_dir = tmp_path / "not-a-repo"
    plain_dir.mkdir()
    workspace, cleanup = cli.resolve_isolated_workspace(
        plain_dir, "session-x", tmp_path / "polecat-home", quiet=quiet
    )
    assert cleanup is None and workspace == plain_dir.resolve()
    emitted = "is not inside a git repository" in capsys.readouterr().err
    assert emitted is expected


def test_quiet_suppresses_the_preserved_workspace_line(monkeypatch, tmp_path):
    result = _invoke_failing(
        monkeypatch, tmp_path, ["run", "claude", "--quiet", "--repo-dir", str(tmp_path / "repo")]
    )
    assert result.exit_code == 3, result.output
    assert "Workspace preserved for inspection" not in result.stderr, result.stderr


def test_failure_path_still_narrates_without_quiet(monkeypatch, tmp_path):
    result = _invoke_failing(
        monkeypatch, tmp_path, ["run", "claude", "--repo-dir", str(tmp_path / "repo")]
    )
    assert result.exit_code == 3, result.output
    assert "Workspace preserved for inspection" in result.stderr, result.stderr
