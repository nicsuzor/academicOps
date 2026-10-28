"""Per-client agent variants.

Most agents ship one `agents/<name>.md` for every client: the frontmatter is
expressible in both schemas, and the client adapters translate what differs.

An agent whose frontmatter or body cannot be expressed once for both ships as
`agents/<name>.<client>.md` instead — one file per client, each written natively
against that client's own vocabulary, with no translation step to get wrong.

`resolve_client_agents` runs first in each adapter's `_adapt_agents`, before it
globs `*.md`. It selects the variant for the client being built, renames it onto
`<name>.md`, and deletes every other client's. From that point the adapter sees
an ordinary agents tree and needs no further knowledge of the mechanism.

An agent may ship one file or one file per client, never both: `<name>.md`
alongside `<name>.<client>.md` fails the build rather than picking a winner.

Agent files may include shared content via `@<path>` import lines (e.g. `@../CORE.md`).
`resolve_agent_imports` inlines the referenced file's content in place of the import
line. `assert_no_unresolved_imports` verifies that no unresolved `@` import lines remain
in built agent files before packaging.
"""

import re
from pathlib import Path

from build.errors import BuildError

CLIENTS = ("claude", "agy", "openclaw")

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
_IMPORT_LINE_RE = re.compile(r"^\s*@([^\s]+)\s*$")


def _resolve_text_imports(text: str, source_file: Path, visited: set[Path] | None = None) -> str:
    if visited is None:
        visited = set()

    source_real = source_file.resolve()
    if source_real in visited:
        raise BuildError(
            f"{source_file}: circular import detected: '{source_file}' has already been imported"
        )
    visited.add(source_real)

    lines: list[str] = []
    in_code_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_fence = not in_code_fence
            lines.append(line)
            continue
        if in_code_fence:
            lines.append(line)
            continue

        m = _IMPORT_LINE_RE.match(line)
        if m:
            rel_path = m.group(1)
            target = (source_file.parent / rel_path).resolve()
            if not target.is_file():
                raise BuildError(
                    f"{source_file}: imported file '{rel_path}' does not exist (resolved to {target})"
                )
            target_content = target.read_text(encoding="utf-8")
            fm_match = _FRONTMATTER_RE.match(target_content)
            target_body = fm_match.group(2) if fm_match else target_content

            imported_content = _resolve_text_imports(
                target_body,
                target,
                visited.copy(),
            )
            lines.append(imported_content.strip("\n"))
        else:
            lines.append(line)
    return "\n".join(lines)


def resolve_agent_imports(agents_dir: Path) -> None:
    """Resolve `@<path>` import lines in agent markdown files, in place."""
    if not agents_dir.is_dir():
        return

    for md_file in sorted(agents_dir.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(content)
        if m:
            frontmatter_part = f"---\n{m.group(1)}\n---\n"
            body_part = m.group(2)
            resolved_body = _resolve_text_imports(body_part, md_file)
            md_file.write_text(frontmatter_part + resolved_body, encoding="utf-8")
        else:
            resolved_content = _resolve_text_imports(content, md_file)
            md_file.write_text(resolved_content, encoding="utf-8")


def assert_no_unresolved_imports(build_dir: Path) -> None:
    """Fail the build if any unresolved `@` import lines remain in built agent files."""
    agents_dir = build_dir / "agents"
    if not agents_dir.is_dir():
        return

    for md_file in sorted(agents_dir.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(content)
        body = m.group(2) if m else content
        in_code_fence = False
        for line_num, line in enumerate(body.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_code_fence = not in_code_fence
                continue
            if in_code_fence:
                continue
            if _IMPORT_LINE_RE.match(line):
                raise BuildError(
                    f"{md_file.relative_to(build_dir)}: unresolved import line '{line.strip()}' "
                    f"at line {line_num} in built agent file"
                )


def resolve_client_agents(agents_dir: Path, client: str) -> None:
    """Resolve `<name>.<client>.md` variants in `agents_dir`, in place."""
    if not agents_dir.is_dir():
        return

    if client not in CLIENTS:
        raise BuildError(
            f"resolve_client_agents: unknown client {client!r}, expected one of {list(CLIENTS)}"
        )

    for other in CLIENTS:
        for variant in sorted(agents_dir.rglob(f"*.{other}.md")):
            if other != client:
                variant.unlink()
                continue

            target = variant.with_name(f"{variant.name.removesuffix(f'.{other}.md')}.md")
            if target.exists():
                raise BuildError(
                    f"{variant}: both {target.name} and {variant.name} exist. "
                    f"An agent ships either one file for every client or one file "
                    f"per client, never both — delete whichever is stale."
                )
            variant.rename(target)
