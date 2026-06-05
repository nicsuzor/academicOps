#!/usr/bin/env -S uv run python
"""One-shot migration: rotate flat $AOPS_SESSIONS/transcripts and summaries
into ``yyyy-mm/`` subfolders.

For every flat file directly under ``$AOPS_SESSIONS/transcripts/`` and
``$AOPS_SESSIONS/summaries/``, derive the rotation bucket from the leading
``YYYYMMDD`` token in the filename (which is the session start date by the
naming convention — see ``lib.session_naming``) and ``git mv`` the file into
``<dir>/YYYY-MM/``.

The script is idempotent — files already living under a ``YYYY-MM/`` subdir
are skipped. Files that don't carry a parseable date prefix are reported and
left in place. A single combined commit is created at the end (one per dir,
to keep summaries-only / transcripts-only migrations clean for review).

See PKB task aops-b975b185.

Usage:
    uv run python aops-core/scripts/migrate_transcripts_to_yyyy_mm.py
    uv run python aops-core/scripts/migrate_transcripts_to_yyyy_mm.py --dry-run
    uv run python aops-core/scripts/migrate_transcripts_to_yyyy_mm.py --no-commit
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.paths import get_sessions_repo, get_summaries_dir, get_transcripts_dir  # noqa: E402
from lib.transcript_paths import (  # noqa: E402
    extract_date_from_filename,
    is_rotated_dir,
    rotated_subdir,
)


def _git_mv(sessions_root: Path, src: Path, dst: Path, dry_run: bool) -> bool:
    """git-mv ``src`` to ``dst`` (creating parent dirs first).

    Falls back to a non-git rename if ``git mv`` fails because the file is
    untracked. Returns True on a real move; False if no-op or failed.

    If the destination already exists and is byte-identical to ``src``
    (a common case when the writer re-emitted the file mid-migration), the
    flat duplicate is removed via ``git rm`` so the rotated copy is kept
    as the single source of truth.
    """
    if dst.exists():
        try:
            same = src.read_bytes() == dst.read_bytes()
        except OSError:
            same = False
        if same:
            if dry_run:
                print(f"  - would dedupe (identical): {src.relative_to(sessions_root)}")
                return True
            rm = subprocess.run(
                ["git", "rm", "-f", str(src.relative_to(sessions_root))],
                cwd=str(sessions_root),
                capture_output=True,
                text=True,
            )
            if rm.returncode == 0:
                return True
            # Fall back to unlink if untracked.
            src.unlink(missing_ok=True)
            return True
        print(f"  ! skip (target differs; manual review): {src.relative_to(sessions_root)}")
        return False

    if dry_run:
        print(f"  + would mv: {src.relative_to(sessions_root)} -> {dst.relative_to(sessions_root)}")
        return True

    dst.parent.mkdir(parents=True, exist_ok=True)
    # Try git mv first — preserves history.
    result = subprocess.run(
        ["git", "mv", str(src.relative_to(sessions_root)), str(dst.relative_to(sessions_root))],
        cwd=str(sessions_root),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True

    # git mv may fail for untracked files; fall back to plain rename then stage.
    if "not under version control" in result.stderr or "did not match any" in result.stderr:
        src.rename(dst)
        subprocess.run(
            ["git", "add", str(dst.relative_to(sessions_root))],
            cwd=str(sessions_root),
            check=False,
        )
        return True

    print(f"  x git mv failed: {result.stderr.strip()}", file=sys.stderr)
    return False


def migrate_dir(sessions_root: Path, base_dir: Path, dry_run: bool) -> dict[str, int]:
    """Migrate flat files in ``base_dir`` into ``base_dir/YYYY-MM/`` subdirs.

    Returns a stats dict.
    """
    stats = {"moved": 0, "skipped_rotated": 0, "skipped_no_date": 0, "skipped_other": 0}
    if not base_dir.exists():
        print(f"  (dir does not exist: {base_dir})")
        return stats

    # Group by rotation bucket for readable logging.
    by_bucket: dict[str, list[Path]] = defaultdict(list)
    no_date: list[Path] = []

    for entry in sorted(base_dir.iterdir()):
        if entry.is_dir():
            if not is_rotated_dir(entry):
                stats["skipped_other"] += 1
            continue
        if not entry.is_file():
            continue
        dt = extract_date_from_filename(entry.name)
        if dt is None:
            no_date.append(entry)
            stats["skipped_no_date"] += 1
            continue
        by_bucket[rotated_subdir(dt)].append(entry)

    if no_date:
        print(f"  ! {len(no_date)} files without parseable date prefix (left in place):")
        for f in no_date[:10]:
            print(f"      {f.name}")
        if len(no_date) > 10:
            print(f"      ... and {len(no_date) - 10} more")

    for bucket, files in sorted(by_bucket.items()):
        print(f"  → {bucket}: {len(files)} files")
        for src in files:
            dst = base_dir / bucket / src.name
            if _git_mv(sessions_root, src, dst, dry_run):
                stats["moved"] += 1

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report what would move; no changes")
    parser.add_argument(
        "--no-commit", action="store_true", help="Stage moves but do not create a commit"
    )
    args = parser.parse_args()

    sessions_root = get_sessions_repo()
    if not (sessions_root / ".git").exists():
        print(f"Error: {sessions_root} is not a git repository", file=sys.stderr)
        return 1

    total_moved = 0
    for label, base in (("transcripts", get_transcripts_dir()), ("summaries", get_summaries_dir())):
        print(f"== {label}: {base} ==")
        stats = migrate_dir(sessions_root, base, args.dry_run)
        total_moved += stats["moved"]
        print(
            f"  summary: moved={stats['moved']} "
            f"no_date={stats['skipped_no_date']} "
            f"other_dirs={stats['skipped_other']}"
        )

    print(f"\nTotal files migrated: {total_moved}")

    if args.dry_run or args.no_commit or total_moved == 0:
        return 0

    # Single commit for both transcripts and summaries.
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=str(sessions_root), check=False
    )
    if diff.returncode == 0:
        print("Nothing staged to commit.")
        return 0

    commit_msg = "chore: rotate transcripts into yyyy-mm subfolders (aops-b975b185)"
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(sessions_root), check=True)
    print(f"Committed: {commit_msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
