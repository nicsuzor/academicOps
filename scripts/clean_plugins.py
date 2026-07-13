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

AOPS_PLUGIN_NAMES = {"aops-core", "aops-tools"}


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


def clean_gui() -> None:
    base = Path.home() / "Library/Application Support/Claude/local-agent-mode-sessions"
    if not base.exists():
        return
    for manifest in base.rglob("rpm/manifest.json"):
        data = json.load(open(manifest))
        keep, drop = [], []
        for p in data.get("plugins", []):
            (drop if p.get("name") in AOPS_PLUGIN_NAMES else keep).append(p)
        if not drop:
            continue
        for p in drop:
            plugin_dir = manifest.parent / p["id"]
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
                print(f"  removed GUI {plugin_dir.relative_to(base)}")
        data["plugins"] = keep
        json.dump(data, open(manifest, "w"), indent=2)
        print(f"  updated GUI {manifest.relative_to(base)} ({len(drop)} entry(ies))")


if __name__ == "__main__":
    clean_cli()
    clean_gui()
    print("✓ Plugin cache pruned")
