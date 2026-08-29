"""Marketplace manifest generation from build/marketplace.toml.

## marketplace.toml schema

    name = "academicOps"
    description = "..."

    [owner]
    name = "Nicolas Suzor"
    email = "nic@suzor.net"

    [[plugins]]
    directory = "aops"     # plugins/<directory> — source dir, matches build.py's discovery
    name = "aops"           # marketplace name; ships as dist/<name>-<client>
    description = "..."
    category = "productivity"

`name`, `description`, `owner`, and `plugins` are all required top-level keys.
Every `[[plugins]]` entry requires `directory`, `name`, `description`, `category`.
"""

import json
import shutil
import tomllib
import zipfile
from pathlib import Path
from typing import Any

from build.errors import BuildError
from build.tree import ignore

_REQUIRED_TOP = ("name", "description", "owner", "plugins")
_REQUIRED_PLUGIN = ("directory", "name", "description", "category")


def load_marketplace_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise BuildError(f"marketplace declaration not found: {path}")

    data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    for key in _REQUIRED_TOP:
        if key not in data:
            raise BuildError(f"{path}: missing required top-level key '{key}'")
    for entry in data["plugins"]:
        for key in _REQUIRED_PLUGIN:
            if key not in entry:
                raise BuildError(f"{path}: [[plugins]] entry missing '{key}': {entry}")
    return data


def _plugin_entries(
    decl: dict[str, Any],
    version: str,
    dist_root: Path,
    owner: dict[str, Any],
    *,
    source_prefix: str = "",
) -> list[dict[str, Any]]:
    plugins = []
    for entry in decl["plugins"]:
        name = entry["name"]
        if not (dist_root / f"{name}-claude").exists():
            continue  # not built this run — reflect only what actually shipped
        plugins.append(
            {
                "name": name,
                "description": entry["description"],
                "version": version,
                "author": {"name": owner.get("name", "")},
                "source": f"./{source_prefix}{name}-claude",
                "category": entry["category"],
            }
        )
    return plugins


def generate_local_marketplace(decl: dict[str, Any], version: str, dist_root: Path) -> Path:
    """dist/.claude-plugin/marketplace.json — `make install-dev`'s local channel,
    named `aops` so it's visibly distinct from the released marketplace."""
    data = {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": "aops",
        "description": f"{decl['name']} LOCAL dev build — distinct from the released '{decl['name']}' marketplace",
        "owner": {"name": "Local Dev"},
        "plugins": _plugin_entries(decl, version, dist_root, {"name": "Local Dev"}),
    }
    out = dist_root / ".claude-plugin" / "marketplace.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out


def generate_production_marketplace(decl: dict[str, Any], version: str, dist_root: Path) -> Path:
    """dist/marketplace-production.json — published at the root of the `dist` branch."""
    data = {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": decl["name"],
        "description": decl["description"],
        "owner": decl["owner"],
        "plugins": _plugin_entries(decl, version, dist_root, decl["owner"]),
    }
    out = dist_root / "marketplace-production.json"
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out


def generate_cowork_dist(decl: dict[str, Any], version: str, dist_root: Path) -> Path:
    """dist/cowork/ — a local directory marketplace assembled from the built
    claude dists (Cowork's RemotePluginManager wipes github-source marketplaces
    on every restart, so a directory source is required), plus per-plugin
    upload zips for the manual path. No URL baking, no separate plugin source —
    it reuses the claude dists verbatim."""
    cowork_root = dist_root / "cowork"
    if cowork_root.exists():
        shutil.rmtree(cowork_root)
    cowork_root.mkdir(parents=True)

    plugins = []
    for entry in decl["plugins"]:
        name = entry["name"]
        src = dist_root / f"{name}-claude"
        if not src.exists():
            continue

        dst = cowork_root / name
        shutil.copytree(src, dst, ignore=ignore())
        plugins.append(
            {
                "name": name,
                "description": entry["description"],
                "version": version,
                "author": {"name": decl["owner"].get("name", "")},
                "source": f"./{name}",
                "category": entry["category"],
            }
        )

        zip_path = cowork_root / f"{name}-v{version}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(dst.rglob("*")):
                if path.is_file():
                    zf.write(path, str(path.relative_to(cowork_root)))

    data = {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": "academicOps-cowork",
        "description": f"{decl['name']} Cowork channel — local directory marketplace",
        "owner": decl["owner"],
        "plugins": plugins,
    }
    marketplace_dir = cowork_root / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    (marketplace_dir / "marketplace.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    return cowork_root


def generate_openclaw_dist(decl: dict[str, Any], version: str, dist_root: Path) -> Path:
    """dist/openclaw/ — a local directory marketplace assembled for OpenClaw
    runtime context, with per-plugin directories and distribution zips."""
    openclaw_root = dist_root / "openclaw"
    if openclaw_root.exists():
        shutil.rmtree(openclaw_root)
    openclaw_root.mkdir(parents=True)

    plugins = []
    for entry in decl["plugins"]:
        name = entry["name"]
        src = dist_root / f"{name}-openclaw"
        if not src.exists():
            src = dist_root / f"{name}-claude"
        if not src.exists():
            continue

        dst = openclaw_root / name
        shutil.copytree(src, dst, ignore=ignore())
        plugins.append(
            {
                "name": name,
                "description": entry["description"],
                "version": version,
                "author": {"name": decl["owner"].get("name", "")},
                "source": f"./{name}",
                "category": entry["category"],
            }
        )

        zip_path = openclaw_root / f"{name}-v{version}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(dst.rglob("*")):
                if path.is_file():
                    zf.write(path, str(path.relative_to(openclaw_root)))

    data = {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": "academicOps-openclaw",
        "description": f"{decl['name']} OpenClaw channel — local directory marketplace",
        "owner": decl["owner"],
        "plugins": plugins,
    }
    marketplace_dir = openclaw_root / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    (marketplace_dir / "marketplace.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    return openclaw_root
