"""Stage 3: render manifest/*.template.json.

specs/ARCHITECTURE.md: "Render manifests. Merge a `manifest/*.template.json`'s
`clients.__base__` with its `clients.<client>` section, and write to the
client's expected path." Writing to the client's expected path is
client-specific and lives in build/clients/ — this module only produces the
merged dict.

Every template declares a `manifestVersion` and holds its `__base__` and
per-client sections under `clients`, leaving the top level for plugin
identity.
"""

import json
from pathlib import Path
from typing import Any

from build.errors import BuildError

_TEMPLATE_SUFFIX = ".template.json"
_BASE_KEY = "__base__"

# Manifest versions this builder knows how to read. An unrecognised version is
# a hard failure: rendering it under these rules would silently produce
# whatever the newer shape happens to leave at these keys.
_SUPPORTED_MANIFEST_VERSIONS = frozenset({"1.0"})


def template_stem(template_path: Path) -> str:
    name = template_path.name
    if not name.endswith(_TEMPLATE_SUFFIX):
        raise ValueError(
            f"not a manifest template (must end in {_TEMPLATE_SUFFIX}): {template_path}"
        )
    return name[: -len(_TEMPLATE_SUFFIX)]


def merge_one_level(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge ``override`` onto ``base``: a dict value merges one level
    deep (its own nested dicts are replaced wholesale, not merged further);
    scalars and lists replace outright."""
    result = dict(base)
    for key, value in override.items():
        base_value = result.get(key)
        if isinstance(value, dict) and isinstance(base_value, dict):
            result[key] = {**base_value, **value}
        else:
            result[key] = value
    return result


def render_template(template_path: Path, client: str) -> dict[str, Any]:
    """Merge a manifest/*.template.json's `clients.__base__` with its
    `clients.<client>` section."""
    template = json.loads(template_path.read_text(encoding="utf-8"))
    sections = _client_sections(template, template_path)
    base = sections.get(_BASE_KEY, {})
    client_section = sections.get(client)
    if client_section is None and client == "openclaw":
        client_section = sections.get("claude", {})
    elif client_section is None:
        client_section = {}
    return merge_one_level(base, client_section)


def _client_sections(template: dict[str, Any], template_path: Path) -> dict[str, Any]:
    """The template's mapping of `__base__` and client names to sections."""
    version = template.get("manifestVersion")

    # Without a version there is nothing to say which keys are section names.
    # Reading such a template's top level as sections is how the pre-versioned
    # shape worked, and doing so now would render a versioned template's
    # identity keys as if they were clients.
    if version is None:
        raise BuildError(
            f"{template_path}: no `manifestVersion`; every manifest template must "
            f"declare one of {sorted(_SUPPORTED_MANIFEST_VERSIONS)} and hold its "
            f"sections under `clients`"
        )

    if version not in _SUPPORTED_MANIFEST_VERSIONS:
        raise BuildError(
            f"{template_path}: unsupported manifestVersion {version!r} "
            f"(this builder reads {sorted(_SUPPORTED_MANIFEST_VERSIONS)})"
        )

    # Every section lives under `clients`. Its absence renders every client
    # empty, which reaches the client adapters as "this plugin has no hooks"
    # and ships a plugin whose hooks are silently missing — the one outcome
    # worth failing the build over.
    clients = template.get("clients")
    if not isinstance(clients, dict):
        raise BuildError(
            f"{template_path}: manifestVersion {version} requires a `clients` object "
            f"holding one section per client; found {type(clients).__name__}"
        )
    return clients
