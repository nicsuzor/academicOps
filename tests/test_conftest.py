"""Tests for pytest fixtures in conftest.py.

These tests verify that the basic pytest fixtures are correctly defined
and return consistent paths for the writing repository structure.
"""

from pathlib import Path


def test_writing_root_fixture(writing_root: Path) -> None:
    """Test writing_root fixture returns valid Path to repository root.

    Args:
        writing_root: Fixture providing path to repository root

    Tests:
        - Fixture returns a Path object
        - Path exists on filesystem
        - Path is a directory
        - Path contains expected marker files (CLAUDE.md, README.md)
    """
    assert isinstance(writing_root, Path), "writing_root must be a Path object"
    assert writing_root.exists(), f"writing_root does not exist: {writing_root}"
    assert writing_root.is_dir(), f"writing_root is not a directory: {writing_root}"

    # Verify this is the actual writing repository root
    assert (
        writing_root / "CLAUDE.md"
    ).exists(), f"CLAUDE.md not found in writing_root: {writing_root}"
    assert (
        writing_root / "README.md"
    ).exists(), f"README.md not found in writing_root: {writing_root}"


def test_bots_dir_fixture(bots_dir: Path) -> None:
    """Test bots_dir fixture returns valid Path (backwards compat alias for AOPS root).

    Args:
        bots_dir: Fixture providing path to framework root (alias for writing_root)

    Tests:
        - Fixture returns a Path object
        - Path exists on filesystem
        - Path is a directory
        - Path contains expected files (CLAUDE.md, AXIOMS.md)
    """
    assert isinstance(bots_dir, Path), "bots_dir must be a Path object"
    assert bots_dir.exists(), f"bots_dir does not exist: {bots_dir}"
    assert bots_dir.is_dir(), f"bots_dir is not a directory: {bots_dir}"

    # Verify this is the framework root (bots_dir is now alias for aops_root)
    assert (
        bots_dir / "CLAUDE.md"
    ).exists(), f"CLAUDE.md not found in bots_dir: {bots_dir}"
    assert (
        bots_dir / "AXIOMS.md"
    ).exists(), f"AXIOMS.md not found in bots_dir: {bots_dir}"


def test_data_dir_fixture(data_dir: Path) -> None:
    """Test data_dir fixture returns valid Path to data/ directory.

    Args:
        data_dir: Fixture providing path to data/ directory

    Tests:
        - Fixture returns a Path object
        - Path exists on filesystem
        - Path is a directory
        - Path contains expected subdirectories (tasks/, sessions/, etc.)
    """
    assert isinstance(data_dir, Path), "data_dir must be a Path object"
    assert data_dir.exists(), f"data_dir does not exist: {data_dir}"
    assert data_dir.is_dir(), f"data_dir is not a directory: {data_dir}"

    # Verify this is the actual data directory with expected structure
    expected_subdirs = ["tasks", "sessions", "projects"]
    for subdir in expected_subdirs:
        subdir_path = data_dir / subdir
        assert subdir_path.exists(), f"Expected subdirectory not found: {subdir_path}"


def test_hooks_dir_fixture(hooks_dir: Path) -> None:
    """Test hooks_dir fixture returns valid Path to AOPS/hooks/ directory.

    Args:
        hooks_dir: Fixture providing path to AOPS/hooks/ directory

    Tests:
        - Fixture returns a Path object
        - Path exists on filesystem
        - Path is a directory
        - Path contains expected subdirectories (prompts/)
    """
    assert isinstance(hooks_dir, Path), "hooks_dir must be a Path object"
    assert hooks_dir.exists(), f"hooks_dir does not exist: {hooks_dir}"
    assert hooks_dir.is_dir(), f"hooks_dir is not a directory: {hooks_dir}"

    # Verify this is the actual hooks directory
    prompts_dir = hooks_dir / "prompts"
    assert prompts_dir.exists(), "prompts/ subdirectory not found in hooks_dir"


def test_fixture_consistency(
    writing_root: Path,
    bots_dir: Path,
    data_dir: Path,
    hooks_dir: Path,
) -> None:
    """Test all fixtures return consistent paths.

    Args:
        writing_root: Fixture providing AOPS framework root
        bots_dir: Fixture providing AOPS framework root (alias for writing_root)
        data_dir: Fixture providing ACA_DATA directory (separate from framework)
        hooks_dir: Fixture providing AOPS/hooks/ directory

    Tests:
        - bots_dir equals writing_root (both are AOPS root)
        - data_dir is independent (uses ACA_DATA)
        - hooks_dir is child of writing_root
        - All paths are absolute
        - All paths resolve correctly
    """
    # All paths should be absolute
    assert writing_root.is_absolute(), "writing_root must be absolute path"
    assert bots_dir.is_absolute(), "bots_dir must be absolute path"
    assert data_dir.is_absolute(), "data_dir must be absolute path"
    assert hooks_dir.is_absolute(), "hooks_dir must be absolute path"

    # Verify new structure relationships
    assert (
        bots_dir == writing_root
    ), f"bots_dir should equal writing_root (both are AOPS root): {bots_dir} != {writing_root}"

    # data_dir is now independent (uses ACA_DATA), not a child of writing_root
    # No parent-child assertion for data_dir

    assert (
        hooks_dir.parent == writing_root
    ), f"hooks_dir parent should be writing_root: {hooks_dir.parent} != {writing_root}"

    # Verify paths resolve correctly to new structure
    assert writing_root == bots_dir, "writing_root should equal bots_dir (alias)"
    assert (
        writing_root / "hooks" == hooks_dir
    ), "writing_root/hooks should equal hooks_dir"
