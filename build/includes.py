"""Stage 2: resolve `@include` lines in shipped markdown files.

specs/ARCHITECTURE.md: "Resolve includes. Replace each `@include <path>` line
in a markdown file with the content of that file from `lib/`. Recursive."
"""

import re
from pathlib import Path

from build.errors import BuildError

_INCLUDE_RE = re.compile(r"^@include\s+(\S+)\s*$")


def resolve_includes(text: str, lib_dir: Path, origin: str) -> str:
    """Replace every `@include <path>` line in ``text`` with the contents of
    `lib/<path>`, recursively. ``origin`` names the shipped file being
    resolved, used only to make cycle/missing-target errors readable.

    A missing include target or an include cycle is a hard error — never a
    silent pass-through.
    """
    return _resolve(text, lib_dir, [origin])


def _resolve(text: str, lib_dir: Path, chain: list[str]) -> str:
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        match = _INCLUDE_RE.match(line)
        if not match:
            out.append(line)
            continue

        rel = match.group(1)
        if rel in chain:
            cycle = " -> ".join([*chain, rel])
            raise BuildError(f"@include cycle detected: {cycle}")

        target = lib_dir / rel
        if not target.is_file():
            raise BuildError(f"@include target not found: lib/{rel} (included from {chain[-1]})")

        target_text = target.read_text(encoding="utf-8")
        out.append(_resolve(target_text, lib_dir, [*chain, rel]))
    return "\n".join(out)
