"""`polecat run` fails at launch when no knowledge-base MCP URL resolves.

An unset $PKB_MCP_URL (and no --mcp-url) used to reach `setup_staging()`
and `_minimal_agent_settings()` as `mcp_url=None`, silently skip wiring the
`services` MCP server, and let the container start anyway with zero MCP
servers and exit code 0. A worker inside such a container has nothing that
names the PKB at all, so it cannot tell "the PKB is down" from "the PKB was
never configured". It is now a hard failure before any container starts,
with an explicit --no-pkb opt-out for runs that genuinely need no
knowledge-base access (e.g. shell/sleep debugging).
"""

import subprocess

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


def _invoke(monkeypatch, tmp_path, argv):
    """Invoke `polecat run ...`, returning `(result, docker_argv_list)`.

    `docker_argv_list` is empty whenever the run is rejected before a
    container starts.
    """
    _base_mocks(monkeypatch, tmp_path)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and ("sbx" in cmd or "run" in cmd):
            captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, argv)
    return result, captured


def test_missing_url_fails_before_any_container_starts(monkeypatch, tmp_path):
    result, docker_cmds = _invoke(
        monkeypatch, tmp_path, ["run", "claude", "--repo-dir", str(tmp_path / "repo")]
    )
    assert result.exit_code != 0, result.output
    assert docker_cmds == [], f"container started despite no PKB URL: {docker_cmds}"


def test_missing_url_error_names_the_variable_and_both_routes(monkeypatch, tmp_path):
    result, _ = _invoke(
        monkeypatch, tmp_path, ["run", "claude", "--repo-dir", str(tmp_path / "repo")]
    )
    assert "PKB_MCP_URL" in result.output, result.output
    assert "8020" in result.output, result.output
    assert "8026" in result.output, result.output


def test_env_var_satisfies_the_requirement(monkeypatch, tmp_path):
    monkeypatch.setenv("PKB_MCP_URL", "http://test-pkb.invalid:8026/mcp")
    result, docker_cmds = _invoke(
        monkeypatch, tmp_path, ["run", "claude", "--repo-dir", str(tmp_path / "repo")]
    )
    assert result.exit_code == 0, result.output
    assert len(docker_cmds) == 1


def test_explicit_mcp_url_flag_satisfies_the_requirement(monkeypatch, tmp_path):
    result, docker_cmds = _invoke(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "--repo-dir",
            str(tmp_path / "repo"),
            "--mcp-url",
            "http://test-pkb.invalid:8020/mcp",
        ],
    )
    assert result.exit_code == 0, result.output
    assert len(docker_cmds) == 1


def test_no_pkb_flag_opts_out_of_the_requirement(monkeypatch, tmp_path):
    result, docker_cmds = _invoke(
        monkeypatch,
        tmp_path,
        ["run", "claude", "--repo-dir", str(tmp_path / "repo"), "--no-pkb"],
    )
    assert result.exit_code == 0, result.output
    assert len(docker_cmds) == 1
