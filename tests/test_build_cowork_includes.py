"""Test that build.py's Cowork inclusion sets reference real paths in aops-core/.

Prevents silent regression where any of the COWORK_* allowlists reference
directories or files that have been renamed, removed, or moved. Without these
checks, the Cowork build would silently produce an incomplete plugin with no
error or warning.

Pattern mirrors tests/test_build_file_completeness.py which covers the analogous
excludelist for the Claude/Gemini builds.
"""

import ast
from pathlib import Path

AOPS_CORE_DIR = Path(__file__).resolve().parent.parent / "aops-core"
BUILD_PY = Path(__file__).resolve().parent.parent / "scripts" / "build.py"

_COWORK_SET_NAMES = {
    "COWORK_INCLUDE",
    "COWORK_MD_INCLUDE",
    "COWORK_SKILLS",
    "COWORK_AGENTS",
    "COWORK_COMMANDS",
}


def _get_cowork_sets() -> dict[str, set[str]]:
    """Parse build.py and extract every COWORK_* set defined in build_aops_cowork."""
    tree = ast.parse(BUILD_PY.read_text())
    found: dict[str, set[str]] = {}

    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "build_aops_cowork"):
            continue
        for sub_node in ast.walk(node):
            if not isinstance(sub_node, ast.Assign):
                continue
            for target in sub_node.targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id not in _COWORK_SET_NAMES:
                    continue
                if not isinstance(sub_node.value, ast.Set):
                    continue
                found[target.id] = {
                    elt.value
                    for elt in sub_node.value.elts
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                }

    missing_names = _COWORK_SET_NAMES - found.keys()
    if missing_names:
        raise RuntimeError(
            f"Could not find {sorted(missing_names)} set(s) in 'build_aops_cowork' in build.py"
        )
    return found


def test_cowork_include_dirs_exist() -> None:
    """Every entry in COWORK_INCLUDE must resolve to a real directory under aops-core/."""
    sets = _get_cowork_sets()
    missing = {name for name in sets["COWORK_INCLUDE"] if not (AOPS_CORE_DIR / name).is_dir()}
    assert not missing, (
        f"COWORK_INCLUDE references directories that don't exist in aops-core/: {sorted(missing)}. "
        "Update COWORK_INCLUDE in build_aops_cowork() to match actual directory names."
    )


def test_cowork_md_include_files_exist() -> None:
    """Every entry in COWORK_MD_INCLUDE must resolve to a real file under aops-core/."""
    sets = _get_cowork_sets()
    missing = {name for name in sets["COWORK_MD_INCLUDE"] if not (AOPS_CORE_DIR / name).is_file()}
    assert not missing, (
        f"COWORK_MD_INCLUDE references files that don't exist in aops-core/: {sorted(missing)}. "
        "Update COWORK_MD_INCLUDE in build_aops_cowork() to match actual file names."
    )


def test_cowork_skills_exist() -> None:
    """Every entry in COWORK_SKILLS must resolve to a real skill directory."""
    sets = _get_cowork_sets()
    skills_dir = AOPS_CORE_DIR / "skills"
    missing = {name for name in sets["COWORK_SKILLS"] if not (skills_dir / name).is_dir()}
    assert not missing, (
        f"COWORK_SKILLS references skills that don't exist in aops-core/skills/: {sorted(missing)}. "
        "Update COWORK_SKILLS in build_aops_cowork() to match actual skill names."
    )


def test_cowork_agents_exist() -> None:
    """Every entry in COWORK_AGENTS must resolve to a real agent file."""
    sets = _get_cowork_sets()
    agents_dir = AOPS_CORE_DIR / "agents"
    missing = {name for name in sets["COWORK_AGENTS"] if not (agents_dir / name).is_file()}
    assert not missing, (
        f"COWORK_AGENTS references agents that don't exist in aops-core/agents/: {sorted(missing)}. "
        "Update COWORK_AGENTS in build_aops_cowork() to match actual agent file names."
    )


def test_cowork_commands_exist() -> None:
    """Every entry in COWORK_COMMANDS must resolve to a real command file."""
    sets = _get_cowork_sets()
    commands_dir = AOPS_CORE_DIR / "commands"
    missing = {name for name in sets["COWORK_COMMANDS"] if not (commands_dir / name).is_file()}
    assert not missing, (
        f"COWORK_COMMANDS references commands that don't exist in aops-core/commands/: {sorted(missing)}. "
        "Update COWORK_COMMANDS in build_aops_cowork() to match actual command file names."
    )
