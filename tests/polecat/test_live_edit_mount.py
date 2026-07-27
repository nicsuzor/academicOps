"""Regression tests for `polecat run --live-edit`.

The mount lets a developer edit plugin source and see it take effect inside a
container without an image rebuild, by bind-mounting this workspace's locally
built `dist/<plugin>-claude` and `dist/<plugin>-agy` over the directories the
image actually installed those plugins into.

The trap this exists to catch: a Claude Code plugin's install directory is
`cache/<marketplace>/<plugin>/<version>`, where `<version>` is the version
baked at IMAGE BUILD time. Deriving that version host-side — from git state or
from the host's own `dist/` manifest — only lines up while the image and the
checkout agree, which is exactly the condition `--live-edit` exists to escape.
A destination the image never had is not an error: Docker auto-creates it as
an empty directory and mounts over it, so the container silently keeps serving
its baked-in code with no error anywhere — a false-green review verdict.
`probe_image_plugin_roots` (ask the image where it loads plugins from) and
`verify_live_edit_destinations` (refuse before any container starts) are what
make that failure impossible and loud respectively.
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

# A stale image's manifest: version `0.4.0-gold` baked in long ago, nothing
# like whatever the host checkout would derive today.
_IMAGE_VERSION = "0.4.0-gold"


def _image_manifest(names, version=_IMAGE_VERSION):
    """The manifest an aops-crew image carries at
    CONTAINER_MARKETPLACE_MANIFEST: every plugin's `source` already rewritten
    to the absolute cache directory that image installed
    (docker_gemini_fixups.py, fixup_marketplace_cache)."""
    return json.dumps(
        {
            "name": cli.CONTAINER_PLUGIN_MARKETPLACE,
            "plugins": [
                {
                    "name": name,
                    "version": version.replace("-g", "+g", 1),
                    "source": (
                        f"/home/worker/.claude/plugins/cache/"
                        f"{cli.CONTAINER_PLUGIN_MARKETPLACE}/{name}/{version}"
                    ),
                }
                for name in names
            ],
        }
    )


def _write_dist_build(workspace, names):
    """What `make build` leaves on the host: a per-plugin build for each
    runtime. No manifest is needed — the plugin set comes from the image."""
    for name in names:
        for suffix in ("claude", "agy"):
            built = workspace / "dist" / f"{name}-{suffix}"
            built.mkdir(parents=True, exist_ok=True)
            (built / "marker.txt").write_text(f"{name}-{suffix}")


def _fake_probe(manifest_stdout, returncode=0, stderr=""):
    def _run(cmd, *a, **kw):
        return subprocess.CompletedProcess(cmd, returncode, stdout=manifest_stdout, stderr=stderr)

    return _run


# ---------------------------------------------------------------------------
# probe_image_plugin_roots: the image, not the host, says where plugins live
# ---------------------------------------------------------------------------


def test_plugin_roots_come_from_the_image_manifest(monkeypatch):
    monkeypatch.setattr(cli.subprocess, "run", _fake_probe(_image_manifest(["aops", "aops-pkb"])))
    roots = cli.probe_image_plugin_roots("stale-image:latest")
    assert roots == {
        "aops": f"/home/worker/.claude/plugins/cache/academicOps/aops/{_IMAGE_VERSION}",
        "aops-pkb": f"/home/worker/.claude/plugins/cache/academicOps/aops-pkb/{_IMAGE_VERSION}",
    }


def test_the_probe_reads_the_marketplaces_manifest_with_nothing_mounted(monkeypatch):
    """A `docker run --rm` against the image alone: no volumes, so what it
    reports is the image's own filesystem and cannot be an echo of a mount."""
    seen = []

    def _run(cmd, *a, **kw):
        seen.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout=_image_manifest(["aops"]), stderr="")

    monkeypatch.setattr(cli.subprocess, "run", _run)
    cli.probe_image_plugin_roots("stale-image:latest")

    assert len(seen) == 1
    assert seen[0] == [
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "cat",
        "stale-image:latest",
        cli.CONTAINER_MARKETPLACE_MANIFEST,
    ]
    assert "-v" not in seen[0]


def test_an_image_without_the_manifest_fails_loudly(monkeypatch):
    """An image predating this layout has no marketplaces/ manifest. There is
    then no way to know where it loads plugins from, so refuse rather than
    guess a path Docker would silently auto-create."""
    monkeypatch.setattr(
        cli.subprocess, "run", _fake_probe("", returncode=1, stderr="No such file or directory")
    )
    with pytest.raises(SystemExit):
        cli.probe_image_plugin_roots("ancient-image:latest")


def test_a_non_json_manifest_fails_loudly(monkeypatch):
    monkeypatch.setattr(cli.subprocess, "run", _fake_probe("not json at all"))
    with pytest.raises(SystemExit):
        cli.probe_image_plugin_roots("broken-image:latest")


def test_a_manifest_declaring_no_plugins_fails_loudly(monkeypatch):
    monkeypatch.setattr(cli.subprocess, "run", _fake_probe(json.dumps({"plugins": []})))
    with pytest.raises(SystemExit):
        cli.probe_image_plugin_roots("empty-image:latest")


def test_a_relative_source_fails_loudly(monkeypatch):
    """Only an absolute container path can be a mount destination. A relative
    `./<plugin>/<version>` would resolve against Docker's own cwd and land
    somewhere nothing reads."""
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        _fake_probe(json.dumps({"plugins": [{"name": "aops", "source": "./aops/0.4.0"}]})),
    )
    with pytest.raises(SystemExit):
        cli.probe_image_plugin_roots("relative-image:latest")


# ---------------------------------------------------------------------------
# resolve_live_edit_mounts: host builds -> the image's own destinations
# ---------------------------------------------------------------------------


def test_no_dist_build_fails_loudly(tmp_path):
    with pytest.raises(SystemExit):
        cli.resolve_live_edit_mounts(tmp_path, {"aops": "/some/dest"})


def test_destinations_are_the_images_not_anything_derived_host_side(tmp_path, monkeypatch):
    """The defect this fix closes. The host's own version — whatever `make
    build` or git state would produce today — must not reach the destination:
    the container's cache path embeds the version baked at image-build time,
    and the two diverge the moment the image is not rebuilt. Proven by making
    any subprocess call (git, docker, anything) an error and confirming the
    destination still comes out as the image's stale path."""

    def _boom(*a, **k):
        raise AssertionError("must not shell out to re-derive a version host-side")

    monkeypatch.setattr(cli.subprocess, "run", _boom)
    _write_dist_build(tmp_path, ["aops"])

    image_roots = {"aops": f"/home/worker/.claude/plugins/cache/academicOps/aops/{_IMAGE_VERSION}"}
    mounts = cli.resolve_live_edit_mounts(tmp_path, image_roots)

    claude_mounts = [m for m in mounts if "/.claude/" in m[2]]
    assert len(claude_mounts) == 1
    name, host_src, container_dest = claude_mounts[0]
    assert name == "aops"
    assert host_src == tmp_path / "dist" / "aops-claude"
    assert container_dest == image_roots["aops"]


def test_the_plugin_set_comes_from_the_image_too(tmp_path):
    """A plugin the host has built but the image never installed has no
    destination to mount over, so it is not mounted at all — mounting it
    somewhere invented is the silent no-op this feature refuses."""
    _write_dist_build(tmp_path, ["aops", "aops-pkb", "aops-tools"])
    mounts = cli.resolve_live_edit_mounts(tmp_path, {"aops": "/dest/aops"})
    assert {name for name, _, _ in mounts} == {"aops"}


def test_the_agy_destination_is_flat_and_unversioned(tmp_path):
    """agy installs each plugin at `plugins/<name>` with no version segment
    (Dockerfile: `cp -r "$MP_ROOT/$p-agy" .../plugins/$p`), so there is no
    version to resolve on that side at all."""
    _write_dist_build(tmp_path, ["aops"])
    mounts = cli.resolve_live_edit_mounts(tmp_path, {"aops": "/dest/aops"})
    agy = [m for m in mounts if m[2].startswith(cli.CONTAINER_AGY_PLUGINS_ROOT)]
    assert len(agy) == 1
    _, host_src, container_dest = agy[0]
    assert host_src == tmp_path / "dist" / "aops-agy"
    assert container_dest == f"{cli.CONTAINER_AGY_PLUGINS_ROOT}/aops"


def test_missing_host_claude_build_fails_loudly(tmp_path):
    (tmp_path / "dist" / "aops-agy").mkdir(parents=True)
    # dist/aops-claude deliberately not created.
    with pytest.raises(SystemExit):
        cli.resolve_live_edit_mounts(tmp_path, {"aops": "/dest/aops"})


def test_missing_host_agy_build_fails_loudly(tmp_path):
    (tmp_path / "dist" / "aops-claude").mkdir(parents=True)
    # dist/aops-agy deliberately not created.
    with pytest.raises(SystemExit):
        cli.resolve_live_edit_mounts(tmp_path, {"aops": "/dest/aops"})


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
    """This is the exact silent-no-op bug: a destination that does not exist
    in the image. verify_live_edit_destinations must refuse to proceed rather
    than let docker auto-create the mount point."""
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


def _docker_faker(captured, manifest, verify_returncode=0):
    """A `subprocess.run` stand-in that answers both --live-edit probes the
    way a real image would, and records every docker argv. No real docker
    call is ever made."""

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker":
            captured.append(list(cmd))
            if "--entrypoint" in cmd and "cat" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout=manifest, stderr="")
            if "--entrypoint" in cmd and "sh" in cmd:
                return subprocess.CompletedProcess(
                    cmd,
                    verify_returncode,
                    stdout="",
                    stderr="no such directory" if verify_returncode else "",
                )
        return subprocess.CompletedProcess(cmd, 0)

    return fake_run


def _capture_all_docker_cmds(monkeypatch, tmp_path, argv, manifest=None, verify_returncode=0):
    """Invoke `polecat run ...` and return (result, [every docker argv run]),
    including both --live-edit preflight probes if they happened."""
    _base_mocks(monkeypatch, tmp_path)
    captured = []
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        _docker_faker(captured, manifest or _image_manifest(["aops"]), verify_returncode),
    )
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, argv)
    return result, captured


def _main_docker_run(captured, image="test-image:latest"):
    for cmd in captured:
        if "--entrypoint" not in cmd and image in cmd:
            return cmd
    raise AssertionError(f"no main docker run found among {captured!r}")


def test_live_edit_absent_by_default(tmp_path, monkeypatch):
    """Opt-in only: no --live-edit flag means no plugin-path -v mount and no
    preflight probe at all."""
    result, captured = _capture_all_docker_cmds(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo")]
    )
    assert result.exit_code == 0, result.output
    main_cmd = _main_docker_run(captured)
    assert not any("/home/worker/.claude/plugins/cache/" in arg for arg in main_cmd)
    assert not any(cli.CONTAINER_AGY_PLUGINS_ROOT in arg for arg in main_cmd)
    # No preflight probe ran either — the whole mechanism is a no-op when off.
    assert len(captured) == 1


def test_live_edit_mounts_over_the_images_stale_version_not_the_hosts(tmp_path, monkeypatch):
    """The end-to-end form of the fix: the image was built long ago at
    `_IMAGE_VERSION` and the host has since moved on. The `-v` destination
    must be the image's path, so the mount actually shadows what the
    container reads."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _write_dist_build(repo, ["aops"])

    result, captured = _capture_all_docker_cmds(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(repo), "--live-edit"]
    )
    assert result.exit_code == 0, result.output

    main_cmd = _main_docker_run(captured)
    expected_dest = f"/home/worker/.claude/plugins/cache/academicOps/aops/{_IMAGE_VERSION}"
    expected = f"{repo / 'dist' / 'aops-claude'}:{expected_dest}:ro"
    assert expected in main_cmd
    assert main_cmd[main_cmd.index(expected) - 1] == "-v"

    expected_agy = f"{repo / 'dist' / 'aops-agy'}:{cli.CONTAINER_AGY_PLUGINS_ROOT}/aops:ro"
    assert expected_agy in main_cmd
    assert main_cmd[main_cmd.index(expected_agy) - 1] == "-v"

    # Both preflight probes ran, against that same path, before the main
    # container started.
    probe_cmds = [c for c in captured if "--entrypoint" in c]
    assert len(probe_cmds) == 2
    assert probe_cmds[0][-1] == cli.CONTAINER_MARKETPLACE_MANIFEST
    assert expected_dest in probe_cmds[1][-1]
    assert captured.index(probe_cmds[1]) < captured.index(main_cmd)


def test_live_edit_refuses_to_start_when_destination_is_bogus(tmp_path, monkeypatch):
    """The loud-failure path: the preflight probe reports a plugin path does
    not exist in the image, so no container may start at all — neither
    probe's own docker run nor the main run may be mistaken for success."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _write_dist_build(repo, ["aops"])

    result, captured = _capture_all_docker_cmds(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(repo), "--live-edit"],
        verify_returncode=1,
    )

    assert result.exit_code != 0
    assert "live-edit" in result.output
    # Only the two preflight probes ran; the main container never started.
    assert len(captured) == 2
    assert all("--entrypoint" in c for c in captured)


def test_live_edit_refuses_when_the_image_cannot_be_read(tmp_path, monkeypatch):
    """No manifest in the image means no known destination. Refusing here is
    what keeps a guessed path from becoming an auto-created empty mount."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _write_dist_build(repo, ["aops"])

    _base_mocks(monkeypatch, tmp_path)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker":
            captured.append(list(cmd))
            if "--entrypoint" in cmd and "cat" in cmd:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="No such file")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, ["run", "claude", "-d", str(repo), "--live-edit"])

    assert result.exit_code != 0
    assert "live-edit" in result.output
    assert len(captured) == 1
    assert captured[0][-1] == cli.CONTAINER_MARKETPLACE_MANIFEST
