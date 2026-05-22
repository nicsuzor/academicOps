"""Path helpers for date-rotated transcript / summary directories.

Session artefacts (transcripts, summaries, and any peer writer that shares the
same date-based naming convention) are rotated into ``yyyy-mm/`` subfolders
keyed off the **session start time (UTC)**. Late writes — e.g. archived or
re-processed sessions — sort into the original month, not the wall-clock
month at write time.

See PKB task aops-b975b185.

Design notes
------------
* The rotation key is **session start time** (the first event timestamp from
  the session, surfaced by callers). We convert to UTC before formatting so a
  session that starts at 23:30 local on the last day of the month doesn't get
  bucketed differently across machines.
* Helpers are generic over the parent directory (``transcripts/``,
  ``summaries/``, future ``subagent-transcripts/``, …) so a single rotation
  contract applies to every artefact that follows the
  ``YYYYMMDD-HHMM-<id>-…`` filename convention.
* Consumers walk recursively via :func:`iter_rotated_files` so both flat
  legacy layouts and rotated layouts are visible during transition.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

# Match a leading YYYYMMDD in a filename (used to derive the rotation bucket
# for files already on disk). The session-naming convention prefixes every
# artefact with this token, so it's the authoritative date for migration.
_FILENAME_DATE_RE = re.compile(r"^(\d{4})(\d{2})\d{2}[-_]")

# Match an already-rotated ``YYYY-MM`` subdir name.
_ROTATED_DIR_RE = re.compile(r"^\d{4}-\d{2}$")


def rotated_subdir(dt: datetime) -> str:
    """Return the ``YYYY-MM`` bucket for the given session start time.

    The input ``dt`` is normalised to UTC before formatting. A naive datetime
    is assumed to already represent UTC (callers should pass timezone-aware
    datetimes; the naive branch exists to keep this helper crash-free in
    test fixtures).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    dt_utc = dt.astimezone(UTC)
    return dt_utc.strftime("%Y-%m")


def rotated_path(base_dir: Path, dt: datetime, filename: str | None = None) -> Path:
    """Return the rotated directory (or full file path) under ``base_dir``.

    ``base_dir`` is the artefact root (e.g. ``$AOPS_SESSIONS/transcripts``).
    With ``filename`` omitted, returns ``base_dir / YYYY-MM/``. With a
    filename supplied, returns ``base_dir / YYYY-MM / filename``.
    """
    subdir = base_dir / rotated_subdir(dt)
    if filename is None:
        return subdir
    return subdir / filename


def ensure_rotated_dir(base_dir: Path, dt: datetime) -> Path:
    """Return the rotated subdir, creating it (and parents) on disk."""
    subdir = rotated_path(base_dir, dt)
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir


def extract_date_from_filename(name: str) -> datetime | None:
    """Parse the leading ``YYYYMMDD`` token from a session artefact filename.

    Returns a timezone-aware UTC datetime at midnight of the parsed day, or
    ``None`` if the filename does not start with a date token. Used by the
    migration script and by lookups that need to recover the rotation
    bucket from an existing filename.
    """
    m = _FILENAME_DATE_RE.match(name)
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2))
    # day is fixed-width digits already validated by the regex; parse via the
    # full match span so we keep one source of truth.
    day = int(name[6:8])
    try:
        return datetime(year, month, day, tzinfo=UTC)
    except ValueError:
        return None


def is_rotated_dir(path: Path) -> bool:
    """True if ``path`` is a ``YYYY-MM`` rotation subdir."""
    return path.is_dir() and bool(_ROTATED_DIR_RE.match(path.name))


def iter_rotated_files(base_dir: Path, pattern: str = "*") -> Iterator[Path]:
    """Iterate over files matching ``pattern`` under ``base_dir``.

    Walks both:
      * flat legacy files (``base_dir/<pattern>``), and
      * rotated files (``base_dir/YYYY-MM/<pattern>``).

    Yields nothing if ``base_dir`` does not exist. The recursion is one
    level deep — we don't blindly ``rglob`` because the artefact directories
    also contain unrelated peers (e.g. ``transcripts/polecats/`` legacy
    state, ``summaries/`` index files) that should not be conflated with
    session artefacts.
    """
    if not base_dir.exists():
        return
    # Flat layout (legacy + active-month before rotation lands).
    for p in base_dir.glob(pattern):
        if p.is_file():
            yield p
    # Rotated layout.
    for sub in base_dir.iterdir():
        if not is_rotated_dir(sub):
            continue
        for p in sub.glob(pattern):
            if p.is_file():
                yield p


def find_artifact(base_dir: Path, pattern: str) -> list[Path]:
    """Return all files matching ``pattern`` across flat + rotated layouts.

    Convenience wrapper around :func:`iter_rotated_files` for callers that
    want a list.
    """
    return list(iter_rotated_files(base_dir, pattern))
