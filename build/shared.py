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

`[[shared]]` is the only shape this stage accepts, and declaring nothing is
distinct from declaring something it cannot read. An absent file, or one whose
every line is a comment, declares nothing and injects nothing. Any other
unrecognised content — a stray table, a misspelled key, a `shared` that is not
an array of tables — fails the build by name. It cannot degrade to zero entries
quietly: `lib/` injection is the only permitted route for shared material, so a
declaration the build silently ignores ships a plugin missing the files its own
instructions tell it to read.
"""

import shutil
import tomllib
from pathlib import Path
from typing import Any

from build.errors import BuildError
from build.tree import ignore

_SHAPE = 'expected `[[shared]]` tables with `from` and `to` keys, e.g.\n    [[shared]]\n    from = "hooks"\n    to = "hooks"'

_ENTRY_KEYS = frozenset({"from", "to"})


def load_shared_entries(plugin_toml_path: Path) -> list[dict[str, str]]:
    if not plugin_toml_path.exists():
        return []

    try:
        data: dict[str, Any] = tomllib.loads(plugin_toml_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise BuildError(f"{plugin_toml_path}: malformed TOML: {exc}") from exc

    unknown = sorted(set(data) - {"shared"})
    if unknown:
        raise BuildError(
            f"{plugin_toml_path}: unrecognised top-level key(s) {unknown} — "
            f"{_SHAPE}\nDeclaring nothing means an absent or comment-only file, "
            f"never an unrecognised one."
        )

    entries = data.get("shared", [])
    if not isinstance(entries, list):
        raise BuildError(
            f"{plugin_toml_path}: `shared` must be an array of tables, got "
            f"{type(entries).__name__} — {_SHAPE}"
        )

    for entry in entries:
        if not isinstance(entry, dict):
            raise BuildError(
                f"{plugin_toml_path}: [[shared]] entry must be a table, got "
                f"{type(entry).__name__} ({entry!r}) — {_SHAPE}"
            )
        stray = sorted(set(entry) - _ENTRY_KEYS)
        if stray:
            raise BuildError(
                f"{plugin_toml_path}: [[shared]] entry has unrecognised key(s) {stray}: {entry} — "
                f"{_SHAPE}"
            )
        for key in ("from", "to"):
            if key not in entry:
                raise BuildError(f"{plugin_toml_path}: [[shared]] entry missing '{key}': {entry}")
            if not isinstance(entry[key], str):
                raise BuildError(
                    f"{plugin_toml_path}: [[shared]] {key} must be a string, got "
                    f"{type(entry[key]).__name__} ({entry[key]!r})"
                )
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
