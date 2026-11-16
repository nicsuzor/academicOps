#!/usr/bin/env python3
"""Render one session's spans from an Arize Phoenix span store as a markdown transcript.

The transcript is for reading how a session reached a decision: a table of contents with
one header per turn, and within each turn, in time order, the prompt, every model call,
every tool call and the reply. Bulky payloads (prompts, tool input and output, model
context) sit in folded ``<details>`` sections and are never truncated. Every turn, model
call and tool call carries its wall-clock duration; every model call its tokens and
estimated cost; the turns and the session carry totals.

Fetch
    One keyset-paged ``GET /v1/projects/{project}/spans?attribute=session.id:<id>``
    sequence routed via indexed ``project_sessions -> traces -> spans`` lookup (hydrating
    oversized span payloads whole via indexed ``span_id`` lookup so nothing is truncated).
    A session slug (a prefix of the id) is resolved through the project's sessions listing;
    a 32-hex trace id through one ``trace_id=`` fetch. With ``--from-file`` the spans come
    from a saved payload instead (a JSON list, or an object with ``data``), so spans
    fetched another way can be rendered offline.

Assemble
    * Turns are clusters of root spans whose time windows overlap. Two emitters often
      each open a root for the same turn; clustering joins them without relying on
      either.
    * Tool calls are deduplicated on their call id (``tool.call_id``, ``tool_use_id``,
      ``tool.id``, ``gen_ai.tool.call.id``). Child spans of a tool call that carry no id
      of their own (execution, permission wait) fold into it. Input and output come from
      whichever span holds them whole; duration runs from the earliest start to the
      latest end in the group.
    * Model calls are ``LLM`` spans, deduplicated on response id where present, else on
      start time and output.

Metrics
    Tokens are normalised to fresh input, cache read, cache write and output across
    attribute conventions: Claude Code's native spans (``input_tokens`` excludes cache
    tokens), OpenInference (``llm.token_count.prompt`` includes them) and OpenTelemetry
    GenAI (``gen_ai.usage.*``, read as including them). Prices are the table in
    ``phoenix_token_cost.py``, overridable with ``--prices``; unpriced models cost 0 and
    are named in the header. The dollar figure is comparable spend, not an invoice.

Configuration is flags or environment only: ``--base-url`` or ``$PHOENIX_MCP_URL``;
``--project`` or ``$PHOENIX_MCP_PROJECT``. No fallback values. Standard library only.

Examples::

    uv run python phoenix_transcript.py <slug> --out ./<slug>.transcript.md --sanitize-paths
    uv run python phoenix_transcript.py <session-uuid>
    uv run python phoenix_transcript.py <32-hex-trace-id>
    uv run python phoenix_transcript.py <slug> --from-file spans.json
    uv run python phoenix_transcript.py --since 2026-11-14T08:45:32Z --out ./sweep --sanitize-paths
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
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phoenix_token_cost as _ptc  # noqa: E402
from phoenix_token_cost import (  # noqa: E402
    _MCP_SESSIONS,
    BASE_URL_ENV_VAR,
    HTTP_TIMEOUT,
    PRICES,
    PROJECT_ENV_VAR,
    ConfigError,
    _extract_jsonrpc_payload,
    _mcp_headers,
    _mcp_init_session,
    cost_usd,
    get_json,
    price_row,
    resolve_base_url,
)

UI_BASE_URL_ENV_VAR = "PHOENIX_UI_URL"

PAGE_LIMIT = 1000
SESSION_PAGE_LIMIT = 100
SLOWEST_STEPS = 10
HINT_CHARS = 72
DETAIL_CHARS = 240

EXIT_CONFIG = 2
EXIT_EMPTY = 1

TRACE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

CALL_ID_KEYS = ("tool.call_id", "tool_use_id", "tool.id", "gen_ai.tool.call.id")
TOOL_NAME_KEYS = ("tool.name", "gen_ai.tool.name", "tool_name")
TOOL_INPUT_KEYS = ("input.value", "gen_ai.tool.call.arguments", "tool_input")
TOOL_OUTPUT_KEYS = ("output.value", "gen_ai.tool.call.result", "tool_output")
MODEL_KEYS = ("llm.model_name", "gen_ai.response.model", "gen_ai.request.model", "model")
RESPONSE_ID_KEYS = ("gen_ai.response.id", "request_id", "llm.response.id")
PROMPT_KEYS = ("input.value", "user_prompt", "gen_ai.prompt")
NEW_CONTEXT_KEYS = ("new_context",)
TURN_KINDS = ("CHAIN", "AGENT")

Span = dict[str, Any]


# --- attribute access --------------------------------------------------------


def attr(span: Span, key: str) -> Any:
    """A span attribute by dotted key, whether the store returns it flat or nested."""
    attributes = span.get("attributes") or {}
    if key in attributes:
        return attributes[key]
    node: Any = attributes
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def first_attr(span: Span, keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = attr(span, key)
        if value not in (None, ""):
            return value
    return None


def as_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def span_id(span: Span) -> str:
    return str((span.get("context") or {}).get("span_id") or span.get("span_id") or "")


def trace_id(span: Span) -> str:
    return str((span.get("context") or {}).get("trace_id") or span.get("trace_id") or "")


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def start_of(span: Span) -> datetime:
    return parse_time(span.get("start_time")) or datetime.min.replace(tzinfo=UTC)


def end_of(span: Span) -> datetime:
    return parse_time(span.get("end_time")) or start_of(span)


def ms_between(start: datetime, end: datetime) -> float:
    return max(0.0, (end - start).total_seconds() * 1000.0)


# --- HTTP --------------------------------------------------------------------


def resolve_project(explicit: str | None) -> str:
    project = (explicit or os.environ.get(PROJECT_ENV_VAR, "")).strip()
    if not project:
        raise ConfigError(f"no Phoenix project. Pass --project, or set {PROJECT_ENV_VAR}")
    return project


def resolve_ui_base_url(explicit: str | None, base_url: str | None) -> str | None:
    """Resolve Phoenix UI base URL from explicit flag, env var, or derived from base URL."""
    candidate = (explicit or os.environ.get(UI_BASE_URL_ENV_VAR, "")).strip()
    if candidate:
        return candidate.rstrip("/")
    if not base_url:
        return None
    parsed = urllib.parse.urlparse(base_url.rstrip("/"))
    netloc = parsed.netloc
    path = parsed.path
    if netloc.startswith("mcp."):
        netloc = "phoenix." + netloc[4:]
        if path == "/mcp":
            path = ""
        elif path.startswith("/mcp/"):
            path = path[4:]
    return urllib.parse.urlunparse((parsed.scheme, netloc, path.rstrip("/"), "", "", ""))


def paged(base_url: str, path: str, query: list[tuple[str, str]]) -> tuple[list[Any], int]:
    rows: list[Any] = []
    cursor: str | None = None
    pages = 0
    while True:
        page_query = [*query, *([("cursor", cursor)] if cursor else [])]
        payload = get_json(f"{base_url}{path}?{urllib.parse.urlencode(page_query)}")
        pages += 1
        rows.extend(payload.get("data", []))
        cursor = payload.get("next_cursor")
        if not cursor:
            return rows, pages


def project_path(project: str, tail: str) -> str:
    return f"/v1/projects/{urllib.parse.quote(project, safe='')}/{tail}"


def phoenix_execute_code(base_url: str, code: str) -> Any:
    """Execute a server-side Python snippet via the Phoenix MCP ``phoenix_execute`` tool."""
    mcp_url = base_url.split("/v1/projects", 1)[0].rstrip("/")
    mcp_sid = _MCP_SESSIONS.get(mcp_url) or _mcp_init_session(mcp_url)
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
        headers=_mcp_headers(mcp_sid),
        method="POST",
    )
    try:
        with _ptc.urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            raw_body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        raise ConfigError(f"HTTP {exc.code} from {mcp_url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ConfigError(f"cannot reach {mcp_url}: {exc.reason}") from exc

    rpc = _extract_jsonrpc_payload(raw_body, mcp_url)
    if "error" in rpc:
        raise ConfigError(f"MCP error from {mcp_url}: {rpc['error']}")
    result = rpc.get("result") or {}
    content = result.get("content") or []
    text = "".join(item.get("text", "") for item in content if isinstance(item, dict)).strip()
    if result.get("isError"):
        raise ConfigError(f"Phoenix MCP phoenix_execute failed: {text}")
    try:
        return json.loads(text) if text else {}
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Phoenix MCP phoenix_execute returned non-JSON: {text[:400]}") from exc


def fetch_session_spans(base_url: str, project: str, session_id: str) -> tuple[list[Span], int]:
    return paged(
        base_url,
        project_path(project, "spans"),
        [("attribute", f"session.id:{session_id}"), ("limit", str(PAGE_LIMIT))],
    )


def resolve_session_id(base_url: str, project: str, ident: str) -> str:
    """A full session ID / conversation ID from a full ID, a slug (ID prefix), or a 32-hex trace ID."""
    if UUID_RE.match(ident):
        return ident
    if TRACE_ID_RE.match(ident):
        spans, _ = paged(
            base_url, project_path(project, "spans"), [("trace_id", ident), ("limit", "100")]
        )
        found = sorted({str(attr(s, "session.id")) for s in spans if attr(s, "session.id")})
        if len(found) == 1:
            return found[0]
        if not found:
            raise ConfigError(f"trace {ident} holds no spans with a session.id")
        raise ConfigError(f"trace {ident} spans several sessions: {', '.join(found)}")
    sessions, _ = paged(
        base_url, project_path(project, "sessions"), [("limit", str(SESSION_PAGE_LIMIT))]
    )
    matches = sorted(
        {s["session_id"] for s in sessions if str(s.get("session_id", "")).startswith(ident)}
    )
    if len(matches) == 1:
        return matches[0]
    if not matches:
        # Not every emitter registers a Phoenix session; treat the input as the id.
        return ident
    raise ConfigError(f"slug {ident!r} matches several sessions: {', '.join(matches)}")


def load_spans_from_file(path: Path) -> list[Span]:
    payload = json.loads(path.read_text())
    spans = payload.get("data", []) if isinstance(payload, dict) else payload
    if not isinstance(spans, list):
        raise ConfigError(f"{path}: expected a JSON list of spans or an object with 'data'")
    return spans


# --- model -------------------------------------------------------------------


@dataclass
class Step:
    kind: str  # "model", "tool", "other"
    start: datetime
    end: datetime
    spans: list[Span]
    title: str = ""
    hint: str = ""
    detail: str = ""
    action: str = ""
    agent: str = ""
    error: str = ""
    model: str = ""
    tokens: dict[str, int] = field(default_factory=dict)
    cost: float = 0.0
    text: str = ""
    context: str = ""
    tool_input: Any = None
    tool_output: Any = None
    anchor: str = ""
    number: str = ""

    @property
    def duration_ms(self) -> float:
        return ms_between(self.start, self.end)


@dataclass
class Turn:
    index: int
    roots: list[Span]
    start: datetime
    end: datetime
    steps: list[Step] = field(default_factory=list)
    others: list[Span] = field(default_factory=list)
    prompt: str = ""
    reply: str = ""
    agent: str = ""

    @property
    def duration_ms(self) -> float:
        return ms_between(self.start, self.end)

    @property
    def model_steps(self) -> list[Step]:
        return [s for s in self.steps if s.kind == "model"]

    @property
    def tool_steps(self) -> list[Step]:
        return [s for s in self.steps if s.kind == "tool"]

    @property
    def cost(self) -> float:
        return sum(s.cost for s in self.model_steps)

    def token_total(self, key: str) -> int:
        return sum(s.tokens.get(key, 0) for s in self.model_steps)


def turn_spans(turn: Turn) -> list[Span]:
    """The root span(s) identifying this turn."""
    candidates = [r for r in turn.roots if r.get("span_kind") in TURN_KINDS and span_id(r)]
    if not candidates:
        candidates = [r for r in turn.roots if span_id(r)]
    seen: set[str] = set()
    result: list[Span] = []
    for s in candidates:
        sid = span_id(s)
        if sid and sid not in seen:
            seen.add(sid)
            result.append(s)
    return result


def empty_tokens() -> dict[str, int]:
    return {"in": 0, "cache_read": 0, "cache_write": 0, "out": 0}


def tokens_of(span: Span) -> dict[str, int]:
    """Fresh input, cache read, cache write and output tokens, across conventions."""
    tokens = empty_tokens()
    if attr(span, "input_tokens") is not None or attr(span, "output_tokens") is not None:
        tokens["in"] = as_int(attr(span, "input_tokens"))
        tokens["out"] = as_int(attr(span, "output_tokens"))
        tokens["cache_read"] = as_int(attr(span, "cache_read_tokens"))
        tokens["cache_write"] = as_int(attr(span, "cache_creation_tokens"))
        return tokens
    if (
        attr(span, "llm.token_count.prompt") is not None
        or attr(span, "llm.token_count.completion") is not None
    ):
        cache_read = as_int(
            first_attr(
                span, ("llm.token_count.prompt_details.cache_read", "llm.prompt_details.cache_read")
            )
        )
        cache_write = as_int(
            first_attr(
                span,
                ("llm.token_count.prompt_details.cache_write", "llm.prompt_details.cache_write"),
            )
        )
        prompt = as_int(attr(span, "llm.token_count.prompt"))
        tokens.update(
            {
                "in": max(0, prompt - cache_read - cache_write),
                "cache_read": cache_read,
                "cache_write": cache_write,
                "out": as_int(attr(span, "llm.token_count.completion")),
            }
        )
        return tokens
    cache_read = as_int(
        first_attr(
            span, ("gen_ai.usage.cache_read.input_tokens", "gen_ai.usage.cache_read_input_tokens")
        )
    )
    cache_write = as_int(
        first_attr(
            span,
            (
                "gen_ai.usage.cache_creation.input_tokens",
                "gen_ai.usage.cache_creation_input_tokens",
            ),
        )
    )
    prompt = as_int(attr(span, "gen_ai.usage.input_tokens"))
    tokens.update(
        {
            "in": max(0, prompt - cache_read - cache_write),
            "cache_read": cache_read,
            "cache_write": cache_write,
            "out": as_int(attr(span, "gen_ai.usage.output_tokens")),
        }
    )
    return tokens


FLAT_MESSAGE_RE = re.compile(
    r"^(?P<prefix>llm\.(?:input|output)_messages)\.(?P<i>\d+)\.message\.(?P<field>.+)$"
)


def messages_attr(span: Span, prefix: str) -> Any:
    """OpenInference messages, whether stored as one list or as flattened indexed keys."""
    value = attr(span, prefix)
    if isinstance(value, dict) and value and all(str(k).isdigit() for k in value):
        return [value[k] for k in sorted(value, key=lambda x: int(str(x)))]
    if value not in (None, ""):
        return value
    rows: dict[int, dict[str, Any]] = {}
    for key, item in (span.get("attributes") or {}).items():
        match = FLAT_MESSAGE_RE.match(key)
        if match and match.group("prefix") == prefix:
            rows.setdefault(int(match.group("i")), {})[match.group("field")] = item
    return [rows[i] for i in sorted(rows)] or None


def message_text(messages: Any) -> str:
    """Concatenated text of OpenInference ``llm.*_messages`` entries."""
    if isinstance(messages, str):
        try:
            messages = json.loads(messages)
        except ValueError:
            return messages
    if not isinstance(messages, list):
        return ""
    parts: list[str] = []
    for entry in messages:
        message = entry.get("message", entry) if isinstance(entry, dict) else {}
        if not isinstance(message, dict):
            continue
        content = message.get("content") or message.get("message.content")
        if isinstance(content, str) and content.strip():
            parts.append(content)
        for item in message.get("contents") or message.get("message.contents") or []:
            inner = item.get("message_content", item) if isinstance(item, dict) else {}
            text = inner.get("text") if isinstance(inner, dict) else None
            if text:
                parts.append(text)
    return "\n\n".join(parts)


def trailing_input_messages(messages: Any) -> str:
    """The messages after the last assistant message: what this call newly received."""
    if isinstance(messages, str):
        try:
            messages = json.loads(messages)
        except ValueError:
            return messages
    if not isinstance(messages, list):
        return ""
    cut = 0
    for i, entry in enumerate(messages):
        message = entry.get("message", entry) if isinstance(entry, dict) else {}
        if (
            isinstance(message, dict)
            and (message.get("role") or message.get("message.role")) == "assistant"
        ):
            cut = i + 1
    return message_text(messages[cut:])


def is_id_stub(value: str) -> bool:
    """``{"id": "..."}`` and the like: an output that carries no content."""
    try:
        parsed = json.loads(value)
    except ValueError:
        return False
    return isinstance(parsed, dict) and set(parsed) <= {"id"}


def model_text(span: Span) -> str:
    for candidate in (
        attr(span, "response.model_output"),
        message_text(messages_attr(span, "llm.output_messages")),
        attr(span, "output.value"),
    ):
        if isinstance(candidate, str) and candidate.strip() and not is_id_stub(candidate):
            return candidate
    return ""


def model_context(span: Span) -> str:
    for candidate in (
        first_attr(span, NEW_CONTEXT_KEYS),
        trailing_input_messages(messages_attr(span, "llm.input_messages")),
        attr(span, "input.value"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return ""


def agent_label(span: Span, session_id: str) -> str:
    agent_id = attr(span, "agent.id")
    if agent_id and str(agent_id) != session_id:
        name = attr(span, "agent.name") or "subagent"
        return f"{name} ({str(agent_id)[:8]})"
    return ""


def error_of(spans: list[Span]) -> str:
    for span in spans:
        if span.get("status_code") == "ERROR":
            return (span.get("status_message") or "ERROR").strip().splitlines()[0][:200] or "ERROR"
    return ""


# --- assembly ----------------------------------------------------------------


def dedupe_model_spans(spans: list[Span]) -> list[Span]:
    seen: set[tuple[str, ...]] = set()
    kept: list[Span] = []
    for span in spans:
        response_id = first_attr(span, RESPONSE_ID_KEYS)
        key = (
            ("rid", str(response_id))
            if response_id
            else ("t", str(span.get("start_time")), str(attr(span, "output.value") or ""))
        )
        if key in seen:
            continue
        seen.add(key)
        kept.append(span)
    return kept


def root_of(span: Span, by_id: dict[str, Span]) -> Span:
    current = span
    visited: set[str] = set()
    while True:
        parent = current.get("parent_id")
        if not parent or parent not in by_id or parent in visited:
            return current
        visited.add(parent)
        current = by_id[parent]


def cluster_turns(roots: list[Span]) -> list[list[Span]]:
    clusters: list[list[Span]] = []
    cluster_end: datetime | None = None
    for root in sorted(roots, key=start_of):
        if clusters and cluster_end is not None and start_of(root) <= cluster_end:
            clusters[-1].append(root)
            cluster_end = max(cluster_end, end_of(root))
        else:
            clusters.append([root])
            cluster_end = end_of(root)
    return clusters


# A tool call's own one-line account of itself, carried in its arguments: agy writes
# toolAction / toolSummary on every call; Claude Code's Bash and Agent take description.
ACTION_KEYS = ("toolAction", "toolSummary", "description", "Description")
# The argument that best names a call's target, across clients.
TARGET_KEYS = (
    "command",
    "CommandLine",
    "file_path",
    "AbsolutePath",
    "TargetFile",
    "notebook_path",
    "path",
    "DirectoryPath",
    "pattern",
    "Query",
    "query",
    "SearchPath",
    "url",
    "Url",
    "prompt",
)
INPUT_LABEL_RE = re.compile(r"^\[[^\]\n]+\]\s*\n")


def tool_args(value: Any) -> Any:
    """Parsed tool arguments, with a leading ``[TOOL INPUT: Name]`` label line removed."""
    if isinstance(value, str):
        value = INPUT_LABEL_RE.sub("", value.lstrip(), count=1)
    return parse_json(value)


def tool_action(value: Any) -> str:
    args = tool_args(value)
    if isinstance(args, dict):
        candidates = [args]
        if isinstance(args.get("Arguments"), dict):
            candidates.append(args["Arguments"])
        for candidate in candidates:
            for key in ACTION_KEYS:
                if isinstance(candidate.get(key), str) and candidate[key].strip():
                    return one_line(candidate[key])
    return ""


# Calls made from inside a code-mode block: ``codemode.name({...})`` or
# ``call_tool("name", {...})``, with the flat object literal that follows.
CODE_CALL_RE = re.compile(
    r"""(?:codemode\.(?P<a>[A-Za-z_]\w*)\s*\(|call_tool\(\s*["'](?P<b>[A-Za-z_][\w.-]*)["']\s*,)\s*\{(?P<args>[^{}]*)\}"""
)
CODE_ARG_RE = re.compile(
    r"""\s*["']?(\w+)["']?\s*:\s*("[^"]*"|'[^']*'|-?\d[\d.]*|true|false|null|None|True|False)\s*(?:,|$)"""
)
CODE_CALLS_SHOWN = 6
ARG_VALUE_CHARS = 60


def code_calls(code: str) -> str:
    """``tool(key=value, ...)`` for each call a code-mode block makes, in order.

    Empty when any call passes something other than literals (a variable, a spread, a
    nested object), since the values that matter would then be missing from the line.
    """
    calls: list[str] = []
    for match in CODE_CALL_RE.finditer(code):
        name = match.group("a") or match.group("b")
        text = match.group("args")
        pairs: list[str] = []
        pos = 0
        while pos < len(text):
            arg = CODE_ARG_RE.match(text, pos)
            if not arg:
                if text[pos:].strip():
                    return ""
                break
            value = arg.group(2).strip(chr(34) + chr(39)).strip()
            if value.startswith("+") or value.endswith("+"):
                return ""  # a quoted fragment of a concatenation, not a literal
            pairs.append(f"{arg.group(1)}={one_line(value, ARG_VALUE_CHARS)}")
            pos = arg.end()
        calls.append(f"{name}({', '.join(pairs)})")
    if len(calls) > CODE_CALLS_SHOWN:
        calls = [*calls[:CODE_CALLS_SHOWN], f"+{len(calls) - CODE_CALLS_SHOWN} more"]
    return ", ".join(calls)


def tool_detail(value: Any) -> str:
    """What a tool call acted on: the calls inside a code block, a command, a path, a query."""
    args = tool_args(value)
    if not isinstance(args, dict):
        return " ".join(str(args).split()) if isinstance(args, str) else ""
    inner = parse_json(args.get("Arguments"))
    code = args.get("code") or (inner.get("code") if isinstance(inner, dict) else None)
    prefix = ""
    if isinstance(args.get("ServerName"), str) and isinstance(args.get("ToolName"), str):
        prefix = f"{args['ServerName']}.{args['ToolName']}"
    if isinstance(code, str) and code.strip():
        calls = code_calls(code)
        body = calls or " ".join(code.split())
        return f"{prefix}: {body}" if prefix else body
    if prefix:
        if isinstance(inner, dict):
            pairs = ", ".join(
                f"{k}={one_line(str(v), ARG_VALUE_CHARS)}"
                for k, v in inner.items()
                if v not in (None, "")
            )
            return f"{prefix}({pairs})"
        return prefix
    for key in TARGET_KEYS:
        if isinstance(args.get(key), str) and args[key].strip():
            return " ".join(args[key].split())
    for key, item in args.items():
        if key not in ACTION_KEYS and isinstance(item, str) and item.strip():
            return " ".join(item.split())
    return ""


def tool_hint(value: Any) -> str:
    return one_line(tool_detail(value))


def one_line(text: str, limit: int = HINT_CHARS) -> str:
    line = " ".join(str(text).split())
    return line if len(line) <= limit else line[: limit - 1] + "…"


def parse_json(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped[:1] in ("{", "["):
            try:
                return json.loads(stripped)
            except ValueError:
                return value
    return value


def build_tool_steps(
    spans: list[Span], by_id: dict[str, Span], session_id: str
) -> tuple[list[Step], set[str]]:
    groups: dict[str, list[Span]] = {}
    member: dict[str, str] = {}
    for span in sorted(spans, key=start_of):
        if span.get("span_kind") != "TOOL":
            continue
        call_id = first_attr(span, CALL_ID_KEYS)
        key = f"call:{call_id}" if call_id else f"span:{span_id(span)}"
        groups.setdefault(key, []).append(span)
        member[span_id(span)] = key
    # Fold id-less children (execution, permission wait) into their tool call.
    changed = True
    while changed:
        changed = False
        for span in spans:
            sid = span_id(span)
            if sid in member or span.get("span_kind") in ("LLM", "AGENT", "CHAIN"):
                continue
            parent = span.get("parent_id")
            if parent in member and not first_attr(span, CALL_ID_KEYS):
                groups[member[parent]].append(span)
                member[sid] = member[parent]
                changed = True
    steps: list[Step] = []
    for group in groups.values():
        named = next((s for s in group if first_attr(s, TOOL_NAME_KEYS)), group[0])
        tool_input = group_attr(group, TOOL_INPUT_KEYS)
        tool_output = group_attr(group, TOOL_OUTPUT_KEYS)
        action_summary = group_attr(group, ("tool.summary",))
        action = (
            one_line(str(action_summary))
            if action_summary and str(action_summary).strip()
            else tool_action(tool_input)
        )
        steps.append(
            Step(
                kind="tool",
                start=min(start_of(s) for s in group),
                end=max(end_of(s) for s in group),
                spans=group,
                title=str(first_attr(named, TOOL_NAME_KEYS) or named.get("name") or "tool"),
                hint=tool_hint(tool_input),
                detail=tool_detail(tool_input),
                action=action,
                agent=next(
                    (agent_label(s, session_id) for s in group if agent_label(s, session_id)), ""
                ),
                error=error_of(group),
                tool_input=tool_input,
                tool_output=tool_output,
            )
        )
    return steps, set(member)


def group_attr(group: list[Span], keys: tuple[str, ...]) -> Any:
    """The first key, in priority order, that any span in the group carries."""
    for key in keys:
        values = [attr(s, key) for s in group if attr(s, key) not in (None, "")]
        if values:
            return max(values, key=lambda v: len(str(v)))
    return None


def build_model_step(span: Span, prices: dict[str, dict[str, float]], session_id: str) -> Step:
    model = str(first_attr(span, MODEL_KEYS) or "unknown model")
    tokens = tokens_of(span)
    return Step(
        kind="model",
        start=start_of(span),
        end=end_of(span),
        spans=[span],
        title=model,
        model=model,
        tokens=tokens,
        cost=cost_usd(tokens, price_row(model, prices)),
        text=model_text(span),
        context=model_context(span),
        agent=agent_label(span, session_id),
        error=error_of([span]),
    )


def has_content(span: Span) -> bool:
    return any(
        isinstance(attr(span, k), str) and attr(span, k).strip() and not is_id_stub(attr(span, k))
        for k in ("input.value", "output.value")
    )


def assemble(spans: list[Span], session_id: str, prices: dict[str, dict[str, float]]) -> list[Turn]:
    by_id = {span_id(s): s for s in spans if span_id(s)}
    tool_steps, tool_members = build_tool_steps(spans, by_id, session_id)
    model_spans = dedupe_model_spans([s for s in spans if s.get("span_kind") == "LLM"])
    model_steps = [build_model_step(s, prices, session_id) for s in model_spans]

    roots = [s for s in spans if root_of(s, by_id) is s]
    clusters = cluster_turns(roots)
    root_turn: dict[str, int] = {}
    turns: list[Turn] = []
    for index, cluster in enumerate(clusters, start=1):
        turns.append(
            Turn(
                index=index,
                roots=cluster,
                start=min(start_of(r) for r in cluster),
                end=max(end_of(r) for r in cluster),
            )
        )
        for root in cluster:
            root_turn[span_id(root)] = index - 1

    def turn_for(span: Span) -> Turn:
        return turns[root_turn.get(span_id(root_of(span, by_id)), 0)]

    for step in tool_steps:
        turn_for(step.spans[0]).steps.append(step)
    for step in model_steps:
        turn_for(step.spans[0]).steps.append(step)
    model_ids = {span_id(s) for s in spans if s.get("span_kind") == "LLM"}
    root_ids = set(root_turn)
    for span in spans:
        sid = span_id(span)
        if sid in tool_members or sid in model_ids or sid in root_ids:
            continue
        turn = turn_for(span)
        if has_content(span):
            turn.steps.append(
                Step(
                    kind="other",
                    start=start_of(span),
                    end=end_of(span),
                    spans=[span],
                    title=str(span.get("name") or span.get("span_kind") or "span"),
                    agent=agent_label(span, session_id),
                    error=error_of([span]),
                    tool_input=attr(span, "input.value"),
                    tool_output=attr(span, "output.value"),
                )
            )
        else:
            turn.others.append(span)

    turns = fold_empty_turns(turns)
    for turn in turns:
        turn.steps.sort(key=lambda s: (s.start, s.end))
        for n, step in enumerate(turn.steps, start=1):
            step.number = f"{turn.index}.{n}"
            step.anchor = f"t{turn.index}-{n}"
        turn.prompt = longest(
            first_attr(r, PROMPT_KEYS) for r in turn.roots if r.get("span_kind") in TURN_KINDS
        )
        if not turn.prompt:
            turn.prompt = next((s.context for s in turn.model_steps if s.context), "")
        reply = next(
            (
                str(attr(r, "output.value"))
                for r in turn.roots
                if r.get("span_kind") in TURN_KINDS
                and isinstance(attr(r, "output.value"), str)
                and attr(r, "output.value").strip()
                and not is_id_stub(attr(r, "output.value"))
            ),
            "",
        )
        if not reply:
            reply = next((s.text for s in reversed(turn.model_steps) if s.text), "")
        turn.reply = reply
        turn.agent = next(
            (str(attr(r, "agent.name")) for r in turn.roots if attr(r, "agent.name")), ""
        )
    return turns


def fold_empty_turns(turns: list[Turn]) -> list[Turn]:
    """Merge root clusters with no steps and no turn root into the next turn (else the last).

    These are stray roots: hook spans fired between turns, or children whose turn root has
    not been exported yet. They keep their spans in the receiving turn's other-spans table.
    """
    kept: list[Turn] = []
    pending: list[Turn] = []
    for turn in turns:
        empty = not turn.steps and not any(r.get("span_kind") in TURN_KINDS for r in turn.roots)
        if empty:
            pending.append(turn)
            continue
        for stray in pending:
            turn.others.extend([*stray.roots, *stray.others])
        pending = []
        kept.append(turn)
    if pending:
        if kept:
            for stray in pending:
                kept[-1].others.extend([*stray.roots, *stray.others])
        else:
            kept = pending
    for index, turn in enumerate(kept, start=1):
        turn.index = index
    return kept


def longest(values: Any) -> str:
    strings = [v for v in values if isinstance(v, str) and v.strip()]
    return max(strings, key=len) if strings else ""


# --- rendering ---------------------------------------------------------------


def fmt_ms(ms: float) -> str:
    if ms < 1000:
        return f"{ms:.0f} ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, secs = divmod(int(round(seconds)), 60)
    if minutes < 60:
        return f"{minutes} m {secs:02d} s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} m"


def fmt_n(n: int) -> str:
    return f"{n:,}"


def fmt_usd(usd: float) -> str:
    return f"${usd:,.2f}" if usd >= 0.01 or usd == 0 else f"${usd:.4f}"


def fmt_time(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def fence(text: str, lang: str = "") -> str:
    runs = re.findall(r"`{3,}", text)
    ticks = "`" * max([3, *(len(r) + 1 for r in runs)])
    return f"{ticks}{lang}\n{text.rstrip()}\n{ticks}"


def details(summary: str, body: str) -> str:
    return f"<details><summary>{summary}</summary>\n\n{body}\n\n</details>"


def quote(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.rstrip().splitlines())


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def render_value(value: Any) -> str:
    """A payload as readable markdown: dict fields one by one, long strings fenced."""
    parsed = parse_json(value)
    if (
        isinstance(parsed, list)
        and parsed
        and all(isinstance(i, dict) and i.get("type") == "text" for i in parsed)
    ):
        return fence("\n\n".join(str(i.get("text", "")) for i in parsed))
    if isinstance(parsed, dict):
        parts: list[str] = []
        for key, item in parsed.items():
            if isinstance(item, str) and ("\n" in item or len(item) > 100):
                parts.append(f"`{key}`:\n\n{fence(item)}")
            elif isinstance(item, (dict, list)):
                parts.append(
                    f"`{key}`:\n\n{fence(json.dumps(item, indent=2, ensure_ascii=False), 'json')}"
                )
            else:
                parts.append(f"`{key}`: `{json.dumps(item, ensure_ascii=False)}`")
        return "\n\n".join(parts) if parts else fence("{}")
    if isinstance(parsed, list):
        return fence(json.dumps(parsed, indent=2, ensure_ascii=False), "json")
    return fence(str(value))


def token_line(tokens: dict[str, int]) -> str:
    return (
        f"in {fmt_n(tokens.get('in', 0))} · cache read {fmt_n(tokens.get('cache_read', 0))} · "
        f"cache write {fmt_n(tokens.get('cache_write', 0))} · out {fmt_n(tokens.get('out', 0))}"
    )


def step_heading(step: Step) -> str:
    agent = f" · {step.agent}" if step.agent else ""
    error = " · ❌ ERROR" if step.error else ""
    if step.kind == "model":
        estimated = (
            " · estimated tokens"
            if attr(step.spans[0], "llm.token_count.type") == "estimated"
            else ""
        )
        return (
            f"### {step.number} 🧠 {step.title} · {fmt_ms(step.duration_ms)} · "
            f"{fmt_usd(step.cost)}{estimated}{agent}{error}"
        )
    return f"### {step.number} {call_label(step)} · {fmt_ms(step.duration_ms)}{agent}{error}"


def call_label(step: Step) -> str:
    """``Action: 🛠 tool — target``, for a step heading."""
    icon = "🛠" if step.kind == "tool" else "▫️"
    label = f"{icon} {step.title}"
    if step.hint:
        label += f" — {escape_cell(step.hint)}"
    return f"{escape_cell(step.action)}: {label}" if step.action else label


def is_tool_request(text: str) -> bool:
    """Model output that is a JSON list of tool calls (``name`` plus arguments) and nothing else."""
    parsed = parse_json(text)
    return (
        isinstance(parsed, list)
        and bool(parsed)
        and all(
            isinstance(i, dict) and "name" in i and ({"args", "input", "arguments"} & set(i))
            for i in parsed
        )
    )


def step_bullet(step: Step) -> list[str]:
    """A tool call as an outline bullet under the model call that made it, its target beneath."""
    agent = f" · {step.agent}" if step.agent else ""
    error = f" · ❌ `{escape_cell(step.error)}`" if step.error else ""
    icon = "🛠" if step.kind == "tool" else "▫️"
    label = (
        f"{escape_cell(step.action)}: {icon} {step.title}"
        if step.action
        else f"{icon} {step.title}"
    )
    lines = [
        f'* <a id="{step.anchor}"></a>{step.number} {label} · {fmt_ms(step.duration_ms)}{agent}{error}'
    ]
    if step.detail:
        lines.append(f"  * {code_span(one_line(step.detail, DETAIL_CHARS))}")
    return lines


def code_span(text: str) -> str:
    ticks = "`" * (max((len(r) for r in re.findall(r"`+", text)), default=0) + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{ticks}{pad}{text}{pad}{ticks}"


def render_step(step: Step, full: bool) -> list[str]:
    """A step's markdown. Without ``full`` (the outline), folded payloads are left out."""
    out = [f'<a id="{step.anchor}"></a>', "", step_heading(step), ""]
    if step.kind == "model":
        out += [token_line(step.tokens), ""]
        if step.text and is_tool_request(step.text):
            # Output that is only tool calls: the calls themselves follow as steps.
            if full:
                out += [details("Tool calls requested", render_value(step.text)), ""]
        elif step.text:
            out += [quote(step.text), ""]
        if step.context and full:
            out += [
                details(
                    f"Context received ({fmt_n(len(step.context))} chars)", fence(step.context)
                ),
                "",
            ]
    else:
        if step.error:
            out += [f"Error: `{escape_cell(step.error)}`", ""]
        if not full:
            return out
        if step.tool_input not in (None, ""):
            size = len(str(step.tool_input))
            out += [details(f"Input ({fmt_n(size)} chars)", render_value(step.tool_input)), ""]
        if step.tool_output not in (None, ""):
            size = len(str(step.tool_output))
            out += [details(f"Output ({fmt_n(size)} chars)", render_value(step.tool_output)), ""]
    return out


def render_others(spans: list[Span]) -> str:
    by_name: dict[str, list[float]] = {}
    for span in spans:
        by_name.setdefault(str(span.get("name") or "span"), []).append(
            ms_between(start_of(span), end_of(span))
        )
    rows = ["| Span | Count | Total |", "| - | -: | -: |"]
    for name, durations in sorted(by_name.items(), key=lambda kv: -sum(kv[1])):
        rows.append(f"| {escape_cell(name)} | {len(durations)} | {fmt_ms(sum(durations))} |")
    total = sum(sum(d) for d in by_name.values())
    return details(
        f"Other spans: {len(spans)} without content ({fmt_ms(total)} total)", "\n".join(rows)
    )


def turn_title(turn: Turn) -> str:
    """The prompt's opening words. A prompt that opens with a tag is labelled by the tag."""
    text = turn.prompt.strip()
    if not text:
        return "(no prompt recorded)"
    tag = re.match(r"<([A-Za-z][\w-]*)", text)
    words = " ".join(re.sub(r"<[^>]*>", " ", text[:2000]).split())
    if tag:
        return one_line(f"[{tag.group(1)}] {words}")
    return one_line(words)


def model_totals(turns: list[Turn]) -> dict[str, dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}
    for turn in turns:
        for step in turn.model_steps:
            row = totals.setdefault(step.model, {"calls": 0, "cost": 0.0, **empty_tokens()})
            row["calls"] += 1
            row["cost"] += step.cost
            for key in ("in", "cache_read", "cache_write", "out"):
                row[key] += step.tokens.get(key, 0)
    return totals


def render(
    turns: list[Turn],
    session_id: str,
    project: str,
    spans: list[Span],
    prices: dict[str, dict[str, float]],
    ui_base_url: str | None = None,
) -> tuple[str, str, str]:
    """The full transcript, the outline (no folded payloads) and the summary block."""
    start = min(t.start for t in turns)
    end = max(t.end for t in turns)
    all_steps = [s for t in turns for s in t.steps]
    tools = [s for s in all_steps if s.kind == "tool"]
    models = model_totals(turns)
    cost = sum(row["cost"] for row in models.values())
    tokens = {
        k: sum(row[k] for row in models.values())
        for k in ("in", "cache_read", "cache_write", "out")
    }
    errors = [s for s in all_steps if s.error]
    unpriced = sorted(m for m in models if price_row(m, prices) is None)
    agents = sorted({s.agent for s in all_steps if s.agent})

    header = [
        f"# Session `{session_id}`",
        "",
        f"- **Project:** {project}",
        f"- **Window:** {fmt_time(start)} → {fmt_time(end)} ({fmt_ms(ms_between(start, end))} wall)",
        f"- **Turns:** {len(turns)} · **model calls:** {sum(r['calls'] for r in models.values())} · "
        f"**tool calls:** {len(tools)} · **errors:** {len(errors)} · **spans:** {len(spans)}",
        f"- **Tokens:** {token_line(tokens)}",
        f"- **Estimated cost:** {fmt_usd(cost)} (list prices; comparable spend, not an invoice)",
    ]
    if agents:
        header.append(f"- **Subagents:** {', '.join(agents)}")
    if unpriced:
        header.append(f"- **Unpriced models (costed at $0):** {', '.join(unpriced)}")
    if ui_base_url and session_id:
        header.append(
            f"- **Phoenix session:** [{session_id}]({ui_base_url}/redirects/sessions/{session_id})"
        )

    summary = [
        "## Turns",
        "",
        "| # | Turn | Start | Duration | Model calls | Tool calls | Out tokens | Cost |",
        "| -: | - | - | -: | -: | -: | -: | -: |",
    ]
    for turn in turns:
        summary.append(
            f"| {turn.index} | [{escape_cell(turn_title(turn))}](#t{turn.index}) | "
            f"{turn.start.astimezone(UTC).strftime('%m-%d %H:%M:%S')} | {fmt_ms(turn.duration_ms)} | "
            f"{len(turn.model_steps)} | {len(turn.tool_steps)} | {fmt_n(turn.token_total('out'))} | "
            f"{fmt_usd(turn.cost)} |"
        )
    summary += [
        "",
        "## Cost by model",
        "",
        "| Model | Calls | In | Cache read | Cache write | Out | Cost |",
        "| - | -: | -: | -: | -: | -: | -: |",
    ]
    for model, row in sorted(models.items(), key=lambda kv: -kv[1]["cost"]):
        summary.append(
            f"| {escape_cell(model)} | {row['calls']} | {fmt_n(row['in'])} | {fmt_n(row['cache_read'])} | "
            f"{fmt_n(row['cache_write'])} | {fmt_n(row['out'])} | {fmt_usd(row['cost'])} |"
        )
    slowest = sorted((s for s in all_steps if s.kind != "other"), key=lambda s: -s.duration_ms)[
        :SLOWEST_STEPS
    ]
    if slowest:
        summary += [
            "",
            "## Slowest steps",
            "",
            "| Step | What | Duration | Cost |",
            "| - | - | -: | -: |",
        ]
        for step in slowest:
            what = (
                step.title
                + (f" — {step.action}" if step.action else "")
                + (f" — {step.hint}" if step.hint and not step.action else "")
            )
            summary.append(
                f"| [{step.number}](#{step.anchor}) | {escape_cell(one_line(what))} | "
                f"{fmt_ms(step.duration_ms)} | {fmt_usd(step.cost) if step.kind == 'model' else ''} |"
            )
    if errors:
        summary += ["", "## Errors", ""]
        for step in errors:
            summary.append(
                f"- [{step.number}](#{step.anchor}) {step.title}: `{escape_cell(step.error)}`"
            )

    head = [*header, "", *summary, ""]
    full = (
        "\n".join(
            [*head, *render_body(turns, full=True, session_id=session_id, ui_base_url=ui_base_url)]
        ).rstrip()
        + "\n"
    )
    outline = (
        "\n".join(
            [*head, *render_body(turns, full=False, session_id=session_id, ui_base_url=ui_base_url)]
        ).rstrip()
        + "\n"
    )
    return full, outline, "\n".join([*header, "", *summary]) + "\n"


def render_body(
    turns: list[Turn],
    full: bool,
    session_id: str = "",
    ui_base_url: str | None = None,
) -> list[str]:
    body: list[str] = []
    for turn in turns:
        agent = f" · {turn.agent}" if turn.agent else ""
        turn_meta = [
            f"{fmt_time(turn.start)} · {fmt_ms(turn.duration_ms)} · {len(turn.model_steps)} model calls · "
            f"{len(turn.tool_steps)} tool calls · {fmt_usd(turn.cost)}{agent}"
        ]
        if ui_base_url and session_id:
            links = [f"[session]({ui_base_url}/redirects/sessions/{session_id})"]
            spans = turn_spans(turn)
            if len(spans) == 1:
                links.append(f"[span]({ui_base_url}/redirects/spans/{span_id(spans[0])})")
            elif len(spans) > 1:
                for i, s in enumerate(spans, start=1):
                    links.append(f"[span {i}]({ui_base_url}/redirects/spans/{span_id(s)})")
            turn_meta.append(" · ".join(links))
        body += [
            f'<a id="t{turn.index}"></a>',
            "",
            f"## Turn {turn.index} · {escape_cell(turn_title(turn))}",
            "",
            " · ".join(turn_meta),
            "",
        ]
        if turn.prompt and full:
            body += [details(f"Prompt ({fmt_n(len(turn.prompt))} chars)", fence(turn.prompt)), ""]
        if turn.prompt and not full:
            body += [quote(turn.prompt), ""]
        in_list = False
        for step in turn.steps:
            if not full and step.kind != "model":
                if not in_list and body and body[-1] != "":
                    body.append("")
                body += step_bullet(step)
                in_list = True
                continue
            if in_list:
                body.append("")
                in_list = False
            body += render_step(step, full)
        if in_list:
            body.append("")
        if turn.reply:
            body += [f"### Turn {turn.index} reply", "", quote(turn.reply), ""]
        if turn.others and full:
            body += [render_others(turn.others), ""]
    return body


# --- path sanitization -------------------------------------------------------

HOST_PATH_PATTERNS = [
    (re.compile(r"/(?:home|Users)/[a-zA-Z0-9._-]+"), "~"),
    (re.compile(r"[a-zA-Z]:(?:\\{1,2}|/)(?:Users|users)(?:\\{1,2}|/)[a-zA-Z0-9._-]+"), "~"),
    (re.compile(r"/tmp/claude-[0-9]+-[^/\s\"'`]+"), "/tmp/claude-session"),
]


def sanitize_paths(text: str) -> str:
    """Sanitize literal host filesystem paths to avoid host-path rejection guards when saving to PKB."""
    for pattern, replacement in HOST_PATH_PATTERNS:
        text = pattern.sub(replacement, text)
    home = os.environ.get("HOME")
    if home and len(home) > 1 and home != "/":
        text = text.replace(home, "~")
    return text


# --- cross-session prompt scan (--since) -------------------------------------

AUTOMATED_PREFIXES = (
    "The following is a <SYSTEM_MESSAGE>",
    "<SYSTEM_MESSAGE",
    "<CONTEXT_SUMMARY>",
    "<agent-message",
    "<teammate-message",
    "<task-notification",
    "<cross-session-message",
    "<system-reminder",
    "<local-command-",
    "<command-message>",
    "<command-name>",
    "<bash-",
    "[polecat-exit]",
)
HEADLESS_ENTRYPOINT_RE = re.compile(r"^/(?:ida:|james:)?(?:pull|supervise)\s+[A-Za-z0-9_.:-]+\s*$")
CHANNEL_BLOCK_RE = re.compile(r"^\s*<channel\b([^>]*)>(.*?)</channel>\s*$", re.DOTALL)
XML_ATTR_RE = re.compile(r'([A-Za-z_][\w:.-]*)\s*=\s*"([^"]*)"')
USER_REQUEST_RE = re.compile(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", re.DOTALL)
SUBAGENT_CONV_RE = re.compile(r'"conversationId"\s*:\s*"([0-9a-f-]{36})"')


@dataclass
class MatchedPrompt:
    start: datetime
    session_id: str
    span_id: str
    source: str
    text: str
    host: str = ""
    message_id: str = ""
    thread_id: str = ""
    turn_index: int = 1


def parse_since_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp requiring an explicit timezone offset, normalized to UTC."""
    raw = (value or "").strip()
    if not raw:
        raise ConfigError("--since requires an ISO-8601 timestamp with an explicit timezone offset")
    normalized = re.sub(r"^(\d{4}-\d{2}-\d{2})\s+", r"\1T", raw)
    if normalized.endswith(("Z", "z")):
        normalized = normalized[:-1] + "+00:00"
    if "T" not in normalized and "t" not in normalized:
        raise ConfigError(
            f"--since timestamp {value!r} must include time and timezone offset (e.g. 2026-11-15T08:00:00Z)"
        )
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ConfigError(f"cannot parse --since timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        raise ConfigError(
            f"--since timestamp {value!r} is missing an explicit timezone offset (e.g. Z or +00:00)"
        )
    return parsed.astimezone(UTC)


def is_automated_wrapper(text: str) -> bool:
    """True when ``text`` is an internal harness/agent transport wrapper or bare worker launch."""
    stripped = text.strip()
    if not stripped or is_id_stub(stripped):
        return True
    if any(stripped.startswith(prefix) for prefix in AUTOMATED_PREFIXES):
        return True
    if HEADLESS_ENTRYPOINT_RE.match(stripped):
        return True
    return False


def _extract_prompt_from_chain_input(
    input_value: str, name_prefix: str = ""
) -> tuple[str, str, str, str] | None:
    """Return ``(source, text, message_id, thread_id)`` for a human root CHAIN input, else None."""
    if name_prefix.startswith("The following is a <SYSTEM_MESSAGE>"):
        return None
    raw = (input_value or "").strip()
    if not raw or raw.startswith("The following is a <SYSTEM_MESSAGE>"):
        return None

    channel_match = CHANNEL_BLOCK_RE.match(raw)
    if channel_match:
        attrs = dict(XML_ATTR_RE.findall(channel_match.group(1)))
        event = attrs.get("event", "message")
        if event not in ("message", "bot_command"):
            return None
        body = channel_match.group(2).strip()
        if is_automated_wrapper(body):
            return None
        source_raw = attrs.get("source", "channel")
        source = source_raw.rsplit(":", 1)[-1] if ":" in source_raw else source_raw
        msg_id = attrs.get("message_id", "")
        thread_id = attrs.get("thread_id") or attrs.get("message_thread_id") or ""
        return source, body, msg_id, thread_id

    user_req = USER_REQUEST_RE.search(raw)
    if user_req:
        body = user_req.group(1).strip()
        if is_automated_wrapper(body):
            return None
        return "agy", body, "", ""

    if is_automated_wrapper(raw):
        return None
    return "cli", raw, "", ""


def _extract_prompt_from_ups_input(input_value: str) -> str | None:
    """Extract ``lastUserInput`` from an agy ``aops-debug.UserPromptSubmit`` hook payload."""
    parsed = parse_json(input_value)
    if not isinstance(parsed, dict):
        return None
    text = parsed.get("lastUserInput")
    if not isinstance(text, str) or is_automated_wrapper(text):
        return None
    return text.strip()


def extract_user_prompts_from_records(
    chains: list[dict[str, Any]],
    ups_rows: list[dict[str, Any]],
    subagent_ids: set[str],
    since_dt: datetime,
) -> list[MatchedPrompt]:
    """Deduplicate and merge human prompts across CLI, channel, and agy surfaces since ``since_dt``."""
    raw_items: list[MatchedPrompt] = []

    for row in chains:
        sid = str(row.get("session_id") or "").strip()
        if not sid or sid in subagent_ids:
            continue
        ts = parse_time(row.get("start_time"))
        if ts is None or ts < since_dt:
            continue
        name_prefix = str(row.get("name_prefix") or "")
        if name_prefix.startswith("aops-debug."):
            continue
        extracted = _extract_prompt_from_chain_input(str(row.get("input_value") or ""), name_prefix)
        if not extracted:
            continue
        source, text, msg_id, thread_id = extracted
        raw_items.append(
            MatchedPrompt(
                start=ts,
                session_id=sid,
                span_id=str(row.get("span_id") or ""),
                source=source,
                text=text,
                host=str(row.get("host_name") or ""),
                message_id=msg_id,
                thread_id=thread_id,
            )
        )

    for row in ups_rows:
        sid = str(row.get("session_id") or "").strip()
        if not sid or sid in subagent_ids:
            continue
        ts = parse_time(row.get("start_time"))
        if ts is None or ts < since_dt:
            continue
        text = _extract_prompt_from_ups_input(str(row.get("input_value") or ""))
        if not text:
            continue
        raw_items.append(
            MatchedPrompt(
                start=ts,
                session_id=sid,
                span_id=str(row.get("span_id") or ""),
                source="agy",
                text=text,
                host=str(row.get("host_name") or ""),
            )
        )

    raw_items.sort(key=lambda item: item.start)
    deduped: list[MatchedPrompt] = []
    seen_channel_msgs: set[tuple[str, str]] = set()
    seen_session_prompts: set[tuple[str, str]] = set()

    for item in raw_items:
        if item.message_id:
            ch_key = (item.source, item.message_id)
            if ch_key in seen_channel_msgs:
                continue
            seen_channel_msgs.add(ch_key)
        sp_key = (item.session_id, " ".join(item.text.split()))
        if sp_key in seen_session_prompts:
            continue
        seen_session_prompts.add(sp_key)
        deduped.append(item)

    return deduped


def discover_prompts_from_spans(universe: list[Span], since_dt: datetime) -> list[MatchedPrompt]:
    """Offline ``--from-file`` prompt discovery using the same rules as live SQL discovery."""
    subagent_ids: set[str] = set()
    chains: list[dict[str, Any]] = []
    ups_rows: list[dict[str, Any]] = []

    for s in universe:
        kind = s.get("span_kind")
        name = str(s.get("name") or "")
        if kind == "TOOL" and (
            name == "invoke_subagent" or first_attr(s, TOOL_NAME_KEYS) == "invoke_subagent"
        ):
            out_val = str(first_attr(s, TOOL_OUTPUT_KEYS) or "")
            subagent_ids.update(SUBAGENT_CONV_RE.findall(out_val))
        elif (
            name == "aops-debug.UserPromptSubmit" and str(attr(s, "hook.client") or "agy") == "agy"
        ):
            ups_rows.append(
                {
                    "span_id": span_id(s),
                    "start_time": s.get("start_time"),
                    "session_id": attr(s, "session.id"),
                    "host_name": attr(s, "host.name") or "",
                    "input_value": attr(s, "input.value") or "",
                }
            )
        elif kind == "CHAIN" and not s.get("parent_id"):
            chains.append(
                {
                    "span_id": span_id(s),
                    "start_time": s.get("start_time"),
                    "name_prefix": name[:80],
                    "session_id": attr(s, "session.id"),
                    "host_name": attr(s, "host.name") or "",
                    "agent_name": attr(s, "agent.name") or "",
                    "input_value": attr(s, "input.value") or "",
                }
            )

    return extract_user_prompts_from_records(chains, ups_rows, subagent_ids, since_dt)


def fetch_prompts_since(base_url: str, project: str, since_dt: datetime) -> list[MatchedPrompt]:
    """Discover human prompts since ``since_dt`` via ``project_sessions -> traces`` joins."""
    since_iso = since_dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    subagent_floor_iso = (
        (since_dt - timedelta(hours=12)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    proj_sql = "'" + project.replace("'", "''") + "'"
    since_sql = "'" + since_iso.replace("'", "''") + "'"
    sub_floor_sql = "'" + subagent_floor_iso.replace("'", "''") + "'"
    code = f"""
import asyncio, re

q_inv = (
    "SELECT s.id, SUBSTR(COALESCE(s.attributes ->> '$.output.value', ''), 1, 800) "
    "FROM projects p "
    "JOIN project_sessions ps ON ps.project_id = p.id "
    "JOIN traces t ON t.project_session_rowid = ps.id "
    "JOIN spans s ON s.trace_rowid = t.id "
    "WHERE p.name = {proj_sql} "
    "AND ps.end_time >= {sub_floor_sql} "
    "AND t.start_time >= {sub_floor_sql} "
    "AND s.span_kind = 'TOOL' AND s.name = 'invoke_subagent'"
)

q_ch = (
    "SELECT s.id, s.span_id, s.start_time, SUBSTR(s.name, 1, 80), "
    "s.attributes ->> '$.session.id', s.attributes ->> '$.host.name', "
    "s.attributes ->> '$.agent.name', "
    "SUBSTR(COALESCE(s.attributes ->> '$.input.value', ''), 1, 16384) "
    "FROM projects p "
    "JOIN project_sessions ps ON ps.project_id = p.id "
    "JOIN traces t ON t.project_session_rowid = ps.id "
    "JOIN spans s ON s.trace_rowid = t.id "
    "WHERE p.name = {proj_sql} "
    "AND ps.end_time >= {since_sql} "
    "AND t.start_time >= {since_sql} "
    "AND s.span_kind = 'CHAIN' "
    "AND (s.parent_id IS NULL OR s.parent_id = '') "
    "AND s.name NOT LIKE 'The following is a <SYSTEM_MESSAGE>%' "
    "AND s.name NOT LIKE 'aops-debug.%'"
)

q_up = (
    "SELECT s.id, s.span_id, s.start_time, "
    "s.attributes ->> '$.session.id', s.attributes ->> '$.host.name', "
    "SUBSTR(COALESCE(s.attributes ->> '$.input.value', ''), 1, 16384) "
    "FROM projects p "
    "JOIN project_sessions ps ON ps.project_id = p.id "
    "JOIN traces t ON t.project_session_rowid = ps.id "
    "JOIN spans s ON s.trace_rowid = t.id "
    "WHERE p.name = {proj_sql} "
    "AND ps.end_time >= {since_sql} "
    "AND t.start_time >= {since_sql} "
    "AND s.name = 'aops-debug.UserPromptSubmit' "
    "AND (s.attributes ->> '$.hook.client') = 'agy' "
    "AND NOT EXISTS ("
    "  SELECT 1 FROM spans r WHERE r.trace_rowid = s.trace_rowid "
    "  AND r.span_kind = 'CHAIN' AND (r.parent_id IS NULL OR r.parent_id = '') "
    "  AND r.name NOT LIKE 'aops-debug.%'"
    ")"
)

r_inv, r_ch, r_up = await asyncio.gather(
    call_tool("executeSql", {{"sql": q_inv, "row_limit": 5000}}),
    call_tool("executeSql", {{"sql": q_ch, "row_limit": 5000}}),
    call_tool("executeSql", {{"sql": q_up, "row_limit": 5000}}),
)
for label, res in (("invoke_subagent", r_inv), ("chains", r_ch), ("UserPromptSubmit", r_up)):
    if isinstance(res, dict) and "error" in res:
        raise RuntimeError(f"executeSql {{label}} failed: {{res['error']}}")

subagent_ids = set()
for _, out_val in (r_inv or {{}}).get("rows") or []:
    for m in re.findall(r'"conversationId"\\s*:\\s*"([0-9a-f-]{{36}})"', out_val or ""):
        subagent_ids.add(m)

chains = [
    {{
        "id": r[0], "span_id": r[1], "start_time": r[2], "name_prefix": r[3],
        "session_id": r[4], "host_name": r[5], "agent_name": r[6], "input_value": r[7],
    }}
    for r in ((r_ch or {{}}).get("rows") or [])
]
ups = [
    {{
        "id": r[0], "span_id": r[1], "start_time": r[2],
        "session_id": r[3], "host_name": r[4], "input_value": r[5],
    }}
    for r in ((r_up or {{}}).get("rows") or [])
]

return {{"subagent_ids": sorted(subagent_ids), "chains": chains, "ups": ups}}
"""
    payload = phoenix_execute_code(base_url, code)
    return extract_user_prompts_from_records(
        payload.get("chains") or [],
        payload.get("ups") or [],
        set(payload.get("subagent_ids") or []),
        since_dt,
    )


def _assign_turn_and_filter_stale(
    prompts: list[MatchedPrompt], turns: list[Turn], since_dt: datetime
) -> list[MatchedPrompt]:
    """Bind each matched prompt to its assembled Turn (#tN) and drop pre-cursor hook echoes."""
    if not turns:
        return prompts
    norm = lambda s: " ".join(s.split())
    kept: list[MatchedPrompt] = []
    for item in prompts:
        needle = norm(item.text)
        # 1. Exact span_id match on turn roots or other/step spans
        matched_turn: Turn | None = None
        for turn in turns:
            all_turn_span_ids = {
                *(span_id(r) for r in turn.roots),
                *(span_id(o) for o in turn.others),
                *(span_id(sp) for st in turn.steps for sp in st.spans),
            }
            if item.span_id and item.span_id in all_turn_span_ids:
                matched_turn = turn
                break
        # 2. Check if this exact prompt belonged to an earlier pre-cursor turn (agy hook echo)
        matching_text_turns = [t for t in turns if needle and needle in norm(t.prompt)]
        if matching_text_turns:
            if all(t.start < since_dt for t in matching_text_turns):
                continue
            post_turns = [t for t in matching_text_turns if t.start >= since_dt]
            if post_turns:
                matched_turn = post_turns[0]
        if matched_turn is None:
            # Nearest turn containing or closest to prompt timestamp
            containing = [t for t in turns if t.start <= item.start <= t.end]
            matched_turn = (
                containing[0]
                if containing
                else min(turns, key=lambda t: abs((t.start - item.start).total_seconds()))
            )
        item.turn_index = matched_turn.index
        kept.append(item)
    return kept


def _unique_slugs(session_ids: list[str]) -> dict[str, str]:
    counts: dict[str, int] = {}
    for sid in session_ids:
        counts[sid[:8]] = counts.get(sid[:8], 0) + 1
    return {sid: (sid[:8] if counts[sid[:8]] == 1 else sid) for sid in session_ids}


def render_prompts_markdown(
    prompts: list[MatchedPrompt],
    slug_by_session: dict[str, str],
    project: str,
    since_dt: datetime,
    ui_base_url: str | None = None,
) -> str:
    """Render a two-tier markdown index (summary table + blockquoted prompt entries)."""
    session_count = len({p.session_id for p in prompts})
    lines = [
        f"# User Prompts Since `{since_dt.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        "",
        f"- **Project:** {project}",
        f"- **Since:** {fmt_time(since_dt)}",
        f"- **Matched prompts:** {len(prompts)} across {session_count} session(s)",
        "",
    ]
    if not prompts:
        lines.append("No human user prompts recorded since this cursor.")
        return "\n".join(lines) + "\n"

    lines += [
        "## Summary",
        "",
        "| # | Time (UTC) | Session | Source | Preview | Outline |",
        "| -: | - | - | - | - | - |",
    ]
    for idx, p in enumerate(prompts, start=1):
        slug = slug_by_session[p.session_id]
        src_label = f"{p.source} #{p.message_id}" if p.message_id else p.source
        preview = escape_cell(one_line(p.text, 60))
        outline_ref = f"{slug}.outline.md#t{p.turn_index}"
        lines.append(
            f"| [{idx}](#p{idx}) | {p.start.astimezone(UTC).strftime('%m-%d %H:%M:%S')} | "
            f"`{slug}` | {escape_cell(src_label)} | {preview} | "
            f"[{slug}#t{p.turn_index}]({outline_ref}) |"
        )

    lines += ["", "## Prompts", ""]
    for idx, p in enumerate(prompts, start=1):
        slug = slug_by_session[p.session_id]
        outline_ref = f"{slug}.outline.md#t{p.turn_index}"
        src_head = f"{p.source} #{p.message_id}" if p.message_id else p.source
        link_parts = [f"[outline]({outline_ref})"]
        if ui_base_url:
            link_parts.append(f"[session]({ui_base_url}/redirects/sessions/{p.session_id})")
            if p.span_id:
                link_parts.append(f"[span]({ui_base_url}/redirects/spans/{p.span_id})")
        meta_parts = [f"`session_id: {p.session_id}`"]
        if p.span_id:
            meta_parts.append(f"`span_id: {p.span_id}`")
        meta_parts.append(f"`source: {p.source}`")
        if p.message_id:
            meta_parts.append(f"`message_id: {p.message_id}`")
        if p.thread_id:
            meta_parts.append(f"`thread_id: {p.thread_id}`")
        if p.host:
            meta_parts.append(f"`host: {p.host}`")

        lines += [
            f'<a id="p{idx}"></a>',
            "",
            f"### {idx} · {fmt_time(p.start)} · `{slug}` · {escape_cell(src_head)}",
            "",
            f"- **Links:** {' · '.join(link_parts)}",
            f"- **Metadata:** {' · '.join(meta_parts)}",
            "",
            quote(p.text),
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


# --- CLI ---------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phoenix_transcript.py",
        description="Render a session's Phoenix spans as a markdown transcript, or scan human user prompts since a UTC cursor.",
    )
    parser.add_argument(
        "ident",
        nargs="?",
        default=None,
        help="session ID / conversation ID, session slug (ID prefix), or 32-hex trace ID",
    )
    parser.add_argument(
        "--since",
        help="discover human user prompts since this ISO-8601 timestamp (explicit timezone offset required, e.g. 2026-11-14T08:45:32Z) and write outline transcripts for matches",
    )
    parser.add_argument("--base-url", help=f"Phoenix base URL (else ${BASE_URL_ENV_VAR})")
    parser.add_argument(
        "--ui-base-url",
        help=f"Phoenix UI base URL (else ${UI_BASE_URL_ENV_VAR}, or derived from base URL)",
    )
    parser.add_argument("--project", help=f"Phoenix project name (else ${PROJECT_ENV_VAR})")
    parser.add_argument(
        "--from-file", help="render spans from a saved JSON payload instead of fetching"
    )
    parser.add_argument(
        "--prices", help="JSON price table (model -> in/out/cache_read/cache_write USD per M)"
    )
    parser.add_argument(
        "--out",
        help="transcript path in single-session mode, or output directory in --since mode",
    )
    parser.add_argument(
        "--sanitize-paths",
        action="store_true",
        help="sanitize literal host filesystem paths (e.g. /home/*, /Users/*) for durable PKB persistence",
    )
    return parser


def run_since(args: argparse.Namespace, prices: dict[str, dict[str, float]]) -> int:
    since_dt = parse_since_utc(args.since)
    if args.from_file:
        project = args.project or os.environ.get(PROJECT_ENV_VAR, "") or "(from file)"
        universe = load_spans_from_file(Path(args.from_file).expanduser())
        base_url = (args.base_url or os.environ.get(BASE_URL_ENV_VAR, "")).strip() or None
        candidates = discover_prompts_from_spans(universe, since_dt)
    else:
        base_url = resolve_base_url(args.base_url)
        project = resolve_project(args.project)
        universe = []
        candidates = fetch_prompts_since(base_url, project, since_dt)

    ui_base_url = resolve_ui_base_url(getattr(args, "ui_base_url", None), base_url)
    out_dir = Path(args.out).expanduser() if args.out else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)

    ordered_sids = list(dict.fromkeys(p.session_id for p in candidates))
    prelim_slugs = _unique_slugs(ordered_sids)
    kept_prompts: list[MatchedPrompt] = []
    outlines_to_write: list[tuple[str, str]] = []

    for sid in ordered_sids:
        if args.from_file:
            spans = [s for s in universe if str(attr(s, "session.id")) == sid]
        else:
            assert base_url is not None
            spans, _ = fetch_session_spans(base_url, project, sid)
        session_prompts = [p for p in candidates if p.session_id == sid]
        if not spans:
            kept_prompts.extend(session_prompts)
            continue
        spans.sort(key=start_of)
        turns = assemble(spans, sid, prices)
        bound = _assign_turn_and_filter_stale(session_prompts, turns, since_dt)
        if not bound:
            continue
        kept_prompts.extend(bound)
        _, outline, _ = render(turns, sid, project, spans, prices, ui_base_url=ui_base_url)
        if getattr(args, "sanitize_paths", False):
            outline = sanitize_paths(outline)
        outlines_to_write.append((sid, outline))

    kept_prompts.sort(key=lambda p: p.start)
    final_sids = list(dict.fromkeys(p.session_id for p in kept_prompts))
    slug_by_session = _unique_slugs(final_sids) if final_sids else prelim_slugs

    written_outlines: list[Path] = []
    for sid, outline in outlines_to_write:
        if sid not in slug_by_session:
            continue
        outline_path = out_dir / f"{slug_by_session[sid]}.outline.md"
        outline_path.write_text(outline)
        written_outlines.append(outline_path)

    prompts_md = render_prompts_markdown(
        kept_prompts, slug_by_session, project, since_dt, ui_base_url=ui_base_url
    )
    if getattr(args, "sanitize_paths", False):
        prompts_md = sanitize_paths(prompts_md)
    prompts_path = out_dir / "prompts.md"
    prompts_path.write_text(prompts_md)

    print(
        f"prompts:  {prompts_path} ({len(kept_prompts)} matched across {len(final_sids)} session(s))"
    )
    for p in written_outlines:
        print(f"outline:  {p}")
    return 0


def run(args: argparse.Namespace) -> int:
    if args.ident and args.since:
        raise ConfigError("pass either <ident> or --since, not both")
    if not args.ident and not args.since:
        raise ConfigError("missing target: pass <ident> or --since <iso-timestamp>")

    prices = dict(PRICES)
    if args.prices:
        prices.update(json.loads(Path(args.prices).expanduser().read_text()))

    if args.since:
        return run_since(args, prices)

    if args.from_file:
        project = args.project or os.environ.get(PROJECT_ENV_VAR, "") or "(from file)"
        universe = load_spans_from_file(Path(args.from_file).expanduser())
        ids = sorted({str(attr(s, "session.id")) for s in universe if attr(s, "session.id")})
        matches = [i for i in ids if i.startswith(args.ident)] or [
            str(attr(s, "session.id")) for s in universe if trace_id(s) == args.ident
        ][:1]
        if len(set(matches)) > 1:
            raise ConfigError(
                f"{args.ident!r} matches several sessions in the file: {', '.join(matches)}"
            )
        session_id = matches[0] if matches else args.ident
        spans = [s for s in universe if str(attr(s, "session.id")) == session_id]
        base_url = (args.base_url or os.environ.get(BASE_URL_ENV_VAR, "")).strip() or None
    else:
        base_url = resolve_base_url(args.base_url)
        project = resolve_project(args.project)
        session_id = resolve_session_id(base_url, project, args.ident)
        spans, _ = fetch_session_spans(base_url, project, session_id)

    ui_base_url = resolve_ui_base_url(getattr(args, "ui_base_url", None), base_url)

    if not spans:
        print(
            f"no spans for session {session_id!r} in project {project!r}. Check the identifier's "
            "shape (session id, slug, or 32-hex trace id); the store may also have evicted it.",
            file=sys.stderr,
        )
        return EXIT_EMPTY

    spans.sort(key=start_of)
    turns = assemble(spans, session_id, prices)
    text, outline, summary = render(
        turns, session_id, project, spans, prices, ui_base_url=ui_base_url
    )
    if getattr(args, "sanitize_paths", False):
        text = sanitize_paths(text)
        outline = sanitize_paths(outline)
    out = (
        Path(args.out).expanduser() if args.out else Path.cwd() / f"{session_id[:8]}.transcript.md"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    outline_path = out.with_name(
        out.name.removesuffix(".md").removesuffix(".transcript") + ".outline.md"
    )
    outline_path.write_text(outline)
    print(f"transcript: {out} ({fmt_n(len(text))} chars)")
    print(f"outline:    {outline_path} ({fmt_n(len(outline))} chars)\n")
    print(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    raise SystemExit(main())
