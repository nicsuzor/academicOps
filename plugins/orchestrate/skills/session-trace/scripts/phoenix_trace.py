#!/usr/bin/env python3
"""Export a Claude Code session's OpenTelemetry trace from an Arize Phoenix span store.

Two output shapes are produced from one span fetch:

``full``
    Every span verbatim, nested into a ``parent_id`` forest. The output is always a
    partition of the input: a span whose parent is absent from the fetch, and a span
    stranded inside a parent cycle that no root reaches, are both reported under
    ``orphans`` (with an ``orphan_reason``) rather than dropped.

``controller``
    The controller trunk only. Subagent spans are grouped under the root session's
    ``session.id`` and carry no agent-identity attribute, so controller spans are
    identified by joining the local markdown controller transcript's tool-call
    timestamps against span start times. Subagent work collapses into ``subagents[]``.
    Its ``meta`` names every count twice — ``session_*`` for the whole session,
    ``controller_*`` for the trunk this document actually contains.

Standard library only, so the skill can invoke it as ``python3 scripts/phoenix_trace.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BASE_URL_ENV_VARS = ("PHOENIX_BASE_URL", "PHOENIX_COLLECTOR_ENDPOINT")
PAGE_LIMIT = 1000
PREVIEW_CHARS = 2000
DEFAULT_TOLERANCE_MS = 500
HTTP_TIMEOUT = 60
# Per-line join warnings are near-identical in bulk; past this many, emit a tail count
# instead so the block stays readable.
MAX_LINE_WARNINGS = 20

EXIT_CONFIG = 2
EXIT_EMPTY = 1

Span = dict[str, Any]

# ``#### 🛠️ Tool call: `Name` `(2026-01-01T00:00:00.000Z)` `` — an optional
# em-dash summary may sit between the two backticked spans.
TOOL_CALL_LINE = re.compile(r"^#{2,6} .*?Tool call: `([^`]+)`.*`\(([^)`]+)\)`\s*$")
FRONTMATTER_SESSION = re.compile(r"^session_id:\s*(\S+)\s*$", re.MULTILINE)


# --- errors ----------------------------------------------------------------


class ConfigError(Exception):
    """A required input is missing or unusable."""


# --- time helpers ----------------------------------------------------------


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def duration_ms(span: Span) -> float | None:
    """Phoenix records no latency field; latency is end minus start."""
    start = parse_time(span.get("start_time"))
    end = parse_time(span.get("end_time"))
    if start is None or end is None:
        return None
    return round((end - start).total_seconds() * 1000.0, 3)


def sort_key(span: Span) -> tuple[float, str]:
    started = parse_time(span.get("start_time"))
    return (started.timestamp() if started else 0.0, str(span.get("id") or ""))


# --- HTTP ------------------------------------------------------------------


def get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        raise ConfigError(f"HTTP {exc.code} from {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ConfigError(f"cannot reach {url}: {exc.reason}") from exc


def resolve_base_url(explicit: str | None) -> str:
    candidate = explicit
    if not candidate:
        for name in BASE_URL_ENV_VARS:
            value = os.environ.get(name, "").strip()
            if value:
                candidate = value
                break
    if not candidate:
        raise ConfigError(
            "no Phoenix base URL. Pass --base-url, or set one of: " + ", ".join(BASE_URL_ENV_VARS)
        )
    return candidate.rstrip("/")


def resolve_project(base_url: str, wanted: str) -> tuple[str, str]:
    """Return ``(project_id, project_name)``; ``wanted`` may be either."""
    payload = get_json(f"{base_url}/v1/projects")
    projects = payload.get("data", []) if isinstance(payload, dict) else []
    for project in projects:
        if wanted in (project.get("name"), project.get("id")):
            return str(project.get("id")), str(project.get("name"))
    known = ", ".join(str(p.get("name")) for p in projects) or "(none)"
    raise ConfigError(f"project {wanted!r} not found. Projects on this server: {known}")


def fetch_spans(
    base_url: str, project_id: str, session_id: str, page_limit: int = PAGE_LIMIT
) -> tuple[list[Span], int]:
    """Page ``/v1/projects/{id}/spans`` to exhaustion. The API returns newest-first.

    Returns ``(spans, pages_fetched)``. ``page_limit`` is exposed as ``--page-limit``
    so the paging loop is exercisable without a thousand-span session.
    """
    spans: list[Span] = []
    cursor: str | None = None
    pages = 0
    while True:
        query = {
            "attribute": f"session.id:{session_id}",
            "limit": str(page_limit),
        }
        if cursor:
            query["cursor"] = cursor
        url = (
            f"{base_url}/v1/projects/{urllib.parse.quote(project_id, safe='')}"
            f"/spans?{urllib.parse.urlencode(query)}"
        )
        payload = get_json(url)
        pages += 1
        spans.extend(payload.get("data", []))
        cursor = payload.get("next_cursor")
        if not cursor:
            break
    return spans, pages


def fetch_sessions(base_url: str, project_id: str) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        query = {"limit": "100"}
        if cursor:
            query["cursor"] = cursor
        url = (
            f"{base_url}/v1/projects/{urllib.parse.quote(project_id, safe='')}"
            f"/sessions?{urllib.parse.urlencode(query)}"
        )
        payload = get_json(url)
        sessions.extend(payload.get("data", []))
        cursor = payload.get("next_cursor")
        if not cursor:
            break
    return sessions


def load_spans_from_file(path: Path, session_id: str) -> list[Span]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
    raw = payload.get("data", []) if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        raise ConfigError(f"{path} holds neither a span list nor an object with 'data'")
    return [s for s in raw if s.get("attributes", {}).get("session.id") == session_id]


# --- transcript ------------------------------------------------------------


def sessions_roots(explicit_root: str | None) -> list[Path]:
    roots: list[Path] = []
    configured = explicit_root or os.environ.get("AOPS_SESSIONS", "").strip()
    if configured:
        base = Path(configured).expanduser()
        roots.extend([base / "transcripts", base])
    return [r for r in roots if r.is_dir()]


def find_transcript(session_id: str, explicit: str | None) -> dict[str, str] | None:
    """Locate ``<base>.controller.md`` for a session id, confirmed by frontmatter."""
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ConfigError(f"--transcript {path} does not exist")
        return transcript_paths(path)

    short = session_id.split("-", 1)[0]
    for root in sessions_roots(None):
        for pattern in (f"*/*-{short}.controller.md", f"*-{short}.controller.md"):
            for candidate in sorted(root.glob(pattern)):
                head = candidate.read_text(encoding="utf-8", errors="replace")[:4000]
                match = FRONTMATTER_SESSION.search(head)
                if match and match.group(1) == session_id:
                    return transcript_paths(candidate)
    return None


def transcript_paths(controller_md: Path) -> dict[str, str]:
    name = str(controller_md)
    base = name[: -len(".controller.md")] if name.endswith(".controller.md") else name
    full = Path(base + ".full.md")
    return {
        "controller_md": str(controller_md),
        "full_md": str(full) if full.is_file() else "",
    }


def parse_controller_tool_calls(path: Path) -> list[dict[str, Any]]:
    """Extract ``(tool name, timestamp)`` for every controller-trunk tool call."""
    calls: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for number, line in enumerate(text.split("\n"), start=1):
        match = TOOL_CALL_LINE.match(line)
        if not match:
            continue
        when = parse_time(match.group(2))
        if when is None:
            continue
        calls.append({"line": number, "tool_name": match.group(1), "time": when})
    return calls


# --- tree ------------------------------------------------------------------


def tool_name_of(span: Span) -> str:
    attributes = span.get("attributes", {})
    return str(attributes.get("tool.name") or span.get("name") or "")


def span_id_of(span: Span) -> str:
    return str(span.get("context", {}).get("span_id") or "")


def trace_id_of(span: Span) -> str:
    return str(span.get("context", {}).get("trace_id") or "")


def build_forest(spans: list[Span]) -> tuple[list[Span], list[Span]]:
    """Nest spans by ``parent_id`` -> ``context.span_id``.

    Returns ``(roots, orphans)``. The result is a partition of the input: every span
    is reachable from exactly one entry in ``roots + orphans``. Two things become an
    orphan, distinguished by ``orphan_reason``:

    ``parent_not_in_fetch``
        the span names a parent that is not in the fetched set.
    ``parent_cycle``
        the span sits in a ``parent_id`` cycle that no root reaches, so walking down
        from the roots would never visit it. Promoting one member of each such cycle
        to a root of its own makes the rest reachable; the back edge is then cut by
        :func:`prune_cycles`.

    Raises ``RuntimeError`` if the partition invariant fails — a silent drop here is
    the failure mode this function exists to prevent.
    """
    nodes: dict[str, Span] = {}
    ordered: list[Span] = []
    for span in sorted(spans, key=sort_key):
        node = dict(span)
        node["duration_ms"] = duration_ms(span)
        node["children"] = []
        ordered.append(node)
        key = span_id_of(span)
        if key:
            nodes[key] = node

    roots: list[Span] = []
    orphans: list[Span] = []
    for node in ordered:
        parent_key = node.get("parent_id")
        if not parent_key:
            roots.append(node)
        elif parent_key in nodes:
            nodes[parent_key]["children"].append(node)
        else:
            node["orphan_reason"] = "parent_not_in_fetch"
            orphans.append(node)

    # Promote cycle-stranded spans until the forest covers every input span. Each
    # promotion detaches one node from its (equally unreachable) parent and makes
    # its whole cycle walkable.
    reached = reachable(roots + orphans)
    for node in ordered:
        if id(node) in reached:
            continue
        parent = nodes.get(str(node.get("parent_id") or ""))
        if parent is not None:
            parent["children"] = [c for c in parent["children"] if c is not node]
        node["orphan_reason"] = "parent_cycle"
        orphans.append(node)
        reached |= reachable([node])

    prune_cycles(roots + orphans)
    covered = reachable(roots + orphans)
    if len(covered) != len(ordered):
        raise RuntimeError(
            f"forest lost spans: {len(ordered)} in, {len(covered)} reachable in the output"
        )
    return roots, orphans


def reachable(entries: list[Span]) -> set[int]:
    """Identities of every node walkable from ``entries``, cycle-safe."""
    seen: set[int] = set()
    stack = list(entries)
    while stack:
        node = stack.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        stack.extend(node["children"])
    return seen


def prune_cycles(entries: list[Span]) -> None:
    seen: set[int] = set()
    stack = list(entries)
    while stack:
        node = stack.pop()
        if id(node) in seen:
            node["children"] = []
            continue
        seen.add(id(node))
        stack.extend(node["children"])


def descendants(span_id: str, children_by_parent: dict[str, list[Span]]) -> list[Span]:
    out: list[Span] = []
    seen: set[str] = {span_id}
    stack = list(children_by_parent.get(span_id, []))
    while stack:
        node = stack.pop()
        key = span_id_of(node)
        if key in seen:
            continue
        seen.add(key)
        out.append(node)
        stack.extend(children_by_parent.get(key, []))
    return out


# --- meta ------------------------------------------------------------------


TOKEN_ATTRS = {
    "prompt": "llm.token_count.prompt",
    "completion": "llm.token_count.completion",
    "total": "llm.token_count.total",
    "cache_read": "llm.token_count.prompt_details.cache_read",
    "cache_write": "llm.token_count.prompt_details.cache_write",
}


def span_metrics(spans: list[Span]) -> dict[str, Any]:
    """Every count that describes a set of spans, computed over exactly that set.

    Kept separate from :func:`build_meta` so the controller export can report the
    same shape twice — once for the whole session, once for the trunk it contains —
    instead of copying whole-session figures onto a partial document.
    """
    kinds: dict[str, int] = {}
    statuses: dict[str, int] = {}
    tokens = dict.fromkeys(TOKEN_ATTRS, 0)
    starts = [t for t in (parse_time(s.get("start_time")) for s in spans) if t]
    ends = [t for t in (parse_time(s.get("end_time")) for s in spans) if t]

    for span in spans:
        kinds[str(span.get("span_kind"))] = kinds.get(str(span.get("span_kind")), 0) + 1
        code = str(span.get("status_code"))
        statuses[code] = statuses.get(code, 0) + 1
        attributes = span.get("attributes", {})
        for label, attribute in TOKEN_ATTRS.items():
            value = attributes.get(attribute)
            if isinstance(value, (int, float)):
                tokens[label] += int(value)

    return {
        "span_count": len(spans),
        "trace_count": len({trace_id_of(s) for s in spans if trace_id_of(s)}),
        "time_range": {
            "start": min(starts).isoformat() if starts else None,
            "end": max(ends).isoformat() if ends else None,
        },
        "span_kind_counts": dict(sorted(kinds.items())),
        "status_counts": dict(sorted(statuses.items())),
        "error_count": statuses.get("ERROR", 0),
        "token_totals": tokens,
    }


def build_meta(
    spans: list[Span],
    session_id: str,
    project_name: str,
    base_url: str | None,
    transcript: dict[str, str] | None,
    fetch_pages: int | None = None,
) -> dict[str, Any]:
    """Session-scoped meta. Correct as-is on the ``full`` export, which holds the
    whole session; the controller export re-labels these under ``session_*``."""
    return {
        "session_id": session_id,
        "project": project_name,
        "base_url": base_url,
        "fetched_at": datetime.now(UTC).isoformat(),
        "fetch_pages": fetch_pages,
        **span_metrics(spans),
        "transcript": transcript or None,
    }


# --- attribution -----------------------------------------------------------


def join_transcript(
    spans: list[Span], calls: list[dict[str, Any]], tolerance_ms: int
) -> dict[str, Any]:
    """Match controller-trunk tool calls to spans by name and nearest start time.

    Phoenix span start trails the transcript timestamp by a small, tight margin,
    so a name-equal pair inside the tolerance identifies the same call.

    An unmatched call is reported as one of two distinct things, because they call
    for opposite responses:

    ``out_of_tolerance``
        no same-named span started within the window. Widening ``--tolerance-ms``
        may help.
    ``collision``
        a span *was* inside the window, but a nearer call claimed it first — two
        transcript calls competing for one span. Widening the tolerance makes this
        strictly worse, so the warning says so.
    """
    candidates = [s for s in spans if s.get("span_kind") in ("TOOL", "AGENT")]
    empty: dict[str, Any] = {
        "method": "transcript-join",
        "tolerance_ms": tolerance_ms,
        "matched": 0,
        "ambiguous": 0,
        "collisions": 0,
        "unmatched": len(calls),
        "transcript_calls": len(calls),
        "matched_span_ids": set(),
    }
    if not candidates and calls:
        # One cause, one warning. Emitting it per transcript line produced hundreds
        # of near-identical lines that all implied a tolerance problem instead.
        empty["warnings"] = [
            f"no TOOL or AGENT spans in this session, so none of the {len(calls)} controller "
            "tool calls can be joined. This is an instrumentation gap, not a tolerance "
            "problem: the run emitted turn-level spans only (see meta.span_kind_counts). "
            "Changing --tolerance-ms cannot help."
        ]
        return empty

    by_name: dict[str, list[Span]] = {}
    for span in candidates:
        by_name.setdefault(tool_name_of(span), []).append(span)

    pairs: list[tuple[float, int, str]] = []
    contenders: dict[int, int] = {}
    for index, call in enumerate(calls):
        for span in by_name.get(str(call["tool_name"]), []):
            started = parse_time(span.get("start_time"))
            if started is None:
                continue
            delta = abs((started - call["time"]).total_seconds() * 1000.0)
            if delta <= tolerance_ms:
                pairs.append((delta, index, span_id_of(span)))
                contenders[index] = contenders.get(index, 0) + 1

    pairs.sort()
    matched: dict[int, str] = {}
    claimed: set[str] = set()
    for _, index, key in pairs:
        if index in matched or key in claimed:
            continue
        matched[index] = key
        claimed.add(key)

    warnings: list[str] = []
    ambiguous = 0
    collisions = 0
    for index, call in enumerate(calls):
        if index not in matched and contenders.get(index, 0) > 0:
            # Had a candidate inside the window; lost it to a nearer call.
            collisions += 1
            warnings.append(
                f"transcript line {call['line']}: tool call `{call['tool_name']}` at "
                f"{call['time'].isoformat()} lost its only candidate span(s) to a nearer "
                f"call — a claimed-span collision, not a tolerance miss. Widening "
                f"--tolerance-ms will NOT help; it makes collisions more likely."
            )
        elif index not in matched:
            warnings.append(
                f"transcript line {call['line']}: tool call `{call['tool_name']}` at "
                f"{call['time'].isoformat()} matched no span within {tolerance_ms} ms"
            )
        elif contenders.get(index, 0) > 1:
            ambiguous += 1
            warnings.append(
                f"transcript line {call['line']}: tool call `{call['tool_name']}` had "
                f"{contenders[index]} candidate spans within {tolerance_ms} ms; nearest taken"
            )

    return {
        "method": "transcript-join",
        "tolerance_ms": tolerance_ms,
        "matched": len(matched),
        "ambiguous": ambiguous,
        "collisions": collisions,
        "unmatched": len(calls) - len(matched),
        "transcript_calls": len(calls),
        "matched_span_ids": claimed,
        "warnings": cap_warnings(warnings),
    }


def cap_warnings(warnings: list[str], cap: int = MAX_LINE_WARNINGS) -> list[str]:
    """Keep the first ``cap`` per-line warnings and replace the tail with its count."""
    if len(warnings) <= cap:
        return warnings
    return [*warnings[:cap], f"…and {len(warnings) - cap} further per-line warnings, suppressed"]


# --- controller shape ------------------------------------------------------


def preview(value: Any, cap: int = PREVIEW_CHARS) -> tuple[str | None, int]:
    if value is None:
        return None, 0
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if len(text) <= cap:
        return text, len(text)
    return text[:cap] + "…[truncated]", len(text)


def summarise_event(span: Span, collapsed: int | None) -> dict[str, Any]:
    attributes = span.get("attributes", {})
    input_preview, input_chars = preview(attributes.get("input.value"))
    output_preview, output_chars = preview(attributes.get("output.value"))
    event: dict[str, Any] = {
        "span_id": span_id_of(span),
        "parent_id": span.get("parent_id"),
        "trace_id": trace_id_of(span),
        "kind": span.get("span_kind"),
        "name": span.get("name"),
        "tool_name": attributes.get("tool.name"),
        "start_time": span.get("start_time"),
        "duration_ms": duration_ms(span),
        "status_code": span.get("status_code"),
        "status_message": span.get("status_message"),
        "input_preview": input_preview,
        "output_preview": output_preview,
        "input_chars": input_chars,
        "output_chars": output_chars,
    }
    if attributes.get("llm.model_name"):
        event["model"] = attributes["llm.model_name"]
    counts = {
        label: attributes[attribute]
        for label, attribute in TOKEN_ATTRS.items()
        if attribute in attributes
    }
    if counts:
        event["token_counts"] = counts
    if collapsed is not None:
        event["collapsed_subagent_spans"] = collapsed
    return event


def agent_status(attributes: dict[str, Any]) -> str | None:
    raw = attributes.get("output.value")
    if not isinstance(raw, str):
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed.get("status") if isinstance(parsed, dict) else None


def build_controller(
    spans: list[Span],
    meta: dict[str, Any],
    attribution: dict[str, Any],
) -> dict[str, Any]:
    children_by_parent: dict[str, list[Span]] = {}
    for span in spans:
        parent = span.get("parent_id")
        if parent:
            children_by_parent.setdefault(str(parent), []).append(span)

    roots = [s for s in spans if not s.get("parent_id")]
    root_ids = {span_id_of(s) for s in roots}
    agent_spans = [s for s in spans if s.get("span_kind") == "AGENT"]

    matched_ids: set[str] = set(attribution.pop("matched_span_ids", set()))
    if attribution["method"] == "roots-only-fallback":
        controller_ids = root_ids | {
            span_id_of(s) for s in agent_spans if s.get("parent_id") in root_ids
        }
    else:
        controller_ids = root_ids | matched_ids
        controller_ids |= {
            span_id_of(s)
            for s in spans
            if s.get("span_kind") == "LLM" and str(s.get("parent_id")) in root_ids
        }

    parent_of = {span_id_of(s): str(s.get("parent_id") or "") for s in spans}

    subagents: list[dict[str, Any]] = []
    subagent_ids: set[str] = set()
    collapsed_by_agent: dict[str, int] = {}
    for span in sorted(agent_spans, key=sort_key):
        attributes = span.get("attributes", {})
        key = span_id_of(span)
        subtree = [d for d in descendants(key, children_by_parent) if span_id_of(d) not in root_ids]
        subagent_ids.update(span_id_of(d) for d in subtree)
        collapsed_by_agent[key] = len(subtree)
        prompt, prompt_chars = preview(attributes.get("input.value"))
        status = agent_status(attributes)
        subagents.append(
            {
                "agent_name": attributes.get("agent.name"),
                "span_id": key,
                # Lineage: enough to reconstruct where this dispatch sits without a
                # tree renderer. `parent_id` is the dispatching span, `root_span_id`
                # the turn root it walks up to.
                "parent_id": span.get("parent_id"),
                "root_span_id": ancestor_root(key, parent_of, root_ids),
                "trace_id": trace_id_of(span),
                "dispatch_prompt": prompt,
                "dispatch_prompt_chars": prompt_chars,
                "start_time": span.get("start_time"),
                "end_time": span.get("end_time"),
                "duration_ms": duration_ms(span),
                # A `teammate_spawned` AGENT span closes when the dispatch is
                # acknowledged, not when the subagent finishes: its duration_ms
                # measures the spawn (order of 100 ms) and says nothing about the
                # subagent's runtime. Use collapsed_span_count for that instead.
                "duration_is_dispatch_only": status == "teammate_spawned",
                "status_code": span.get("status_code"),
                "status": status,
                "collapsed_span_count": len(subtree),
            }
        )

    events = [
        summarise_event(span, collapsed_by_agent.get(span_id_of(span)))
        for span in sorted(spans, key=sort_key)
        if span_id_of(span) in controller_ids
    ]

    accounted = controller_ids | subagent_ids | {span_id_of(s) for s in agent_spans}
    unattributed = [s for s in spans if span_id_of(s) not in accounted]

    # `meta` describes the whole session; this document holds only the controller
    # trunk. Report both, and never under a bare name that could mean either.
    body = [s for s in spans if span_id_of(s) in controller_ids]
    controller_meta: dict[str, Any] = {}
    session_scoped = set(span_metrics([]))  # the population-dependent key names
    for name, value in meta.items():
        controller_meta[f"session_{name}" if name in session_scoped else name] = value
    for name, value in span_metrics(body).items():
        controller_meta[f"controller_{name}"] = value
    controller_meta["attribution"] = attribution
    return {
        "meta": controller_meta,
        "subagents": subagents,
        "events": events,
        "unattributed_span_count": len(unattributed),
    }


def ancestor_root(span_id: str, parent_of: dict[str, str], root_ids: set[str]) -> str | None:
    """Walk up ``parent_id`` to the enclosing root span id, or ``None``."""
    seen: set[str] = set()
    current = span_id
    while current and current not in seen:
        if current in root_ids:
            return current
        seen.add(current)
        current = parent_of.get(current, "")
    return None


# --- driver ----------------------------------------------------------------


def default_out_dir() -> Path:
    root = os.environ.get("AOPS_SESSIONS", "").strip()
    return Path(root).expanduser() / "traces" if root else Path(".")


def print_sessions(base_url: str, project_id: str, project_name: str) -> None:
    sessions = fetch_sessions(base_url, project_id)
    print(f"{len(sessions)} session(s) retained in project {project_name!r}")
    for record in sessions:
        traces = record.get("traces")
        count = len(traces) if isinstance(traces, list) else traces
        print(
            f"  {record.get('session_id')}  "
            f"{record.get('start_time')} -> {record.get('end_time')}  traces={count}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phoenix_trace.py",
        description="Export a Claude Code session trace from an Arize Phoenix span store.",
    )
    parser.add_argument("session_id", nargs="?", help="session.id to export")
    parser.add_argument(
        "--mode", choices=("full", "controller", "both"), default="both", help="output shape"
    )
    parser.add_argument("--out", help="output directory")
    parser.add_argument("--project", default="default", help="Phoenix project name or id")
    parser.add_argument("--base-url", help="Phoenix base URL (overrides the environment)")
    parser.add_argument("--transcript", help="path to <base>.controller.md for the join")
    parser.add_argument(
        "--tolerance-ms",
        type=int,
        default=DEFAULT_TOLERANCE_MS,
        help=f"transcript join tolerance in milliseconds (default {DEFAULT_TOLERANCE_MS})",
    )
    parser.add_argument(
        "--page-limit",
        type=int,
        default=PAGE_LIMIT,
        help=f"spans requested per API page (default {PAGE_LIMIT}); lower it to exercise paging",
    )
    parser.add_argument(
        "--from-file", help="read spans from a saved JSON payload instead of the server"
    )
    parser.add_argument(
        "--list-sessions", action="store_true", help="list the sessions the server still retains"
    )
    return parser


def run(args: argparse.Namespace) -> int:
    if args.list_sessions:
        base_url = resolve_base_url(args.base_url)
        project_id, project_name = resolve_project(base_url, args.project)
        print_sessions(base_url, project_id, project_name)
        return 0

    if not args.session_id:
        raise ConfigError("a session id is required (or pass --list-sessions)")

    if args.page_limit < 1:
        raise ConfigError("--page-limit must be at least 1")

    if args.from_file:
        base_url = None
        project_name = args.project
        pages = None
        spans = load_spans_from_file(Path(args.from_file).expanduser(), args.session_id)
    else:
        base_url = resolve_base_url(args.base_url)
        project_id, project_name = resolve_project(base_url, args.project)
        spans, pages = fetch_spans(base_url, project_id, args.session_id, args.page_limit)

    if not spans:
        print(
            f"no spans for session {args.session_id!r} in project {project_name!r}. "
            "Run --list-sessions to see what the server still holds: Phoenix retention is "
            "bounded by its storage configuration and older sessions are evicted.",
            file=sys.stderr,
        )
        return EXIT_EMPTY

    spans.sort(key=sort_key)
    transcript = find_transcript(args.session_id, args.transcript)
    meta = build_meta(spans, args.session_id, project_name, base_url, transcript, pages)

    out_dir = Path(args.out).expanduser() if args.out else default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if args.mode in ("full", "both"):
        roots, orphans = build_forest(spans)
        document = {"meta": meta, "roots": roots, "orphans": orphans}
        path = out_dir / f"{args.session_id}.trace.json"
        path.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(path)
        print(
            f"full: {path} ({len(spans)} spans, {len(roots)} roots, {len(orphans)} orphans, "
            f"{meta['error_count']} errors)"
        )

    if args.mode in ("controller", "both"):
        if transcript and transcript["controller_md"]:
            calls = parse_controller_tool_calls(Path(transcript["controller_md"]))
            attribution = join_transcript(spans, calls, args.tolerance_ms)
            attribution["transcript_path"] = transcript["controller_md"]
        else:
            attribution = {
                "method": "roots-only-fallback",
                "tolerance_ms": args.tolerance_ms,
                "matched": 0,
                "ambiguous": 0,
                "collisions": 0,
                "unmatched": 0,
                "transcript_calls": 0,
                "transcript_path": None,
                "warning": (
                    "no local controller transcript for this session, so controller tool calls "
                    "cannot be separated from subagent tool calls. Falling back to root spans "
                    "and their direct agent dispatches only; fidelity is reduced."
                ),
                "warnings": [],
            }
        document = build_controller(spans, meta, attribution)
        path = out_dir / f"{args.session_id}.trace.controller.json"
        path.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(path)
        stats = document["meta"]["attribution"]
        print(
            f"controller: {path} ({len(document['events'])} events, "
            f"{len(document['subagents'])} subagents, method={stats['method']}, "
            f"matched={stats['matched']}, ambiguous={stats['ambiguous']}, "
            f"collisions={stats['collisions']}, unmatched={stats['unmatched']}, "
            f"unattributed_spans={document['unattributed_span_count']})"
        )

    return 0 if written else EXIT_CONFIG


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
