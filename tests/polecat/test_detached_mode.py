"""Unit and integration tests for detached mode in polecat CLI.

Verifies:
1. `polecat run` provides `--detach` / `--detached` options.
2. `polecat run --help` advertises `--detach` / `--detached`.
3. `-d` flag remains exclusively `--repo-dir` (mounting a host repository), not a boolean detach flag.
4. `--detach` runs docker with `-d` and writes run.json with status="detached".
"""

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from lib.polecat import cli


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
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)


def test_run_help_contains_detach():
    """`polecat run --help` must advertise --detach option."""
    runner = CliRunner()
    result = runner.invoke(cli.main, ["run", "--help"])
    assert result.exit_code == 0, result.output
    help_text = result.output.lower()
    assert "--detach" in help_text or "--detached" in help_text


def test_run_options_contain_detach_parameters():
    """`cli.run` parameter definitions must include --detach / --detached."""
    opts = []
    for param in cli.run.params:
        opts.extend(getattr(param, "opts", []))
        opts.extend(getattr(param, "secondary_opts", []))
    assert "--detach" in opts or "--detached" in opts


def test_d_flag_is_exclusively_repo_dir():
    """`-d` flag must belong exclusively to `--repo-dir`, mounting a host repository."""
    d_params = [
        param
        for param in cli.run.params
        if "-d" in getattr(param, "opts", []) or "-d" in getattr(param, "secondary_opts", [])
    ]
    assert len(d_params) == 1, f"Expected exactly one param with '-d', found {len(d_params)}"
    param = d_params[0]
    assert param.name == "repo_dir"
    assert "--repo-dir" in param.opts
    assert not param.is_flag, "'-d' must not be a boolean flag (e.g. detach flag)"


def test_d_flag_requires_directory_argument():
    """Invoking `-d` without a path must fail because `-d` is not a standalone boolean detach flag."""
    runner = CliRunner()
    result = runner.invoke(cli.main, ["run", "-d"])
    assert result.exit_code != 0
    assert "requires an argument" in result.output or "Error" in result.output


def test_detach_execution_spawns_docker_with_d_flag(tmp_path, monkeypatch):
    """Passing --detach runs docker run -d and writes run.json with status 'detached'."""
    _base_mocks(monkeypatch, tmp_path)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append((list(cmd), kw.get("env")))
            cidfile_idx = cmd.index("--cidfile") + 1
            cidfile_path = Path(cmd[cidfile_idx])
            cidfile_path.write_text("c12345detached\n")
            return subprocess.CompletedProcess(cmd, 0, stdout="c12345detached\n")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    runner = CliRunner()
    res = runner.invoke(
        cli.main,
        [
            "run",
            "agy",
            "-d",
            str(tmp_path / "repo"),
            "-s",
            "session-detach1",
            "-t",
            "aops_test",
            "--detach",
        ],
    )
    assert res.exit_code == 0, res.output

    assert len(captured) == 1
    docker_cmd, docker_env = captured[0]
    assert "-d" in docker_cmd
    assert "--rm" in docker_cmd
    assert "--cidfile" in docker_cmd
    assert docker_env.get("POLECAT_TARGET_TASK") == "aops_test"

    run_jsons = list((tmp_path / "sessions").glob("**/run.json"))
    assert len(run_jsons) == 1
    data = json.loads(run_jsons[0].read_text())
    assert data["status"] == "detached"
    assert data["container_id"] == "c12345detached"
    assert data["task_id"] == "aops_test"
    assert data["seeded_prompt"] == "/pkb:pull aops_test"
