#!/usr/bin/env python3
"""Prune stale plugin state across both Claude Code surfaces.

CLI surface (`~/.claude/plugins/`):
  - cache/*/*/<version>/ dirs not referenced by installed_plugins.json
  - .install-manifests/<plugin>@<marketplace>.json whose marketplace dir is gone

Desktop GUI surface (`~/Library/Application Support/Claude/
local-agent-mode-sessions/<account>/<surface>/rpm/`):
  - aops-* entries in rpm/manifest.json, and their unpacked plugin_<id>/ dirs.
    Use this when the GUI's "Uninstall plugin" button fails.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

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
    if toml_path.exists():
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        return {p["name"] for p in data["plugins"]}
    return set()


def is_aops_plugin(p: dict) -> bool:
    name = p.get("name", "")
    mp_name = p.get("marketplaceName", "")
    display = p.get("displayName", "")
    all_names = get_aops_plugin_names() | STALE_PLUGIN_NAMES
    if name in all_names or name.startswith("aops-") or name.startswith("aops_"):
        return True
    if mp_name in {"academicOps", "academicOps-cowork", "aops"}:
        return True
    if display.lower().startswith("aops") or display.lower().startswith("academicops"):
        return True
    return False


def clean_cli() -> None:
    root = Path.home() / ".claude/plugins"
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
    # Check WSL Windows path if running in WSL
    wsl_users = Path("/mnt/c/Users")
    if wsl_users.exists():
        for user_dir in wsl_users.iterdir():
            claude_dir = user_dir / "AppData/Roaming/Claude/local-agent-mode-sessions"
            if claude_dir.exists():
                bases.append(claude_dir)
    return [b for b in bases if b.exists()]


def clean_gui() -> None:
    bases = get_cowork_bases()
    if not bases:
        return
    for base in bases:
        # 1. Clean from rpm/manifest.json
        for manifest in base.rglob("rpm/manifest.json"):
            try:
                data = json.load(open(manifest))
            except Exception:
                continue
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
                json.dump(data, open(manifest, "w"), indent=2)
                print(f"  updated Cowork {manifest.relative_to(base)} ({len(drop)} entry(ies))")

        # 2. Clean orphaned plugin directories in rpm/
        for rpm_dir in base.rglob("rpm"):
            if not rpm_dir.is_dir():
                continue
            for item in rpm_dir.iterdir():
                if item.is_dir() and item.name.startswith("plugin_"):
                    manifest_file = item / ".claude-plugin" / "plugin.json"
                    if manifest_file.exists():
                        try:
                            pdata = json.loads(manifest_file.read_text(encoding="utf-8"))
                            if is_aops_plugin(pdata):
                                shutil.rmtree(item)
                                print(f"  removed orphan Cowork package {item.relative_to(base)}")
                        except Exception:
                            pass

        # 3. Clean session-level plugin data
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
    clean_cli()
    clean_gui()
    print("✓ Plugin cache and Cowork packages pruned")
