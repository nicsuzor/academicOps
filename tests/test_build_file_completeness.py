"""Test that build.py includes all framework .md files in its copy list.

Prevents regression where new framework files are added to aops-core/
but not to the items_to_copy list in build.py, causing them to be
missing from Gemini/Claude extension deploys.

Root cause of hydrator context failure: GLOSSARY.md and SCRIPTS.md were
in aops-core/ but not in items_to_copy, so the Gemini extension never
received them.
"""

from pathlib import Path

AOPS_CORE_DIR = Path(__file__).resolve().parent.parent / "aops-core"

# Files that are intentionally NOT deployed (generated, dev-only, or platform-specific)
EXCLUDED_FILES = {
    "GEMINI.md",  # Added conditionally for gemini platform only (line 602 of build.py)
}


def _get_items_to_copy_from_build() -> set[str]:
    """Parse build.py to extract the items_to_copy list using AST for robustness."""
    import ast

    build_py = Path(__file__).resolve().parent.parent / "scripts" / "build.py"
    content = build_py.read_text()
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_aops_core":
            for sub_node in node.body:
                if isinstance(sub_node, ast.Assign):
                    for target in sub_node.targets:
                        if isinstance(target, ast.Name) and target.id == "items_to_copy":
                            if isinstance(sub_node.value, ast.List):
                                return {
                                    elt.value
                                    for elt in sub_node.value.elts
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                                }

    raise RuntimeError(
        "Could not find 'items_to_copy' list in 'build_aops_core' function in build.py"
    )


def test_all_framework_md_files_in_build_copy_list() -> None:
    """Every .md file in aops-core/ root must be in build.py's items_to_copy."""
    source_md_files = {f.name for f in AOPS_CORE_DIR.glob("*.md")}
    items_to_copy = _get_items_to_copy_from_build()

    # Files in source but not in build list (excluding intentional exclusions)
    missing = source_md_files - items_to_copy - EXCLUDED_FILES

    assert not missing, (
        f"Framework .md files in aops-core/ missing from build.py items_to_copy: {sorted(missing)}. "
        "These files will not be deployed to Gemini/Claude extensions. "
        "Add them to items_to_copy in scripts/build.py."
    )


def test_build_copy_list_has_no_phantom_files() -> None:
    """Every .md file in items_to_copy must actually exist in aops-core/."""
    items_to_copy = _get_items_to_copy_from_build()
    source_files = {f.name for f in AOPS_CORE_DIR.iterdir()}

    md_items = {item for item in items_to_copy if item.endswith(".md")}
    phantom = md_items - source_files

    assert not phantom, (
        f"build.py items_to_copy references files that don't exist in aops-core/: {sorted(phantom)}. "
        "Remove stale entries or create the missing files."
    )
