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
import os
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


def _bake_cowork_mcp_json(mcp_path: Path, plugin_name: str) -> str | None:
    """The Cowork channel's .mcp.json: every server that defers to
    $PKB_MCP_URL collapsed into one `type: http` server whose URL is the
    literal value of PKB_MCP_URL in the build environment — or None to ship
    the file as the claude dist built it.

    Cowork launches a plugin's MCP servers from a bare environment: no login
    shell, no launchctl setenv, nothing the plugin's own config did not carry
    in. `${PKB_MCP_URL}` in a url does not expand there (the client reports
    "Missing environment variables"), and a stdio command that reads it gets
    the empty string. Neither install path — directory marketplace or zip
    upload — has a way to supply the value after the fact, so the URL has to
    be in the artifact. A literal `type: http` url is the one form Cowork
    connects with (tested 2026-09-11), so that is what the channel ships; the
    stdio launcher (scripts/run-mcp.sh) is not used here.

    The URL is read from the build environment and never committed. An unset
    PKB_MCP_URL is NOT a build failure: the published channel is built without
    one and ships the claude dist's env-var form unchanged, which means its
    services MCP does not work in Cowork. Only a local build with PKB_MCP_URL
    exported produces a usable Cowork channel. The warning below is the whole
    signal, so don't quiet it.

    Only dist/cowork/ is rewritten. dist/<name>-claude keeps the env-var form,
    which Claude Code resolves at launch.
    """
    try:
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BuildError(f"{mcp_path}: malformed .mcp.json: {e}") from e

    servers = data.get("mcpServers", {})
    # Only servers that defer to the env var at launch — anything with a
    # concrete endpoint of its own is left alone.
    pkb_names = [name for name, cfg in servers.items() if "PKB_MCP_URL" in json.dumps(cfg)]
    if not pkb_names:
        return None

    baked = os.environ.get("PKB_MCP_URL", "").strip()
    if not baked:
        print(
            f"  cowork: {plugin_name} — PKB_MCP_URL unset at build time; "
            "the channel ships with no PKB endpoint and its services MCP will "
            "fail at first use"
        )
        return None

    # The streamable-HTTP endpoint is served without a trailing slash; a
    # trailing slash 404s.
    while baked.endswith("/"):
        baked = baked[:-1]

    # One server, not one per transport: a second entry pointing at the same
    # endpoint would load every PKB tool schema twice.
    for name in pkb_names:
        del servers[name]
    servers["services"] = {"type": "http", "url": baked}
    return json.dumps(data, indent=2) + "\n"


def generate_cowork_dist(decl: dict[str, Any], version: str, dist_root: Path) -> Path:
    """dist/cowork/ — a local directory marketplace assembled from the built
    claude dists (Cowork's RemotePluginManager wipes github-source marketplaces
    on every restart, so a directory source is required), plus per-plugin
    upload zips for the manual path.

    Both are the claude dist with one difference: .mcp.json gets $PKB_MCP_URL
    resolved into a literal http server at build time, because neither Cowork
    install path can supply it afterwards (see _bake_cowork_mcp_json). The zip
    is the directory copy, verbatim."""
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
        mcp_path = dst / ".mcp.json"
        if mcp_path.is_file():
            baked = _bake_cowork_mcp_json(mcp_path, name)
            if baked is not None:
                mcp_path.write_text(baked, encoding="utf-8")
                print(f"  cowork: {name} — PKB_MCP_URL baked into .mcp.json as a literal http url")
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
