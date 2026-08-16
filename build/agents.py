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
"""

from pathlib import Path

from build.errors import BuildError

CLIENTS = ("claude", "agy")


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
