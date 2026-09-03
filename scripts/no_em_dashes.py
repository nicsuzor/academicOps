#!/usr/bin/env -S uv run python
"""Pre-commit hook: rewrite em-dashes to `--`.

Banning U+2014 is a character substitution, not a markdown-structure rule, so
it runs over the whole file — YAML frontmatter included. A markdownlint custom
rule cannot: rules receive frontmatter only as `params.frontMatterLines`, and
`onError` line numbers index the body, so a frontmatter hit has no addressable
position and cannot carry a fix.

Exclusions live in `.pre-commit-config.yaml`, not here.
"""

from __future__ import annotations

import sys
from pathlib import Path

EM_DASH = "—"
REPLACEMENT = "--"


def main(argv: list[str]) -> int:
    changed: list[str] = []
    for name in argv:
        path = Path(name)
        original = path.read_text(encoding="utf-8")
        if EM_DASH not in original:
            continue
        path.write_text(original.replace(EM_DASH, REPLACEMENT), encoding="utf-8")
        changed.append(f"{name}: {original.count(EM_DASH)} em-dash(es) rewritten")

    for line in changed:
        print(line)
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
