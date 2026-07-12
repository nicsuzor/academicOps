"""Independent transcripts and insights for subagent (Task tool) sessions.

Background
----------
When a parent agent dispatches a ``Task`` subagent, Claude Code writes the
subagent's tool calls to its own ``agent-<id>.jsonl`` file under
``<session_dir>/<session_uuid>/subagents/``, alongside a sibling
``agent-<id>.meta.json`` sidecar carrying its identity/provenance
(``agentType``, ``description``, ``name``, ``parentAgentId``, ``spawnDepth``,
``teamName``, ``color``, ``model``, ``permissionMode``, ``taskKind``,
``toolUseId``) — written directly by the harness at spawn time.

This module (PKB ``task-b483e037``) emits, per subagent invocation:

* An independent ``-full.md`` transcript in
  ``$AOPS_SESSIONS/subagent-transcripts/YYYY-MM/`` — a separate top-level
  directory from primary session ``transcripts/`` — using the same yyyy-mm
  rotation contract as parent transcripts (see :mod:`lib.transcript_paths`).
* An insights JSON in ``$AOPS_SESSIONS/subagent-summaries/YYYY-MM/``.
* An additive footer section on the parent transcript listing every
  subagent invocation with its type, child session ID, and a relative
  link to the child transcript markdown. This is purely additive — no
  changes to the existing transcript body — so existing parsers stay
  compatible.

The ``agent-<id>.meta.json`` sidecar is the sole, required source of
subagent identity for the transcript/insights emitted here — this module
does not reconstruct it by parsing Task/Agent tool_use blocks in the main
thread (that approach cannot see nested subagent-of-subagent spawns or
background "teammate" Agent calls, and silently mis-resolves once it's
wrong). ``_build_subagent_type_index`` retains that tool_use-pairing
approach, but only for a separate, unrelated caller
(``SessionProcessor._aggregate_session_usage``'s best-effort ``by_agent``
cost-dashboard remap) — it is not used anywhere in this module's own
subagent-identity resolution.

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
from lib.transcript_paths import ensure_rotated_dir

if TYPE_CHECKING:
    from lib.transcript_parser import Entry, ParsedSession, SessionProcessor


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
    subagent_type: str  # meta.json's agentType, e.g. "rbg", "aops-pkb:pauli"
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


def _subagent_slug(subagent_type: str, invocation_id: str) -> str:
    """Build a deterministic slug for the subagent transcript filename.

    Format: ``subagent-<type>``. The invocation id is always present in
    the filename via session_naming's ``session_id`` slot, so this slug
    only needs to keep multiple subagents of the same type distinguishable
    visually.
    """
    # Sanitize: lowercase, replace separators with hyphens.
    s = subagent_type.lower().replace("_", "-").replace(":", "-")
    # Strip anything that isn't alphanum or hyphen.
    s = "".join(c if (c.isalnum() or c == "-") else "-" for c in s)
    # Collapse runs of hyphens.
    while "--" in s:
        s = s.replace("--", "-")
    s = s.strip("-")
    return f"subagent-{s}"


def _build_subagent_type_index(main_entries: list[Entry]) -> dict[str, str]:
    """Map agent file id (the file-stem after ``agent-``) to its subagent_type.

    Walks main session entries pairing Task/Agent tool_use blocks with their
    tool_result. The result's ``tool_use_result.agentId``/``agent_id`` is the
    file id; the tool_use's ``input.subagent_type``/``agent_type`` is the
    human-readable type (e.g. ``rbg``, ``aops-pkb:pauli``). This reads
    structured tool-call metadata only — it performs no parsing of model
    prose.

    Used solely by :func:`SessionProcessor._aggregate_session_usage` to
    remap ``by_agent`` token-cost UUIDs to human-readable names for the
    dashboard cost breakdown — a best-effort supplementary label, not
    subagent identity (that comes from ``agent-<id>.meta.json`` via
    :func:`_load_agent_meta`/:func:`iter_subagent_invocations`). Unresolved
    UUIDs are preserved verbatim by the caller rather than failing the
    whole token_metrics aggregation.
    """
    type_by_tool_id: dict[str, str] = {}
    for entry in main_entries:
        if entry.type != "assistant" or not entry.message:
            continue
        content = entry.message.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use":
                continue
            if block.get("name") not in ("Task", "Agent"):
                continue
            tool_id = block.get("id")
            if not tool_id:
                continue
            tool_input = block.get("input") or {}
            subagent_type = tool_input.get("subagent_type") or tool_input.get("agent_type")
            if subagent_type:
                type_by_tool_id[tool_id] = subagent_type

    index: dict[str, str] = {}
    for entry in main_entries:
        if entry.type != "user":
            continue
        message = entry.message or {}
        content = message.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tool_id = block.get("tool_use_id")
            if not tool_id or tool_id not in type_by_tool_id:
                continue
            result = entry.tool_use_result
            agent_file_id = None
            if isinstance(result, dict):
                agent_file_id = result.get("agentId") or result.get("agent_id")
            if agent_file_id:
                index[agent_file_id] = type_by_tool_id[tool_id]
    return index


def _load_agent_meta(parent_session_path: Path, invocation_id: str) -> dict[str, Any]:
    """Load the ``agent-<id>.meta.json`` sidecar the harness writes next to
    each ``agent-<id>.jsonl`` file — the required, authoritative source of
    subagent identity/provenance (``agentType``, ``description``, ``name``,
    ``parentAgentId``, ``spawnDepth``, ``teamName``, ``color``, ``model``,
    ``permissionMode``, ``taskKind``, ``toolUseId``).

    Searches the same two locations subagent jsonl files live in (legacy
    flat layout and the ``<session_uuid>/subagents/`` layout). Raises if no
    sidecar is found or it fails to parse — the sidecar is always written
    by the harness at spawn time, so a missing one is a real defect to
    surface, not a degraded mode to paper over.
    """
    session_dir = parent_session_path.parent
    main_session_uuid = parent_session_path.stem
    for candidate in (
        session_dir / f"agent-{invocation_id}.meta.json",
        session_dir / main_session_uuid / "subagents" / f"agent-{invocation_id}.meta.json",
    ):
        if candidate.exists():
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"{candidate} did not contain a JSON object")
            return data
    raise FileNotFoundError(
        f"agent-{invocation_id}.meta.json not found next to {parent_session_path}"
    )


def iter_subagent_invocations(
    agent_entries: dict[str, list[Entry]] | None,
    parent_session_path: Path,
) -> list[dict[str, Any]]:
    """Enumerate subagent invocations discovered for a parent session.

    Each item: ``{"invocation_id", "subagent_type", "entries",
    "first_timestamp", "meta"}``. Order follows ``agent_entries`` insertion
    order (deterministic per filesystem listing of ``agent-*.jsonl``).

    ``subagent_type`` is the ``agent-<id>.meta.json`` sidecar's
    ``agentType`` (see :func:`_load_agent_meta`); ``meta`` carries the full
    parsed sidecar so callers can pull ``description``, ``name``,
    ``parentAgentId``, ``spawnDepth``, etc.
    """
    if not agent_entries:
        return []

    out: list[dict[str, Any]] = []
    for invocation_id, entries in agent_entries.items():
        meta = _load_agent_meta(parent_session_path, invocation_id)
        out.append(
            {
                "invocation_id": invocation_id,
                "subagent_type": meta["agentType"],
                "entries": entries,
                "first_timestamp": _first_timestamp(entries),
                "meta": meta,
            }
        )
    return out


def _build_subagent_session_summary(
    parent_summary: ParsedSession,
    invocation_id: str,
    subagent_type: str,
    entries: list[Entry],
    meta: dict[str, Any],
) -> ParsedSession:
    """Synthesize a ParsedSession for a subagent transcript.

    Inherits parent metadata (machine, hostname, provider, crew, repo,
    task_id) and tags ``slug`` / ``summary`` with the subagent type so
    downstream filename inference and frontmatter reads naturally. When the
    ``agent-<id>.meta.json`` sidecar carries a ``description`` (the
    commissioning agent's own one-line task description), fold it into the
    title.
    """
    # Lazy import to avoid circular ``transcript_parser`` ↔ this module
    # cycle: transcript.py imports this module, which would otherwise
    # need transcript_parser at module load.
    from lib.transcript_parser import ParsedSession  # noqa: PLC0415

    description = meta.get("description")
    summary = f"Subagent: {subagent_type}"
    if description:
        summary = f"{summary} — {description}"
    return ParsedSession(
        uuid=invocation_id,
        summary=summary,
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
    subagent_type: str,
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
    subagent_type: str,
    entries: list[Entry],
    timestamp: datetime,
    transcript_path: Path,
    meta: dict[str, Any],
    parent_surface: str | None = None,
    parent_client: str | None = None,
) -> dict[str, Any]:
    """Construct a minimal insights dict for one subagent invocation.

    Mirrors the schema used by parent insights, scoped down: no
    reflection (subagents don't emit framework reflections), but with
    enough provenance — parent session id, invocation id, subagent type,
    entry count, transcript path — that trend/sweep tooling can rank
    subagent quality independently. ``meta`` (the ``agent-<id>.meta.json``
    sidecar) contributes the commissioning ``description``, custom
    ``name``, true ``parentAgentId`` (may be another subagent for nested
    spawns, not just the top session), ``spawnDepth``, ``teamName``,
    ``model``, ``permissionMode``, ``taskKind``.
    """
    insights = {
        "session_id": invocation_id,
        "date": timestamp.isoformat(),
        "project": parent_repo or "unknown",
        "summary": f"Subagent invocation ({subagent_type})",
        "outcome": None,
        "accomplishments": [],
        "friction_points": [],
        "proposed_changes": [],
        "repo": parent_repo,
        "task_id": parent_task_id,
        "provider": parent_provider,
        # Launch surface/client inherited from the parent session — the .md
        # frontmatter already carries these (via ParsedSession), but the JSON
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
    if meta.get("description"):
        insights["agent_description"] = meta["description"]
    if meta.get("name"):
        insights["agent_name"] = meta["name"]
    if meta.get("parentAgentId"):
        insights["parent_agent_id"] = meta["parentAgentId"]
    if meta.get("spawnDepth") is not None:
        insights["spawn_depth"] = meta["spawnDepth"]
    if meta.get("teamName"):
        insights["team_name"] = meta["teamName"]
    if meta.get("model"):
        insights["agent_model"] = meta["model"]
    if meta.get("permissionMode"):
        insights["agent_permission_mode"] = meta["permissionMode"]
    if meta.get("taskKind"):
        insights["task_kind"] = meta["taskKind"]
    return insights


def write_subagent_transcripts(
    parent_session_path: Path,
    parent_session_id: str,
    parent_summary: ParsedSession,
    agent_entries: dict[str, list[Entry]] | None,
    processor: SessionProcessor,
    *,
    transcripts_root: Path | None = None,
    summaries_root: Path | None = None,
) -> list[SubagentArtifact]:
    """Emit per-subagent ``-full.md`` and insights JSON for one session.

    Args:
        parent_session_path: Path to the parent session JSONL (for
            ``source_file`` frontmatter on the subagent transcript, and to
            locate each subagent's ``agent-<id>.meta.json`` sidecar).
        parent_session_id: 8-char parent session id used to anchor
            ``shortform=subagent-of-<parent>`` in the subagent filename.
        parent_summary: Parent ``ParsedSession``; metadata is inherited.
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

    invocations = iter_subagent_invocations(agent_entries, parent_session_path)
    artifacts: list[SubagentArtifact] = []

    for inv in invocations:
        invocation_id = inv["invocation_id"]
        subagent_type = inv["subagent_type"]
        entries = inv["entries"]
        ts = inv["first_timestamp"]
        meta = inv["meta"]

        if not entries:
            # Skip empty subagent files (rare; happens when a Task call is
            # cancelled before any agent output lands).
            continue

        if ts is None:
            # No timestamps in any entry — fall back to source file mtime
            # so the rotation bucket is at least deterministic.
            ts = datetime.fromtimestamp(parent_session_path.stat().st_mtime, tz=UTC)

        # Build summary, render markdown, write files.
        sub_summary = _build_subagent_session_summary(
            parent_summary, invocation_id, subagent_type, entries, meta
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
            meta=meta,
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
            meta=meta,
        )
        write_insights_file(insights_path, insights, session_id=invocation_id)

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
                extra=meta,
            )
        )

    return artifacts


def _yaml_safe_scalar(value: Any) -> str:
    """Quote a string for a single-line ``key: "value"`` YAML entry."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def _inject_parent_link_into_frontmatter(
    markdown: str,
    *,
    parent_session_id: str,
    parent_session_path: Path,
    subagent_type: str,
    invocation_id: str,
    meta: dict[str, Any],
) -> str:
    """Splice subagent provenance fields into the frontmatter block.

    The subagent transcript is generated through the standard
    ``format_session_as_markdown`` path, which always produces a
    ``---\\nfrontmatter\\n---`` block. We splice subagent-specific
    keys before the closing ``---`` so consumers can detect, filter,
    and link without parsing the body.

    ``meta`` (the ``agent-<id>.meta.json`` sidecar) contributes
    ``parentAgentId`` — the *true* immediate parent — for a nested
    subagent-of-subagent spawn this is another subagent's invocation id,
    not ``parent_session_id`` (which always anchors to the top-level
    session for directory/filename purposes) — plus additive
    ``description``/``name``/``spawnDepth``/``teamName``/``model``/
    ``permissionMode``/``taskKind`` provenance.
    """
    parts = markdown.split("---\n", 2)
    # format_session_as_markdown always emits "---\n<frontmatter>\n---\n<body>".
    assert len(parts) == 3 and parts[0] == "", (
        f"expected frontmatter block, got unrecognized markdown shape: {markdown[:80]!r}"
    )

    inject = (
        f"artifact_type: subagent\n"
        f"parent_session_id: {parent_session_id}\n"
        f'parent_session_file: "{parent_session_path}"\n'
        f"invocation_id: {invocation_id}\n"
        f'subagent_type: "{subagent_type}"\n'
    )
    if meta.get("name"):
        inject += f'agent_name: "{_yaml_safe_scalar(meta["name"])}"\n'
    if meta.get("description"):
        inject += f'agent_description: "{_yaml_safe_scalar(meta["description"])}"\n'
    if meta.get("parentAgentId"):
        inject += f'parent_agent_id: "{_yaml_safe_scalar(meta["parentAgentId"])}"\n'
    if meta.get("spawnDepth") is not None:
        inject += f"spawn_depth: {int(meta['spawnDepth'])}\n"
    if meta.get("teamName"):
        inject += f'team_name: "{_yaml_safe_scalar(meta["teamName"])}"\n'
    if meta.get("model"):
        inject += f'agent_model: "{_yaml_safe_scalar(meta["model"])}"\n'
    if meta.get("permissionMode"):
        inject += f'agent_permission_mode: "{_yaml_safe_scalar(meta["permissionMode"])}"\n'
    if meta.get("taskKind"):
        inject += f'task_kind: "{_yaml_safe_scalar(meta["taskKind"])}"\n'

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
        description = art.extra.get("description")
        desc_suffix = f" — {description}" if description else ""
        lines.append(
            f"- **{art.subagent_type}**{desc_suffix} "
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
