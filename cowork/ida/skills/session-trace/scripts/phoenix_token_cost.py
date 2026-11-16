#!/usr/bin/env python3
"""Token usage and estimated cost per session (and per PKB task) from Phoenix LLM spans.

One screen, ranked by cost: session, agent/role, task, model, in/out/cache tokens,
estimated USD. Routes ``GET /v1/projects/{id}/...`` queries through the Phoenix MCP
``phoenix_execute`` endpoint (using indexed keyset-paged session/trace joins when
filtering spans on ``session.id``, with full-payload ``getSpans`` hydration for
oversized rows).

Method
------
``LLM`` spans carry ``llm.model_name`` and ``llm.token_count.*``. ``prompt`` *includes*
the cache tokens, so::

    fresh_in = prompt - cache_read - cache_write

Spans are deduplicated on ``(session.id, start_time, output.value)`` before summing:
roughly a sixth of Opus spans arrive twice (same start, same output) and would double
the bill. Gemini spans (``gemini-*``) carry no token counts and are counted as calls only.

``session.id`` is the aggregation key. Subagents inherit the parent's session id
(``subagent.id == session.id``), so a row is a whole desk/face/subagent tree.

The task column is recovered from ``TOOL`` spans -- ``claim_task`` / ``release_task`` /
``get_task`` / ``update_task`` / ``append`` calls whose ``input.value`` names an id -- because
the tracer drops ``task.id`` / ``tag.task_id`` when equal to the project name or not a
valid task id (leaving them unset on spans for sessions without an active task). A session
that touched several tasks lists them all (claim/release first); a session with none
prints ``unknown``. ``--by task`` splits a session's spend across the tasks it touched,
attributing each LLM call to the task most recently claimed/read before it.

The agent/role column is a label, not an attribute: Claude Code emits no role. It is
built from, in order: a user-supplied labels file (``--labels``, JSON of session-id
prefix -> label); the name the session printed for itself in a ``ListAgents`` call;
the channel it fronts (``telegram face``); its first human-typed prompt in the window;
``agy polecat``. The ``agent.name`` kinds of subagents it dispatched are appended.

Prices are USD per million tokens and live in :data:`PRICES`; override with
``--prices path.json``. Unknown models cost 0 and are flagged in the footer.

Configuration is flags or environment, matching ``phoenix_transcript.py``: ``--base-url`` or
``$PHOENIX_MCP_URL``; ``--project`` or ``$PHOENIX_MCP_PROJECT``. Standard library only.

Examples::

    uv run python phoenix_token_cost.py --since "2026-09-12 00:00" --tz +10:00
    uv run python phoenix_token_cost.py --since 2026-09-11T14:00:00Z --by task --json
    uv run python phoenix_token_cost.py --since 2026-09-11T14:00:00Z --session 5b239939
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
from collections import defaultdict
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BASE_URL_ENV_VAR = "PHOENIX_MCP_URL"
PROJECT_ENV_VAR = "PHOENIX_MCP_PROJECT"
_ACCESS_TOKEN_PAIRS = (("DISPATCHER_MCP_TOKEN_ID", "DISPATCHER_MCP_TOKEN_SECRET"),)
_MCP_SESSIONS: dict[str, str] = {}
PAGE_LIMIT = 1000
SQL_PAGE_MAX_ROWS = 499
SQL_ATTR_INLINE_BYTES = 200_000
SQL_EVENTS_INLINE_BYTES = 50_000
HTTP_TIMEOUT = 120

EXIT_CONFIG = 2
EXIT_EMPTY = 1

Span = dict[str, Any]

# USD per million tokens: fresh input, output, cache read, cache write (5-minute TTL).
# List prices from https://platform.claude.com/docs/en/about-claude/pricing as read on
# 2026-09-12. Cache read = 0.1x input (0.025x on Fable 5.1), 5-minute cache write = 1.25x.
# Claude Code's subscription quota is not billed at these rates; the dollar column is a
# comparable-spend estimate, not an invoice. Override with --prices.
PRICES: dict[str, dict[str, float]] = {
    "claude-fable-5-1": {"in": 10.0, "out": 50.0, "cache_read": 0.25, "cache_write": 12.5},
    "claude-fable-5": {"in": 10.0, "out": 50.0, "cache_read": 1.0, "cache_write": 12.5},
    "claude-opus-5": {"in": 5.0, "out": 25.0, "cache_read": 0.5, "cache_write": 6.25},
    "claude-sonnet-5": {"in": 2.0, "out": 10.0, "cache_read": 0.2, "cache_write": 2.5},
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0, "cache_read": 0.1, "cache_write": 1.25},
}

# Substrings of model names that share a price row (dated ids, provider prefixes).
# Order matters: the first match wins.
PRICE_ALIASES: list[tuple[str, str]] = [
    ("fable-5-1", "claude-fable-5-1"),
    ("fable", "claude-fable-5"),
    ("opus", "claude-opus-5"),
    ("sonnet", "claude-sonnet-5"),
    ("haiku", "claude-haiku-4-5"),
]

# TOOL span names that name a PKB task in their input. Claim/release are the strongest
# signal (the session owns the task); the rest show what it read or wrote.
TASK_TOOL_STRONG = ("claim_task", "release_task")
TASK_TOOL_WEAK = ("get_task", "update_task", "append", "edit_body", "update_body")
TASK_ID_RE = re.compile(
    r"^(?:[a-z][a-z0-9-]*[_-])?[0-9a-f]{8}$|^wf-[a-z0-9-]+$|^[a-z]+-[0-9a-f]{8}$"
)

CHANNEL_RE = re.compile(r'<channel source="(?:plugin:)?([a-z]+)')
# ``ListAgents`` output opens with "This session is <name> [<ref>]" -- the only place a
# Claude Code session states its own name. The ref is kept: names get reused across
# sessions in one day (two distinct ``ida-07`` sessions on 2026-09-12).
SELF_NAME_RE = re.compile(r"This session is ([^\s\[]+(?: \[[0-9a-f]+\])?)")
INJECTED_RE = re.compile(
    r"^\s*<(?:cross-session-message|channel|task-notification|system-reminder)"
)


class ConfigError(Exception):
    """A required input is missing or unusable."""


# --- HTTP / MCP proxy ------------------------------------------------------


def _mcp_headers(session_id: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {
        "User-Agent": "academicOps/0.10 (session-trace)",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    for id_var, secret_var in _ACCESS_TOKEN_PAIRS:
        cf_id = os.environ.get(id_var)
        cf_secret = os.environ.get(secret_var)
        if cf_id and cf_secret:
            headers["CF-Access-Client-Id"] = cf_id
            headers["CF-Access-Client-Secret"] = cf_secret
            break
    if session_id:
        headers["mcp-session-id"] = session_id
    return headers


def _parse_v1_url(url: str) -> tuple[str, str, dict[str, Any]]:
    if "/v1/projects" not in url:
        raise ConfigError(f"unsupported Phoenix URL path: {url}")
    mcp_url, rest = url.split("/v1/projects", 1)
    path_part, _, query_part = rest.partition("?")
    qs = urllib.parse.parse_qs(query_part, keep_blank_values=False)

    segments = [urllib.parse.unquote(s) for s in path_part.strip("/").split("/") if s]
    if not segments:
        args: dict[str, Any] = {"limit": int(qs["limit"][0]) if "limit" in qs else 100}
        if "cursor" in qs:
            args["cursor"] = qs["cursor"][0]
        return mcp_url, "getProjects", args

    if len(segments) == 2 and segments[1] == "sessions":
        args = {"project_identifier": segments[0]}
        args["limit"] = int(qs["limit"][0]) if "limit" in qs else 100
        if "cursor" in qs:
            args["cursor"] = qs["cursor"][0]
        return mcp_url, "listProjectSessions", args

    if len(segments) == 2 and segments[1] == "spans":
        args = {"project_identifier": segments[0]}
        if "limit" in qs:
            args["limit"] = int(qs["limit"][0])
        if "cursor" in qs:
            args["cursor"] = qs["cursor"][0]
        if "start_time" in qs:
            args["start_time"] = qs["start_time"][0]
        if "end_time" in qs:
            args["end_time"] = qs["end_time"][0]
        for list_key in ("attribute", "trace_id", "span_id", "span_kind"):
            if list_key in qs:
                args[list_key] = qs[list_key]
        return mcp_url, "getSpans", args

    raise ConfigError(f"unsupported Phoenix endpoint: {url}")


def _extract_jsonrpc_payload(raw_body: str, mcp_url: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_body)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    for line in raw_body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            try:
                payload = json.loads(line[5:].strip())
                if isinstance(payload, dict) and ("result" in payload or "error" in payload):
                    return payload
            except json.JSONDecodeError:
                continue
    raise ConfigError(f"unparseable MCP response from {mcp_url}: {raw_body[:400]}")


def _mcp_init_session(mcp_url: str) -> str:
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "academicOps-session-trace", "version": "0.10"},
        },
    }
    request = urllib.request.Request(
        mcp_url,
        data=json.dumps(init_payload).encode("utf-8"),
        headers=_mcp_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            session_id = response.headers.get("mcp-session-id")
            if not session_id:
                raise ConfigError(f"MCP initialize at {mcp_url} returned no mcp-session-id header")
            _MCP_SESSIONS[mcp_url] = session_id
            return session_id
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        raise ConfigError(f"HTTP {exc.code} from {mcp_url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ConfigError(f"cannot reach {mcp_url}: {exc.reason}") from exc


_SQL_IDENT_PART_RE = re.compile(r"^[A-Za-z_]\w*$")


def _sql_quote(value: str) -> str:
    if "\x00" in value:
        raise ConfigError("NUL byte is not permitted in Phoenix SQL literal")
    return "'" + value.replace("'", "''") + "'"


def _sql_attr_expr(attr_key: str) -> str:
    if not attr_key or "\x00" in attr_key:
        raise ConfigError(f"invalid attribute key: {attr_key!r}")
    flat_path = '$."' + attr_key.replace('"', '""') + '"'
    if "." not in attr_key:
        return f"(s.attributes ->> {_sql_quote(flat_path)})"
    parts = [
        part if _SQL_IDENT_PART_RE.match(part) else '"' + part.replace('"', '""') + '"'
        for part in attr_key.split(".")
    ]
    nested_path = "$." + ".".join(parts)
    return (
        f"COALESCE(s.attributes ->> {_sql_quote(nested_path)}, "
        f"s.attributes ->> {_sql_quote(flat_path)})"
    )


def _build_session_spans_code(tool_args: dict[str, Any]) -> str:
    """Build phoenix_execute code for indexed keyset-paged session.id span extraction.

    Phoenix's ``getSpans(attribute=['session.id:...'])`` sequentially scans unindexed JSONB
    attributes across the entire span table and times out on multi-hundred-thousand-row stores.
    Joining ``project_sessions -> projects -> traces -> spans`` uses relational indexes while:
      * preserving internal child spans on session traces whose ``session.id`` is NULL and
        excluding foreign-session spans on shared traces;
      * projecting NULL for rows exceeding SQLite's 256 KiB executeSql row cap and hydrating
        those spans whole via indexed ``getSpans(span_id=[...])`` in the same call; and
      * paging deterministically on monotonic ``s.id > cursor`` with ``LIMIT (page_limit + 1)``
        so both small caller limits and 4 MiB byte-capped partial SQL pages advance losslessly.
    """
    attrs = [str(a) for a in (tool_args.get("attribute") or [])]
    session_ids = [a.split(":", 1)[1] for a in attrs if a.startswith("session.id:")]
    other_attrs = [a for a in attrs if not a.startswith("session.id:")]
    unique_sids = list(dict.fromkeys(session_ids))
    if not unique_sids or any(not sid for sid in unique_sids):
        raise ConfigError("session.id attribute filter cannot be empty")
    if len(unique_sids) > 1:
        raise ConfigError(f"conflicting session.id attribute filters: {unique_sids}")

    project_id = str(tool_args["project_identifier"])
    session_id = unique_sids[0]
    requested_limit = int(tool_args.get("limit", PAGE_LIMIT))
    if requested_limit <= 0:
        raise ConfigError(f"span limit must be positive, got {requested_limit}")
    page_limit = min(requested_limit, SQL_PAGE_MAX_ROWS)

    raw_cursor = tool_args.get("cursor")
    if raw_cursor is None:
        cursor_id = 0
    else:
        try:
            cursor_id = int(str(raw_cursor))
        except ValueError as exc:
            raise ConfigError(f"invalid session span cursor: {raw_cursor!r}") from exc
        if cursor_id < 0:
            raise ConfigError(f"invalid negative session span cursor: {raw_cursor!r}")

    q_proj = _sql_quote(project_id)
    q_sid = _sql_quote(session_id)
    sid_expr = _sql_attr_expr("session.id")
    where_clauses = [
        f"(p.name = {q_proj} OR p.graphql_node_id = {q_proj})",
        f"ps.session_id = {q_sid}",
        f"s.id > {cursor_id}",
        f"({sid_expr} IS NULL OR {sid_expr} = ps.session_id)",
    ]
    if "start_time" in tool_args:
        where_clauses.append(f"s.start_time >= {_sql_quote(str(tool_args['start_time']))}")
    if "end_time" in tool_args:
        where_clauses.append(f"s.start_time < {_sql_quote(str(tool_args['end_time']))}")
    for col_expr, arg_key in (
        ("t.trace_id", "trace_id"),
        ("s.span_id", "span_id"),
        ("s.span_kind", "span_kind"),
    ):
        values = tool_args.get(arg_key)
        if values:
            quoted_vals = ", ".join(_sql_quote(str(v)) for v in values)
            where_clauses.append(f"{col_expr} IN ({quoted_vals})")
    for raw_attr in other_attrs:
        if ":" not in raw_attr:
            raise ConfigError(f"invalid attribute filter (expected key:value): {raw_attr!r}")
        attr_key, attr_val = raw_attr.split(":", 1)
        if not attr_key:
            raise ConfigError(f"empty key in attribute filter: {raw_attr!r}")
        where_clauses.append(f"{_sql_attr_expr(attr_key)} = {_sql_quote(attr_val)}")

    where_sql = "\n  AND ".join(where_clauses)
    sql = (
        "SELECT\n"
        "  s.id,\n"
        "  s.graphql_node_id,\n"
        "  t.trace_id,\n"
        "  s.span_id,\n"
        "  s.parent_id,\n"
        "  s.name,\n"
        "  s.span_kind,\n"
        "  s.start_time,\n"
        "  s.end_time,\n"
        "  s.status_code,\n"
        "  s.status_message,\n"
        f"  CASE WHEN LENGTH(s.attributes) <= {SQL_ATTR_INLINE_BYTES} THEN s.attributes ELSE NULL END AS attributes,\n"
        f"  CASE WHEN LENGTH(s.events) <= {SQL_EVENTS_INLINE_BYTES} THEN s.events ELSE NULL END AS events,\n"
        f"  CASE WHEN LENGTH(s.attributes) > {SQL_ATTR_INLINE_BYTES} OR LENGTH(s.events) > {SQL_EVENTS_INLINE_BYTES} THEN 1 ELSE 0 END AS oversized\n"
        "FROM project_sessions ps\n"
        "JOIN projects p ON ps.project_id = p.id\n"
        "JOIN traces t ON t.project_session_rowid = ps.id\n"
        "JOIN spans s ON s.trace_rowid = t.id\n"
        f"WHERE {where_sql}\n"
        "ORDER BY s.id ASC\n"
        f"LIMIT {page_limit + 1}"
    )

    return (
        "import json\n"
        "def _norm_ts(val):\n"
        "    if not val:\n"
        "        return val\n"
        "    s = str(val).strip().replace(' ', 'T', 1)\n"
        "    if s.endswith('Z'):\n"
        "        return s[:-1] + '+00:00'\n"
        "    t_pos = s.find('T')\n"
        "    tail = s[t_pos + 1:] if t_pos >= 0 else s\n"
        "    if '+' not in tail and '-' not in tail:\n"
        "        return s + '+00:00'\n"
        "    return s\n"
        "def _flatten(obj, prefix=''):\n"
        "    out = {}\n"
        "    if not isinstance(obj, dict):\n"
        "        return out\n"
        "    for k, v in obj.items():\n"
        "        key = f'{prefix}.{k}' if prefix else str(k)\n"
        "        if isinstance(v, dict) and v:\n"
        "            out.update(_flatten(v, key))\n"
        "        elif not isinstance(v, dict):\n"
        "            out[key] = v\n"
        "    return out\n"
        f"page = await call_tool('executeSql', {{'sql': {json.dumps(sql)}}})\n"
        "if not isinstance(page, dict) or 'error' in page:\n"
        "    raise RuntimeError(f'executeSql failed: {page}')\n"
        "raw_rows = page.get('rows')\n"
        "if not isinstance(raw_rows, list):\n"
        "    raise RuntimeError(f'executeSql returned invalid rows: {page}')\n"
        f"has_more = len(raw_rows) > {page_limit} or bool(page.get('row_count_is_partial'))\n"
        f"rows = raw_rows[:{page_limit}]\n"
        "oversized_ids = [str(r[3]) for r in rows if r[13]]\n"
        "hydrated = {}\n"
        "if oversized_ids:\n"
        f"    h_res = await call_tool('getSpans', {{'project_identifier': {json.dumps(project_id)}, 'span_id': oversized_ids, 'limit': len(oversized_ids)}})\n"
        "    if not isinstance(h_res, dict) or 'error' in h_res or not isinstance(h_res.get('data'), list):\n"
        "        raise RuntimeError(f'getSpans hydration failed: {h_res}')\n"
        "    for sp in h_res['data']:\n"
        "        if isinstance(sp, dict):\n"
        "            sid = (sp.get('context') or {}).get('span_id') or sp.get('span_id')\n"
        "            if sid:\n"
        "                hydrated[str(sid)] = sp\n"
        "data = []\n"
        "for r in rows:\n"
        "    span_id_val = str(r[3])\n"
        "    if r[13]:\n"
        "        if span_id_val not in hydrated:\n"
        "            raise RuntimeError(f'getSpans hydration missing span_id={span_id_val}')\n"
        "        data.append(hydrated[span_id_val])\n"
        "        continue\n"
        "    attrs_obj = json.loads(r[11]) if r[11] else {}\n"
        "    events_obj = json.loads(r[12]) if r[12] else []\n"
        "    data.append({\n"
        "        'id': r[1] or str(r[0]),\n"
        "        'name': r[5],\n"
        "        'context': {'trace_id': r[2], 'span_id': span_id_val},\n"
        "        'span_kind': r[6],\n"
        "        'parent_id': r[4],\n"
        "        'start_time': _norm_ts(r[7]),\n"
        "        'end_time': _norm_ts(r[8]),\n"
        "        'status_code': r[9] or 'UNSET',\n"
        "        'status_message': r[10] or '',\n"
        "        'attributes': _flatten(attrs_obj),\n"
        "        'events': events_obj,\n"
        "    })\n"
        "next_cursor = str(rows[-1][0]) if (has_more and rows) else None\n"
        "return {'data': data, 'next_cursor': next_cursor}\n"
    )


def get_json(url: str) -> Any:
    mcp_url, tool_name, tool_args = _parse_v1_url(url)
    if tool_name == "getSpans" and any(
        isinstance(a, str) and a.startswith("session.id:")
        for a in (tool_args.get("attribute") or [])
    ):
        tool_label = "executeSql"
        code = _build_session_spans_code(tool_args)
    else:
        tool_label = tool_name
        code = f"return await call_tool({json.dumps(tool_name)}, {json.dumps(tool_args)})"
    session_id = _MCP_SESSIONS.get(mcp_url) or _mcp_init_session(mcp_url)
    call_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "phoenix_execute",
            "arguments": {"code": code},
        },
    }
    request = urllib.request.Request(
        mcp_url,
        data=json.dumps(call_payload).encode("utf-8"),
        headers=_mcp_headers(session_id),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            raw_body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        raise ConfigError(f"HTTP {exc.code} from {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ConfigError(f"cannot reach {url}: {exc.reason}") from exc

    rpc = _extract_jsonrpc_payload(raw_body, mcp_url)
    if "error" in rpc:
        raise ConfigError(f"MCP error from {mcp_url}: {rpc['error']}")
    result = rpc.get("result") or {}
    content = result.get("content") or []
    text = "".join(item.get("text", "") for item in content if isinstance(item, dict)).strip()
    if result.get("isError"):
        raise ConfigError(f"Phoenix MCP tool {tool_label} failed: {text}")
    try:
        parsed = json.loads(text) if text else {}
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Phoenix MCP tool {tool_label} returned non-JSON: {text[:400]}") from exc
    if isinstance(parsed, dict) and "error" in parsed:
        raise ConfigError(f"Phoenix MCP tool {tool_label} failed: {parsed['error']}")
    return parsed


def resolve_base_url(explicit: str | None) -> str:
    candidate = (explicit or os.environ.get(BASE_URL_ENV_VAR, "")).strip()
    if not candidate:
        raise ConfigError(f"no Phoenix base URL. Pass --base-url, or set {BASE_URL_ENV_VAR}")
    return candidate.rstrip("/")


def resolve_project(base_url: str, wanted: str | None) -> tuple[str, str]:
    wanted = (wanted or os.environ.get(PROJECT_ENV_VAR, "")).strip()
    if not wanted:
        raise ConfigError(f"no Phoenix project. Pass --project, or set {PROJECT_ENV_VAR}")
    projects = get_json(f"{base_url}/v1/projects").get("data", [])
    for project in projects:
        if wanted in (project.get("name"), project.get("id")):
            return str(project["id"]), str(project["name"])
    names = ", ".join(str(p.get("name")) for p in projects) or "none"
    raise ConfigError(f"project {wanted!r} not found; Phoenix has: {names}")


def page_spans(base_url: str, project_id: str, filters: list[tuple[str, str]]) -> list[Span]:
    """Page ``/v1/projects/{id}/spans`` to exhaustion under the given filters."""
    spans: list[Span] = []
    cursor: str | None = None
    while True:
        query = [*filters, ("limit", str(PAGE_LIMIT))]
        if cursor:
            query.append(("cursor", cursor))
        url = f"{base_url}/v1/projects/{urllib.parse.quote(project_id, safe='')}/spans?{urllib.parse.urlencode(query)}"
        payload = get_json(url)
        spans.extend(payload.get("data", []))
        cursor = payload.get("next_cursor")
        if not cursor:
            return spans


# --- time ------------------------------------------------------------------


def parse_when(value: str, tz: timezone) -> datetime:
    """``2026-09-12``, ``2026-09-12 00:00``, or ISO-8601; naive values take ``tz``."""
    text = value.strip().replace(" ", "T")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ConfigError(f"cannot parse time {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(UTC)


def parse_tz(value: str) -> timezone:
    match = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", value.strip())
    if not match:
        raise ConfigError(f"--tz must look like +10:00, got {value!r}")
    sign = 1 if match.group(1) == "+" else -1
    return timezone(sign * timedelta(hours=int(match.group(2)), minutes=int(match.group(3))))


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- pricing ---------------------------------------------------------------


def price_row(model: str, prices: dict[str, dict[str, float]]) -> dict[str, float] | None:
    if model in prices:
        return prices[model]
    lowered = model.lower()
    for needle, canonical in PRICE_ALIASES:
        if needle in lowered and canonical in prices:
            return prices[canonical]
    return None


def cost_usd(tokens: dict[str, int], row: dict[str, float] | None) -> float:
    if not row:
        return 0.0
    return (
        tokens["in"] * row["in"]
        + tokens["out"] * row["out"]
        + tokens["cache_read"] * row["cache_read"]
        + tokens["cache_write"] * row["cache_write"]
    ) / 1e6


# --- span helpers ----------------------------------------------------------


def attr(span: Span, key: str, default: Any = None) -> Any:
    return span.get("attributes", {}).get(key, default)


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def session_of(span: Span) -> str:
    return str(attr(span, "session.id") or attr(span, "agent.id") or "(no session)")


def tokens_of(span: Span) -> dict[str, int] | None:
    prompt = attr(span, "llm.token_count.prompt")
    completion = attr(span, "llm.token_count.completion")
    if prompt is None and completion is None:
        return None
    cache_read = as_int(attr(span, "llm.token_count.prompt_details.cache_read"))
    cache_write = as_int(attr(span, "llm.token_count.prompt_details.cache_write"))
    return {
        "in": max(as_int(prompt) - cache_read - cache_write, 0),
        "out": as_int(completion),
        "cache_read": cache_read,
        "cache_write": cache_write,
    }


def dedupe_llm(spans: list[Span]) -> tuple[list[Span], int]:
    """Drop exact re-emissions: same session, start_time and output. Keep the max counts."""
    best: dict[tuple[str, str, str], Span] = {}
    for span in spans:
        key = (session_of(span), str(span.get("start_time")), str(attr(span, "output.value", "")))
        current = best.get(key)
        if current is None or as_int(attr(span, "llm.token_count.total")) > as_int(
            attr(current, "llm.token_count.total")
        ):
            best[key] = span
    kept = sorted(best.values(), key=lambda s: str(s.get("start_time")))
    return kept, len(spans) - len(kept)


def task_ids_in(text: str) -> list[str]:
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    found: list[str] = []
    for key in ("id", "task_id", "parent_id", "parent"):
        value = payload.get(key)
        if isinstance(value, str) and TASK_ID_RE.match(value):
            found.append(value)
    for value in payload.get("ids", []) if isinstance(payload.get("ids"), list) else []:
        if isinstance(value, str) and TASK_ID_RE.match(value):
            found.append(value)
    return found


# --- labelling -------------------------------------------------------------


def load_labels(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    file = Path(path).expanduser()
    if not file.exists():
        return {}
    data = json.loads(file.read_text())
    return {str(k): str(v) for k, v in data.items()}


def label_session(
    sid: str, chains: list[Span], tools: list[Span], agents: list[Span], labels: dict[str, str]
) -> str:
    """Best available name for a session, in falling order of authority.

    1. the labels file; 2. the session's own name as printed by ``ListAgents``;
    3. the channel it fronts (telegram/discord face); 4. the first human-typed prompt
    in the window; 5. ``agy polecat``. The dispatched subagent kinds are appended.
    """
    for prefix, label in labels.items():
        if sid.startswith(prefix):
            return label
    label = ""
    for span in tools:
        if span.get("name") == "ListAgents" and (
            m := SELF_NAME_RE.search(str(attr(span, "output.value", "")))
        ):
            label = m.group(1)
            break
    if not label:
        for span in chains:
            if m := CHANNEL_RE.search(str(attr(span, "input.value", ""))):
                label = f"{m.group(1)} face"
                break
    if not label:
        for span in chains:
            text = str(attr(span, "input.value") or "")
            if text and not INJECTED_RE.match(text):
                label = '"' + " ".join(text.split())[:40] + '"'
                break
    if not label and any(s.get("name") == "agy session" for s in chains):
        label = "agy polecat"
    dispatched = sorted(
        {str(attr(s, "agent.name")).split(":")[-1] for s in agents if attr(s, "agent.name")}
    )
    if dispatched:
        label = f"{label} +{','.join(dispatched[:3])}".strip()
    hosts = sorted({str(attr(s, "host.name")) for s in chains + agents if attr(s, "host.name")})
    return f"{label or '(unlabelled)'} @{'/'.join(hosts)}" if hosts else (label or "(unlabelled)")


# --- aggregation -----------------------------------------------------------


def new_bucket() -> dict[str, Any]:
    return {
        "calls": 0,
        "models": defaultdict(int),
        "tokens": {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0},
        "cost": 0.0,
        "first": None,
        "last": None,
    }


def add(bucket: dict[str, Any], span: Span, tokens: dict[str, int] | None, cost: float) -> None:
    bucket["calls"] += 1
    bucket["models"][str(attr(span, "llm.model_name", "?"))] += 1
    if tokens:
        for k, v in tokens.items():
            bucket["tokens"][k] += v
    bucket["cost"] += cost
    started = str(span.get("start_time"))
    bucket["first"] = min(filter(None, [bucket["first"], started]))
    bucket["last"] = max(filter(None, [bucket["last"], started]))


def build_task_timeline(tool_spans: list[Span]) -> dict[str, list[tuple[str, str, bool]]]:
    """Per session: ``(start_time, task_id, strong)`` for every task-naming tool call."""
    timeline: dict[str, list[tuple[str, str, bool]]] = defaultdict(list)
    for span in tool_spans:
        name = str(span.get("name") or attr(span, "tool.name") or "")
        strong = any(t in name for t in TASK_TOOL_STRONG)
        if not strong and not any(t in name for t in TASK_TOOL_WEAK):
            continue
        for task_id in task_ids_in(str(attr(span, "input.value", ""))):
            timeline[session_of(span)].append((str(span.get("start_time")), task_id, strong))
    for sid in timeline:
        timeline[sid].sort()
    return timeline


def task_summary(entries: list[tuple[str, str, bool]]) -> str:
    strong = [t for _, t, s in entries if s]
    weak = [t for _, t, s in entries if not s]
    ordered: list[str] = []
    for t in strong + weak:
        if t not in ordered:
            ordered.append(t)
    if not ordered:
        return "unknown"
    shown = ordered[:3]
    more = f" +{len(ordered) - 3}" if len(ordered) > 3 else ""
    return ",".join(shown) + more


def task_at(entries: list[tuple[str, str, bool]], when: str) -> str:
    """The task most recently claimed (strong) or, failing that, read before ``when``."""
    last_strong = last_weak = None
    for started, task_id, strong in entries:
        if started > when:
            break
        if strong:
            last_strong = task_id
        else:
            last_weak = task_id
    return last_strong or last_weak or "unknown"


def aggregate(
    llm: list[Span],
    tools: list[Span],
    chains: list[Span],
    agents: list[Span],
    prices: dict[str, dict[str, float]],
    labels: dict[str, str],
    by: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    timeline = build_task_timeline(tools)
    chains_by: dict[str, list[Span]] = defaultdict(list)
    for s in sorted(chains, key=lambda s: str(s.get("start_time"))):
        chains_by[session_of(s)].append(s)
    agents_by: dict[str, list[Span]] = defaultdict(list)
    for s in agents:
        agents_by[session_of(s)].append(s)
    tools_by: dict[str, list[Span]] = defaultdict(list)
    for s in tools:
        tools_by[session_of(s)].append(s)

    buckets: dict[tuple[str, str], dict[str, Any]] = defaultdict(new_bucket)
    unpriced: dict[str, int] = defaultdict(int)
    uncounted: dict[str, int] = defaultdict(int)
    total = new_bucket()
    for span in llm:
        sid = session_of(span)
        model = str(attr(span, "llm.model_name", "?"))
        tokens = tokens_of(span)
        row = price_row(model, prices)
        if tokens is None:
            uncounted[model] += 1
        elif row is None:
            unpriced[model] += 1
        cost = cost_usd(tokens, row) if tokens else 0.0
        task = (
            task_at(timeline.get(sid, []), str(span.get("start_time")))
            if by == "task"
            else task_summary(timeline.get(sid, []))
        )
        add(buckets[(sid, task)], span, tokens, cost)
        add(total, span, tokens, cost)

    rows: list[dict[str, Any]] = []
    for (sid, task), bucket in buckets.items():
        models = sorted(bucket["models"].items(), key=lambda kv: -kv[1])
        rows.append(
            {
                "session": sid,
                "role": label_session(
                    sid,
                    chains_by.get(sid, []),
                    tools_by.get(sid, []),
                    agents_by.get(sid, []),
                    labels,
                ),
                "task": task,
                "model": models[0][0] + (f" +{len(models) - 1}" if len(models) > 1 else ""),
                "calls": bucket["calls"],
                **bucket["tokens"],
                "cost": round(bucket["cost"], 2),
                "first": bucket["first"],
                "last": bucket["last"],
            }
        )
    rows.sort(key=lambda r: (-r["cost"], -r["calls"], r["session"]))
    meta = {
        "calls": total["calls"],
        "tokens": total["tokens"],
        "cost": round(total["cost"], 2),
        "unpriced_models": dict(unpriced),
        "uncounted_models": dict(uncounted),
    }
    return rows, meta


# --- rendering -------------------------------------------------------------


def fmt_k(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}M"
    if n >= 1_000:
        return f"{n / 1e3:.0f}k"
    return str(n)


def render(
    rows: list[dict[str, Any]],
    meta: dict[str, Any],
    window: tuple[datetime, datetime],
    project: str,
    dropped: int,
    width: int,
) -> str:
    head = f"{'session':<8} {'agent/role':<{width}} {'task':<24} {'model':<16} {'calls':>5} {'in':>7} {'out':>7} {'cache_rd':>8} {'cache_wr':>8} {'USD':>8}"
    lines = [
        f"Token cost by session -- Phoenix project {project!r}, {iso(window[0])} -> {iso(window[1])}",
        f"{meta['calls']} LLM calls after dropping {dropped} duplicate spans; total est. US${meta['cost']:.2f}",
        "",
        head,
        "-" * len(head),
    ]
    for r in rows:
        role = r["role"] if len(r["role"]) <= width else r["role"][: width - 1] + "~"
        task = r["task"] if len(r["task"]) <= 24 else r["task"][:23] + "~"
        lines.append(
            f"{r['session'][:8]:<8} {role:<{width}} {task:<24} {r['model'][:16]:<16} {r['calls']:>5} "
            f"{fmt_k(r['in']):>7} {fmt_k(r['out']):>7} {fmt_k(r['cache_read']):>8} {fmt_k(r['cache_write']):>8} {r['cost']:>8.2f}"
        )
    t = meta["tokens"]
    lines.append("-" * len(head))
    lines.append(
        f"{'total':<8} {'':<{width}} {'':<24} {'':<16} {meta['calls']:>5} {fmt_k(t['in']):>7} {fmt_k(t['out']):>7} {fmt_k(t['cache_read']):>8} {fmt_k(t['cache_write']):>8} {meta['cost']:>8.2f}"
    )
    if meta["unpriced_models"]:
        lines.append(f"unpriced models (cost 0): {meta['unpriced_models']}")
    if meta["uncounted_models"]:
        lines.append(f"spans without token counts (calls only): {meta['uncounted_models']}")
    lines.append(
        "in = prompt - cache_read - cache_write; prices USD/M in PRICES (override --prices)"
    )
    return "\n".join(lines)


def render_markdown(
    rows: list[dict[str, Any]],
    meta: dict[str, Any],
    window: tuple[datetime, datetime],
    project: str,
    dropped: int,
) -> str:
    lines = [
        f"Phoenix project `{project}`, {iso(window[0])} -> {iso(window[1])}: {meta['calls']} LLM calls "
        f"({dropped} duplicate spans dropped), total est. US${meta['cost']:.2f}",
        "",
        "| session | agent/role | task | model | calls | in | out | cache_rd | cache_wr | USD |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['session'][:8]} | {r['role']} | {r['task']} | {r['model']} | {r['calls']} | {fmt_k(r['in'])} | "
            f"{fmt_k(r['out'])} | {fmt_k(r['cache_read'])} | {fmt_k(r['cache_write'])} | {r['cost']:.2f} |"
        )
    t = meta["tokens"]
    lines.append(
        f"| **total** | | | | {meta['calls']} | {fmt_k(t['in'])} | {fmt_k(t['out'])} | {fmt_k(t['cache_read'])} | {fmt_k(t['cache_write'])} | **{meta['cost']:.2f}** |"
    )
    if meta["unpriced_models"]:
        lines.append(f"\nUnpriced models (cost 0): `{meta['unpriced_models']}`")
    if meta["uncounted_models"]:
        lines.append(f"\nSpans without token counts (calls only): `{meta['uncounted_models']}`")
    return "\n".join(lines)


# --- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--since", required=True, help="window start (ISO, or 'YYYY-MM-DD HH:MM' in --tz)"
    )
    parser.add_argument("--until", help="window end (default: now)")
    parser.add_argument(
        "--tz", default="+00:00", help="offset for naive --since/--until, e.g. +10:00 for AEST"
    )
    parser.add_argument(
        "--by", choices=("session", "task"), default="session", help="row grain (default session)"
    )
    parser.add_argument("--session", help="only this session id (prefix ok)")
    parser.add_argument("--labels", help="JSON file: session-id prefix -> agent/role label")
    parser.add_argument(
        "--prices", help="JSON file: model -> {in,out,cache_read,cache_write} USD/M"
    )
    parser.add_argument("--project", help=f"Phoenix project (fallback ${PROJECT_ENV_VAR})")
    parser.add_argument("--base-url", help=f"Phoenix base URL (fallback ${BASE_URL_ENV_VAR})")
    parser.add_argument("--json", action="store_true", help="emit rows + meta as JSON")
    parser.add_argument("--markdown", action="store_true", help="emit a markdown table")
    parser.add_argument("--role-width", type=int, default=34, help="agent/role column width")
    parser.add_argument("--save-spans", help="write the fetched spans to this JSON file")
    parser.add_argument(
        "--from-file", help="read spans from a --save-spans file instead of Phoenix"
    )
    args = parser.parse_args(argv)

    try:
        tz = parse_tz(args.tz)
        since = parse_when(args.since, tz)
        until = parse_when(args.until, tz) if args.until else datetime.now(UTC)
        prices = dict(PRICES)
        if args.prices:
            prices.update(json.loads(Path(args.prices).expanduser().read_text()))
        labels = load_labels(args.labels)

        if args.from_file:
            saved = json.loads(Path(args.from_file).expanduser().read_text())
            project_name = str(saved.get("project", "(file)"))
            # Report the window the spans were fetched for, not the time of the rerun,
            # so an offline table carries the same header as the live one.
            if saved.get("window"):
                since, until = (parse_when(w, UTC) for w in saved["window"])
            llm_raw, tools, chains, agents = (
                list(saved.get(k, [])) for k in ("llm", "tools", "chains", "agents")
            )
        else:
            base_url = resolve_base_url(args.base_url)
            project_id, project_name = resolve_project(base_url, args.project)
            window = [("start_time", iso(since)), ("end_time", iso(until))]
            llm_raw = page_spans(base_url, project_id, [("span_kind", "LLM"), *window])
            tools = page_spans(base_url, project_id, [("span_kind", "TOOL"), *window])
            chains = page_spans(base_url, project_id, [("span_kind", "CHAIN"), *window])
            agents = page_spans(base_url, project_id, [("span_kind", "AGENT"), *window])
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    if args.session:
        keep = lambda s: session_of(s).startswith(args.session)  # noqa: E731
        llm_raw, tools, chains, agents = (
            list(filter(keep, xs)) for xs in (llm_raw, tools, chains, agents)
        )
    if args.save_spans:
        Path(args.save_spans).write_text(
            json.dumps(
                {
                    "project": project_name,
                    "window": [iso(since), iso(until)],
                    "llm": llm_raw,
                    "tools": tools,
                    "chains": chains,
                    "agents": agents,
                }
            )
        )

    llm, dropped = dedupe_llm(llm_raw)
    if not llm:
        print(
            f"no LLM spans in {iso(since)} -> {iso(until)} for project {project_name!r}",
            file=sys.stderr,
        )
        return EXIT_EMPTY

    rows, meta = aggregate(llm, tools, chains, agents, prices, labels, args.by)
    meta.update(
        {
            "window": [iso(since), iso(until)],
            "project": project_name,
            "duplicates_dropped": dropped,
            "by": args.by,
        }
    )
    if args.json:
        print(json.dumps({"rows": rows, "meta": meta}, indent=1))
    elif args.markdown:
        print(render_markdown(rows, meta, (since, until), project_name, dropped))
    else:
        print(render(rows, meta, (since, until), project_name, dropped, args.role_width))
    return 0


if __name__ == "__main__":
    sys.exit(main())
