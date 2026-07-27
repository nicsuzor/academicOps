"""Regression tests for `polecat run --live-edit`.

The mount lets a developer edit plugin source and see it take effect inside a
container without an image rebuild, by bind-mounting this workspace's locally
built `dist/<plugin>-claude` over the container's installed-plugin cache.

The trap this exists to catch, confirmed live in a container: Claude Code's
plugin installer writes each plugin's cache directory as
`cache/<marketplace>/<plugin>/<version>`, rewriting any `+` in the version to
`-` first — source version `0.5.0+gdff86d32` installs at
`.../0.5.0-gdff86d32/`. A mount computed from the raw, un-sanitized version
names a path Docker happily auto-creates as an empty directory rather than
erroring, so the container silently keeps serving its baked-in code with no
error anywhere — a false-green review verdict. `sanitize_cache_version` and
`verify_live_edit_destinations` are what make that failure loud instead.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PLUGINS_DIR = str(_REPO_ROOT / "plugins")
if _PLUGINS_DIR not in sys.path:
    sys.path.insert(0, _PLUGINS_DIR)

from aops.polecat import cli  # noqa: E402

# ---------------------------------------------------------------------------
# sanitize_cache_version: the exact sanitization the installer performs
# ---------------------------------------------------------------------------


def test_plus_is_rewritten_to_hyphen():
    assert cli.sanitize_cache_version("0.5.0+gdff86d32") == "0.5.0-gdff86d32"


def test_the_confirmed_live_example_matches_exactly():
    """Verified live in a container: this exact input/output pair is real,
    not a hypothesis about how the installer behaves."""
    assert cli.sanitize_cache_version("0.5.0+gdff86d32") == "0.5.0-gdff86d32"


def test_a_version_with_no_plus_is_unchanged():
    assert cli.sanitize_cache_version("0.5.0") == "0.5.0"


def test_a_prerelease_dirty_version_is_also_sanitized():
    assert (
        cli.sanitize_cache_version("0.5.1-dev.0+gabc12345.dirty") == "0.5.1-dev.0-gabc12345.dirty"
    )


# ---------------------------------------------------------------------------
# resolve_live_edit_mounts: reading dist/.claude-plugin/marketplace.json
# ---------------------------------------------------------------------------


def _write_dist_manifest(workspace, plugins):
    manifest_dir = workspace / "dist" / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "marketplace.json").write_text(json.dumps({"name": "aops", "plugins": plugins}))
    for entry in plugins:
        built = workspace / "dist" / f"{entry['name']}-claude"
        built.mkdir(parents=True, exist_ok=True)
        (built / "marker.txt").write_text(entry["name"])


def test_no_dist_build_fails_loudly(tmp_path):
    with pytest.raises(SystemExit):
        cli.resolve_live_edit_mounts(tmp_path)


def test_mounts_are_derived_from_the_manifest_not_current_git_state(tmp_path, monkeypatch):
    """The whole point of live-edit is to dirty the tree after the image was
    built. If the mount were recomputed from current git state it would
    drift from what the image actually has on disk the moment that happens.
    Proven here by making the derivation from live git state return
    something else entirely and confirming resolve_live_edit_mounts ignores
    it."""
    _write_dist_manifest(tmp_path, [{"name": "aops", "version": "0.5.0+gdff86d32"}])

    def _boom(*a, **k):
        raise AssertionError("must not re-derive from git state")

    monkeypatch.setattr(subprocess, "run", _boom, raising=False)
    # Only patch cli's own subprocess usage sparingly — resolve_live_edit_mounts
    # must do no subprocess calls at all, so patching module-global subprocess
    # is safe: any call would raise.
    monkeypatch.setattr(cli.subprocess, "run", _boom)

    mounts = cli.resolve_live_edit_mounts(tmp_path)
    assert len(mounts) == 1
    name, host_src, container_dest = mounts[0]
    assert name == "aops"
    assert container_dest.endswith("/0.5.0-gdff86d32")


def test_missing_declared_plugin_directory_fails_loudly(tmp_path):
    manifest_dir = tmp_path / "dist" / ".claude-plugin"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "marketplace.json").write_text(
        json.dumps({"name": "aops", "plugins": [{"name": "aops", "version": "0.5.0+gabc"}]})
    )
    # dist/aops-claude deliberately not created.
    with pytest.raises(SystemExit):
        cli.resolve_live_edit_mounts(tmp_path)


def test_container_destination_uses_the_fixed_academicops_marketplace_name(tmp_path):
    """The container always installs under `academicOps` (Dockerfile
    MP_NAME), regardless of the local dist/ marketplace's own name (which is
    deliberately `aops`, see build/marketplace.py). The destination must
    never be built from the local manifest's own `name` field."""
    _write_dist_manifest(tmp_path, [{"name": "aops", "version": "0.5.0+gdff86d32"}])
    _, _, container_dest = cli.resolve_live_edit_mounts(tmp_path)[0]
    assert container_dest == ("/home/worker/.claude/plugins/cache/academicOps/aops/0.5.0-gdff86d32")


# ---------------------------------------------------------------------------
# verify_live_edit_destinations: the loud-failure preflight
# ---------------------------------------------------------------------------


def test_verify_passes_when_the_probe_succeeds(monkeypatch):
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="", stderr=""),
    )
    # Must not raise.
    cli.verify_live_edit_destinations("some-image:latest", [("aops", "/host/aops", "/dest/aops")])


def test_verify_fails_loudly_when_the_destination_is_bogus(monkeypatch):
    """This is the exact silent-no-op bug: a computed destination that does
    not exist in the image. verify_live_edit_destinations must refuse to
    proceed rather than let docker auto-create the mount point."""
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, stdout="", stderr="no such directory"),
    )
    with pytest.raises(SystemExit):
        cli.verify_live_edit_destinations(
            "some-image:latest",
            [
                (
                    "aops",
                    "/host/aops",
                    "/home/worker/.claude/plugins/cache/academicOps/aops/9.9.9-bogus",
                )
            ],
        )


# ---------------------------------------------------------------------------
# End-to-end: docker run argv with --live-edit on and off
# ---------------------------------------------------------------------------


def _base_mocks(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_image_available_locally", lambda image: True)
    monkeypatch.setattr(cli, "load_config", lambda: {})
    monkeypatch.setattr(cli, "load_local_overlay", lambda home: {})
    monkeypatch.setattr(cli, "setup_staging", lambda staging_dir, mcp_url, agent_home: None)
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)


def _capture_all_docker_cmds(monkeypatch, tmp_path, argv):
    """Invoke `polecat run ...` and return (result, [every docker argv run]),
    including the --live-edit preflight probe if one happened. Real docker
    calls are never made."""
    _base_mocks(monkeypatch, tmp_path)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker":
            captured.append(list(cmd))
            if "--entrypoint" in cmd:
                # The --live-edit preflight probe: succeed unconditionally so
                # tests control failure explicitly via monkeypatching
                # verify_live_edit_destinations itself where needed.
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, argv)
    return result, captured


def _main_docker_run(captured, image="test-image:latest"):
    for cmd in captured:
        if "--entrypoint" not in cmd and image in cmd:
            return cmd
    raise AssertionError(f"no main docker run found among {captured!r}")


def test_live_edit_absent_by_default(tmp_path, monkeypatch):
    """Opt-in only: no --live-edit flag means no cache-path -v mount and no
    preflight probe at all."""
    result, captured = _capture_all_docker_cmds(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo")]
    )
    assert result.exit_code == 0, result.output
    main_cmd = _main_docker_run(captured)
    assert not any("/home/worker/.claude/plugins/cache/" in arg for arg in main_cmd)
    # No preflight probe ran either — the whole mechanism is a no-op when off.
    assert len(captured) == 1


def test_live_edit_adds_the_expected_v_mount_when_enabled(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _write_dist_manifest(repo, [{"name": "aops", "version": "0.5.0+gdff86d32"}])

    result, captured = _capture_all_docker_cmds(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(repo), "--live-edit"]
    )
    assert result.exit_code == 0, result.output

    main_cmd = _main_docker_run(captured)
    expected_dest = "/home/worker/.claude/plugins/cache/academicOps/aops/0.5.0-gdff86d32"
    expected = f"{repo / 'dist' / 'aops-claude'}:{expected_dest}:ro"
    assert expected in main_cmd
    assert main_cmd[main_cmd.index(expected) - 1] == "-v"

    # And the preflight probe actually ran, checking that same path, before
    # the main container started.
    probe_cmds = [c for c in captured if "--entrypoint" in c]
    assert len(probe_cmds) == 1
    assert expected_dest in probe_cmds[0][-1]
    assert captured.index(probe_cmds[0]) < captured.index(main_cmd)


def test_live_edit_refuses_to_start_when_destination_is_bogus(tmp_path, monkeypatch):
    """The loud-failure path: the preflight probe reports the computed cache
    path does not exist in the image, so no container may start at all —
    neither the probe's own docker run nor the main run may be mistaken for
    success."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _write_dist_manifest(repo, [{"name": "aops", "version": "0.5.0+gdff86d32"}])

    _base_mocks(monkeypatch, tmp_path)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker":
            captured.append(list(cmd))
            if "--entrypoint" in cmd:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="no such directory")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, ["run", "claude", "-d", str(repo), "--live-edit"])

    assert result.exit_code != 0
    assert "live-edit" in result.output
    # Only the failed preflight probe ran; the main container never started.
    assert len(captured) == 1
    assert "--entrypoint" in captured[0]
