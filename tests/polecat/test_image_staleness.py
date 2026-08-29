"""Tests for polecat image staleness detection and surfacing.

Implements TDD specification from specs/polecat/spec-image-staleness-detection.md (aops_866c0666 / aops_40a3faa8).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "lib" / "hooks") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "lib" / "hooks"))

from click.testing import CliRunner
from dispatch import HookContext

from lib.polecat import cli
from lib.polecat.staleness import (
    ImageProvenance,
    evaluate_staleness,
)
from plugins.orchestrate.hooks import handlers


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
    monkeypatch.setattr(
        cli,
        "_get_image_digest",
        lambda image: "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    )
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")


def _init_git_repo(repo_dir: Path) -> str:
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    (repo_dir / "initial.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit"], cwd=repo_dir, check=True, capture_output=True
    )
    res = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
    )
    return res.stdout.strip()


def test_staleness_detection_local_fresh(tmp_path):
    """Image commit matches workspace commit, source is local: not stale, fresh header."""
    repo = tmp_path / "repo"
    repo.mkdir()
    commit_sha = _init_git_repo(repo)

    prov = ImageProvenance(
        dist_source="local",
        commit_sha=commit_sha,
        short_sha=commit_sha[:8],
        version="0.9.1",
        is_dirty=False,
    )

    result = evaluate_staleness(prov, repo, dispatch_mode="direct", session_id="session-test")

    assert result["is_stale"] is False
    assert result["staleness_status"] == "FRESH_LOCAL_BUILD"
    assert result["staleness_reason"] is None
    assert result["warning_banner"] is None
    assert result["header_banner"] is not None
    assert "PLUGINS FRESH [local match]" in result["header_banner"]
    assert "local:match" in result["plugins_version_str"]


def test_staleness_detection_local_stale(tmp_path, monkeypatch):
    """Image commit lags workspace commit, source is local: stale, warning banner, warn-only."""
    _base_mocks(monkeypatch, tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    old_commit = "62456fff11111111111111111111111111111111"
    prov = ImageProvenance(
        dist_source="local",
        commit_sha=old_commit,
        short_sha="62456fff",
        version="0.8.0",
        is_dirty=False,
    )

    result = evaluate_staleness(prov, repo, dispatch_mode="direct", session_id="session-stale")

    assert result["is_stale"] is True
    assert result["staleness_status"] == "STALE_LOCAL_BUILD"
    assert "image commit 62456fff behind workspace commit" in result["staleness_reason"]
    assert result["warning_banner"] is not None
    assert "WARNING: POLECAT IMAGE PLUGINS ARE STALE" in result["warning_banner"]
    assert "local:stale" in result["plugins_version_str"]

    # Verify via CLI runner: warn-only policy (exits 0 if inner succeeds)
    monkeypatch.setattr(cli, "inspect_image_provenance", lambda img: prov)

    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd[:2] == ["docker", "run"]:
            cidfile_idx = cmd.index("--cidfile") + 1
            cidfile_path = Path(cmd[cidfile_idx])
            cidfile_path.write_text("fake-container-id-stale\n")
            session_dir = cidfile_path.parent
            (session_dir / "6912ac2b-781f-4515-94d5-d883e2b94a54.jsonl").write_text(
                '{"type": "user", "message": "hello"}\n'
            )
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    runner = CliRunner()
    res = runner.invoke(cli.main, ["run", "claude", "-d", str(repo), "-s", "session-stale-run"])
    assert res.exit_code == 0
    assert "WARNING: POLECAT IMAGE PLUGINS ARE STALE" in res.output


def test_staleness_detection_local_dirty_workspace(tmp_path):
    """Image commit matches HEAD, but workspace has uncommitted changes: dirty unbaked warning."""
    repo = tmp_path / "repo"
    repo.mkdir()
    commit_sha = _init_git_repo(repo)

    # Make workspace dirty
    (repo / "modified.txt").write_text("uncommitted edits\n")

    prov = ImageProvenance(
        dist_source="local",
        commit_sha=commit_sha,
        short_sha=commit_sha[:8],
        version="0.9.1",
        is_dirty=False,
    )

    result = evaluate_staleness(prov, repo, dispatch_mode="direct", session_id="session-dirty")

    assert result["is_stale"] is True
    assert result["staleness_status"] == "DIRTY_WORKSPACE_UNBAKED"
    assert "uncommitted changes" in result["staleness_reason"]
    assert result["warning_banner"] is not None
    assert "WARNING: POLECAT IMAGE PLUGINS ARE STALE" in result["warning_banner"]
    assert "local:dirty" in result["plugins_version_str"]


def test_staleness_detection_remote_lagging_local_not_flagged_stale(tmp_path):
    """Remote-sourced image lagging local workspace: not flagged stale, info notice."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    remote_release_commit = "62456fff00000000000000000000000000000000"
    prov = ImageProvenance(
        dist_source="remote",
        commit_sha=remote_release_commit,
        short_sha="62456fff",
        version="0.9.1",
        dist_ref="v0.9.1",
        is_dirty=False,
    )

    result = evaluate_staleness(
        prov, repo, dispatch_mode="direct", session_id="session-remote", branch="feat/new-work"
    )

    assert result["is_stale"] is False
    assert result["staleness_status"] == "REMOTE_RELEASE_RUN"
    assert result["staleness_reason"] is None
    assert result["warning_banner"] is None
    assert result["header_banner"] is not None
    assert "REMOTE RELEASE IMAGE" in result["header_banner"]
    assert "remote:release" in result["plugins_version_str"]


def test_session_start_hook_surfaces_plugin_version(monkeypatch):
    """In-container SessionStart hook outputs plugin version in metadata and warning when stale."""
    ctx = HookContext(
        client="claude",
        event="SessionStart",
        session_id="session-prov-1",
        cwd="/workspace",
        raw={
            "session_id": "session-prov-1",
            "cwd": "/workspace",
            "plugins": "0.9.1+gf31ebcf7 (local:match)",
        },
    )

    res = handlers.session_start(ctx)
    assert res is not None
    assert "plugins: 0.9.1+gf31ebcf7 (local:match)" in res.inject_text
    assert "plugins: 0.9.1+gf31ebcf7 (local:match)" in res.user_text

    # When stale warning is passed via environment
    monkeypatch.setenv(
        "AOPS_IMAGE_STALENESS_WARNING",
        "[SYSTEM WARNING: RUNNING WITH STALE BAKED PLUGINS]\nContainer plugin payload lags workspace under test.",
    )
    monkeypatch.setenv("AOPS_IMAGE_PLUGINS_VERSION", "0.8.0 (local:stale)")

    stale_res = handlers.session_start(ctx)
    assert stale_res is not None
    assert "plugins: 0.8.0 (local:stale)" in stale_res.inject_text
    assert "[SYSTEM WARNING: RUNNING WITH STALE BAKED PLUGINS]" in stale_res.inject_text
    assert "[SYSTEM WARNING: RUNNING WITH STALE BAKED PLUGINS]" in stale_res.user_text


def test_run_json_records_provenance(tmp_path, monkeypatch):
    """run.json records structured plugin_provenance dictionary."""
    _base_mocks(monkeypatch, tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    prov = ImageProvenance(
        dist_source="local",
        commit_sha="62456fff11111111111111111111111111111111",
        short_sha="62456fff",
        version="0.8.0",
        is_dirty=False,
    )
    monkeypatch.setattr(cli, "inspect_image_provenance", lambda img: prov)

    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd[:2] == ["docker", "run"]:
            cidfile_idx = cmd.index("--cidfile") + 1
            cidfile_path = Path(cmd[cidfile_idx])
            cidfile_path.write_text("fake-cid-prov\n")
            session_dir = cidfile_path.parent
            (session_dir / "6912ac2b-781f-4515-94d5-d883e2b94a54.jsonl").write_text(
                '{"type": "user", "message": "hello"}\n'
            )
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    runner = CliRunner()
    res = runner.invoke(cli.main, ["run", "claude", "-d", str(repo), "-s", "session-json-prov"])
    assert res.exit_code == 0

    run_jsons = list((tmp_path / "sessions").glob("**/run.json"))
    assert len(run_jsons) == 1

    data = json.loads(run_jsons[0].read_text())
    assert "plugin_provenance" in data
    prov_data = data["plugin_provenance"]
    assert prov_data["is_stale"] is True
    assert prov_data["image_source"] == "local"
    assert prov_data["staleness_status"] == "STALE_LOCAL_BUILD"
    assert "image commit 62456fff" in prov_data["staleness_reason"]
