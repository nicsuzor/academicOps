"""Regression tests for the `git_identity` forwarding/halt logic (aops_29ebef95).

Background: `polecat/cli.py` never forwarded `GIT_AUTHOR_NAME`/`GIT_AUTHOR_EMAIL`
into the container env, so `entrypoint.sh`'s `aops-bot` fallback silently became
the standing commit-author identity for every polecat dispatch (`run` and
`crew`), instead of the required `botnicbot` identity. The fix adds a
`git_identity: {name, email}` key to `polecat.yaml` that `get_env_forwards()`
reads and forwards, and — the REJECT-grade defect this file specifically
regression-guards — `run()` must HALT (non-zero exit, no container launch)
when `git_identity` is missing or misconfigured, rather than printing a
stderr warning and proceeding under the wrong identity (halt-on-failure
axiom: a missing/misconfigured required credential must fail loudly, never
fall through silently).

These tests cover two layers:
1. `get_env_forwards(config)` — the pure dict-in/dict-out forwarding logic.
2. `run()`'s hard halt when the forwarded env ends up without a complete
   git identity — proven by asserting the container is never launched.
"""

import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from polecat import cli  # noqa: E402

# --------------------------------------------------------------------------
# get_env_forwards() — pure forwarding logic
# --------------------------------------------------------------------------


def test_get_env_forwards_forwards_valid_git_identity():
    config = {"git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}}

    env = cli.get_env_forwards(config)

    assert env["GIT_AUTHOR_NAME"] == "botnicbot"
    assert env["GIT_AUTHOR_EMAIL"] == "botnicbot@users.noreply.github.com"


def test_get_env_forwards_omits_keys_when_git_identity_missing():
    """No `git_identity` key at all: get_env_forwards must not invent one —
    it forwards nothing, leaving `run()`'s halt check (below) as the sole
    guard against silently falling through to entrypoint.sh's default."""
    env = cli.get_env_forwards({})

    assert "GIT_AUTHOR_NAME" not in env
    assert "GIT_AUTHOR_EMAIL" not in env


def test_get_env_forwards_omits_keys_when_git_identity_partially_configured():
    """Misconfigured (e.g. name but no email, or blank values) must not
    half-forward — both keys are required or neither is set."""
    env = cli.get_env_forwards({"git_identity": {"name": "botnicbot"}})

    assert "GIT_AUTHOR_NAME" in env  # name alone is present...
    assert "GIT_AUTHOR_EMAIL" not in env  # ...but email is not: run() must catch this


def test_get_env_forwards_omits_keys_when_git_identity_is_empty_dict():
    env = cli.get_env_forwards({"git_identity": {}})

    assert "GIT_AUTHOR_NAME" not in env
    assert "GIT_AUTHOR_EMAIL" not in env


# --------------------------------------------------------------------------
# run() — hard halt when git_identity is missing/misconfigured
# --------------------------------------------------------------------------


def _base_mocks(monkeypatch, tmp_path, config=None):
    """Patch out everything docker/filesystem-heavy so `run()` is exercised
    as a pure control-flow unit, mirroring test_cli_seed_verification.py's
    `_base_mocks`. `config` lets each test control `git_identity`."""
    monkeypatch.setattr(cli, "_image_available_locally", lambda image: True)
    monkeypatch.setattr(cli, "load_config", lambda: (config or {}))
    monkeypatch.setattr(cli, "load_local_overlay", lambda home: {})
    monkeypatch.setattr(cli, "setup_staging", lambda staging_dir, pkb_url: None)
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("AOPS", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)


def test_run_halts_and_never_launches_container_when_git_identity_missing(tmp_path, monkeypatch):
    """The REJECT-grade regression case: no `git_identity` configured at all.
    `run()` must exit non-zero and must NEVER call subprocess.run (i.e. never
    launch the container) — falling through to entrypoint.sh's `aops-bot`
    default is exactly the silent-fallback bug this fix closes."""
    launched = {"n": 0}

    def fake_subprocess_run(cmd, *a, **kw):
        launched["n"] += 1
        return subprocess.CompletedProcess(cmd, 0)

    _base_mocks(monkeypatch, tmp_path, config={})
    monkeypatch.setattr(cli.subprocess, "run", fake_subprocess_run)

    runner = CliRunner()
    result = runner.invoke(cli.main, ["run", "claude", "-d", str(tmp_path / "repo")])

    assert result.exit_code != 0
    assert launched["n"] == 0, "container must never launch when git_identity is missing"
    assert "git_identity" in result.output


def test_run_halts_when_git_identity_partially_configured(tmp_path, monkeypatch):
    """Misconfigured (email missing) must halt exactly like fully-missing —
    no half-applied identity is allowed through."""
    launched = {"n": 0}

    def fake_subprocess_run(cmd, *a, **kw):
        launched["n"] += 1
        return subprocess.CompletedProcess(cmd, 0)

    _base_mocks(monkeypatch, tmp_path, config={"git_identity": {"name": "botnicbot"}})
    monkeypatch.setattr(cli.subprocess, "run", fake_subprocess_run)

    runner = CliRunner()
    result = runner.invoke(cli.main, ["run", "claude", "-d", str(tmp_path / "repo")])

    assert result.exit_code != 0
    assert launched["n"] == 0


def test_run_proceeds_and_forwards_identity_when_git_identity_valid(tmp_path, monkeypatch):
    """Control case: a valid, complete `git_identity` must NOT halt, and the
    resolved env actually passed to `docker run` must carry the forwarded
    GIT_AUTHOR_NAME/EMAIL as `-e` flags."""
    captured_cmd = {}

    def fake_subprocess_run(cmd, *a, **kw):
        captured_cmd["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    _base_mocks(
        monkeypatch,
        tmp_path,
        config={
            "git_identity": {
                "name": "botnicbot",
                "email": "botnicbot@users.noreply.github.com",
            }
        },
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_subprocess_run)

    runner = CliRunner()
    result = runner.invoke(cli.main, ["run", "claude", "-d", str(tmp_path / "repo")])

    assert result.exit_code == 0, result.output
    cmd = captured_cmd["cmd"]
    assert "GIT_AUTHOR_NAME=botnicbot" in cmd
    assert "GIT_AUTHOR_EMAIL=botnicbot@users.noreply.github.com" in cmd
