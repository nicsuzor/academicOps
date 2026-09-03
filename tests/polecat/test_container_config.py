"""Regression tests for two container-surface config paths polecat plumbs:

Layer-3 rules mount: cope/rbg's user-scoped rule layer
(`$ACA_DATA/.agents/rules/`) had no way to reach a container at all — nothing
in `polecat.yaml`'s schema named it, and nothing mounted it. `resolve_rules_dir`
and the `-v ...:/data/.agents/rules:ro` mount in `run()` are what close that
gap: absent config is a clean no-op, configured-but-unreadable is a hard
failure before any container starts.

cope evaluator wiring: `COPE_EVALUATOR_*` used to reach a container only by
accident — forwarded when the operator happened to have exported it in the
invoking shell, with no path through the operator's own `polecat.yaml`.
`resolve_cope_evaluator` adds that path; a host environment variable still
wins when both are set.
"""

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from lib.polecat import cli

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# resolve_rules_dir: the config path itself
# ---------------------------------------------------------------------------


def test_absent_rules_dir_is_a_silent_no_op(monkeypatch):
    monkeypatch.delenv("POLECAT_RULES_DIR", raising=False)
    assert cli.resolve_rules_dir({}) is None


def test_env_var_names_the_rules_dir(tmp_path, monkeypatch):
    rules = tmp_path / "pkb-rules"
    rules.mkdir()
    monkeypatch.setenv("POLECAT_RULES_DIR", str(rules))
    assert cli.resolve_rules_dir({}) == rules


def test_config_file_names_the_rules_dir(tmp_path, monkeypatch):
    rules = tmp_path / "pkb-rules"
    rules.mkdir()
    monkeypatch.delenv("POLECAT_RULES_DIR", raising=False)
    assert cli.resolve_rules_dir({"rules_dir": str(rules)}) == rules


def test_env_var_wins_over_config_file(tmp_path, monkeypatch):
    env_rules = tmp_path / "env-rules"
    env_rules.mkdir()
    cfg_rules = tmp_path / "cfg-rules"
    cfg_rules.mkdir()
    monkeypatch.setenv("POLECAT_RULES_DIR", str(env_rules))
    assert cli.resolve_rules_dir({"rules_dir": str(cfg_rules)}) == env_rules


def test_configured_but_missing_directory_is_a_hard_failure(tmp_path, monkeypatch):
    """Setting rules_dir is a claim the layer exists. A path that does not
    resolve to a readable directory must not silently degrade to 'no layer 3'
    — that is indistinguishable from the operator never having configured it."""
    monkeypatch.delenv("POLECAT_RULES_DIR", raising=False)
    missing = tmp_path / "does-not-exist"
    with pytest.raises(SystemExit):
        cli.resolve_rules_dir({"rules_dir": str(missing)})


def test_configured_but_a_file_not_a_directory_is_a_hard_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("POLECAT_RULES_DIR", raising=False)
    not_a_dir = tmp_path / "a-file"
    not_a_dir.write_text("not a directory")
    with pytest.raises(SystemExit):
        cli.resolve_rules_dir({"rules_dir": str(not_a_dir)})


# ---------------------------------------------------------------------------
# resolve_scratch_dir: the config path itself
# ---------------------------------------------------------------------------


def test_absent_scratch_dir_is_a_silent_no_op(monkeypatch):
    monkeypatch.delenv("POLECAT_SCRATCH_DIR", raising=False)
    assert cli.resolve_scratch_dir({}) is None


def test_cli_scratch_dir_names_the_scratch_dir(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch-space"
    monkeypatch.delenv("POLECAT_SCRATCH_DIR", raising=False)
    assert cli.resolve_scratch_dir({}, cli_scratch_dir=str(scratch)) == scratch
    assert scratch.is_dir()


def test_env_var_names_the_scratch_dir(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch-space"
    monkeypatch.setenv("POLECAT_SCRATCH_DIR", str(scratch))
    assert cli.resolve_scratch_dir({}) == scratch
    assert scratch.is_dir()


def test_config_file_names_the_scratch_dir(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch-space"
    monkeypatch.delenv("POLECAT_SCRATCH_DIR", raising=False)
    assert cli.resolve_scratch_dir({"scratch_dir": str(scratch)}) == scratch
    assert scratch.is_dir()


def test_docker_config_file_names_the_scratch_dir(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch-space"
    monkeypatch.delenv("POLECAT_SCRATCH_DIR", raising=False)
    assert cli.resolve_scratch_dir({"docker": {"scratch_dir": str(scratch)}}) == scratch
    assert scratch.is_dir()


def test_cli_wins_over_env_and_config_for_scratch_dir(tmp_path, monkeypatch):
    cli_scratch = tmp_path / "cli-scratch"
    env_scratch = tmp_path / "env-scratch"
    cfg_scratch = tmp_path / "cfg-scratch"
    monkeypatch.setenv("POLECAT_SCRATCH_DIR", str(env_scratch))
    assert (
        cli.resolve_scratch_dir({"scratch_dir": str(cfg_scratch)}, cli_scratch_dir=str(cli_scratch))
        == cli_scratch
    )


def test_env_var_wins_over_config_file_for_scratch_dir(tmp_path, monkeypatch):
    env_scratch = tmp_path / "env-scratch"
    cfg_scratch = tmp_path / "cfg-scratch"
    monkeypatch.setenv("POLECAT_SCRATCH_DIR", str(env_scratch))
    assert cli.resolve_scratch_dir({"scratch_dir": str(cfg_scratch)}) == env_scratch


def test_configured_scratch_dir_file_not_a_directory_is_a_hard_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("POLECAT_SCRATCH_DIR", raising=False)
    not_a_dir = tmp_path / "a-scratch-file"
    not_a_dir.write_text("not a directory")
    with pytest.raises(SystemExit):
        cli.resolve_scratch_dir({"scratch_dir": str(not_a_dir)})


# ---------------------------------------------------------------------------
# resolve_rules_dir & resolve_scratch_dir wired through `run()`
# ---------------------------------------------------------------------------


def _base_mocks(monkeypatch, tmp_path, config):
    monkeypatch.setattr(cli, "_image_available_locally", lambda image: True)
    cfg = dict(config)
    cfg.setdefault(
        "git_identity", {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}
    )
    monkeypatch.setattr(cli, "load_config", lambda: cfg)
    monkeypatch.setattr(cli, "load_local_overlay", lambda home: {})
    monkeypatch.setattr(
        cli, "setup_staging", lambda staging_dir, mcp_url, agent_home, agent_cmd=None: None
    )
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")
    monkeypatch.setenv("PKB_MCP_URL", "http://test-pkb.invalid:8026/mcp")
    monkeypatch.delenv("POLECAT_RULES_DIR", raising=False)
    monkeypatch.delenv("POLECAT_SCRATCH_DIR", raising=False)
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)


def _capture_docker_run(monkeypatch, tmp_path, argv, config):
    """`(argv, env)` for the `docker run` polecat built.

    Values now reach docker through its own environment rather than on argv,
    so the env half is what proves a variable was forwarded rather than lost.
    """
    _base_mocks(monkeypatch, tmp_path, config)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append((list(cmd), kw.get("env")))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, argv)
    assert result.exit_code == 0, result.output
    assert len(captured) == 1, f"expected one docker run, got {len(captured)}"
    return captured[0]


def _capture_docker_cmd(monkeypatch, tmp_path, argv, config):
    """The `docker run` argv alone, for assertions that do not touch env."""
    return _capture_docker_run(monkeypatch, tmp_path, argv, config)[0]


def _mount_targets(docker_cmd):
    return [
        docker_cmd[i + 1]
        for i, arg in enumerate(docker_cmd)
        if arg == "-v" and i + 1 < len(docker_cmd)
    ]


def test_no_rules_mount_when_unconfigured(tmp_path, monkeypatch):
    cmd = _capture_docker_cmd(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo")], {}
    )
    assert not any(".agents/rules" in mount for mount in _mount_targets(cmd))


def test_rules_dir_mounted_read_only_at_container_aca_data(tmp_path, monkeypatch):
    rules = tmp_path / "pkb-rules"
    rules.mkdir()
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo")],
        {"rules_dir": str(rules)},
    )
    expected = f"{rules}:{cli.CONTAINER_ACA_DATA}/.agents/rules:ro"
    assert expected in cmd
    assert cmd[cmd.index(expected) - 1] == "-v"


def test_rules_mount_target_matches_what_cope_reads_for_aca_data_slash_data(tmp_path, monkeypatch):
    """The mount target must be exactly `$ACA_DATA/.agents/rules` as the
    Dockerfile's `ENV ACA_DATA=/data` resolves it — the same path
    plugins/rbg/hooks/rules.py builds from `os.environ["ACA_DATA"]`."""
    assert cli.CONTAINER_ACA_DATA == "/data"
    rules = tmp_path / "pkb-rules"
    rules.mkdir()
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo")],
        {"rules_dir": str(rules)},
    )
    assert f"{rules}:/data/.agents/rules:ro" in cmd


def test_configured_but_missing_rules_dir_fails_before_any_container_starts(tmp_path, monkeypatch):
    _base_mocks(monkeypatch, tmp_path, {"rules_dir": str(tmp_path / "nope")})
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli.main, ["run", "claude", "-d", str(tmp_path / "repo")])
    assert result.exit_code != 0
    assert captured == [], "no container may start when a configured rules_dir is unreadable"


def test_no_scratch_mount_when_unconfigured(tmp_path, monkeypatch):
    cmd = _capture_docker_cmd(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo")], {}
    )
    assert not any(":/scratch" in mount for mount in _mount_targets(cmd))


def test_scratch_dir_mounted_read_write_at_container_scratch(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch-space"
    scratch.mkdir()
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo")],
        {"scratch_dir": str(scratch)},
    )
    expected = f"{scratch}:/scratch"
    assert expected in cmd
    assert cmd[cmd.index(expected) - 1] == "-v"


def test_scratch_dir_cli_option_mounted_at_container_scratch(tmp_path, monkeypatch):
    scratch = tmp_path / "cli-scratch"
    scratch.mkdir()
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--scratch-dir", str(scratch)],
        {},
    )
    expected = f"{scratch}:/scratch"
    assert expected in cmd
    assert cmd[cmd.index(expected) - 1] == "-v"


def test_scratch_alias_cli_option_mounted_at_container_scratch(tmp_path, monkeypatch):
    scratch = tmp_path / "cli-scratch-alias"
    scratch.mkdir()
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--scratch", str(scratch)],
        {},
    )
    expected = f"{scratch}:/scratch"
    assert expected in cmd
    assert cmd[cmd.index(expected) - 1] == "-v"


def test_configured_but_file_scratch_dir_fails_before_any_container_starts(tmp_path, monkeypatch):
    not_a_dir = tmp_path / "scratch-file"
    not_a_dir.write_text("file")
    _base_mocks(monkeypatch, tmp_path, {"scratch_dir": str(not_a_dir)})
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli.main, ["run", "claude", "-d", str(tmp_path / "repo")])
    assert result.exit_code != 0
    assert captured == [], "no container may start when a configured scratch_dir is a file"


# ---------------------------------------------------------------------------
# resolve_cope_evaluator: the config path itself
# ---------------------------------------------------------------------------


def test_unconfigured_cope_forwards_nothing():
    assert cli.resolve_cope_evaluator({}) == {}


def test_config_file_supplies_the_evaluator_env():
    env = cli.resolve_cope_evaluator(
        {
            "cope": {
                "evaluator_url": "https://evaluator.example/v1/label",
                "evaluator_protocol": "cope",
                "evaluator_model": "test-model",
                "evaluator_api_key": "secret",
                "evaluator_timeout": 3.5,
            }
        }
    )
    assert env == {
        "COPE_EVALUATOR_URL": "https://evaluator.example/v1/label",
        "COPE_EVALUATOR_PROTOCOL": "cope",
        "COPE_EVALUATOR_MODEL": "test-model",
        "COPE_EVALUATOR_API_KEY": "secret",
        "COPE_EVALUATOR_TIMEOUT": "3.5",
    }


def test_partial_cope_config_forwards_only_what_is_set():
    env = cli.resolve_cope_evaluator({"cope": {"evaluator_url": "https://evaluator.example"}})
    assert env == {"COPE_EVALUATOR_URL": "https://evaluator.example"}


# ---------------------------------------------------------------------------
# get_env_forwards: config feeds the container's environment
# ---------------------------------------------------------------------------


def test_get_env_forwards_carries_cope_config_into_the_container(monkeypatch):
    for name in (
        "COPE_EVALUATOR_URL",
        "COPE_EVALUATOR_PROTOCOL",
        "COPE_EVALUATOR_MODEL",
        "COPE_EVALUATOR_API_KEY",
        "COPE_EVALUATOR_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)

    config = {
        "git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"},
        "cope": {
            "evaluator_url": "https://evaluator.example/v1/label",
            "evaluator_protocol": "cope",
            "evaluator_model": "test-model",
        },
    }
    env = cli.get_env_forwards(config)
    assert env["COPE_EVALUATOR_URL"] == "https://evaluator.example/v1/label"
    assert env["COPE_EVALUATOR_PROTOCOL"] == "cope"
    assert env["COPE_EVALUATOR_MODEL"] == "test-model"


def test_host_env_var_wins_over_cope_config(monkeypatch):
    monkeypatch.setenv("COPE_EVALUATOR_MODEL", "ambient-model")
    config = {
        "git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"},
        "cope": {"evaluator_model": "configured-model"},
    }
    env = cli.get_env_forwards(config)
    assert env["COPE_EVALUATOR_MODEL"] == "ambient-model"


def test_a_loopback_evaluator_url_is_rehosted_to_reach_the_host(monkeypatch):
    """A loopback URL names the container's own empty loopback once forwarded.

    Observed on 2026-08-03 in a real container: with
    ``COPE_EVALUATOR_URL=http://127.0.0.1:8099/v1/label`` forwarded verbatim,
    curl from inside returned ``http=000`` (unreachable) and rbg's PreToolUse
    hook reported its evaluator unanswering for 23/23 rules — turn-by-turn
    enforcement silently off for every containerised worker.
    """
    for name in ("COPE_EVALUATOR_PROTOCOL", "COPE_EVALUATOR_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("COPE_EVALUATOR_URL", "http://127.0.0.1:8099/v1/label")
    config = {"git_identity": {"name": "botnicbot", "email": "bot@users.noreply.github.com"}}

    env = cli.get_env_forwards(config)

    assert env["COPE_EVALUATOR_URL"] == "http://host.docker.internal:8099/v1/label", (
        "a loopback host must be rewritten to the host-gateway alias, or the "
        "evaluator is unreachable from inside the container"
    )


def test_rehosting_rewrites_only_the_host_and_only_for_loopback(monkeypatch):
    """It must not invent an endpoint, and must leave real hosts untouched."""
    monkeypatch.delenv("COPE_EVALUATOR_MODEL", raising=False)
    monkeypatch.setenv("COPE_EVALUATOR_URL", "http://localhost:8099/v1/label?x=1")
    # A tailnet or public host is already reachable and must pass through.
    monkeypatch.setenv("PKB_MCP_URL", "http://services.example.ts.net:8020/mcp")
    config = {"git_identity": {"name": "botnicbot", "email": "bot@users.noreply.github.com"}}

    env = cli.get_env_forwards(config)

    assert env["COPE_EVALUATOR_URL"] == "http://host.docker.internal:8099/v1/label?x=1"
    assert env["PKB_MCP_URL"] == "http://services.example.ts.net:8020/mcp"


def test_get_env_forwards_requires_git_identity(monkeypatch):
    """Calling get_env_forwards without git_identity in config fails loudly."""
    for name in ("COPE_EVALUATOR_URL", "COPE_EVALUATOR_PROTOCOL", "COPE_EVALUATOR_MODEL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(SystemExit):
        cli.get_env_forwards()


# ---------------------------------------------------------------------------
# resolve_git_identity: strictly from polecat.yaml git_identity
# ---------------------------------------------------------------------------


def test_resolve_git_identity_success():
    config = {"git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}}
    identity = cli.resolve_git_identity(config)
    assert identity == {
        "GIT_AUTHOR_NAME": "botnicbot",
        "GIT_AUTHOR_EMAIL": "botnicbot@users.noreply.github.com",
        "GIT_COMMITTER_NAME": "botnicbot",
        "GIT_COMMITTER_EMAIL": "botnicbot@users.noreply.github.com",
    }


def test_missing_git_identity_block_fails(monkeypatch):
    monkeypatch.setenv("GIT_AUTHOR_NAME", "operator-name")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "operator-email@example.com")
    with pytest.raises(SystemExit):
        cli.resolve_git_identity({})


def test_incomplete_git_identity_fails():
    with pytest.raises(SystemExit):
        cli.resolve_git_identity({"git_identity": {"name": "botnicbot"}})
    with pytest.raises(SystemExit):
        cli.resolve_git_identity({"git_identity": {"email": "bot@example.com"}})


def test_get_env_forwards_does_not_fallback_to_user_env(monkeypatch):
    monkeypatch.setenv("GIT_AUTHOR_NAME", "user-name")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "user-email@example.com")
    config = {"git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}}
    env = cli.get_env_forwards(config)
    assert env["GIT_AUTHOR_NAME"] == "botnicbot"
    assert env["GIT_AUTHOR_EMAIL"] == "botnicbot@users.noreply.github.com"


# ---------------------------------------------------------------------------
# resolve_telemetry: standard OTEL configuration
# ---------------------------------------------------------------------------


def test_unconfigured_telemetry_forwards_nothing():
    assert cli.resolve_telemetry({}) == {}


def test_config_file_supplies_telemetry_endpoint_and_resource_attributes():
    env = cli.resolve_telemetry(
        {
            "telemetry": {
                "endpoint": "TEST_ENDPOINT",
                "resource_attributes": "deployment.environment=workstation,host.name=nicwin",
            }
        }
    )
    assert env == {
        "BETA_TRACING_ENDPOINT": "TEST_ENDPOINT",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "TEST_ENDPOINT",
        "OTEL_RESOURCE_ATTRIBUTES": "deployment.environment=workstation,host.name=nicwin",
    }


# ---------------------------------------------------------------------------
# CONTAINER_SET_ENV: default agent teams env var propagation
# ---------------------------------------------------------------------------


def test_default_agent_teams_env_var_in_container_set_env():
    from lib.polecat.env_contract import CONTAINER_SET_ENV

    assert CONTAINER_SET_ENV.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1"


def test_default_agent_teams_env_var_forwarded_by_default(monkeypatch):
    config = {"git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}}
    env = cli.get_env_forwards(config)
    assert env.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1"


def test_default_agent_teams_env_var_in_docker_env_args():
    from lib.polecat.env_contract import docker_env_args

    args = docker_env_args()
    assert "-e" in args
    assert "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1" in args


# ---------------------------------------------------------------------------
# format_otel_resource_attributes & polecat resource attribute injection
# ---------------------------------------------------------------------------


def test_format_otel_resource_attributes_merges_session_project_task():
    from lib.polecat.env_contract import format_otel_resource_attributes

    res = format_otel_resource_attributes(
        existing="service.name=my-service,deployment.env=prod",
        session_id="session-xyz",
        project="proj-abc",
        task_id="task-123",
    )
    assert (
        res
        == "service.name=my-service,deployment.env=prod,polecat.session_id=session-xyz,polecat.project=proj-abc,polecat.task_id=task-123"
    )


def test_format_otel_resource_attributes_handles_empty_existing_and_optional_fields():
    from lib.polecat.env_contract import format_otel_resource_attributes

    res = format_otel_resource_attributes(
        existing=None,
        session_id="session-xyz",
        project=None,
        task_id=None,
    )
    assert res == "polecat.session_id=session-xyz"


def test_format_otel_resource_attributes_overrides_existing_polecat_keys():
    from lib.polecat.env_contract import format_otel_resource_attributes

    res = format_otel_resource_attributes(
        existing="polecat.session_id=old,service.name=svc",
        session_id="new_session",
        project="proj1",
    )
    assert res == "polecat.session_id=new_session,service.name=svc,polecat.project=proj1"


def test_run_injects_polecat_otel_resource_attributes(tmp_path, monkeypatch):
    cmd, docker_env = _capture_docker_run(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "-p",
            "myproj",
            "-t",
            "mytask",
            "-s",
            "mysess",
            "-d",
            str(tmp_path / "repo"),
        ],
        {},
    )
    assert "OTEL_RESOURCE_ATTRIBUTES" in cmd
    assert cmd[cmd.index("OTEL_RESOURCE_ATTRIBUTES") - 1] == "-e"
    val = docker_env["OTEL_RESOURCE_ATTRIBUTES"]
    assert "polecat.session_id=mysess" in val
    assert "polecat.project=myproj" in val
    assert "polecat.task_id=mytask" in val


# ---------------------------------------------------------------------------
# GenAI engine & OTEL traces protocol forwarding and task identifier
# ---------------------------------------------------------------------------


def test_get_env_forwards_carries_genai_engine_and_otel_protocol_from_config():
    config = {
        "git_identity": {"name": "botnicbot", "email": "bot@users.noreply.github.com"},
        "telemetry": {
            "trace_endpoint": "http://traces.example.com/v1/traces",
            "api_key": "engine-key-xyz",
            "task_id": "engine-task-99",
            "protocol": "http/protobuf",
        },
    }
    env = cli.get_env_forwards(config)

    assert env["GENAI_ENGINE_TRACE_ENDPOINT"] == "http://traces.example.com/v1/traces"
    assert env["GENAI_ENGINE_API_KEY"] == "engine-key-xyz"
    assert env["GENAI_ENGINE_TASK_ID"] == "engine-task-99"
    assert env["GENAI_ENGINE_TRACE_PROTOCOL"] == "http/protobuf"
    assert env["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] == "http/protobuf"
    assert env["OTEL_EXPORTER_OTLP_PROTOCOL"] == "http/protobuf"


def test_get_env_forwards_ignores_ambient_genai_engine_and_otel_protocol_env(monkeypatch):
    monkeypatch.setenv("GENAI_ENGINE_TRACE_ENDPOINT", "http://traces.example.com/v1/traces")
    monkeypatch.setenv("GENAI_ENGINE_API_KEY", "engine-key-xyz")
    monkeypatch.setenv("GENAI_ENGINE_TASK_ID", "engine-task-99")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_PROTOCOL", "http/protobuf")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")

    config = {"git_identity": {"name": "botnicbot", "email": "bot@users.noreply.github.com"}}
    env = cli.get_env_forwards(config)

    assert "GENAI_ENGINE_TRACE_ENDPOINT" not in env
    assert "GENAI_ENGINE_API_KEY" not in env
    assert "GENAI_ENGINE_TASK_ID" not in env
    assert "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL" not in env
    assert "OTEL_EXPORTER_OTLP_PROTOCOL" not in env


def test_get_env_forwards_rehosts_loopback_genai_engine_trace_endpoint():
    config = {
        "git_identity": {"name": "botnicbot", "email": "bot@users.noreply.github.com"},
        "telemetry": {
            "trace_endpoint": "http://127.0.0.1:8000/v1/traces",
        },
    }
    env = cli.get_env_forwards(config)
    assert env["GENAI_ENGINE_TRACE_ENDPOINT"] == "http://host.docker.internal:8000/v1/traces"


def test_resolve_telemetry_supports_trace_endpoint():
    env = cli.resolve_telemetry(
        {
            "telemetry": {
                "trace_endpoint": "http://otel.example.com:4318/v1/traces",
            }
        }
    )
    assert env.get("GENAI_ENGINE_TRACE_ENDPOINT") == "http://otel.example.com:4318/v1/traces"


def test_run_constructs_task_id_and_service_name_with_project_and_task(tmp_path, monkeypatch):
    cmd, docker_env = _capture_docker_run(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "-p",
            "academicOps",
            "-t",
            "aops_ded39198",
            "-d",
            str(tmp_path / "repo"),
        ],
        {},
    )
    assert "GENAI_ENGINE_TASK_ID" in cmd
    assert cmd[cmd.index("GENAI_ENGINE_TASK_ID") - 1] == "-e"
    assert docker_env["GENAI_ENGINE_TASK_ID"] == "aops_ded39198"
    assert "OTEL_SERVICE_NAME" in cmd
    assert docker_env["OTEL_SERVICE_NAME"] == "academicOps"
    assert docker_env["PHOENIX_PROJECT_NAME"] == "academicOps"


def test_run_constructs_task_id_and_service_name_with_task_only(tmp_path, monkeypatch):
    cmd, docker_env = _capture_docker_run(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "-t",
            "aops_ded39198",
            "-d",
            str(tmp_path / "repo"),
        ],
        {},
    )
    assert docker_env["GENAI_ENGINE_TASK_ID"] == "aops_ded39198"


def test_run_constructs_task_id_and_service_name_with_project_only(tmp_path, monkeypatch):
    monkeypatch.delenv("GENAI_ENGINE_TASK_ID", raising=False)
    cmd, docker_env = _capture_docker_run(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "-p",
            "academicOps",
            "-d",
            str(tmp_path / "repo"),
        ],
        {},
    )
    assert "GENAI_ENGINE_TASK_ID" not in docker_env
    assert docker_env["OTEL_SERVICE_NAME"] == "academicOps"
    assert docker_env["PHOENIX_PROJECT_NAME"] == "academicOps"


def test_run_preserves_config_genai_engine_task_id_when_neither_project_nor_task(
    tmp_path, monkeypatch
):
    cmd, docker_env = _capture_docker_run(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "-d",
            str(tmp_path / "repo"),
        ],
        {"telemetry": {"task_id": "config_task_id"}},
    )
    assert docker_env["GENAI_ENGINE_TASK_ID"] == "config_task_id"


def test_run_ignores_ambient_genai_engine_task_id_when_neither_project_nor_task(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GENAI_ENGINE_TASK_ID", "ambient_task_id")
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    cmd, docker_env = _capture_docker_run(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "-d",
            str(tmp_path / "repo"),
        ],
        {},
    )
    assert "GENAI_ENGINE_TASK_ID" not in cmd
    assert "OTEL_SERVICE_NAME" not in cmd
    assert "OTEL_SERVICE_NAME" not in docker_env


def test_run_leaves_genai_engine_task_id_unset_when_unprovided(tmp_path, monkeypatch):
    monkeypatch.delenv("GENAI_ENGINE_TASK_ID", raising=False)
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    cmd, docker_env = _capture_docker_run(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "-d",
            str(tmp_path / "repo"),
        ],
        {},
    )
    assert "GENAI_ENGINE_TASK_ID" not in cmd
    assert "GENAI_ENGINE_TASK_ID" not in docker_env
    assert "OTEL_SERVICE_NAME" not in cmd
    assert "OTEL_SERVICE_NAME" not in docker_env


def test_entrypoint_fails_loudly_when_trace_endpoint_unset(tmp_path):
    entrypoint = _REPO_ROOT / "lib" / "polecat" / "entrypoint.sh"
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "GIT_AUTHOR_NAME": "Bot",
        "GIT_AUTHOR_EMAIL": "bot@example.com",
        "AOPS_BOT_GH_TOKEN": "test_token",
    }
    result = subprocess.run(
        ["bash", str(entrypoint), "true"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "FATAL: GENAI_ENGINE_TRACE_ENDPOINT is not set" in result.stderr


def test_entrypoint_succeeds_when_trace_endpoint_set(tmp_path):
    entrypoint = _REPO_ROOT / "lib" / "polecat" / "entrypoint.sh"
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "GIT_AUTHOR_NAME": "Bot",
        "GIT_AUTHOR_EMAIL": "bot@example.com",
        "AOPS_BOT_GH_TOKEN": "test_token",
        "GENAI_ENGINE_TRACE_ENDPOINT": "http://collector:4318/v1/traces",
    }
    result = subprocess.run(
        ["bash", str(entrypoint), "true"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
