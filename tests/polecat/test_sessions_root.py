"""The sessions root is required, and a run lands under exactly that root.

An unset `$AOPS_SESSIONS` used to fall back to `<polecat_home>/sessions`. That
made a cron or detached-tmux dispatch write a complete transcript into a
directory the export pipeline never scans, exit zero, and report success — the
failure had no surface at all. It is now a loud failure, resolved next to the
other required values, before any container starts.
"""

import subprocess
from pathlib import Path

import pytest
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
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")
    monkeypatch.setenv("PKB_MCP_URL", "http://test-pkb.invalid:8026/mcp")
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# resolve_sessions_root
# --------------------------------------------------------------------------


def test_resolve_sessions_root_returns_the_configured_root(monkeypatch, tmp_path):
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    assert cli.resolve_sessions_root() == tmp_path / "sessions"


def test_resolve_sessions_root_expands_user_and_vars(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AOPS_SESSIONS", "~/sessions")
    assert cli.resolve_sessions_root() == tmp_path / "sessions"


def test_resolve_sessions_root_fails_loudly_when_unset(monkeypatch):
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)
    with pytest.raises(SystemExit) as exc:
        cli.resolve_sessions_root()
    assert exc.value.code == 1


def test_resolve_sessions_root_fails_loudly_when_empty(monkeypatch):
    monkeypatch.setenv("AOPS_SESSIONS", "")
    with pytest.raises(SystemExit) as exc:
        cli.resolve_sessions_root()
    assert exc.value.code == 1


def test_resolve_sessions_root_reads_no_config_key(monkeypatch, tmp_path):
    """The config file is found at `$AOPS_SESSIONS/polecat.yaml`, so no key in
    it can define the sessions root. A config that names one must not rescue an
    unset environment — that would be a fallback wearing a different hat."""
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)
    monkeypatch.setattr(cli, "load_config", lambda: {"sessions_root": str(tmp_path / "nope")})
    with pytest.raises(SystemExit):
        cli.resolve_sessions_root()


# --------------------------------------------------------------------------
# run() — the wiring
# --------------------------------------------------------------------------


def test_run_refuses_to_start_a_container_without_a_sessions_root(tmp_path, monkeypatch):
    started = {"n": 0}

    def fake_run(cmd, *a, **kw):
        if cmd and ("sbx" in cmd or "run" in cmd):
            started["n"] += 1
        return subprocess.CompletedProcess(cmd, 0)

    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli.main, ["run", "claude", "-d", str(tmp_path / "repo")])

    assert result.exit_code == 1
    assert "AOPS_SESSIONS" in result.output
    assert started["n"] == 0, "no container may start before the sessions root resolves"


def test_run_writes_under_the_configured_sessions_root(tmp_path, monkeypatch):
    """And nowhere near `<polecat_home>/sessions`, the old silent fallback."""
    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd and ("sbx" in cmd or "run" in cmd):
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    _base_mocks(monkeypatch, tmp_path)
    sessions = tmp_path / "elsewhere" / "sessions"
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions))
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = CliRunner().invoke(
        cli.main, ["run", "claude", "-d", str(tmp_path / "repo"), "-s", "session-root-check"]
    )

    assert result.exit_code == 0, result.output
    run_jsons = list(sessions.glob("logs/*/session-root-check/*/run.json"))
    assert len(run_jsons) == 1, f"expected one run.json under {sessions}, got {run_jsons}"
    assert not (Path(str(tmp_path / "polecat-home")) / "sessions").exists()
