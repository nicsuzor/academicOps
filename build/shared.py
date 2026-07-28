"""Stage 1: inject `lib/` content a plugin declares in manifest/plugin.toml.

## manifest/plugin.toml schema

Optional file. A plugin with no shared dependencies omits it entirely.

    [[shared]]
    from = "doctrine/pauli-core.md"   # path relative to lib/
    to = "skills/pauli/core.md"        # path relative to the plugin's build tree

Each `[[shared]]` entry is a table with two required string keys:

- `from` — path under `lib/`. May name a file (copied as one file) or a
  directory (copied recursively, merging into any existing destination).
- `to` — destination path relative to the plugin's build tree root (the
  staged, client-agnostic copy produced before per-client packaging).

Neither `from` nor `to` may contain a `..` path segment.
"""

import shutil
import tomllib
from pathlib import Path
from typing import Any

from build.errors import BuildError
from build.tree import ignore


def load_shared_entries(plugin_toml_path: Path) -> list[dict[str, str]]:
    if not plugin_toml_path.exists():
        return []

    data: dict[str, Any] = tomllib.loads(plugin_toml_path.read_text(encoding="utf-8"))
    entries = data.get("shared", [])
    for entry in entries:
        for key in ("from", "to"):
            if key not in entry:
                raise BuildError(f"{plugin_toml_path}: [[shared]] entry missing '{key}': {entry}")
            if ".." in Path(entry[key]).parts:
                raise BuildError(
                    f"{plugin_toml_path}: [[shared]] {key}={entry[key]!r} may not contain '..'"
                )
    return entries


def inject_shared(plugin_toml_path: Path, lib_dir: Path, stage_dir: Path) -> None:
    for entry in load_shared_entries(plugin_toml_path):
        src = lib_dir / entry["from"]
        dst = stage_dir / entry["to"]
        if not src.exists():
            raise BuildError(
                f"{plugin_toml_path}: shared source lib/{entry['from']} does not exist"
            )

        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore())
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
