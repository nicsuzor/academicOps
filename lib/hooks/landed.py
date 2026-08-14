#!/usr/bin/env python3
"""The completion line: one already-persisted daily-note line per finished unit.

## What this is for

Nic delegates something and then hears nothing until it is finished. When it
finishes he gets exactly one line, and that line is a *pointer to a record that
already exists* — not the record itself. Scrollback is not a record: by tomorrow
he will not remember the line was there. So the line goes into
``$ACA_DATA/daily/YYYYMMDD-daily.md`` first, and only then does anything speak.

## Why it renders from the graph instead of being written by the worker

Four independent records on this exact surface are cases of an agent reporting a
success it had not achieved (``obs_c07c32b0``, ``obs_1e941c3e``, ``mem-fe14d1e9``,
``lear_1edc63c5``). A completion line that a worker can produce by asserting it
finished is worthless, because a suppressed channel and a channel with nothing
to say look identical from the reader's side. So the line needs two independent
keys, and this module requires both:

1. **A marker in the task's own body** — ``LANDED: <what> (<where it landed>)``,
   or ``BLOCKED-ON-YOU: <what>``, or ``FAILED: <what>``. This supplies the
   *wording*, which is a judgement, not a truth claim.
2. **The graph's own status agreeing with that marker's outcome class.** This
   supplies the *truth*. A worker that writes ``LANDED:`` on a task the graph
   does not have in a landed status produces no line at all.

Neither key alone renders anything. That is the whole design.

## Why it is a view, not an append

Every line this module writes is re-derivable from the task files alone, so a
daily note that loses the section can have it rebuilt by running the sweep
again. That is what makes the daily note a *view* of the graph rather than a
second, divergent copy of it — and it is why a regeneration that clobbers the
section is a recoverable annoyance rather than a lost record.

## Safety properties, each of which is load-bearing

- **Surgical.** The note is read, one line is inserted or replaced, and the
  result is written back. Everything else is byte-identical.
- **Serialised.** The read-modify-write happens under an exclusive ``flock``
  held for the whole cycle, so two units finishing at once cannot lose each
  other's line. Concurrent whole-file writes are how the daily note has been
  corrupted before; this is the fix, not an edge case.
- **Atomic.** The new content lands via a same-directory temporary file and
  ``os.replace``, so a crash mid-write cannot leave a truncated daily note.
- **Idempotent on task id.** A line carrying ``[<id>]`` is replaced in place
  wherever it already sits in the note, so running twice yields one line, and a
  line a human already parked under another heading is updated rather than
  duplicated.
- **Never creates a daily note through the PKB ``create`` path**, whose type
  enum has no ``daily`` value and which has already misfiled six daily notes
  into ``brain/notes/``. If it has to create one it writes the canonical path
  with ``type: daily`` frontmatter directly.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

SECTION_HEADING = "## Landed today"

# The three outcomes, and the statuses that count as each. Nothing else renders.
#
# `review` and `merge_ready` count as landed deliberately, and this is the one
# genuine judgement call in the module. In this framework a worker's handback
# state *is* `review`: the work is delivered and what remains is an internal
# evaluator's pass, not more work by the delegate. Nic asked to hear when the
# thing he asked for is done, and it is done at handback. The task id on the line
# is what lets him follow the review if he wants to. Recorded here rather than
# buried so it can be reversed by editing one table.
LANDED_STATUSES = frozenset({"done", "review", "merge_ready"})
BLOCKED_STATUSES = frozenset({"blocked", "paused"})
FAILED_STATUSES = frozenset({"failed", "cancelled", "partial"})

OUTCOMES: dict[str, frozenset[str]] = {
    "LANDED": LANDED_STATUSES,
    "BLOCKED-ON-YOU": BLOCKED_STATUSES,
    "FAILED": FAILED_STATUSES,
}

# How each outcome renders. `landed` is the shape Nic dictated, verbatim:
#   - [x] <what> (<where it landed>) [<task id>]
# The other two keep the same one-line-in-the-same-place contract but do not
# claim a tick they have not earned. A capability that can only report success
# is one that hides its failures.
PREFIXES: dict[str, str] = {
    "LANDED": "- [x] ",
    "BLOCKED-ON-YOU": "- [ ] **blocked on you** — ",
    "FAILED": "- [ ] **failed** — ",
}

_MARKER_RE = re.compile(
    r"^(?P<kw>LANDED|BLOCKED-ON-YOU|FAILED)\s*:\s*(?P<text>\S.*?)\s*$",
)

# `pkb append` prefixes what it writes with `**<ts> UTC** — `, and a marker may
# also arrive as a list item. Both are stripped before the marker is matched, so
# the marker can be written through the sanctioned PKB append path.
_LIST_PREFIX_RE = re.compile(r"^\s*(?:[-*+]\s+|>\s*)*")
_BOLD_PREFIX_RE = re.compile(r"^\*\*[^*]*\*\*\s*(?:—|-|–|:)?\s*")

# A line this module rendered, identified by its trailing `[<id>]` and by
# starting like one of the shapes above. Deliberately loose about the middle so
# a line whose wording changed is still recognised as the same line.
_RENDERED_LINE_RE = re.compile(r"^\s*-\s*\[[ xX]\]\s.*\[(?P<id>[^\[\]\s]+)\]\s*$")


@dataclass(frozen=True)
class Rendered:
    task_id: str
    outcome: str
    line: str


@dataclass(frozen=True)
class Skipped:
    task_id: str
    reason: str


@dataclass(frozen=True)
class Report:
    note: Path
    written: tuple[Rendered, ...] = ()
    unchanged: tuple[Rendered, ...] = ()
    skipped: tuple[Skipped, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.written)


# --------------------------------------------------------------------------
# Reading the graph
# --------------------------------------------------------------------------


def read_frontmatter(text: str) -> dict[str, str]:
    """The top-level scalar keys of a leading YAML block, and nothing else.

    Hand-parsed on purpose: this module ships inside a plugin's ``hooks/``
    directory and runs on every tool batch, so it takes no dependency a hook
    environment might not have. Only flat ``key: value`` pairs are read, which
    is all any caller here needs (``id``, ``status``, ``title``, ``assignee``).
    Nested structures are skipped rather than guessed at.
    """
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() in ("---", "..."):
            break
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) > 1:
            value = value[1:-1]
        out[key] = value
    return out


def _strip_prefixes(line: str) -> str:
    stripped = _LIST_PREFIX_RE.sub("", line)
    return _BOLD_PREFIX_RE.sub("", stripped).lstrip()


def find_marker(body: str) -> tuple[str, str] | None:
    """The last outcome marker in a task body, as ``(keyword, text)``.

    Last rather than first: a task's body is appended to over its life, so the
    most recent marker is the current one. A task with no marker returns None
    and renders nothing in sweep mode — silence is correct there, because a
    marker is one of the two keys this module requires.
    """
    found: tuple[str, str] | None = None
    for raw in body.splitlines():
        candidate = _strip_prefixes(raw)
        match = _MARKER_RE.match(candidate)
        if match:
            found = (match.group("kw"), match.group("text"))
    return found


def task_files(aca_data: Path) -> list[Path]:
    tasks_dir = aca_data / "tasks"
    if not tasks_dir.is_dir():
        return []
    return [Path(e.path) for e in os.scandir(tasks_dir) if e.is_file() and e.name.endswith(".md")]


def resolve_task(aca_data: Path, task_id: str) -> Path | None:
    """The file whose frontmatter ``id`` is ``task_id``.

    Matched on the frontmatter rather than the filename, because a PKB task's
    filename is ``<id>-<slugified title>.md`` and the slug can change.
    """
    prefix = f"{task_id}-"
    candidates = [
        p for p in task_files(aca_data) if p.name == f"{task_id}.md" or p.name.startswith(prefix)
    ]
    for path in candidates:
        if read_frontmatter(path.read_text(encoding="utf-8")).get("id") == task_id:
            return path
    for path in task_files(aca_data):
        if read_frontmatter(path.read_text(encoding="utf-8")).get("id") == task_id:
            return path
    return None


def render_one(path: Path, *, require_marker: bool) -> Rendered | Skipped:
    """Turn one task file into its line, or into the reason there is no line.

    This is where the two keys meet. ``require_marker`` is the difference
    between the sweep (which needs a marker to know a unit was delegated and
    finished, and to get its wording) and an explicit ``--task`` call (where the
    caller has already named the unit, so a missing marker falls back to the
    task title rather than producing nothing).
    """
    text = path.read_text(encoding="utf-8")
    front = read_frontmatter(text)
    task_id = front.get("id") or path.stem
    status = (front.get("status") or "").strip().lower()

    marker = find_marker(text)
    if marker is None:
        if require_marker:
            return Skipped(task_id, "no outcome marker in the task body")
        for keyword, statuses in OUTCOMES.items():
            if status in statuses:
                title = front.get("title") or task_id
                return Rendered(task_id, keyword, _line(keyword, title, task_id))
        return Skipped(task_id, f"status {status!r} is not a rendered outcome")

    keyword, wording = marker
    statuses = OUTCOMES[keyword]
    if status not in statuses:
        # The refusal that makes worker self-report inadmissible: the task said
        # it landed and the graph disagrees, so nothing is written.
        return Skipped(
            task_id,
            f"marker claims {keyword} but the graph has status {status!r} "
            f"(expected one of {sorted(statuses)}) — not rendered",
        )
    return Rendered(task_id, keyword, _line(keyword, wording, task_id))


def _line(keyword: str, wording: str, task_id: str) -> str:
    wording = wording.strip()
    # An id the wording already carries is not repeated.
    suffix = f" [{task_id}]"
    if wording.endswith(f"[{task_id}]"):
        return f"{PREFIXES[keyword]}{wording}"
    return f"{PREFIXES[keyword]}{wording}{suffix}"


# --------------------------------------------------------------------------
# Writing the note
# --------------------------------------------------------------------------


def note_path(aca_data: Path, day: date) -> Path:
    return aca_data / "daily" / f"{day:%Y%m%d}-daily.md"


def _minimal_note(day: date) -> str:
    """A daily note this module is willing to create from nothing.

    ``type: daily`` is the canonical-path derivation key, and the PKB ``create``
    type enum has no ``daily`` value — creating a daily note through it files the
    note as ``type: note`` and six historical dailies sit in ``brain/notes/``
    from exactly that mistake. So this writes the canonical path directly with
    the right type, and writes nothing else: the template owns the note's
    content, this owns one section of it.
    """
    return (
        "---\n"
        f'title: "Daily Summary - {day:%Y-%m-%d}"\n'
        "type: daily\n"
        f"date: {day:%Y-%m-%d}\n"
        "---\n"
        "\n"
        f"# Daily Summary - {day:%Y-%m-%d}\n"
    )


def _lock_path(target: Path) -> Path:
    digest = hashlib.sha1(str(target.resolve()).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"aops-landed-{digest}.lock"


def _section_bounds(lines: list[str]) -> tuple[int, int] | None:
    """``(heading index, index one past the section's last content line)``."""
    start = None
    for i, line in enumerate(lines):
        if line.strip() == SECTION_HEADING:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return start, end


def apply_lines(text: str, rendered: list[Rendered]) -> tuple[str, list[Rendered], list[Rendered]]:
    """Insert or replace each line, and report which of them actually changed.

    Replacement is searched over the *whole note*, not just this module's own
    section, so a line a human already parked under another heading is corrected
    in place instead of being duplicated below the fold. That is the behaviour
    that makes running this twice safe.
    """
    lines = text.splitlines()
    written: list[Rendered] = []
    unchanged: list[Rendered] = []

    for item in rendered:
        existing = None
        for i, line in enumerate(lines):
            match = _RENDERED_LINE_RE.match(line)
            if match and match.group("id") == item.task_id:
                existing = i
                break
        if existing is not None:
            if lines[existing].rstrip() == item.line:
                unchanged.append(item)
            else:
                lines[existing] = item.line
                written.append(item)
            continue

        bounds = _section_bounds(lines)
        if bounds is None:
            if lines and lines[-1].strip():
                lines.append("")
            lines.extend([SECTION_HEADING, "", item.line])
        else:
            _, end = bounds
            lines.insert(end, item.line)
        written.append(item)

    out = "\n".join(lines)
    if text.endswith("\n") or not text:
        out += "\n"
    return out, written, unchanged


def _atomic_write(target: Path, content: str) -> None:
    tmp = target.with_name(f".{target.name}.aops-landed.tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def _reindex(aca_data: Path, target: Path) -> None:
    """Hand the changed file back to the PKB's own indexer, best effort.

    The write is a filesystem write because no PKB CLI command can do it —
    ``append`` stamps a ``**<ts> UTC** —`` prefix on what it writes, which
    destroys a markdown checkbox, and ``update`` touches frontmatter only. So the
    index is refreshed through the CLI afterwards instead. Failure here is not a
    failure of the write: the line is on disk either way, and the next reindex
    picks it up.
    """
    binary = os.environ.get("AOPS_PKB_BIN") or shutil.which("pkb")
    if not binary:
        return
    try:
        subprocess.run(
            [binary, "--pkb-root", str(aca_data), "add", str(target)],
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def write_lines(
    aca_data: Path,
    rendered: list[Rendered],
    *,
    day: date | None = None,
    create: bool = True,
    reindex: bool = True,
) -> Report:
    """The whole read-modify-write cycle, under one exclusive lock."""
    day = day or date.today()
    target = note_path(aca_data, day)
    if not rendered:
        return Report(note=target)

    lock = _lock_path(target)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            if target.exists():
                text = target.read_text(encoding="utf-8")
            elif create:
                target.parent.mkdir(parents=True, exist_ok=True)
                text = _minimal_note(day)
            else:
                return Report(
                    note=target,
                    skipped=tuple(Skipped(r.task_id, f"{target} does not exist") for r in rendered),
                )
            out, written, unchanged = apply_lines(text, rendered)
            if out != text:
                _atomic_write(target, out)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    if written and reindex:
        _reindex(aca_data, target)
    return Report(note=target, written=tuple(written), unchanged=tuple(unchanged))


# --------------------------------------------------------------------------
# The two entry points
# --------------------------------------------------------------------------


def render_tasks(
    aca_data: Path,
    task_ids: list[str],
    *,
    day: date | None = None,
    dry_run: bool = False,
    create: bool = True,
) -> Report:
    rendered: list[Rendered] = []
    skipped: list[Skipped] = []
    for task_id in task_ids:
        path = resolve_task(aca_data, task_id)
        if path is None:
            skipped.append(Skipped(task_id, "no task with that id in the graph"))
            continue
        outcome = render_one(path, require_marker=False)
        (rendered if isinstance(outcome, Rendered) else skipped).append(outcome)  # type: ignore[arg-type]
    if dry_run:
        return Report(
            note=note_path(aca_data, day or date.today()),
            written=tuple(rendered),
            skipped=tuple(skipped),
        )
    report = write_lines(aca_data, rendered, day=day, create=create)
    return Report(
        note=report.note,
        written=report.written,
        unchanged=report.unchanged,
        skipped=tuple(skipped) + report.skipped,
    )


def sweep(
    aca_data: Path,
    *,
    day: date | None = None,
    since: float | None = None,
    dry_run: bool = False,
    create: bool = True,
) -> Report:
    """Every task that carries a marker the graph agrees with, for one day.

    Bounded twice over so this is cheap enough to run on every tool batch: the
    ``mtime`` window keeps it to the files the day actually touched, and the
    marker requirement keeps it to units that were actually delegated. On a
    5,000-task graph the ``scandir`` is single-digit milliseconds and only the
    handful of files inside the window are opened.
    """
    day = day or date.today()
    if since is None:
        since = datetime.combine(day, datetime.min.time()).timestamp()
    rendered: list[Rendered] = []
    skipped: list[Skipped] = []
    for path in task_files(aca_data):
        try:
            if path.stat().st_mtime < since:
                continue
        except OSError:
            continue
        outcome = render_one(path, require_marker=True)
        if isinstance(outcome, Rendered):
            rendered.append(outcome)
        elif "no outcome marker" not in outcome.reason:
            skipped.append(outcome)
    rendered.sort(key=lambda r: r.task_id)
    if dry_run:
        return Report(
            note=note_path(aca_data, day), written=tuple(rendered), skipped=tuple(skipped)
        )
    report = write_lines(aca_data, rendered, day=day, create=create)
    return Report(
        note=report.note,
        written=report.written,
        unchanged=report.unchanged,
        skipped=tuple(skipped) + report.skipped,
    )


def resolve_aca_data(explicit: str | None = None) -> Path | None:
    for candidate in (explicit, os.environ.get("ACA_DATA"), "~/brain"):
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.is_dir():
            return path
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="landed",
        description="Render finished delegated units into today's daily note.",
    )
    parser.add_argument("--task", action="append", default=[], metavar="ID")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--aca-data", default=None)
    parser.add_argument("--day", default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-create", action="store_true")
    args = parser.parse_args(argv)

    if not args.task and not args.sweep:
        parser.error("give --task ID (repeatable) or --sweep")

    aca_data = resolve_aca_data(args.aca_data)
    if aca_data is None:
        print("landed: no ACA_DATA directory found", file=sys.stderr)
        return 2

    day = date.fromisoformat(args.day) if args.day else date.today()
    create = not args.no_create

    reports: list[Report] = []
    if args.task:
        reports.append(
            render_tasks(aca_data, args.task, day=day, dry_run=args.dry_run, create=create)
        )
    if args.sweep:
        reports.append(sweep(aca_data, day=day, dry_run=args.dry_run, create=create))

    for report in reports:
        for item in report.written:
            print(f"{'would write' if args.dry_run else 'wrote'} {report.note}: {item.line}")
        for item in report.unchanged:
            print(f"already present {report.note}: {item.line}")
        for miss in report.skipped:
            print(f"skipped {miss.task_id}: {miss.reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
