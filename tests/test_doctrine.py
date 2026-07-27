"""Doctrine fragments must reach the built artifacts that declare them.

`lib/doctrine/*.md` is shared agent instruction inlined at build time via
`@include doctrine/<name>.md`. Nothing else checks that a declared fragment
survives into `dist/`, that a fragment is used at all, or that the fragment
table in `lib/doctrine/README.md` still describes the tree it documents.
"""

import re
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCTRINE_DIR = PROJECT_ROOT / "lib" / "doctrine"
PLUGINS_ROOT = PROJECT_ROOT / "plugins"
DIST_ROOT = PROJECT_ROOT / "dist"
CLIENT_SUFFIXES = ("-claude", "-agy")

INCLUDE_RE = re.compile(r"^@include\s+doctrine/(\S+\.md)\s*$", re.MULTILINE)


def _marketplace_names() -> dict[str, str]:
    """Plugin source directory -> marketplace name, per build/marketplace.toml."""
    with open(PROJECT_ROOT / "build" / "marketplace.toml", "rb") as f:
        manifest = tomllib.load(f)
    return {p["directory"]: p["name"] for p in manifest["plugins"]}


def _fragments() -> list[str]:
    return sorted(p.name for p in DOCTRINE_DIR.glob("*.md") if p.name != "README.md")


def _references() -> list[tuple[str, Path, str]]:
    """Every (plugin directory, agent source file, fragment filename) declared."""
    found = []
    for agent_file in sorted(PLUGINS_ROOT.glob("*/agents/*.md")):
        plugin_dir = agent_file.relative_to(PLUGINS_ROOT).parts[0]
        for fragment in INCLUDE_RE.findall(agent_file.read_text()):
            found.append((plugin_dir, agent_file, fragment))
    return found


REFERENCES = _references()
FRAGMENTS = _fragments()


def test_doctrine_fragments_exist():
    assert FRAGMENTS, f"{DOCTRINE_DIR} contains no fragments"


def test_every_reference_resolves_to_a_real_fragment():
    dangling = [
        f"  {agent.relative_to(PROJECT_ROOT)} -> doctrine/{fragment}"
        for _, agent, fragment in REFERENCES
        if not (DOCTRINE_DIR / fragment).is_file()
    ]
    assert not dangling, "@include names a fragment that does not exist:\n" + "\n".join(dangling)


def test_no_fragment_is_orphaned():
    """A fragment nothing includes ships to nobody and is dead weight in lib/."""
    referenced = {fragment for _, _, fragment in REFERENCES}
    orphaned = sorted(set(FRAGMENTS) - referenced)
    assert not orphaned, (
        f"doctrine fragments referenced by no agent: {orphaned}. "
        "Include them somewhere or delete them."
    )


@pytest.mark.parametrize(
    ("plugin_dir", "agent_file", "fragment"),
    REFERENCES,
    ids=[f"{p}:{a.stem}:{f}" for p, a, f in REFERENCES],
)
def test_declared_fragment_ships_resolved_in_every_client_build(plugin_dir, agent_file, fragment):
    """Each fragment's body must appear in the built agent file, for both clients."""
    if not DIST_ROOT.exists():
        pytest.skip(f"{DIST_ROOT} does not exist — run 'make build'")

    body = (DOCTRINE_DIR / fragment).read_text().strip()
    marketplace_name = _marketplace_names()[plugin_dir]

    checked = 0
    for suffix in CLIENT_SUFFIXES:
        built = DIST_ROOT / f"{marketplace_name}{suffix}" / "agents" / agent_file.name
        if not built.is_file():
            continue
        checked += 1
        content = built.read_text()
        assert "@include" not in content, (
            f"{built.relative_to(PROJECT_ROOT)} shipped with an unresolved @include"
        )
        # Compare line by line: the build reflows blank lines around an include
        # boundary, so the fragment is not guaranteed to be one contiguous block.
        missing = [line for line in body.splitlines() if line.strip() and line not in content]
        assert not missing, (
            f"{built.relative_to(PROJECT_ROOT)} is missing content from doctrine/{fragment}. "
            f"First missing line: {missing[0]!r}"
        )

    assert checked, f"no built artifact found for {marketplace_name} carrying {agent_file.name}"


def test_readme_table_matches_the_tree():
    """lib/doctrine/README.md's 'Included by' column is a claim about the tree."""
    documented: dict[str, set[str]] = {}
    row_re = re.compile(r"^\|\s*`(\S+\.md)`\s*\|[^|]*\|([^|]*)\|\s*$", re.MULTILINE)
    for fragment, included_by in row_re.findall((DOCTRINE_DIR / "README.md").read_text()):
        documented[fragment] = {name.strip() for name in included_by.split(",") if name.strip()}

    actual: dict[str, set[str]] = {fragment: set() for fragment in FRAGMENTS}
    for _, agent_file, fragment in REFERENCES:
        actual.setdefault(fragment, set()).add(agent_file.stem)

    assert documented == actual, (
        "lib/doctrine/README.md's fragment table disagrees with the @include lines "
        f"in plugins/*/agents/.\nDocumented: {documented}\nActual:     {actual}"
    )
