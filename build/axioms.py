"""Parse `trigger: always_on` frontmatter out of a plugin's shipped axioms/*.md.

Shared by both client adapters — parsing frontmatter is not client-specific.
What gets emitted from the parsed result (axioms.jsonl vs rules/*.md) is
client-specific and stays in build/clients/.
"""

import re
from pathlib import Path
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def load_always_on_axioms(axioms_dir: Path) -> list[dict[str, Any]]:
    """Axioms carry simple `key: value` frontmatter (no nested YAML needed).
    Only `trigger: always_on` files are universal rules that get wired into a
    client's native rule mechanism — other axioms/*.md files are reference
    docs, shipped verbatim but not auto-merged into every session."""
    if not axioms_dir.exists():
        return []

    axioms: list[dict[str, Any]] = []
    for md_file in sorted(axioms_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(text)
        if not m:
            continue

        meta: dict[str, str] = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()

        if meta.get("trigger") != "always_on":
            continue

        axioms.append(
            {
                "slug": md_file.stem,
                "description": meta.get("description", ""),
                "body": m.group(2).strip(),
                "source_file": md_file.name,
            }
        )

    return axioms
