"""
Database path resolver and cache validator.

This module resolves the canonical database path absolutely and asserts
that no confusable duplicate cache files exist within the project.
"""

import os
import subprocess
from pathlib import Path


def get_project_root() -> Path:
    """Find the project root directory using environment variables or git."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir).resolve()

    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.PIPE,
        ).strip()
        return Path(root).resolve()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"git rev-parse failed (exit {e.returncode}). "
            "Set CLAUDE_PROJECT_DIR or run within a git repository."
        ) from e
    except FileNotFoundError:
        raise RuntimeError(
            "git executable not found. Set CLAUDE_PROJECT_DIR or ensure git is installed."
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
