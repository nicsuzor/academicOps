"""PATH bootstrap — detect common tool locations and return PATH additions.

Centralises PATH detection logic for the Python layer (session_env_setup).
The shell equivalent lives in scripts/ensure-path.sh.

Both layers share the same conceptual list of required binaries and common
directories. The Python layer additionally tries ``brew --prefix`` as a
fallback on macOS (too slow for the shell layer which runs on every hook).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Binaries the framework needs on PATH.
REQUIRED_BINARIES: list[str] = ["uv", "gh"]

# Common binary directories — mirrors ensure-path.sh.
# Order matters: first match wins per binary.
COMMON_BIN_DIRS: list[Path] = [
    Path.home() / ".local" / "bin",  # pip --user
    Path.home() / ".cargo" / "bin",  # cargo installs (pkb)
    Path("/home/debian/.local/bin"),  # Debian containers
    Path("/usr/local/bin"),  # macOS standard / Intel Homebrew
    Path("/opt/homebrew/bin"),  # Apple Silicon Homebrew
    Path("/usr/bin"),  # Linux standard
]


def _get_brew_bin_dir() -> str | None:
    """Return Homebrew's bin directory via ``brew --prefix``, or None."""
    try:
        result = subprocess.run(
            ["brew", "--prefix"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip() + "/bin"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def detect_path_additions(current_path: str) -> str | None:
    """Return an updated PATH string with directories needed for missing binaries.

    For each binary in :data:`REQUIRED_BINARIES`:

    1. Check ``shutil.which`` against *current_path*.
    2. If missing, scan :data:`COMMON_BIN_DIRS` for an executable.
    3. If still missing and on macOS, try ``brew --prefix`` (cached per call).

    Returns the full updated PATH string, or ``None`` if no changes are needed.
    """
    path_segments = [s for s in current_path.split(os.pathsep) if s]
    normalized_path = os.pathsep.join(path_segments)
    dirs_to_add: list[str] = []
    brew_bin: str | None = None  # lazy, cached
    brew_checked = False

    for binary in REQUIRED_BINARIES:
        # Already available?
        if shutil.which(binary, path=normalized_path):
            continue

        # Also check against dirs we've already decided to add
        augmented = (
            os.pathsep.join([*dirs_to_add, normalized_path]) if dirs_to_add else normalized_path
        )
        if shutil.which(binary, path=augmented):
            continue

        found = False
        for bin_dir in COMMON_BIN_DIRS:
            if shutil.which(binary, path=str(bin_dir)):
                dir_str = str(bin_dir)
                if dir_str not in path_segments and dir_str not in dirs_to_add:
                    dirs_to_add.append(dir_str)
                found = True
                break

        # macOS fallback: try brew --prefix (once per call)
        if not found and sys.platform == "darwin":
            if not brew_checked:
                brew_bin = _get_brew_bin_dir()
                brew_checked = True
            if brew_bin and shutil.which(binary, path=brew_bin):
                if brew_bin not in path_segments and brew_bin not in dirs_to_add:
                    dirs_to_add.append(brew_bin)

    if not dirs_to_add:
        return None

    return os.pathsep.join([*dirs_to_add, *path_segments])
