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
# resolve_rules_dir wired through `run()`: the actual docker mount
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
    monkeypatch.delenv("POLECAT_RULES_DIR", raising=False)
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)


def _capture_docker_cmd(monkeypatch, tmp_path, argv, config):
    _base_mocks(monkeypatch, tmp_path, config)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, argv)
    assert result.exit_code == 0, result.output
    assert len(captured) == 1, f"expected one docker run, got {len(captured)}"
    return captured[0]


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


def test_no_endpoint_or_credential_is_compiled_into_the_source():
    """The binding constraint, asserted at the source: cli.py may plumb the
    path, but nothing in it may name a real endpoint, model, or key.

    A *dialable* endpoint is what is forbidden — a scheme, or a host with a
    port. A bare loopback token in `_LOOPBACK_HOSTS` is not one: those exist to
    be detected and rewritten by `_rehost_loopback_urls`, which is the opposite
    of a compiled-in default. Pinned below so the exemption cannot widen.
    """
    text = (_REPO_ROOT / "lib" / "polecat" / "cli.py").read_text()
    for needle in ("http://", "https://", "zentropi", "gpt-"):
        assert needle not in text, f"{needle!r} found in cli.py"

    # `localhost` is permitted only as a bare member of the loopback set.
    for line in text.splitlines():
        if "localhost" not in line:
            continue
        assert line.strip().startswith("_LOOPBACK_HOSTS = frozenset("), (
            f"'localhost' outside the loopback-detection set: {line.strip()!r}"
        )

    # Nothing in that set may carry a scheme or a port — i.e. be dialable.
    # A single colon followed by digits is host:port; more colons is an IPv6
    # literal like `::1`, which is a bare host.
    for host in cli._LOOPBACK_HOSTS:
        looks_dialable = "//" in host or (
            host.count(":") == 1 and host.rpartition(":")[2].isdigit()
        )
        assert not looks_dialable, (
            f"{host!r} in _LOOPBACK_HOSTS looks like an endpoint, not a bare host"
        )

    # The alias replacing them is Docker's own, and carries no port either.
    assert ":" not in cli._CONTAINER_HOST_ALIAS


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
