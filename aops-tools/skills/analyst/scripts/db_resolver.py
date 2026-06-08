"""
Database path resolver and cache validator.

This module resolves the canonical database path absolutely and asserts
that no confusable duplicate cache files exist within the project.
"""

import os
import subprocess
from pathlib import Path


def get_project_root() -> Path:
    """Find the project root directory using environment variables, git, or parent traversal."""
    # 1. Check if CLAUDE_PROJECT_DIR is set (standard framework env var)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir).resolve()

    # 2. Try git rev-parse
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(root).resolve()
    except Exception:
        pass

    # 3. Fallback: traverse upwards from cwd
    current = Path.cwd().resolve()
    for parent in [current] + list(current.parents):
        if (
            (parent / ".git").exists()
            or (parent / "dbt").exists()
            or (parent / "pyproject.toml").exists()
        ):
            return parent

    raise RuntimeError(
        "Could not determine project root. Ensure you are running within the project repository."
    )


def get_canonical_db_path(db_filename: str = "warehouse.db") -> Path:
    """Resolve the absolute canonical database path and assert that no confusable duplicates exist.

    Parameters
    ----------
    db_filename : str
        The filename of the database (default is "warehouse.db").

    Returns
    -------
    Path
        The absolute Path to the canonical database.

    Raises
    ------
    AssertionError
        If any duplicate db_filename files are found in the project.
    """
    project_root = get_project_root()
    canonical_path = (project_root / "data" / db_filename).resolve()

    # Find duplicate database files to assert that none are used by mistake
    confusable_files = []
    for path in project_root.rglob(db_filename):
        resolved = path.resolve()
        if resolved != canonical_path:
            # Skip common environment and build folders to avoid false positives
            if any(
                part.startswith(".")
                or part in ("venv", "node_modules", "dist", "output", "build", "_book", "_site")
                for part in resolved.parts
            ):
                continue
            confusable_files.append(resolved)

    if confusable_files:
        confusable_str = ", ".join(str(p) for p in confusable_files)
        msg = (
            f"ERROR: Confusable duplicate cache files found at: [{confusable_str}]. "
            f"Only the canonical database at {canonical_path} must be used to prevent stale cache addressing."
        )
        raise AssertionError(msg)

    # Ensure the parent directory exists
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    return canonical_path
