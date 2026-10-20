#!/usr/bin/env python3
"""Prune stale plugin state across both Claude Code surfaces.

CLI surface (`~/.claude/plugins/`):
  - cache/*/*/<version>/ dirs not referenced by installed_plugins.json
  - .install-manifests/<plugin>@<marketplace>.json whose marketplace dir is gone
  - uninstalls every aops plugin from @academicOps
  - disables claude.ai-synced copies (~/.claude/plugins/synced/<org>_<user>/<name>~g2)
  - strips enabledPlugins in ~/.claude/settings*.json absent from dist/.claude-plugin/marketplace.json or naming @academicOps
  - empties ~/.claude/plugins/.trash/

Desktop GUI surface (`~/Library/Application Support/Claude/
local-agent-mode-sessions/<account>/<surface>/rpm/`):
  - aops-* entries in rpm/manifest.json, and their unpacked plugin_<id>/ dirs.
    Use this when the GUI's "Uninstall plugin" button fails.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

STALE_PLUGIN_NAMES = {
    "aops",
    "aops-cope",
    "aops-extras",
    "aops-ida",
    "aops-jr",
    "aops-pkb",
    "aops-tools",
    "aops-ts",
    "pkb",
    "aops-core",
    "aops-cowork",
}


def get_aops_plugin_names() -> set[str]:
    import tomllib

    toml_path = Path(__file__).resolve().parent.parent / "build" / "marketplace.toml"
    if not toml_path.exists():
        raise FileNotFoundError(f"Authoritative marketplace definition missing: {toml_path}")
    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    return {p["name"] for p in data.get("plugins", [])}


def get_dist_plugin_names() -> set[str]:
    dist_manifest = (
        Path(__file__).resolve().parent.parent / "dist" / ".claude-plugin" / "marketplace.json"
    )
    if dist_manifest.exists():
        data = json.loads(dist_manifest.read_text(encoding="utf-8"))
        return {p["name"] for p in data.get("plugins", [])}
    return get_aops_plugin_names()


def is_aops_plugin(p: dict[str, Any]) -> bool:
    name = str(p.get("name", ""))
    mp_name = str(p.get("marketplaceName", ""))
    display = str(p.get("displayName", ""))
    all_names = get_aops_plugin_names() | STALE_PLUGIN_NAMES
    base_name = name.split("~")[0]
    if (
        base_name in all_names
        or name in all_names
        or name.startswith("aops-")
        or name.startswith("aops_")
    ):
        return True
    if mp_name in {"academicOps", "academicOps-cowork", "aops"}:
        return True
    if display.lower().startswith("aops") or display.lower().startswith("academicops"):
        return True
    return False


def remove_marketplaces(root: Path, marketplaces: tuple[str, ...]) -> None:
    """Remove named marketplaces from known_marketplaces.json."""
    known_mp = root / "known_marketplaces.json"
    if not known_mp.exists():
        return
    mp_data = json.loads(known_mp.read_text(encoding="utf-8"))
    removed = []
    for mp in marketplaces:
        if mp in mp_data:
            del mp_data[mp]
            removed.append(mp)
    if removed:
        known_mp.write_text(json.dumps(mp_data, indent=2) + "\n", encoding="utf-8")
        print(f"  removed {', '.join(removed)} from known_marketplaces.json")


def uninstall_academicops_plugins(root: Path) -> None:
    """Uninstall every aops plugin from @academicOps and prune associated cache/manifests."""
    reg = root / "installed_plugins.json"
    data: dict[str, Any] = (
        json.loads(reg.read_text(encoding="utf-8")) if reg.exists() else {"plugins": {}}
    )
    plugins: dict[str, Any] = data.get("plugins", {})
    stale_keys = [
        k for k in plugins if k.endswith("@academicOps") or k.split("@")[-1] == "academicOps"
    ]

    claude_bin = shutil.which("claude")
    if claude_bin and stale_keys:
        for key in stale_keys:
            for scope in ("user", "local", "project"):
                subprocess.run(
                    [claude_bin, "plugin", "uninstall", "--scope", scope, key],
                    capture_output=True,
                    check=False,
                )

    if reg.exists():
        data = json.loads(reg.read_text(encoding="utf-8"))
        plugins = data.get("plugins", {})
        remaining = [
            k for k in plugins if k.endswith("@academicOps") or k.split("@")[-1] == "academicOps"
        ]
        if remaining:
            for k in remaining:
                del plugins[k]
            reg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(f"  uninstalled {len(remaining)} plugin(s) from @academicOps in {reg.name}")

    manifests = root / ".install-manifests"
    if manifests.exists():
        for m in manifests.glob("*@academicOps.json"):
            m.unlink(missing_ok=True)
            print(f"  removed manifest {m.name}")

    cache = root / "cache" / "academicOps"
    if cache.exists():
        shutil.rmtree(cache)
        print("  removed cache/academicOps")

    remove_marketplaces(root, ("academicOps",))


def is_dev_channel_active(root: Path) -> bool:
    """Check whether local development marketplace (@aops) is active."""
    known_mp = root / "known_marketplaces.json"
    if known_mp.exists():
        mp_data = json.loads(known_mp.read_text(encoding="utf-8"))
        if "aops" in mp_data:
            return True
    reg = root / "installed_plugins.json"
    if reg.exists():
        data = json.loads(reg.read_text(encoding="utf-8"))
        for key in data.get("plugins", {}):
            if key.endswith("@aops") or key.split("@")[-1] == "aops":
                return True
    return False


def disable_synced_plugins(root: Path, settings_dir: Path) -> None:
    """Make exactly one copy of each plugin load per surface by managing claude.ai-synced copies.

    When local/dev plugins (@aops) are active, synced copies (@synced) are disabled to prevent duplicate loading.
    When switching to the catalog release channel (make install), synced copies are not disabled so they can load.
    """
    synced_root = root / "synced"
    synced_plugins: set[str] = set()
    if synced_root.exists():
        for p in synced_root.glob("*/*"):
            name = p.stem.split("~")[0]
            if is_aops_plugin({"name": name}):
                synced_plugins.add(name)

    all_aops = get_aops_plugin_names() | synced_plugins
    dev_active = is_dev_channel_active(root)

    to_disable = sorted(all_aops) if dev_active else []
    to_enable = sorted(all_aops) if not dev_active else []

    claude_bin = shutil.which("claude")
    if claude_bin:
        for p in to_disable:
            subprocess.run(
                [claude_bin, "plugin", "disable", f"{p}@synced"],
                capture_output=True,
                check=False,
            )
        for p in to_enable:
            subprocess.run(
                [claude_bin, "plugin", "enable", f"{p}@synced"],
                capture_output=True,
                check=False,
            )

    for filename in ("settings.json", "settings.local.json"):
        spath = settings_dir / filename
        if not spath.exists():
            continue
        sdata = json.loads(spath.read_text(encoding="utf-8"))
        enabled = sdata.setdefault("enabledPlugins", {})
        if isinstance(enabled, dict):
            updated = False
            for p in to_disable:
                key = f"{p}@synced"
                if enabled.get(key) is not False:
                    enabled[key] = False
                    updated = True
            for p in to_enable:
                key = f"{p}@synced"
                if key in enabled and enabled[key] is False:
                    del enabled[key]
                    updated = True
            if updated:
                spath.write_text(json.dumps(sdata, indent=2) + "\n", encoding="utf-8")
                print(f"  updated synced plugin state in {filename}")


def clean_settings(settings_dir: Path, dist_plugins: set[str] | None = None) -> None:
    """Strip enabledPlugins entries absent from dist/.claude-plugin/marketplace.json or naming @academicOps."""
    if dist_plugins is None:
        dist_plugins = get_dist_plugin_names()

    for filename in ("settings.json", "settings.local.json"):
        spath = settings_dir / filename
        if not spath.exists():
            continue
        sdata = json.loads(spath.read_text(encoding="utf-8"))

        updated = False
        enabled = sdata.get("enabledPlugins")
        if isinstance(enabled, dict):
            cleaned: dict[str, Any] = {}
            for key, val in enabled.items():
                if "@academicOps" in key:
                    continue
                plugin_name = key.split("@")[0]
                if plugin_name not in dist_plugins:
                    continue
                cleaned[key] = val

            if cleaned != enabled:
                sdata["enabledPlugins"] = cleaned
                updated = True

        extra_mp = sdata.get("extraKnownMarketplaces")
        if isinstance(extra_mp, dict) and "academicOps" in extra_mp:
            del extra_mp["academicOps"]
            updated = True

        if updated:
            spath.write_text(json.dumps(sdata, indent=2) + "\n", encoding="utf-8")
            print(f"  stripped stale plugin entries from {filename}")


def clean_trash(root: Path) -> None:
    """Empty ~/.claude/plugins/.trash/."""
    trash = root / ".trash"
    trash.mkdir(parents=True, exist_ok=True)
    for item in trash.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink(missing_ok=True)
    print("  emptied .trash/")


def clean_cli(root: Path | None = None, settings_dir: Path | None = None) -> None:
    root = root or (Path.home() / ".claude/plugins")
    settings_dir = settings_dir or (Path.home() / ".claude")

    uninstall_academicops_plugins(root)
    clean_trash(root)
    disable_synced_plugins(root, settings_dir)
    clean_settings(settings_dir)

    reg = root / "installed_plugins.json"
    data = json.load(open(reg)) if reg.exists() else {"plugins": {}}
    active = {
        Path(e["installPath"]).resolve()
        for entries in data.get("plugins", {}).values()
        for e in entries
        if e.get("installPath")
    }
    cache = root / "cache"
    if cache.exists():
        for mp in cache.iterdir():
            if not mp.is_dir():
                continue
            for plugin in mp.iterdir():
                if not plugin.is_dir():
                    continue
                for v in plugin.iterdir():
                    if v.is_dir() and v.resolve() not in active:
                        shutil.rmtree(v)
                        print(f"  removed cache {v.relative_to(cache)}")

    manifests = root / ".install-manifests"
    marketplaces = root / "marketplaces"
    if manifests.exists():
        for m in manifests.glob("*.json"):
            if "@" not in m.stem:
                continue
            _, market = m.stem.split("@", 1)
            if not (marketplaces / market).exists():
                m.unlink()
                print(f"  removed orphan manifest {m.name}")


def get_cowork_bases() -> list[Path]:
    bases = [
        Path.home() / "Library/Application Support/Claude/local-agent-mode-sessions",
        Path.home() / ".config/Claude/local-agent-mode-sessions",
    ]
    wsl_users = Path("/mnt/c/Users")
    if wsl_users.exists():
        for user_dir in wsl_users.iterdir():
            claude_dir = user_dir / "AppData/Roaming/Claude/local-agent-mode-sessions"
            if claude_dir.exists():
                bases.append(claude_dir)
    return [b for b in bases if b.exists()]


def clean_gui(bases: list[Path] | None = None) -> None:
    if bases is None:
        bases = get_cowork_bases()
    if not bases:
        return
    for base in bases:
        for manifest in base.rglob("rpm/manifest.json"):
            with open(manifest) as f:
                data = json.load(f)
            keep, drop = [], []
            for p in data.get("plugins", []):
                (drop if is_aops_plugin(p) else keep).append(p)
            if drop:
                for p in drop:
                    plugin_dir = manifest.parent / p.get("id", "")
                    if plugin_dir.exists() and p.get("id"):
                        shutil.rmtree(plugin_dir)
                        print(f"  removed Cowork {plugin_dir.relative_to(base)}")
                data["plugins"] = keep
                with open(manifest, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"  updated Cowork {manifest.relative_to(base)} ({len(drop)} entry(ies))")

        for rpm_dir in base.rglob("rpm"):
            if not rpm_dir.is_dir():
                continue
            for item in rpm_dir.iterdir():
                if item.is_dir() and item.name.startswith("plugin_"):
                    manifest_file = item / ".claude-plugin" / "plugin.json"
                    if manifest_file.exists():
                        pdata = json.loads(manifest_file.read_text(encoding="utf-8"))
                        if is_aops_plugin(pdata):
                            shutil.rmtree(item)
                            print(f"  removed orphan Cowork package {item.relative_to(base)}")

        for data_dir in base.rglob(".claude/plugins/data"):
            if not data_dir.is_dir():
                continue
            for child in data_dir.iterdir():
                if child.is_dir() and (
                    child.name.startswith("aops") or child.name.startswith("academicOps")
                ):
                    shutil.rmtree(child)
                    print(f"  removed Cowork session data {child.relative_to(base)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prune stale plugin state across Claude surfaces.")
    parser.add_argument(
        "--remove-marketplaces",
        nargs="*",
        default=[],
        help="Marketplace names to remove from known_marketplaces.json",
    )
    args = parser.parse_args()

    clean_cli()
    clean_gui()
    if args.remove_marketplaces:
        remove_marketplaces(Path.home() / ".claude/plugins", tuple(args.remove_marketplaces))
    print("✓ Plugin cache and Cowork packages pruned")
