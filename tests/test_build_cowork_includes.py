"""Test that build.py's Cowork inclusion sets reference real paths in aops-core/.

Prevents silent regression where COWORK_INCLUDE or COWORK_MD_INCLUDE reference
directories or files that have been renamed, removed, or moved. Without this test,
the Cowork build would silently produce an incomplete plugin with no error or warning.

Pattern mirrors tests/test_build_file_completeness.py which covers the analogous
excludelist for the Claude/Gemini builds.
"""

import ast
from pathlib import Path

AOPS_CORE_DIR = Path(__file__).resolve().parent.parent / "aops-core"
BUILD_PY = Path(__file__).resolve().parent.parent / "scripts" / "build.py"


def _get_cowork_sets() -> tuple[set[str], set[str]]:
    """Parse build.py to extract COWORK_INCLUDE and COWORK_MD_INCLUDE via AST."""
    content = BUILD_PY.read_text()
    tree = ast.parse(content)

    cowork_include: set[str] | None = None
    cowork_md_include: set[str] | None = None

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_aops_cowork":
            for sub_node in ast.walk(node):
                if isinstance(sub_node, ast.Assign):
                    for target in sub_node.targets:
                        if not isinstance(target, ast.Name):
                            continue
                        if target.id == "COWORK_INCLUDE" and isinstance(sub_node.value, ast.Set):
                            cowork_include = {
                                elt.value
                                for elt in sub_node.value.elts
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                            }
                        elif target.id == "COWORK_MD_INCLUDE" and isinstance(
                            sub_node.value, ast.Set
                        ):
                            cowork_md_include = {
                                elt.value
                                for elt in sub_node.value.elts
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                            }

    if cowork_include is None:
        raise RuntimeError(
            "Could not find 'COWORK_INCLUDE' set in 'build_aops_cowork' function in build.py"
        )
    if cowork_md_include is None:
        raise RuntimeError(
            "Could not find 'COWORK_MD_INCLUDE' set in 'build_aops_cowork' function in build.py"
        )

    return cowork_include, cowork_md_include


def test_cowork_include_dirs_exist() -> None:
    """Every entry in COWORK_INCLUDE must resolve to a real directory under aops-core/."""
    cowork_include, _ = _get_cowork_sets()

    missing = {
        name for name in cowork_include if not (AOPS_CORE_DIR / name).is_dir()
    }

    assert not missing, (
        f"COWORK_INCLUDE references directories that don't exist in aops-core/: {sorted(missing)}. "
        "Update COWORK_INCLUDE in build_aops_cowork() to match actual directory names."
    )


def test_cowork_md_include_files_exist() -> None:
    """Every entry in COWORK_MD_INCLUDE must resolve to a real file under aops-core/."""
    _, cowork_md_include = _get_cowork_sets()

    missing = {
        name for name in cowork_md_include if not (AOPS_CORE_DIR / name).is_file()
    }

    assert not missing, (
        f"COWORK_MD_INCLUDE references files that don't exist in aops-core/: {sorted(missing)}. "
        "Update COWORK_MD_INCLUDE in build_aops_cowork() to match actual file names."
    )
