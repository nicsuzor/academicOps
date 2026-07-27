"""Stage 3: render manifest/*.template.json.

specs/ARCHITECTURE.md: "Render manifests. Merge `manifest/*.template.json`
`__base__` with the client's section, and write to the client's expected
path." Writing to the client's expected path is client-specific and lives in
build/clients/ — this module only produces the merged dict.
"""

import json
from pathlib import Path
from typing import Any

_TEMPLATE_SUFFIX = ".template.json"


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
    """Merge a manifest/*.template.json's `__base__` with its `<client>` section."""
    template = json.loads(template_path.read_text(encoding="utf-8"))
    base = template.get("__base__", {})
    client_section = template.get(client, {})
    return merge_one_level(base, client_section)
