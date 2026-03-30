"""Test that build.py deploys all framework files via its excludelist.

Prevents regression where new framework files are added to aops-core/
but accidentally excluded from Gemini/Claude extension deploys.

The build uses an excludelist (EXCLUDED_FROM_COPY) — everything in
aops-core/ is deployed unless explicitly excluded. This test ensures
no .md files are silently caught by the excludelist without being
intentionally listed.
"""

from pathlib import Path

AOPS_CORE_DIR = Path(__file__).resolve().parent.parent / "aops-core"


def _get_excluded_from_copy() -> set[str]:
    """Parse build.py to extract the EXCLUDED_FROM_COPY set using AST."""
    import ast

    build_py = Path(__file__).resolve().parent.parent / "scripts" / "build.py"
    content = build_py.read_text()
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_aops_core":
            for sub_node in node.body:
                if isinstance(sub_node, ast.Assign):
                    for target in sub_node.targets:
                        if isinstance(target, ast.Name) and target.id == "EXCLUDED_FROM_COPY":
                            if isinstance(sub_node.value, ast.Set):
                                return {
                                    elt.value
                                    for elt in sub_node.value.elts
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                                }

    raise RuntimeError(
        "Could not find 'EXCLUDED_FROM_COPY' set in 'build_aops_core' function in build.py"
    )


def test_no_md_files_silently_excluded() -> None:
    """Every .md file in aops-core/ root is either deployed or explicitly excluded."""
    source_md_files = {f.name for f in AOPS_CORE_DIR.glob("*.md")}
    excluded = _get_excluded_from_copy()

    # Files that are in source AND in the excludelist — these are intentionally not deployed
    intentionally_excluded = source_md_files & excluded

    # This is fine — but if the set grows unexpectedly, we want to know
    assert intentionally_excluded == {"BUTLER.md", "GEMINI.md"}, (
        f"Unexpected .md files in EXCLUDED_FROM_COPY: {sorted(intentionally_excluded)}. "
        "If a new .md file should genuinely be excluded, update this assertion."
    )


def test_excludelist_has_no_phantom_entries() -> None:
    """Every .md entry in EXCLUDED_FROM_COPY must actually exist in aops-core/."""
    excluded = _get_excluded_from_copy()
    source_files = {f.name for f in AOPS_CORE_DIR.iterdir()}

    md_excluded = {item for item in excluded if item.endswith(".md")}
    phantom = md_excluded - source_files

    assert not phantom, (
        f"EXCLUDED_FROM_COPY references .md files that don't exist in aops-core/: {sorted(phantom)}. "
        "Remove stale entries from the excludelist."
    )
