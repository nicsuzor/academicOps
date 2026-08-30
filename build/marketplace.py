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


def _bake_cowork_mcp_json(mcp_path: Path, plugin_dir: Path) -> str | None:
    """The zip variant's .mcp.json, with $PKB_MCP_URL resolved at build time —
    or None to zip the file unchanged.

    Cowork plugins are installed by uploading the zip through the desktop app
    (Customize -> Add plugins -> Upload a file). The MCP server it launches
    from that install gets a bare environment: no login shell, no launchctl
    setenv, nothing the plugin's own config did not carry in. The claude dist's
    server config defers to `$PKB_MCP_URL` at launch, which in Cowork expands
    to the empty string — `fastmcp run ""` exits immediately and the client
    reports "Connection closed" (observed 2026-08-29). There is no --config
    equivalent on the upload path to supply it after the fact, so the URL has
    to be in the artifact.

    So the zip swaps that server for the stdio launcher the plugin already
    ships (scripts/run-mcp.sh) with the URL resolved into its env block. The
    launcher is used rather than an inline `uvx` line because the same bare
    environment routinely lacks uvx on PATH, and probing for it is exactly
    what run-mcp.sh does.

    The URL is read from the build environment and never committed. An unset
    PKB_MCP_URL is NOT a build failure: the published zips are built without
    one, and are expected to ship without one — which means Cowork's services
    MCP does not work from a published zip, and will not until there is a way
    to configure it after install. Only a local build with PKB_MCP_URL
    exported produces a usable Cowork zip. The warning below is the whole
    signal, so don't quiet it.

    Only the zip is rewritten. dist/<name>-claude and the dist/cowork/<name>
    directory copy keep the env-var form, which is correct for Claude Code and
    for a directory-marketplace install (`claude plugin install --config`).
    """
    baked = os.environ.get("PKB_MCP_URL", "").strip()
    if not baked:
        if "PKB_MCP_URL" in mcp_path.read_text(encoding="utf-8"):
            print(
                f"  cowork zip: {plugin_dir.name} — PKB_MCP_URL unset at build time; "
                "the zip ships with no PKB endpoint and its services MCP will fail "
                "at first use"
            )
        return None

    launcher = plugin_dir / "scripts" / "run-mcp.sh"
    if not launcher.exists():
        return None

    try:
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BuildError(f"{mcp_path}: malformed .mcp.json: {e}") from e

    servers = data.get("mcpServers", {})
    rewritten = False
    for name, cfg in list(servers.items()):
        # Only servers that defer to the env var at launch — anything with a
        # concrete endpoint of its own is left alone.
        if "PKB_MCP_URL" not in json.dumps(cfg):
            continue
        servers[name] = {
            "command": "bash",
            "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/run-mcp.sh"],
            "env": {"PKB_MCP_URL": baked},
        }
        rewritten = True

    if not rewritten:
        return None
    return json.dumps(data, indent=2) + "\n"


def generate_cowork_dist(decl: dict[str, Any], version: str, dist_root: Path) -> Path:
    """dist/cowork/ — a local directory marketplace assembled from the built
    claude dists (Cowork's RemotePluginManager wipes github-source marketplaces
    on every restart, so a directory source is required), plus per-plugin
    upload zips for the manual path.

    The directory copy reuses the claude dists verbatim. The zips do not: their
    .mcp.json gets $PKB_MCP_URL resolved at build time, because the upload path
    has no way to supply it afterwards (see _bake_cowork_mcp_json)."""
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
                if not path.is_file():
                    continue
                arcname = str(path.relative_to(cowork_root))
                baked = None
                if path.name == ".mcp.json" and path.parent == dst:
                    baked = _bake_cowork_mcp_json(path, dst)
                if baked is not None:
                    zf.writestr(arcname, baked)
                    print(f"  cowork zip: {name} — PKB_MCP_URL baked into .mcp.json")
                else:
                    zf.write(path, arcname)

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
