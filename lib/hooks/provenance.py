"""Provenance check: reports which plugin build is running, and what else the
client has installed alongside it. Reports only — reads nothing it was not
given the location of, and never writes.

Both facts are read from files this runtime is standing in, located by walking
out from ``__file__``. Nothing here contains a host path, a home directory, or
a client install path: a shipped artifact may not carry one (specs/
ARCHITECTURE.md, Binding constraints), and a baked search path is exactly the
regression ``tests/test_shipped_hooks.py`` already pins for the ts hook. So the
plugin root is the hooks directory's parent, and the client's plugin registry
is found by walking up from there until a directory holding it appears. Neither
lookup is a plugin reading another plugin's files: the first is this plugin's
own manifest, and the second is the client's own installation state, the same
class of thing as the ``CLAUDE_ENV_FILE`` credentials.py appends to.

A hook must never end a session, so every function here degrades to a sentence
saying the fact is unavailable rather than raising.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Where each client adapter writes the plugin manifest, relative to the plugin
# root (build/clients/claude.py, build/clients/agy.py). Both are tried because
# one runtime ships to both clients.
_MANIFEST_PATHS = (Path(".claude-plugin") / "plugin.json", Path("plugin.json"))

# The client's own record of what it has installed. Used as the anchor for
# finding it as well as the source read from it: a directory containing this
# file IS the client's plugin directory, which is what makes the walk below
# self-validating rather than a guess about install layout.
_REGISTRY_NAME = "installed_plugins.json"


def _load_json(path: Path) -> dict[str, Any] | None:
    """``path`` parsed as a JSON object, or ``None`` — absent, unreadable, not
    JSON, JSON that is not an object, or anything else that stops it becoming
    one. A caller gets one answer for "no usable data here" instead of an open
    set of exceptions."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    # Not (OSError, ValueError): a deeply nested file raises RecursionError, a
    # huge one MemoryError, and neither is either. The caller drops its whole
    # handler on a raise — including the credential shim session_start sets up
    # after this report — so an unreadable file resolves to "no usable data
    # here" rather than costing unrelated work. KeyboardInterrupt and
    # SystemExit are BaseException and still get through.
    except Exception:  # noqa: BLE001 - a report may not cost the caller its handler
        return None
    return data if isinstance(data, dict) else None


def _manifest(hooks_dir: Path) -> dict[str, Any] | None:
    """This plugin's own rendered manifest, whichever client packaged it."""
    root = Path(hooks_dir).resolve().parent
    for relative in _MANIFEST_PATHS:
        data = _load_json(root / relative)
        if data is not None:
            return data
    return None


def _registry(hooks_dir: Path) -> dict[str, Any] | None:
    """The client's installed-plugin registry, found by walking out from here.

    Returns ``None`` when no ancestor holds one — an agy install, a source
    checkout, or a client that keeps no such file. That is the unconfigured
    case, not a fault: reporting nothing beats reporting a roster inferred from
    a directory layout no client promised.
    """
    for ancestor in Path(hooks_dir).resolve().parents:
        registry = ancestor / _REGISTRY_NAME
        if registry.is_file():
            return _load_json(registry)
    return None


def plugin(hooks_dir: Path) -> str:
    """One line naming the plugin build this hook is running out of."""
    manifest = _manifest(hooks_dir)
    if manifest is None:
        return "plugin: build manifest not readable"
    version = manifest.get("version")
    name = manifest.get("name")
    if not isinstance(version, str) or not version:
        return "plugin: build manifest carries no version"
    return f"plugin: {name} {version}" if isinstance(name, str) and name else f"plugin: {version}"


def installed(hooks_dir: Path) -> str:
    """One line listing the plugins the client records as installed.

    Names only. A sibling plugin's own version would have to come out of that
    plugin's manifest, which this plugin may not read (specs/ARCHITECTURE.md,
    Loose coupling); the client's registry names are not that.
    """
    registry = _registry(hooks_dir)
    if registry is None:
        return "plugins installed: no client registry beside this build"
    entries = registry.get("plugins")
    if not isinstance(entries, dict):
        return "plugins installed: client registry not in the expected shape"
    # Registry keys are "<name>@<marketplace>". The marketplace is uniform
    # across a real install and buys nothing on a one-line report.
    names = sorted({str(key).split("@", 1)[0] for key in entries})
    if not names:
        return "plugins installed: none recorded"
    return "plugins installed: " + ", ".join(names)
