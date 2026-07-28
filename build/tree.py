"""Filesystem-tree hygiene for the build: what never ships, and what must be
executable when it does.

Every copy the build performs — plugin source into the stage tree, `lib/`
content injected on top of it, the stage tree into each client's build dir,
a claude build dir into the cowork channel — goes through the same exclusion
set defined here. One definition, applied at every copy site, then verified
once on the finished tree so a leak fails the build instead of shipping.

A shipped file carrying a `#!` line is a script somebody is expected to be
able to run. `shutil.copy2` reproduces the source's mode faithfully, so a
library file committed `0644` that also happens to be an entry point ships
unrunnable. This module makes the shebang the single declaration of intent:
carry one, and the build marks you executable.
"""

import os
import shutil
import stat
from pathlib import Path

from build.errors import BuildError

# Development artifacts. Never in a stage tree, a build dir, a tarball, or the
# cowork channel.
EXCLUDE_NAMES = frozenset(
    {
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".DS_Store",
        ".git",
    }
)

_EXCLUDE_SUFFIXES = (".pyc", ".pyo")


def ignore():
    """`shutil.copytree`'s `ignore=` argument, for every copytree the build does."""
    return shutil.ignore_patterns(*EXCLUDE_NAMES, *(f"*{suffix}" for suffix in _EXCLUDE_SUFFIXES))


def _is_excluded(name: str) -> bool:
    return name in EXCLUDE_NAMES or name.endswith(_EXCLUDE_SUFFIXES)


def copytree_filtered(src: Path, dst: Path, *, exclude_top: frozenset[str] | None = None) -> None:
    """Copy `src`'s contents into `dst`, dropping build artifacts at every
    depth and, at the top level only, the names in `exclude_top`."""
    exclude_top = exclude_top or frozenset()
    for item in sorted(src.iterdir()):
        if _is_excluded(item.name) or item.name in exclude_top:
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=ignore())
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def has_shebang(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(2) == b"#!"
    except OSError:
        return False


def mark_shebangs_executable(root: Path) -> list[Path]:
    """Give every regular file under `root` that starts with `#!` mode 0755.

    Returns the paths whose mode this actually changed, so a caller can report
    them. Idempotent: a file already executable is left alone.
    """
    changed: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() or not has_shebang(path):
            continue
        mode = stat.S_IMODE(path.stat().st_mode)
        wanted = mode | 0o755
        if mode != wanted:
            os.chmod(path, wanted)
            changed.append(path)
    return changed


def assert_no_build_artifacts(root: Path) -> None:
    """Fail the build if anything in `EXCLUDE_NAMES` survived into `root`.

    The exclusions above are the prevention; this is the proof. A new copy
    site that forgets `ignore()` fails here rather than shipping quietly.
    """
    leaked = sorted(str(p.relative_to(root)) for p in root.rglob("*") if _is_excluded(p.name))
    if leaked:
        raise BuildError(
            f"{root.name}: build artifacts leaked into the shipped tree: {', '.join(leaked)}"
        )
