"""Independent transcripts and insights for subagent (Task tool) sessions.

Background
----------
When a parent agent dispatches a ``Task`` subagent, Claude Code writes the
subagent's tool calls to its own ``agent-<id>.jsonl`` file under
``<session_dir>/<session_uuid>/subagents/``. Historically these folded into
the parent transcript only — there was no standalone ``-full.md`` per
subagent, no per-subagent insights JSON, and no link from the parent
transcript to the subagent's session ID.

This module fills that gap (PKB ``task-b483e037``):

* Subagent transcripts land in ``$AOPS_SESSIONS/subagent-transcripts/YYYY-MM/``
  — a separate top-level directory from primary session ``transcripts/`` —
  using the same yyyy-mm rotation contract as parent transcripts (see
  :mod:`lib.transcript_paths`).
* Per-subagent insights JSON land in ``$AOPS_SESSIONS/subagent-summaries/YYYY-MM/``.
* The parent transcript gets an additive footer section listing every
  subagent invocation with its type, child session ID, and a relative
  link to the child transcript markdown. This is purely additive — no
  changes to the existing transcript body — so existing parsers stay
  compatible.

The module deliberately avoids invasive surgery in
:mod:`lib.transcript_parser`. It re-uses the existing ``SessionProcessor``
machinery by toggling each subagent's entries' ``is_sidechain`` flag off so
the standard turn-grouping / markdown pipeline treats them as a normal
main thread. The flag flip is scoped to a copy of the entries.
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import lib.session_naming as session_naming
from lib.insights_generator import write_insights_file
from lib.paths import get_subagent_summaries_dir, get_subagent_transcripts_dir
from lib.reviewer_verdicts import _build_subagent_type_index
from lib.transcript_paths import ensure_rotated_dir

if TYPE_CHECKING:
    from lib.transcript_parser import Entry, SessionProcessor, SessionSummary


__all__ = [
    "SubagentArtifact",
    "iter_subagent_invocations",
    "write_subagent_transcripts",
    "render_parent_subagent_footer",
]


@dataclass
class SubagentArtifact:
    """One subagent invocation's on-disk products and metadata.

    ``transcript_path`` and ``insights_path`` are written under
    ``$AOPS_SESSIONS/subagent-transcripts/YYYY-MM/`` and
    ``$AOPS_SESSIONS/subagent-summaries/YYYY-MM/`` respectively.
    """

    invocation_id: str  # agent file id (e.g. "a14a1c4")
    subagent_type: str | None  # e.g. "rbg", "aops-core:pauli", or None if unresolved
    child_session_id: str  # short id used in the transcript filename (== invocation_id)
    parent_session_id: str  # parent's session id (8-char)
    first_timestamp: datetime | None
    transcript_path: Path | None = None
    insights_path: Path | None = None
    entry_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


def _first_timestamp(entries: list[Entry]) -> datetime | None:
    """Return the first non-None timestamp in ``entries``, or None."""
    for e in entries:
        if e.timestamp:
            return e.timestamp
    return None


def _subagent_slug(subagent_type: str | None, invocation_id: str) -> str:
    """Build a deterministic slug for the subagent transcript filename.

    Format: ``subagent-<type>`` when the type resolved, else
    ``subagent-<invocation-id>``. The invocation id is always present in
    the filename via session_naming's ``session_id`` slot, so this slug
    only needs to keep multiple subagents of the same type distinguishable
    visually.
    """
    if subagent_type:
        # Sanitize: lowercase, replace separators with hyphens.
        s = subagent_type.lower().replace("_", "-").replace(":", "-")
        # Strip anything that isn't alphanum or hyphen.
        s = "".join(c if (c.isalnum() or c == "-") else "-" for c in s)
        # Collapse runs of hyphens.
        while "--" in s:
            s = s.replace("--", "-")
        s = s.strip("-")
        if s:
            return f"subagent-{s}"
    return f"subagent-{invocation_id[:8]}"


def iter_subagent_invocations(
    main_entries: list[Entry],
    agent_entries: dict[str, list[Entry]] | None,
) -> list[dict[str, Any]]:
    """Enumerate subagent invocations discovered for a parent session.

    Each item: ``{"invocation_id", "subagent_type", "entries",
    "first_timestamp"}``. Order follows ``agent_entries`` insertion order
    (deterministic per filesystem listing of ``agent-*.jsonl``).

    ``subagent_type`` is resolved via :func:`reviewer_verdicts._build_subagent_type_index`
    when possible; it may be ``None`` for stray agent files that have no
    matching Task tool_use in the main thread.
    """
    if not agent_entries:
        return []

    type_index = _build_subagent_type_index(main_entries)
    out: list[dict[str, Any]] = []
    for invocation_id, entries in agent_entries.items():
        out.append(
            {
                "invocation_id": invocation_id,
                "subagent_type": type_index.get(invocation_id),
                "entries": entries,
                "first_timestamp": _first_timestamp(entries),
            }
        )
    return out


def _build_subagent_session_summary(
    parent_summary: SessionSummary,
    invocation_id: str,
    subagent_type: str | None,
    entries: list[Entry],
) -> SessionSummary:
    """Synthesize a SessionSummary for a subagent transcript.

    Inherits parent metadata (machine, hostname, provider, crew, repo,
    task_id) and tags ``slug`` / ``summary`` with the subagent type so
    downstream filename inference and frontmatter reads naturally.
    """
    # Lazy import to avoid circular ``transcript_parser`` ↔ this module
    # cycle: transcript.py imports this module, which would otherwise
    # need transcript_parser at module load.
    from lib.transcript_parser import SessionSummary  # noqa: PLC0415

    type_label = subagent_type or "unknown"
    return SessionSummary(
        uuid=invocation_id,
        summary=f"Subagent: {type_label}",
        artifact_type="subagent",
        created_at=(_first_timestamp(entries) or datetime.now(tz=UTC)).isoformat(),
        machine=parent_summary.machine,
        hostname=parent_summary.hostname,
        provider=parent_summary.provider,
        crew=parent_summary.crew,
        repo=parent_summary.repo,
        task_id=parent_summary.task_id,
        slug=_subagent_slug(subagent_type, invocation_id),
        surface=parent_summary.surface,
        client=parent_summary.client,
    )


def _entries_as_main_thread(entries: list[Entry]) -> list[Entry]:
    """Return a copy of ``entries`` with ``is_sidechain=False``.

    The standard ``SessionProcessor.format_session_as_markdown`` ignores
    entries flagged ``is_sidechain=True`` from the main turn grouping
    (it expects parent transcripts to render those via the sidechain
    summary path). For a *standalone* subagent transcript the subagent
    IS the main thread, so we flip the flag off on a shallow copy
    rather than mutating the originals (which still belong to the parent
    session's data model).
    """
    out: list[Entry] = []
    for e in entries:
        if e.is_sidechain:
            ec = copy.copy(e)
            ec.is_sidechain = False
            out.append(ec)
        else:
            out.append(e)
    return out


def _build_subagent_filename(
    invocation_id: str,
    subagent_type: str | None,
    timestamp: datetime,
    parent_session_id: str,
    parent_repo: str | None,
) -> str:
    """Build the subagent transcript base filename.

    Reuses :func:`session_naming.generate_base_name` so the file matches
    the project-wide ``YYYYMMDD-HHMM-<id>-<shortform>-<slug>`` convention
    — that's what :mod:`lib.transcript_paths` keys rotation off, what
    ``iter_rotated_files`` walks, and what /retro can grep for.

    ``shortform`` is set to ``subagent-of-<parent_short>`` so the parent
    linkage is grep-discoverable from the filename alone, even when the
    insights JSON / footer is unavailable.
    """
    slug = _subagent_slug(subagent_type, invocation_id)
    shortform = f"subagent-of-{parent_session_id[:8]}"
    return session_naming.generate_base_name(
        session_id=invocation_id[:8],
        timestamp=timestamp,
        slug=slug,
        repo=parent_repo or None,
        shortform=shortform,
        task_id=os.environ.get("AOPS_TASK_ID"),
    )


def _build_subagent_insights(
    parent_session_id: str,
    parent_repo: str | None,
    parent_provider: str | None,
    parent_task_id: str | None,
    invocation_id: str,
    subagent_type: str | None,
    entries: list[Entry],
    timestamp: datetime,
    transcript_path: Path,
    parent_surface: str | None = None,
    parent_client: str | None = None,
) -> dict[str, Any]:
    """Construct a minimal insights dict for one subagent invocation.

    Mirrors the schema used by parent insights, scoped down: no
    reflection (subagents don't emit framework reflections), but with
    enough provenance — parent session id, invocation id, subagent type,
    entry count, transcript path — that trend/sweep tooling can rank
    subagent quality independently.
    """
    return {
        "session_id": invocation_id,
        "date": timestamp.isoformat(),
        "project": parent_repo or "unknown",
        "summary": f"Subagent invocation ({subagent_type or 'unknown'})",
        "outcome": None,
        "accomplishments": [],
        "friction_points": [],
        "proposed_changes": [],
        "repo": parent_repo,
        "task_id": parent_task_id,
        "provider": parent_provider,
        # Launch surface/client inherited from the parent session — the .md
        # frontmatter already carries these (via SessionSummary), but the JSON
        # dropped them, leaving subagent summaries unclassifiable by surface.
        "surface": parent_surface,
        "client": parent_client,
        # Subagent-specific provenance.
        "artifact_type": "subagent",
        "parent_session_id": parent_session_id,
        "subagent_type": subagent_type,
        "invocation_id": invocation_id,
        "entry_count": len(entries),
        "transcript_path": str(transcript_path),
    }


def write_subagent_transcripts(
    parent_session_path: Path,
    parent_session_id: str,
    parent_summary: SessionSummary,
    main_entries: list[Entry],
    agent_entries: dict[str, list[Entry]] | None,
    processor: SessionProcessor,
    *,
    transcripts_root: Path | None = None,
    summaries_root: Path | None = None,
) -> list[SubagentArtifact]:
    """Emit per-subagent ``-full.md`` and insights JSON for one session.

    Args:
        parent_session_path: Path to the parent session JSONL (for
            ``source_file`` frontmatter on the subagent transcript).
        parent_session_id: 8-char parent session id used to anchor
            ``shortform=subagent-of-<parent>`` in the subagent filename.
        parent_summary: Parent ``SessionSummary``; metadata is inherited.
        main_entries: Parent's main-thread entries — used to resolve
            subagent_type via tool_use/tool_result pairing.
        agent_entries: Mapping of agent file id → entries (from
            ``SessionProcessor._load_agent_files``). Empty / None ⇒ no-op.
        processor: A ``SessionProcessor`` instance used to render markdown.
        transcripts_root: Override for the subagent transcripts root
            (defaults to ``$AOPS_SESSIONS/subagent-transcripts``). Test hook.
        summaries_root: Override for the subagent summaries root
            (defaults to ``$AOPS_SESSIONS/subagent-summaries``). Test hook.

    Returns:
        List of :class:`SubagentArtifact` — one per subagent invocation
        discovered. The caller (transcript.py) uses these to emit the
        parent footer linking to each child transcript.
    """
    if not agent_entries:
        return []

    transcripts_root = transcripts_root or get_subagent_transcripts_dir()
    summaries_root = summaries_root or get_subagent_summaries_dir()
    transcripts_root.mkdir(parents=True, exist_ok=True)
    summaries_root.mkdir(parents=True, exist_ok=True)

    invocations = iter_subagent_invocations(main_entries, agent_entries)
    artifacts: list[SubagentArtifact] = []

    for inv in invocations:
        invocation_id = inv["invocation_id"]
        subagent_type = inv["subagent_type"]
        entries = inv["entries"]
        ts = inv["first_timestamp"]

        if not entries:
            # Skip empty subagent files (rare; happens when a Task call is
            # cancelled before any agent output lands).
            continue

        if ts is None:
            # No timestamps in any entry — fall back to source file mtime
            # so the rotation bucket is at least deterministic.
            try:
                ts = datetime.fromtimestamp(parent_session_path.stat().st_mtime, tz=UTC)
            except OSError:
                ts = datetime.now(tz=UTC)

        # Build summary, render markdown, write files.
        sub_summary = _build_subagent_session_summary(
            parent_summary, invocation_id, subagent_type, entries
        )

        # Strip sidechain flag so the standard turn renderer treats this
        # as the main thread.
        sub_entries = _entries_as_main_thread(entries)

        # Filename + rotated output dir.
        filename_base = _build_subagent_filename(
            invocation_id=invocation_id,
            subagent_type=subagent_type,
            timestamp=ts,
            parent_session_id=parent_session_id,
            parent_repo=parent_summary.repo,
        )
        out_dir = ensure_rotated_dir(transcripts_root, ts)
        transcript_path = out_dir / f"{filename_base}-full.md"

        # Render via the existing formatter. Subagents don't have their
        # own agent_entries (no nested subagents in the current Claude
        # Code model), so we pass an empty dict.
        markdown = processor.format_session_as_markdown(
            sub_summary,
            sub_entries,
            agent_entries={},
            include_tool_results=True,
            variant="full",
            source_file=str(parent_session_path.resolve()),
            reflection_header=None,
        )

        # Inject a tiny YAML-level link to the parent transcript so a
        # reader landing here cold can navigate back. We append to the
        # frontmatter rather than restructuring the body — backwards-
        # compatible with existing parsers.
        markdown = _inject_parent_link_into_frontmatter(
            markdown,
            parent_session_id=parent_session_id,
            parent_session_path=parent_session_path,
            subagent_type=subagent_type,
            invocation_id=invocation_id,
        )

        transcript_path.write_text(markdown, encoding="utf-8")

        # Insights JSON.
        sum_out_dir = ensure_rotated_dir(summaries_root, ts)
        insights_path = sum_out_dir / f"{filename_base}.json"
        insights = _build_subagent_insights(
            parent_session_id=parent_session_id,
            parent_repo=parent_summary.repo,
            parent_provider=parent_summary.provider,
            parent_surface=parent_summary.surface,
            parent_client=parent_summary.client,
            parent_task_id=parent_summary.task_id,
            invocation_id=invocation_id,
            subagent_type=subagent_type,
            entries=entries,
            timestamp=ts,
            transcript_path=transcript_path,
        )
        try:
            write_insights_file(insights_path, insights, session_id=invocation_id)
        except Exception:  # noqa: BLE001
            # Insights are best-effort; the transcript itself is the
            # primary artefact and must not be invalidated by an
            # insights-write hiccup. Fall back to a direct write.
            insights_path.write_text(json.dumps(insights, indent=2), encoding="utf-8")

        artifacts.append(
            SubagentArtifact(
                invocation_id=invocation_id,
                subagent_type=subagent_type,
                child_session_id=invocation_id,
                parent_session_id=parent_session_id,
                first_timestamp=ts,
                transcript_path=transcript_path,
                insights_path=insights_path,
                entry_count=len(entries),
            )
        )

    return artifacts


def _inject_parent_link_into_frontmatter(
    markdown: str,
    *,
    parent_session_id: str,
    parent_session_path: Path,
    subagent_type: str | None,
    invocation_id: str,
) -> str:
    """Splice subagent provenance fields into the frontmatter block.

    The subagent transcript is generated through the standard
    ``format_session_as_markdown`` path, which produces a normal
    ``---\\nfrontmatter\\n---`` block. We splice subagent-specific
    keys before the closing ``---`` so consumers can detect, filter,
    and link without parsing the body.
    """
    parts = markdown.split("---\n", 2)
    # Expected layout: ["", "<frontmatter>\n", "<body>"]
    if len(parts) < 3 or parts[0] != "":
        # Frontmatter not present in the expected shape — fall back to
        # appending a small footer to body so we never lose the link.
        footer = (
            f"\n\n---\n\n_Subagent provenance: parent={parent_session_id}, "
            f"invocation_id={invocation_id}, "
            f"subagent_type={subagent_type or 'unknown'}_\n"
        )
        return markdown + footer

    inject = (
        f"artifact_type: subagent\n"
        f"parent_session_id: {parent_session_id}\n"
        f'parent_session_file: "{parent_session_path}"\n'
        f"invocation_id: {invocation_id}\n"
        f'subagent_type: "{subagent_type or "unknown"}"\n'
    )
    fm = parts[1].rstrip("\n") + "\n" + inject
    return f"---\n{fm}---\n{parts[2]}"


def render_parent_subagent_footer(
    artifacts: list[SubagentArtifact],
    parent_transcript_path: Path,
) -> str:
    """Build the additive footer to append to the parent transcript.

    Returns markdown that lists each subagent invocation with its type,
    child session id, and a path to the child transcript. The path is
    rendered relative to ``parent_transcript_path`` so the link works
    from wherever the parent is published.

    The footer is intentionally short, anchored on a stable heading
    (``## Subagent Transcripts``) so:

    * Existing parsers that read body content can ignore the new
      section (it's after all chronological content).
    * /retro can navigate parent → child by following the links.
    * Late re-runs of the transcript generator re-emit the same
      content (the heading is the dedupe key — see
      :func:`maybe_append_subagent_footer`).

    Returns an empty string if ``artifacts`` is empty so callers don't
    need to special-case the "no subagents" path.
    """
    if not artifacts:
        return ""

    lines = ["", "## Subagent Transcripts", ""]
    lines.append(
        "_The following Task subagent invocations have independent transcripts "
        "and insights. Each has its own session id; click through to inspect "
        "the subagent's tool calls and reflection in isolation._"
    )
    lines.append("")

    parent_dir = parent_transcript_path.parent
    for art in artifacts:
        type_label = art.subagent_type or "unknown"
        if art.transcript_path is None:
            continue
        try:
            rel = os.path.relpath(art.transcript_path, parent_dir).replace(os.sep, "/")
        except ValueError:
            # Different drives on Windows; fall back to absolute.
            rel = str(art.transcript_path).replace(os.sep, "/")
        ts_str = (
            art.first_timestamp.astimezone().strftime("%Y-%m-%d %H:%M")
            if art.first_timestamp
            else "unknown time"
        )
        lines.append(
            f"- **{type_label}** "
            f"(id: `{art.child_session_id}`, started {ts_str}, "
            f"{art.entry_count} entries) → "
            f"[{Path(rel).name}]({rel})"
        )

    lines.append("")
    return "\n".join(lines)


def maybe_append_subagent_footer(
    parent_transcript_path: Path,
    artifacts: list[SubagentArtifact],
) -> bool:
    """Append the subagent footer to the parent transcript, idempotently.

    Returns True if the footer was written (or refreshed), False if
    there were no artifacts.

    Idempotency: we anchor on the ``## Subagent Transcripts`` heading.
    If it's already present, we replace from that heading to EOF with
    the new footer; otherwise we append. This keeps the footer fresh
    when a session is re-processed after new subagents land.
    """
    if not artifacts or not parent_transcript_path.exists():
        return False

    footer = render_parent_subagent_footer(artifacts, parent_transcript_path)
    if not footer:
        return False

    existing = parent_transcript_path.read_text(encoding="utf-8")
    anchor = "\n## Subagent Transcripts\n"
    if anchor in existing:
        idx = existing.index(anchor)
        new_body = existing[:idx].rstrip() + "\n" + footer.lstrip("\n")
    else:
        new_body = existing.rstrip() + "\n" + footer

    parent_transcript_path.write_text(new_body, encoding="utf-8")
    return True
