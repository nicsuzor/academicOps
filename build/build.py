#!/usr/bin/env python3
"""Assembles dist/<marketplace-name>-<client>/ for every plugin and client.

specs/ARCHITECTURE.md: "build/build.py assembles dist/<plugin>-<client> for
each plugin and client." Stages, in order: inject, render
manifests, adapt to client, package. Then generate the marketplace manifests.

Usage (always as a module — `python build/build.py` breaks the `build.*`
package imports):
    uv run python -m build.build                       # build everything, both clients
    uv run python -m build.build --plugins aops pkb     # build a subset
    uv run python -m build.build --clients claude       # one client only
    uv run python -m build.build --version              # print the version and exit
"""

import argparse
import shutil
import tarfile
from pathlib import Path
from typing import Any

from build.clients import agy as agy_client
from build.clients import claude as claude_client
from build.context import BuildContext, Plugin
from build.errors import BuildError
from build.manifest import merge_one_level, render_template, template_stem
from build.marketplace import (
    generate_cowork_dist,
    generate_local_marketplace,
    generate_production_marketplace,
    load_marketplace_toml,
)
from build.shared import inject_shared
from build.tree import (
    assert_no_build_artifacts,
    copytree_filtered,
    ignore,
    mark_shebangs_executable,
)
from build.version import get_current_version

CLIENT_ADAPTERS = {
    "claude": claude_client.adapt,
    "agy": agy_client.adapt,
}

_STAGE_EXCLUDE_TOP = frozenset({"manifest"})  # manifest/ is rendered per client, never shipped raw


def discover_plugins(
    project_root: Path, decl: dict[str, Any], requested: list[str] | None
) -> list[Plugin]:
    declared = {entry["directory"]: entry for entry in decl["plugins"]}
    directories = requested if requested is not None else list(declared.keys())

    plugins = []
    for directory in directories:
        if directory not in declared:
            raise BuildError(f"'{directory}' is not declared in marketplace.toml [[plugins]]")
        source_dir = project_root / "plugins" / directory
        if not source_dir.exists():
            raise BuildError(f"plugin source missing: {source_dir} (declared as '{directory}')")
        plugins.append(
            Plugin(
                directory=directory,
                marketplace_name=declared[directory]["name"],
                description=declared[directory]["description"],
                category=declared[directory]["category"],
                source_dir=source_dir,
            )
        )
    return plugins


def _stage_plugin(plugin: Plugin, lib_dir: Path, stage_dir: Path, version: str) -> None:
    """Stages 1-2: a client-agnostic copy with shared content injected and
    built once, then reused for every client."""
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)

    copytree_filtered(plugin.source_dir, stage_dir, exclude_top=_STAGE_EXCLUDE_TOP)
    inject_shared(plugin.source_dir / "manifest" / "plugin.toml", lib_dir, stage_dir)

    repo_root = plugin.source_dir.parent.parent
    plugin_pyproject = plugin.source_dir / "pyproject.toml"
    plugin_uvlock = plugin.source_dir / "uv.lock"

    if plugin_pyproject.exists():
        shutil.copy2(plugin_pyproject, stage_dir / "pyproject.toml")
        if plugin_uvlock.exists():
            shutil.copy2(plugin_uvlock, stage_dir / "uv.lock")
    else:
        template_path = repo_root / "templates" / "plugin" / "pyproject.template.toml"
        if template_path.exists():
            content = template_path.read_text(encoding="utf-8")
            content = content.replace("${PLUGIN_NAME}", plugin.marketplace_name)
            content = content.replace("${VERSION}", version)
            content = content.replace("${PLUGIN_DESCRIPTION}", plugin.description)
            (stage_dir / "pyproject.toml").write_text(content, encoding="utf-8")


def _render_manifests(
    plugin: Plugin, client: str, version: str, owner: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Stage 3."""
    manifest_dir = plugin.source_dir / "manifest"
    manifests: dict[str, dict[str, Any]] = {}

    if manifest_dir.exists():
        for template_path in sorted(manifest_dir.glob("*.template.json")):
            stem = template_stem(template_path)
            data = render_template(template_path, client)
            manifests[stem] = data

    base_plugin = {
        "name": plugin.marketplace_name,
        "description": plugin.description,
        "author": {"name": owner.get("name", "")},
        "license": "MIT",
    }

    plugin_data = base_plugin
    if "plugin" in manifests:
        plugin_data = merge_one_level(base_plugin, manifests["plugin"])

    plugin_data["version"] = version
    manifests["plugin"] = plugin_data

    return manifests


def _prune_empty_dirs(build_dir: Path) -> None:
    for dirpath in sorted(build_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if dirpath.is_dir() and not any(dirpath.iterdir()):
            dirpath.rmdir()


def _package(build_dir: Path, client: str, dist_root: Path) -> Path:
    """Stage 5: tar per client. Both claude and agy tarballs contain the
    directory itself at the archive root."""
    archive_path = dist_root / f"{build_dir.name}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(build_dir, arcname=build_dir.name)
    return archive_path


def _build_plugin_client(
    plugin: Plugin,
    client: str,
    stage_dir: Path,
    dist_root: Path,
    version: str,
    owner: dict[str, Any],
) -> Path:
    adapter = CLIENT_ADAPTERS.get(client)
    if adapter is None:
        raise BuildError(f"unknown client {client!r} — expected one of {sorted(CLIENT_ADAPTERS)}")

    build_dir = dist_root / f"{plugin.marketplace_name}-{client}"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    shutil.copytree(stage_dir, build_dir, ignore=ignore())

    manifests = _render_manifests(plugin, client, version, owner)  # stage 3
    ctx = BuildContext(plugin=plugin, client=client, version=version, manifests=manifests)
    adapter(build_dir, ctx)  # stage 4

    _prune_empty_dirs(build_dir)
    # A shipped `#!` file is an entry point; copy2 would otherwise ship it with
    # whatever mode the source repo happened to commit.
    mark_shebangs_executable(build_dir)
    assert_no_build_artifacts(build_dir)
    _package(build_dir, client, dist_root)  # stage 5
    return build_dir


def build_all(
    project_root: Path,
    dist_root: Path,
    *,
    marketplace_path: Path | None = None,
    clients: tuple[str, ...] = ("claude", "agy"),
    plugins: list[str] | None = None,
    version: str | None = None,
) -> dict[str, list[Path]]:
    lib_dir = project_root / "lib"
    if not lib_dir.exists():
        raise BuildError(f"lib/ not found at {lib_dir}")

    marketplace_path = marketplace_path or (project_root / "build" / "marketplace.toml")
    decl = load_marketplace_toml(marketplace_path)
    resolved_version = version or get_current_version(project_root)

    dist_root.mkdir(parents=True, exist_ok=True)
    stage_root = dist_root / ".stage"

    built: dict[str, list[Path]] = {}
    try:
        for plugin in discover_plugins(project_root, decl, plugins):
            stage_dir = stage_root / plugin.directory
            _stage_plugin(plugin, lib_dir, stage_dir, resolved_version)
            for client in clients:
                build_dir = _build_plugin_client(
                    plugin, client, stage_dir, dist_root, resolved_version, decl["owner"]
                )
                built.setdefault(plugin.marketplace_name, []).append(build_dir)
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)

    if "claude" in clients:
        generate_local_marketplace(decl, resolved_version, dist_root)
        generate_production_marketplace(decl, resolved_version, dist_root)
        generate_cowork_dist(decl, resolved_version, dist_root)

    return built


def main() -> None:
    parser = argparse.ArgumentParser(description="Build academicOps plugin distributions")
    parser.add_argument(
        "--plugins", nargs="+", default=None, help="Build only these plugin directories"
    )
    parser.add_argument(
        "--clients", nargs="+", default=["claude", "agy"], choices=["claude", "agy"]
    )
    parser.add_argument("--version", action="store_true", help="Print the current version and exit")
    parser.add_argument(
        "--set-version", type=str, default=None, help="Override the derived version"
    )
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--dist-root", type=Path, default=None)
    args = parser.parse_args()

    project_root = args.project_root or Path(__file__).resolve().parent.parent

    if args.version:
        print(get_current_version(project_root))
        return

    dist_root = args.dist_root or (project_root / "dist")
    built = build_all(
        project_root,
        dist_root,
        clients=tuple(args.clients),
        plugins=args.plugins,
        version=args.set_version,
    )
    for name, dirs in sorted(built.items()):
        print(f"✓ built {name}: " + ", ".join(d.name for d in dirs))


if __name__ == "__main__":
    main()
