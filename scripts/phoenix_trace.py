#!/usr/bin/env python3
"""Dump every span belonging to a session's traces from a Phoenix instance.

A subagent carries its own ``session.id`` but inherits the parent's
``trace_id``. Filtering on ``session.id`` alone therefore returns the parent's
spans and silently drops every subagent span in the same trace. This tool
resolves the session to the set of trace ids it appears in, then fetches *all*
spans in those traces regardless of which session they claim, and reports the
narrow set and the full trees separately.

Configuration is environment-only, per specs/ARCHITECTURE.md "No defaults":

    PHOENIX_COLLECTOR_ENDPOINT   base URL of the Phoenix server, e.g. http://host:6006
    PHOENIX_PROJECT_NAME         project identifier (name or ID); ``--project`` overrides

Both are required. The tool exits 2 when either is unset.

Run directly: ``uv run python scripts/phoenix_trace.py <session-id>``
or via the console script: ``aops-trace <session-id>``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

PAGE_LIMIT = 1000
SCAN_PAGE_CAP = 200

Span = dict[str, Any]


class PhoenixError(RuntimeError):
    """Any failure reaching or interpreting the Phoenix HTTP API."""


@dataclass
class Config:
    """Resolved connection settings. Every field comes from the environment."""

    endpoint: str
    project: str


def load_config(project_override: str | None) -> Config:
    """Read connection settings from the environment, failing loudly when unset."""
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "").strip()
    if not endpoint:
        raise PhoenixError(
            "PHOENIX_COLLECTOR_ENDPOINT is unset. "
            "Set it to the base URL of the Phoenix server (no default is baked in)."
        )
    project = (project_override or os.environ.get("PHOENIX_PROJECT_NAME", "")).strip()
    if not project:
        raise PhoenixError(
            "PHOENIX_PROJECT_NAME is unset and --project was not given. "
            "Set it to the Phoenix project name or ID (no default is baked in)."
        )
    return Config(endpoint=endpoint.rstrip("/"), project=project)


@dataclass
class Client:
    """Thin paginating reader over the Phoenix REST span API."""

    config: Config

    def _get(self, path: str, params: list[tuple[str, str]]) -> dict[str, Any]:
        url = f"{self.config.endpoint}{path}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:500]
            raise PhoenixError(f"GET {url} -> HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise PhoenixError(f"GET {url} -> unreachable: {exc.reason}") from exc

    def spans(self, params: list[tuple[str, str]]) -> list[Span]:
        """Fetch every page of a span query, following ``next_cursor``."""
        path = f"/v1/projects/{urllib.parse.quote(self.config.project, safe='')}/spans"
        out: list[Span] = []
        cursor: str | None = None
        for _ in range(SCAN_PAGE_CAP):
            page = [*params, ("limit", str(PAGE_LIMIT))]
            if cursor:
                page.append(("cursor", cursor))
            body = self._get(path, page)
            out.extend(body.get("data", []))
            cursor = body.get("next_cursor")
            if not cursor:
                return out
        raise PhoenixError(
            f"Query returned more than {SCAN_PAGE_CAP} pages of {PAGE_LIMIT} spans; refusing to keep paging."
        )


def session_of(span: Span) -> str | None:
    """The span's own ``session.id`` attribute, if it declares one."""
    value = span.get("attributes", {}).get("session.id")
    return value if isinstance(value, str) else None


def resolve_session(client: Client, wanted: str) -> str:
    """Resolve a full or prefix session id to exactly one full session id.

    Tries an exact server-side attribute filter first. Only when that returns
    nothing does it scan the project and prefix-match, so the common case costs
    one request.
    """
    exact = client.spans([("attribute", f'session.id:"{wanted}"')])
    if exact:
        return wanted

    seen: Counter[str] = Counter()
    for span in client.spans([]):
        found = session_of(span)
        if found:
            seen[found] += 1
    matches = sorted(s for s in seen if s.startswith(wanted))
    if not matches:
        raise PhoenixError(
            f"No session matches {wanted!r}. Searched: exact attribute filter "
            f'session.id:"{wanted}", then a full scan of project '
            f"{client.config.project!r} covering {sum(seen.values())} spans "
            f"across {len(seen)} distinct session.id values."
        )
    if len(matches) > 1:
        raise PhoenixError(
            f"Prefix {wanted!r} is ambiguous across {len(matches)} sessions: {matches}"
        )
    return matches[0]


@dataclass
class Topology:
    """Structural facts about one trace, derived only from the spans returned."""

    trace_id: str
    span_count: int = 0
    first_start_time: str | None = None
    last_end_time: str | None = None
    roots: list[str] = field(default_factory=list)
    orphans: list[dict[str, str]] = field(default_factory=list)
    span_kinds: dict[str, int] = field(default_factory=dict)
    sessions: dict[str, int] = field(default_factory=dict)


def topology(trace_id: str, spans: list[Span]) -> Topology:
    """Classify a trace's spans into roots, orphans, kinds, and owning sessions."""
    present = {s["context"]["span_id"] for s in spans}
    report = Topology(trace_id=trace_id, span_count=len(spans))
    if spans:
        report.first_start_time = min(s["start_time"] for s in spans)
        report.last_end_time = max(s["end_time"] for s in spans if s.get("end_time"))
    kinds: Counter[str] = Counter()
    sessions: Counter[str] = Counter()
    for span in spans:
        kinds[span.get("span_kind") or "UNKNOWN"] += 1
        sessions[session_of(span) or "<none>"] += 1
        parent = span.get("parent_id")
        if parent is None:
            report.roots.append(f"{span['name']} [{span['context']['span_id']}]")
        elif parent not in present:
            report.orphans.append(
                {
                    "span": span["name"],
                    "span_id": span["context"]["span_id"],
                    "missing_parent_span_id": parent,
                    "session_id": session_of(span) or "<none>",
                }
            )
    report.span_kinds = dict(kinds.most_common())
    report.sessions = dict(sessions.most_common())
    return report


def collect(client: Client, session_id: str) -> dict[str, Any]:
    """Resolve session -> trace ids -> all spans in those traces."""
    narrow = client.spans([("attribute", f'session.id:"{session_id}"')])
    trace_ids = sorted({s["context"]["trace_id"] for s in narrow})
    full = client.spans([("trace_id", t) for t in trace_ids]) if trace_ids else []

    by_trace: dict[str, list[Span]] = {t: [] for t in trace_ids}
    for span in full:
        by_trace.setdefault(span["context"]["trace_id"], []).append(span)
    for spans in by_trace.values():
        spans.sort(key=lambda s: s["start_time"])

    return {
        "session_id": session_id,
        "project": client.config.project,
        "trace_ids": trace_ids,
        "counts": {
            "narrow_spans": len(narrow),
            "full_spans": len(full),
            "trace_ids": len(trace_ids),
        },
        "narrow_spans": sorted(narrow, key=lambda s: s["start_time"]),
        "traces": [
            {
                "trace_id": t,
                "topology": vars(topology(t, by_trace[t])),
                "spans": by_trace[t],
            }
            for t in trace_ids
        ],
    }


def summarise(result: dict[str, Any]) -> dict[str, Any]:
    """Strip span bodies, keeping only the structural report."""
    return {
        "session_id": result["session_id"],
        "project": result["project"],
        "counts": result["counts"],
        "traces": [{**t["topology"]} for t in result["traces"]],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aops-trace",
        description="Dump every span in the traces a session appears in, as JSON.",
    )
    parser.add_argument("session_id", help="Full session id, or a unique prefix of one.")
    parser.add_argument(
        "--project", help="Phoenix project name or ID; overrides PHOENIX_PROJECT_NAME."
    )
    parser.add_argument(
        "--narrow",
        action="store_true",
        help="Emit only spans carrying this session.id, omitting inherited-trace siblings.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit the trace topology only: roots, orphans, span kinds, owning sessions.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = Client(load_config(args.project))
        session_id = resolve_session(client, args.session_id)
        result = collect(client, session_id)
    except PhoenixError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.summary:
        payload: Any = summarise(result)
    elif args.narrow:
        payload = {
            "session_id": result["session_id"],
            "project": result["project"],
            "trace_ids": result["trace_ids"],
            "counts": result["counts"],
            "narrow_spans": result["narrow_spans"],
        }
    else:
        payload = result
    json.dump(payload, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
