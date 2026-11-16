"""phoenix_transcript.py: turns, deduplicated tool calls, token normalisation, outline."""

import asyncio
import importlib.util
import json
import re
import sqlite3
import sys
import textwrap
from datetime import UTC, datetime
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "plugins/ida/skills/session-trace/scripts"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location(
    "phoenix_transcript", SCRIPTS / "phoenix_transcript.py"
)
pt = importlib.util.module_from_spec(_spec)
sys.modules["phoenix_transcript"] = pt
_spec.loader.exec_module(pt)

SESSION = "11111111-2222-4333-8444-555555555555"


def span(sid, name, kind, start, end, parent=None, **attributes):
    return {
        "name": name,
        "span_kind": kind,
        "context": {"trace_id": "a" * 32, "span_id": sid},
        "parent_id": parent,
        "start_time": f"2026-10-01T00:00:{start:06.3f}+00:00",
        "end_time": f"2026-10-01T00:00:{end:06.3f}+00:00",
        "status_code": "UNSET",
        "attributes": {"session.id": SESSION, **attributes},
    }


def two_emitter_turn():
    """One turn as two emitters record it: a hook tracer's CHAIN and a client's native spans."""
    return [
        span(
            "c1",
            "turn",
            "CHAIN",
            1,
            9,
            **{"input.value": "<msg from=x>\nWhy X?", "output.value": "Because Y."},
        ),
        span(
            "t1",
            "Bash",
            "TOOL",
            3,
            4,
            "c1",
            **{
                "tool.call_id": "toolu_1",
                "tool.name": "Bash",
                "input.value": json.dumps({"command": "ls", "description": "List files"}),
                "output.value": "a\nb",
            },
        ),
        span("i1", "interaction", "AGENT", 1.1, 9.1, user_prompt="Why X?"),
        span(
            "l1",
            "llm_request",
            "LLM",
            1.2,
            2.9,
            "i1",
            model="claude-opus-5-5",
            input_tokens=10,
            output_tokens=100,
            cache_read_tokens=1000,
            cache_creation_tokens=200,
            new_context="[USER]\nWhy X?",
            **{
                "output.value": '{"id": "req_1"}',
                "request_id": "req_1",
                "response.model_output": "Let me look.",
            },
        ),
        span(
            "n1",
            "tool",
            "TOOL",
            2.95,
            4.2,
            "i1",
            tool_use_id="toolu_1",
            tool_name="Bash",
            tool_input="[TOOL INPUT: Bash]\n{}",
        ),
        span("n2", "tool.blocked_on_user", "UNKNOWN", 2.96, 3.0, "n1"),
        span("h1", "hook", "UNKNOWN", 4.3, 4.4, "i1"),
        span(
            "l2",
            "llm_request",
            "LLM",
            4.5,
            8.0,
            "i1",
            model="claude-opus-5-5",
            input_tokens=5,
            output_tokens=20,
            cache_read_tokens=2000,
            cache_creation_tokens=0,
            request_id="req_2",
            **{"response.model_output": "Because Y."},
        ),
    ]


def test_two_emitters_make_one_turn_with_one_tool_call():
    turns = pt.assemble(sorted(two_emitter_turn(), key=pt.start_of), SESSION, pt.PRICES)
    assert len(turns) == 1
    turn = turns[0]
    assert [s.kind for s in turn.steps] == ["model", "tool", "model"]
    tool = turn.tool_steps[0]
    assert tool.title == "Bash"
    assert tool.action == "List files" and tool.hint == "ls"
    assert json.loads(tool.tool_input)["command"] == "ls"
    assert tool.duration_ms == 1250  # earliest start (2.95) to latest end (4.2)
    assert turn.prompt.endswith("Why X?") and turn.reply == "Because Y."
    assert pt.turn_title(turn) == "[msg] Why X?"
    assert [s["name"] for s in turn.others] == ["hook"]


def test_tokens_normalise_across_conventions():
    native = span(
        "a",
        "x",
        "LLM",
        0,
        1,
        input_tokens=10,
        output_tokens=5,
        cache_read_tokens=100,
        cache_creation_tokens=20,
    )
    openinference = span(
        "b",
        "x",
        "LLM",
        0,
        1,
        **{
            "llm.token_count.prompt": 130,
            "llm.token_count.completion": 5,
            "llm.token_count.prompt_details.cache_read": 100,
            "llm.token_count.prompt_details.cache_write": 20,
        },
    )
    genai = span(
        "c",
        "x",
        "LLM",
        0,
        1,
        **{
            "gen_ai.usage.input_tokens": 130,
            "gen_ai.usage.output_tokens": 5,
            "gen_ai.usage.cache_read.input_tokens": 100,
            "gen_ai.usage.cache_creation.input_tokens": 20,
        },
    )
    expected = {"in": 10, "cache_read": 100, "cache_write": 20, "out": 5}
    assert pt.tokens_of(native) == pt.tokens_of(openinference) == pt.tokens_of(genai) == expected


def test_flattened_openinference_messages():
    s = span(
        "a",
        "x",
        "LLM",
        0,
        1,
        **{
            "llm.output_messages.0.message.role": "assistant",
            "llm.output_messages.0.message.content": "Answer.",
        },
    )
    assert pt.model_text(s) == "Answer."


def test_transcript_and_outline(tmp_path, capsys):
    spans_file = tmp_path / "spans.json"
    spans_file.write_text(json.dumps({"data": two_emitter_turn()}))
    out = tmp_path / "s.transcript.md"
    assert pt.main([SESSION[:8], "--from-file", str(spans_file), "--out", str(out)]) == 0
    text = out.read_text()
    outline = (tmp_path / "s.outline.md").read_text()
    assert '<a id="t1"></a>' in text and "](#t1)" in text and '<a id="t1-2"></a>' in text
    assert "<details><summary>Input" in text and "<details>" not in outline
    assert "### 1.1 🧠 claude-opus-5-5" in outline and "1.2 List files: 🛠 Bash · " in outline
    assert "### 1.2 List files: 🛠 Bash — ls ·" in text
    # (10+5)*5 + (100+20)*25 + (1000+2000)*0.5 + 200*6.25 = 5,825 USD per million tokens
    assert "**Estimated cost:** $0.0058" in text
    assert "transcript:" in capsys.readouterr().out


def test_agy_tool_action_and_tool_request_output():
    args = {
        "DirectoryPath": "/x/axioms",
        "toolAction": "Listing axiom files",
        "toolSummary": "Axiom files",
    }
    assert pt.tool_action(json.dumps(args)) == "Listing axiom files"
    assert pt.tool_hint(json.dumps(args)) == "/x/axioms"
    assert pt.tool_hint('[TOOL INPUT: Read]\n{"file_path": "/a/b.md"}') == "/a/b.md"
    assert pt.tool_hint(
        json.dumps({"ServerName": "services", "ToolName": "search", "toolAction": "x"})
    ) == ("services.search")
    assert pt.is_tool_request(json.dumps([{"name": "list_dir", "args": args}]))
    assert not pt.is_tool_request("Let me look.")


def test_tool_detail_names_what_a_call_acted_on():
    code = (
        "async () => { const a = await codemode.pkb_get_document({ id: 'kb_1', max_bytes: 600 }); }"
    )
    agy = {
        "ServerName": "services",
        "ToolName": "portal_codemode_execute",
        "Arguments": {"code": code},
        "toolAction": "Reading proposal",
    }
    assert pt.tool_detail(json.dumps(agy)) == (
        "services.portal_codemode_execute: pkb_get_document(id=kb_1, max_bytes=600)"
    )
    assert pt.tool_detail(json.dumps({"code": code})) == "pkb_get_document(id=kb_1, max_bytes=600)"
    sql = 'res = await call_tool("executeSql", {"sql": "SELECT 1"})'
    assert pt.tool_detail(json.dumps({"code": sql})) == "executeSql(sql=SELECT 1)"
    assert pt.tool_detail(
        json.dumps({"CommandLine": 'python3 -c "\nprint(1)\n"', "toolAction": "x"})
    ) == ('python3 -c " print(1) "')


def test_tool_action_extracts_tool_summary():
    code = "async () => { const a = await codemode.pkb_claim_task({ id: 'item_12345678' }); }"
    agy = {
        "ServerName": "services",
        "ToolName": "portal_codemode_execute",
        "Arguments": {"code": code, "toolSummary": "Claim task item_12345678"},
    }
    assert pt.tool_action(json.dumps(agy)) == "Claim task item_12345678"

    direct = {
        "code": code,
        "toolSummary": "Search documents for ambiguous terms",
    }
    assert pt.tool_action(json.dumps(direct)) == "Search documents for ambiguous terms"


def test_resolve_endpoint_from_environment_variables(monkeypatch):
    """AC1: With only PHOENIX_MCP_URL and PHOENIX_MCP_PROJECT set, resolve from env vars."""
    monkeypatch.setenv("PHOENIX_MCP_URL", "http://phoenix.internal:6006/")
    monkeypatch.setenv("PHOENIX_MCP_PROJECT", "test-project")
    # Ensure legacy vars are not set
    monkeypatch.delenv("PHOENIX_BASE_URL", raising=False)
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    monkeypatch.delenv("PHOENIX_PROJECT_NAME", raising=False)

    assert pt.resolve_base_url(None) == "http://phoenix.internal:6006"
    assert pt.resolve_project(None) == "test-project"


def test_resolve_endpoint_from_explicit_flags(monkeypatch):
    """AC2: Explicit flags take precedence over environment variables."""
    monkeypatch.setenv("PHOENIX_MCP_URL", "http://env-phoenix:6006")
    monkeypatch.setenv("PHOENIX_MCP_PROJECT", "env-project")

    assert pt.resolve_base_url("http://flag-phoenix:6006/") == "http://flag-phoenix:6006"
    assert pt.resolve_project("flag-project") == "flag-project"


def test_resolve_endpoint_supplies_no_default_when_unset(monkeypatch):
    """AC3: With neither flag nor variable set, script supplies no default value and fails."""
    monkeypatch.delenv("PHOENIX_MCP_URL", raising=False)
    monkeypatch.delenv("PHOENIX_MCP_PROJECT", raising=False)
    monkeypatch.delenv("PHOENIX_BASE_URL", raising=False)
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    monkeypatch.delenv("PHOENIX_PROJECT_NAME", raising=False)

    with pytest.raises(pt.ConfigError) as exc_url:
        pt.resolve_base_url(None)
    assert "no Phoenix base URL" in str(exc_url.value)

    with pytest.raises(pt.ConfigError) as exc_proj:
        pt.resolve_project(None)
    assert "no Phoenix project" in str(exc_proj.value)


def test_phoenix_trace_and_token_cost_canonical_env_vars_only(monkeypatch):
    """phoenix_trace and phoenix_token_cost resolve only PHOENIX_MCP_URL / PHOENIX_MCP_PROJECT and reject legacy vars."""
    import phoenix_token_cost as ptc
    import phoenix_trace as ptr

    monkeypatch.delenv("PHOENIX_MCP_URL", raising=False)
    monkeypatch.delenv("PHOENIX_MCP_PROJECT", raising=False)
    monkeypatch.setenv("PHOENIX_BASE_URL", "http://legacy-base:6006")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://legacy-collector:6006")
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "legacy-project")

    with pytest.raises(ptc.ConfigError, match="PHOENIX_MCP_URL"):
        ptc.resolve_base_url(None)
    with pytest.raises(ptr.ConfigError, match="PHOENIX_MCP_URL"):
        ptr.resolve_base_url(None)
    with pytest.raises(ptr.ConfigError, match="PHOENIX_MCP_PROJECT"):
        ptr.resolve_project_name(None, None)

    monkeypatch.setenv("PHOENIX_MCP_URL", "https://mcp.example.test/mcp/")
    monkeypatch.setenv("PHOENIX_MCP_PROJECT", "academicOps")
    assert ptc.resolve_base_url(None) == "https://mcp.example.test/mcp"
    assert ptr.resolve_base_url(None) == "https://mcp.example.test/mcp"
    assert ptr.resolve_project_name(None, None) == "academicOps"


class FakePhoenixMcpServer:
    """Process-boundary MCP proxy double backed by real in-memory SQLite tables.

    Mirrors Phoenix's relational span store (projects -> project_sessions -> traces -> spans),
    executeSql's 500-row / 262,144-byte caps and ISO timestamp literal rewriting, and
    reproduces #3642 by timing out if getSpans is called with an unindexed session.id filter.
    """

    ISO_LITERAL_RE = re.compile(
        r"'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)'"
    )

    def __init__(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                graphql_node_id TEXT NOT NULL
            );
            CREATE TABLE project_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                project_id INTEGER NOT NULL REFERENCES projects(id)
            );
            CREATE TABLE traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_rowid INTEGER NOT NULL REFERENCES projects(id),
                project_session_rowid INTEGER REFERENCES project_sessions(id),
                trace_id TEXT NOT NULL UNIQUE
            );
            CREATE TABLE spans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_rowid INTEGER NOT NULL REFERENCES traces(id),
                span_id TEXT NOT NULL UNIQUE,
                parent_id TEXT,
                name TEXT NOT NULL,
                span_kind TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                attributes TEXT NOT NULL,
                events TEXT NOT NULL,
                status_code TEXT NOT NULL,
                status_message TEXT NOT NULL,
                graphql_node_id TEXT NOT NULL
            );
            """
        )
        self.recorded_requests: list[tuple[str, dict[str, str], dict]] = []
        self.tool_calls: list[tuple[str, dict]] = []
        self._openapi_spans: list[dict] = []
        self.max_sql_rows: int = 500
        self.max_row_bytes: int = 262_144
        self.sql_error: dict | None = None
        self.get_spans_error: str | None = None
        self.omit_hydrated_span_ids: set[str] = set()

    def ensure_project(self, name: str = "test-project", node_id: str = "UHJvamVjdDox") -> int:
        row = self.conn.execute("SELECT id FROM projects WHERE name = ?", (name,)).fetchone()
        if row:
            return int(row[0])
        cur = self.conn.execute(
            "INSERT INTO projects (name, graphql_node_id) VALUES (?, ?)", (name, node_id)
        )
        return int(cur.lastrowid)

    def ensure_session(self, project_rowid: int, session_id: str) -> int:
        row = self.conn.execute(
            "SELECT id FROM project_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row:
            return int(row[0])
        cur = self.conn.execute(
            "INSERT INTO project_sessions (session_id, project_id) VALUES (?, ?)",
            (session_id, project_rowid),
        )
        return int(cur.lastrowid)

    def ensure_trace(self, project_rowid: int, trace_id: str, session_rowid: int | None) -> int:
        row = self.conn.execute("SELECT id FROM traces WHERE trace_id = ?", (trace_id,)).fetchone()
        if row:
            return int(row[0])
        cur = self.conn.execute(
            "INSERT INTO traces (project_rowid, project_session_rowid, trace_id) VALUES (?, ?, ?)",
            (project_rowid, session_rowid, trace_id),
        )
        return int(cur.lastrowid)

    @staticmethod
    def _nest_attributes(flat: dict) -> dict:
        nested: dict = {}
        for key, val in flat.items():
            parts = key.split(".")
            cur = nested
            for part in parts[:-1]:
                cur = cur.setdefault(part, {})
            cur[parts[-1]] = val
        return nested

    def add_span(
        self,
        *,
        project: str = "test-project",
        trace_session_id: str | None = SESSION,
        trace_id: str = "a" * 32,
        span_id: str,
        parent_id: str | None = None,
        name: str = "step",
        span_kind: str = "TOOL",
        start_sql: str = "2026-10-01 00:00:01.000000",
        end_sql: str = "2026-10-01 00:00:02.000000",
        flat_attributes: dict | None = None,
        nested_attributes: dict | None = None,
        events: list | None = None,
        status_code: str = "UNSET",
        status_message: str = "",
    ) -> int:
        proj_id = self.ensure_project(project)
        sess_rowid = (
            self.ensure_session(proj_id, trace_session_id) if trace_session_id is not None else None
        )
        trace_rowid = self.ensure_trace(proj_id, trace_id, sess_rowid)
        flat = dict(flat_attributes or {})
        raw_nested = (
            nested_attributes if nested_attributes is not None else self._nest_attributes(flat)
        )
        ev_list = list(events or [])
        cur = self.conn.execute(
            """
            INSERT INTO spans (
                trace_rowid, span_id, parent_id, name, span_kind,
                start_time, end_time, attributes, events,
                status_code, status_message, graphql_node_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace_rowid,
                span_id,
                parent_id,
                name,
                span_kind,
                start_sql,
                end_sql,
                json.dumps(raw_nested),
                json.dumps(ev_list),
                status_code,
                status_message,
                f"SpanNode:{span_id}",
            ),
        )
        start_iso = start_sql.replace(" ", "T", 1) + "+00:00"
        end_iso = end_sql.replace(" ", "T", 1) + "+00:00"
        self._openapi_spans.append(
            {
                "id": f"SpanNode:{span_id}",
                "name": name,
                "context": {"trace_id": trace_id, "span_id": span_id},
                "span_kind": span_kind,
                "parent_id": parent_id,
                "start_time": start_iso,
                "end_time": end_iso,
                "status_code": status_code,
                "status_message": status_message,
                "attributes": flat,
                "events": ev_list,
            }
        )
        return int(cur.lastrowid)

    def _rewrite_sql_timestamps(self, sql: str) -> str:
        def _repl(match: re.Match[str]) -> str:
            lit = match.group(1)
            norm = lit.replace(" ", "T", 1)
            if norm.endswith("Z"):
                norm = norm[:-1] + "+00:00"
            dt = datetime.fromisoformat(norm)
            if dt.tzinfo is None:
                raise ValueError(f"naive timestamp literal rejected: {lit}")
            utc_str = dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")
            return f"'{utc_str}'"

        return self.ISO_LITERAL_RE.sub(_repl, sql)

    async def _call_tool(self, tool_name: str, tool_args: dict) -> dict:
        self.tool_calls.append((tool_name, tool_args))
        if tool_name == "getProjects":
            rows = self.conn.execute("SELECT graphql_node_id, name FROM projects").fetchall()
            return {"data": [{"id": r[0], "name": r[1]} for r in rows], "next_cursor": None}
        if tool_name == "listProjectSessions":
            rows = self.conn.execute("SELECT session_id FROM project_sessions").fetchall()
            return {"data": [{"session_id": r[0]} for r in rows], "next_cursor": None}
        if tool_name == "executeSql":
            if self.sql_error is not None:
                return {"error": self.sql_error}
            try:
                rewritten = self._rewrite_sql_timestamps(tool_args["sql"])
                cur = self.conn.execute(rewritten)
                cols = [d[0] for d in (cur.description or [])]
                fetched = cur.fetchmany(self.max_sql_rows + 1)
            except Exception as exc:  # noqa: BLE001
                return {"error": {"code": "sql_error", "message": str(exc)}}
            partial = len(fetched) > self.max_sql_rows
            rows = [list(r) for r in fetched[: self.max_sql_rows]]
            for row in rows:
                if sum(len(str(cell or "").encode("utf-8")) for cell in row) > self.max_row_bytes:
                    return {
                        "error": {
                            "code": "row_too_large",
                            "message": "row exceeds 262144 byte executeSql cap",
                        }
                    }
            return {
                "columns": cols,
                "rows": rows,
                "row_count": len(rows),
                "row_count_is_partial": partial,
            }
        if tool_name == "getSpans":
            attrs = tool_args.get("attribute") or []
            if any(isinstance(a, str) and a.startswith("session.id:") for a in attrs):
                raise TimeoutError("MCP error -32001: Request timed out")
            if self.get_spans_error is not None:
                raise RuntimeError(self.get_spans_error)
            matched = list(self._openapi_spans)
            if "span_id" in tool_args:
                wanted = set(tool_args["span_id"]) - self.omit_hydrated_span_ids
                matched = [s for s in matched if s["context"]["span_id"] in wanted]
            if "trace_id" in tool_args:
                wanted_t = set(tool_args["trace_id"])
                matched = [s for s in matched if s["context"]["trace_id"] in wanted_t]
            if "span_kind" in tool_args:
                wanted_k = set(tool_args["span_kind"])
                matched = [s for s in matched if s["span_kind"] in wanted_k]
            limit = int(tool_args.get("limit", 100))
            return {"data": matched[:limit], "next_cursor": None}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    def urlopen(self, req, timeout=None):
        payload = json.loads(req.data.decode("utf-8"))
        headers = {k.lower(): v for k, v in req.header_items()}
        self.recorded_requests.append((req.full_url, headers, payload))

        class _FakeResponse:
            def __init__(self, body: str, resp_headers: dict[str, str] | None = None):
                self._body = body.encode("utf-8")
                self.headers = resp_headers or {}

            def read(self) -> bytes:
                return self._body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        if payload.get("method") == "initialize":
            return _FakeResponse(
                json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}}),
                resp_headers={"mcp-session-id": "mcp-sess-123"},
            )

        code = payload["params"]["arguments"]["code"]
        wrapped = "async def _run(call_tool):\n" + textwrap.indent(code, "    ")
        ns: dict = {}
        exec(wrapped, ns)
        try:
            out = asyncio.run(ns["_run"](self._call_tool))
            rpc_res = {
                "content": [{"type": "text", "text": json.dumps(out)}],
                "isError": False,
            }
        except Exception as exc:  # noqa: BLE001
            rpc_res = {
                "content": [{"type": "text", "text": str(exc)}],
                "isError": True,
            }
        sse = (
            "event: message\ndata: "
            + json.dumps({"jsonrpc": "2.0", "id": 2, "result": rpc_res})
            + "\n\n"
        )
        return _FakeResponse(sse)


def test_get_json_routes_through_services_mcp_proxy(monkeypatch):
    """get_json authenticates with CF-Access headers, reuses mcp-session-id, and parses SSE responses."""
    import phoenix_token_cost as ptc

    monkeypatch.setenv("DISPATCHER_MCP_TOKEN_ID", "test-cf-id")
    monkeypatch.setenv("DISPATCHER_MCP_TOKEN_SECRET", "test-cf-secret")
    ptc._MCP_SESSIONS.clear()

    server = FakePhoenixMcpServer()
    trace_hex = "b" * 32
    server.add_span(
        project="test-project",
        trace_id=trace_hex,
        span_id="0000000000000001",
        name="turn",
        span_kind="CHAIN",
        flat_attributes={"session.id": SESSION},
    )
    monkeypatch.setattr(ptc.urllib.request, "urlopen", server.urlopen)

    res = pt.get_json(
        f"https://mcp.example.test/mcp/v1/projects/test-project/spans?trace_id={trace_hex}&limit=10"
    )
    assert len(res["data"]) == 1
    assert res["data"][0]["context"]["span_id"] == "0000000000000001"
    assert res["next_cursor"] is None
    assert len(server.recorded_requests) == 2

    init_url, init_headers, init_payload = server.recorded_requests[0]
    assert init_url == "https://mcp.example.test/mcp"
    assert init_headers["cf-access-client-id"] == "test-cf-id"
    assert init_headers["cf-access-client-secret"] == "test-cf-secret"
    assert init_payload["method"] == "initialize"

    call_url, call_headers, call_payload = server.recorded_requests[1]
    assert call_url == "https://mcp.example.test/mcp"
    assert call_headers["mcp-session-id"] == "mcp-sess-123"
    assert call_payload["params"]["name"] == "phoenix_execute"


def test_fetch_session_spans_avoids_unindexed_attribute_timeout_and_normalises_rows(monkeypatch):
    """Session span fetches execute indexed SQL joins without hitting getSpans(attribute=session.id) timeout."""
    import phoenix_token_cost as ptc

    ptc._MCP_SESSIONS.clear()
    server = FakePhoenixMcpServer()
    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        span_id="1000000000000001",
        name="turn",
        span_kind="CHAIN",
        start_sql="2026-10-01 00:00:01.000000",
        end_sql="2026-10-01 00:00:09.000000",
        flat_attributes={
            "session.id": SESSION,
            "input.value": "Explain the decision.",
            "output.value": "Decision explained.",
        },
        events=[{"name": "turn.start", "timestamp": "2026-10-01T00:00:01+00:00", "attributes": {}}],
    )
    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        span_id="1000000000000002",
        parent_id="1000000000000001",
        name="llm_call",
        span_kind="LLM",
        start_sql="2026-10-01 00:00:02.000000",
        end_sql="2026-10-01 00:00:08.000000",
        nested_attributes={
            "session": {"id": SESSION},
            "llm": {
                "model_name": "claude-opus-5-5",
                "token_count": {
                    "prompt": 130,
                    "completion": 25,
                    "prompt_details": {"cache_read": 100, "cache_write": 20},
                },
                "output_messages": [
                    {"message": {"role": "assistant", "content": "Decision explained."}}
                ],
            },
        },
    )
    monkeypatch.setattr(ptc.urllib.request, "urlopen", server.urlopen)

    spans, pages = pt.fetch_session_spans("https://mcp.example.test/mcp", "test-project", SESSION)
    assert pages == 1
    assert len(spans) == 2
    assert spans[0]["start_time"] == "2026-10-01T00:00:01.000000+00:00"
    assert spans[0]["events"][0]["name"] == "turn.start"
    assert spans[1]["attributes"]["llm.model_name"] == "claude-opus-5-5"
    assert isinstance(spans[1]["attributes"]["llm.output_messages"], list)

    turns = pt.assemble(spans, SESSION, pt.PRICES)
    assert len(turns) == 1
    assert turns[0].prompt == "Explain the decision."
    assert turns[0].reply == "Decision explained."
    assert turns[0].model_steps[0].tokens == {
        "in": 10,
        "cache_read": 100,
        "cache_write": 20,
        "out": 25,
    }


def test_fetch_session_spans_keyset_pagination_and_partial_pages(monkeypatch):
    """Session span paging preserves monotonic completeness across small page limits and partial SQL pages."""
    import phoenix_token_cost as ptc
    import phoenix_trace as ptr

    ptc._MCP_SESSIONS.clear()
    server = FakePhoenixMcpServer()
    for idx in range(1, 8):
        server.add_span(
            project="test-project",
            trace_session_id=SESSION,
            span_id=f"{idx:016x}",
            name=f"step-{idx}",
            span_kind="TOOL",
            start_sql=f"2026-10-01 00:00:{idx:02d}.000000",
            end_sql=f"2026-10-01 00:00:{idx:02d}.500000",
            flat_attributes={"session.id": SESSION},
        )
    monkeypatch.setattr(ptc.urllib.request, "urlopen", server.urlopen)

    # Caller-bounded page_limit=3 across 7 spans -> 3 pages (3 + 3 + 1)
    paged_spans, page_count = ptr.fetch_spans(
        "https://mcp.example.test/mcp", "test-project", SESSION, page_limit=3
    )
    assert page_count == 3
    assert [s["name"] for s in paged_spans] == [f"step-{i}" for i in range(1, 8)]

    # Backend-bounded partial pages (e.g. 4 MiB executeSql cap after 2 rows)
    server.max_sql_rows = 2
    all_spans, partial_pages = pt.fetch_session_spans(
        "https://mcp.example.test/mcp", "test-project", SESSION
    )
    assert partial_pages == 4
    assert [s["name"] for s in all_spans] == [f"step-{i}" for i in range(1, 8)]


def test_fetch_session_spans_keeps_null_session_children_and_excludes_foreign_spans(monkeypatch):
    """Child tool spans lacking session.id on session traces are kept; foreign session.id spans are excluded."""
    import phoenix_token_cost as ptc

    ptc._MCP_SESSIONS.clear()
    server = FakePhoenixMcpServer()
    other_session = "99999999-8888-4777-8666-555555555555"

    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        trace_id="c" * 32,
        span_id="2000000000000001",
        name="turn",
        span_kind="CHAIN",
        start_sql="2026-10-01 00:00:01.000000",
        end_sql="2026-10-01 00:00:05.000000",
        flat_attributes={"session.id": SESSION, "input.value": "Search"},
    )
    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        trace_id="c" * 32,
        span_id="2000000000000002",
        parent_id="2000000000000001",
        name="mcp.pkb.search",
        span_kind="TOOL",
        start_sql="2026-10-01 00:00:02.000000",
        end_sql="2026-10-01 00:00:04.000000",
        flat_attributes={
            "session.id": SESSION,
            "tool.call_id": "call_pkb_1",
            "tool.name": "pkb_search",
            "input.value": '{"query": "timeout"}',
        },
    )
    # Internal server child span with NULL session.id on the same trace
    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        trace_id="c" * 32,
        span_id="2000000000000003",
        parent_id="2000000000000002",
        name="search_hybrid",
        span_kind="INTERNAL",
        start_sql="2026-10-01 00:00:02.100000",
        end_sql="2026-10-01 00:00:04.500000",
        nested_attributes={"db": {"operation": "vector_scan"}},
    )
    # Contaminated foreign-session span sharing the trace
    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        trace_id="c" * 32,
        span_id="2000000000000004",
        parent_id="2000000000000001",
        name="foreign_span",
        span_kind="TOOL",
        start_sql="2026-10-01 00:00:03.000000",
        end_sql="2026-10-01 00:00:03.500000",
        flat_attributes={"session.id": other_session, "tool.name": "leaked"},
    )
    monkeypatch.setattr(ptc.urllib.request, "urlopen", server.urlopen)

    spans, _ = pt.fetch_session_spans("https://mcp.example.test/mcp", "test-project", SESSION)
    assert [s["name"] for s in spans] == ["turn", "mcp.pkb.search", "search_hybrid"]

    turns = pt.assemble(spans, SESSION, pt.PRICES)
    assert len(turns) == 1
    assert len(turns[0].tool_steps) == 1
    # Duration stretches from 2.0s to 4.5s because search_hybrid folded into mcp.pkb.search
    assert turns[0].tool_steps[0].duration_ms == 2500.0


def test_fetch_session_spans_hydrates_oversized_payloads_without_truncation(monkeypatch):
    """Spans exceeding SQLite row caps are projected safely and hydrated whole via indexed getSpans(span_id=...)."""
    import phoenix_token_cost as ptc

    ptc._MCP_SESSIONS.clear()
    server = FakePhoenixMcpServer()
    huge_output = "X" * 240_000
    huge_event_detail = "E" * 60_000

    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        span_id="3000000000000001",
        name="large_tool",
        span_kind="TOOL",
        flat_attributes={
            "session.id": SESSION,
            "tool.name": "Read",
            "output.value": huge_output,
        },
    )
    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        span_id="3000000000000002",
        name="large_events",
        span_kind="TOOL",
        flat_attributes={"session.id": SESSION, "tool.name": "Bash"},
        events=[{"name": "stdout", "attributes": {"chunk": huge_event_detail}}],
    )
    monkeypatch.setattr(ptc.urllib.request, "urlopen", server.urlopen)

    spans, _ = pt.fetch_session_spans("https://mcp.example.test/mcp", "test-project", SESSION)
    assert len(spans) == 2
    assert spans[0]["attributes"]["output.value"] == huge_output
    assert spans[1]["events"][0]["attributes"]["chunk"] == huge_event_detail


def test_fetch_session_spans_fails_fast_on_backend_or_hydration_errors(monkeypatch):
    """SQL errors, failed oversized-span hydrations, and invalid cursors raise ConfigError loudly."""
    import phoenix_token_cost as ptc

    ptc._MCP_SESSIONS.clear()
    server = FakePhoenixMcpServer()
    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        span_id="4000000000000001",
        name="oversized",
        span_kind="TOOL",
        flat_attributes={"session.id": SESSION, "output.value": "Z" * 220_000},
    )
    monkeypatch.setattr(ptc.urllib.request, "urlopen", server.urlopen)

    server.sql_error = {"code": "syntax_error", "message": "simulated SQL failure"}
    with pytest.raises(pt.ConfigError, match="simulated SQL failure"):
        pt.fetch_session_spans("https://mcp.example.test/mcp", "test-project", SESSION)
    server.sql_error = None

    server.omit_hydrated_span_ids.add("4000000000000001")
    with pytest.raises(pt.ConfigError, match="4000000000000001"):
        pt.fetch_session_spans("https://mcp.example.test/mcp", "test-project", SESSION)
    server.omit_hydrated_span_ids.clear()

    with pytest.raises(pt.ConfigError, match="cursor"):
        pt.get_json(
            f"https://mcp.example.test/mcp/v1/projects/test-project/spans"
            f"?attribute=session.id%3A{SESSION}&cursor=not-an-integer"
        )


def test_session_span_query_honours_time_kind_and_extra_attribute_filters(monkeypatch):
    """Additional span_kind, start_time/end_time, and attribute filters compose with session.id."""
    import phoenix_token_cost as ptc
    import phoenix_trace as ptr

    ptc._MCP_SESSIONS.clear()
    server = FakePhoenixMcpServer()
    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        span_id="5000000000000001",
        name="early_bash",
        span_kind="TOOL",
        start_sql="2026-10-01 01:00:00.000000",
        end_sql="2026-10-01 01:00:01.000000",
        flat_attributes={"session.id": SESSION, "tool.name": "Bash"},
    )
    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        span_id="5000000000000002",
        name="in_window_bash",
        span_kind="TOOL",
        start_sql="2026-10-01 02:30:00.000000",
        end_sql="2026-10-01 02:30:01.000000",
        flat_attributes={"session.id": SESSION, "tool.name": "Bash"},
    )
    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        span_id="5000000000000003",
        name="in_window_read",
        span_kind="TOOL",
        start_sql="2026-10-01 02:35:00.000000",
        end_sql="2026-10-01 02:35:01.000000",
        flat_attributes={"session.id": SESSION, "tool.name": "Read"},
    )
    server.add_span(
        project="test-project",
        trace_session_id=SESSION,
        span_id="5000000000000004",
        name="in_window_llm",
        span_kind="LLM",
        start_sql="2026-10-01 02:40:00.000000",
        end_sql="2026-10-01 02:40:01.000000",
        flat_attributes={"session.id": SESSION, "tool.name": "Bash"},
    )
    monkeypatch.setattr(ptc.urllib.request, "urlopen", server.urlopen)

    matched, _ = ptr.page_spans(
        "https://mcp.example.test/mcp",
        "test-project",
        [
            ("attribute", f"session.id:{SESSION}"),
            ("attribute", "tool.name:Bash"),
            ("span_kind", "TOOL"),
            ("start_time", "2026-10-01T02:00:00Z"),
            ("end_time", "2026-10-01T03:00:00Z"),
        ],
        page_limit=50,
    )
    assert [s["name"] for s in matched] == ["in_window_bash"]


def test_sanitize_paths(monkeypatch):
    monkeypatch.setenv("HOME", "/home/testuser")
    raw = (
        '{"path": "/home/testuser/project/file.py", '
        '"other": "/Users/developer/code/script.sh", '
        '"win": "C:\\\\Users\\\\alice\\\\data.txt", '
        '"tmp": "/tmp/claude-1000-xyz123/scratchpad"}'
    )
    sanitized = pt.sanitize_paths(raw)
    assert "/home/testuser" not in sanitized
    assert "/Users/developer" not in sanitized
    assert "C:\\\\Users\\\\alice" not in sanitized
    assert "/tmp/claude-1000-xyz123" not in sanitized
    assert "~/project/file.py" in sanitized
    assert "~/code/script.sh" in sanitized
    assert "~\\\\data.txt" in sanitized
    assert "/tmp/claude-session/scratchpad" in sanitized


def test_transcript_and_outline_with_sanitize_paths(tmp_path):
    spans_data = [
        span(
            "t1",
            "Bash",
            "TOOL",
            1,
            2,
            **{
                "tool.call_id": "toolu_1",
                "tool.name": "Bash",
                "input.value": json.dumps({"command": "ls /home/devuser/workspace"}),
                "output.value": "/home/devuser/workspace/README.md",
            },
        ),
        span("i1", "interaction", "AGENT", 0.5, 2.5, user_prompt="Check /home/devuser/workspace"),
    ]
    spans_file = tmp_path / "spans.json"
    spans_file.write_text(json.dumps({"data": spans_data}))
    out = tmp_path / "sanitized.transcript.md"
    assert (
        pt.main(
            [
                SESSION[:8],
                "--from-file",
                str(spans_file),
                "--out",
                str(out),
                "--sanitize-paths",
            ]
        )
        == 0
    )
    transcript = out.read_text()
    outline = (tmp_path / "sanitized.outline.md").read_text()
    assert "/home/devuser" not in transcript
    assert "~/workspace" in transcript
    assert "/home/devuser" not in outline
    assert "~/workspace" in outline


def test_turn_links_to_own_spans_in_transcript_and_outline():
    """AC1: Every turn in each markdown output links to its own span(s) in Phoenix."""
    spans = two_emitter_turn()
    turns = pt.assemble(spans, SESSION, pt.PRICES)
    full, outline, _ = pt.render(
        turns,
        SESSION,
        "academicOps",
        spans,
        pt.PRICES,
        ui_base_url="https://phoenix.example.test",
    )
    # Both c1 and i1 are turn roots
    assert "https://phoenix.example.test/redirects/spans/c1" in full
    assert "https://phoenix.example.test/redirects/spans/i1" in full
    assert "https://phoenix.example.test/redirects/spans/c1" in outline
    assert "https://phoenix.example.test/redirects/spans/i1" in outline


def test_turn_links_to_session_in_transcript_and_outline():
    """AC2: Every turn links to its session in Phoenix."""
    spans = two_emitter_turn()
    turns = pt.assemble(spans, SESSION, pt.PRICES)
    full, outline, _ = pt.render(
        turns,
        SESSION,
        "academicOps",
        spans,
        pt.PRICES,
        ui_base_url="https://phoenix.example.test",
    )
    expected_session_link = f"[session](https://phoenix.example.test/redirects/sessions/{SESSION})"
    assert expected_session_link in full
    assert expected_session_link in outline


def test_resolve_ui_base_url(monkeypatch):
    """Test resolution and derivation of Phoenix UI URL."""
    monkeypatch.delenv("PHOENIX_UI_URL", raising=False)
    # Derived from standard Phoenix base URL
    assert (
        pt.resolve_ui_base_url(None, "http://phoenix.internal:6006")
        == "http://phoenix.internal:6006"
    )
    assert pt.resolve_ui_base_url(None, "http://localhost:6006/") == "http://localhost:6006"

    # Derived from MCP proxy gateway URL (mcp. -> phoenix., strip /mcp)
    assert (
        pt.resolve_ui_base_url(None, "https://mcp.example.org/mcp") == "https://phoenix.example.org"
    )
    assert (
        pt.resolve_ui_base_url(None, "https://mcp.example.com/mcp") == "https://phoenix.example.com"
    )

    # Explicit flag overrides everything
    assert (
        pt.resolve_ui_base_url("https://custom.ui", "https://mcp.example.org/mcp")
        == "https://custom.ui"
    )

    # Environment variable PHOENIX_UI_URL overrides base_url derivation
    monkeypatch.setenv("PHOENIX_UI_URL", "https://env.ui")
    assert pt.resolve_ui_base_url(None, "https://mcp.example.org/mcp") == "https://env.ui"

    # None when no base_url and no env var
    monkeypatch.delenv("PHOENIX_UI_URL", raising=False)
    assert pt.resolve_ui_base_url(None, None) is None


def test_transcript_and_outline_contain_phoenix_links_via_cli(tmp_path):
    spans_data = two_emitter_turn()
    spans_file = tmp_path / "spans.json"
    spans_file.write_text(json.dumps({"data": spans_data}))
    out = tmp_path / "linked.transcript.md"
    assert (
        pt.main(
            [
                SESSION[:8],
                "--from-file",
                str(spans_file),
                "--out",
                str(out),
                "--base-url",
                "https://mcp.example.com/mcp",
            ]
        )
        == 0
    )
    transcript = out.read_text()
    outline = (tmp_path / "linked.outline.md").read_text()
    session_link = f"[session](https://phoenix.example.com/redirects/sessions/{SESSION})"
    assert session_link in transcript
    assert session_link in outline
    assert "https://phoenix.example.com/redirects/spans/c1" in transcript
    assert "https://phoenix.example.com/redirects/spans/c1" in outline


def _session_span(session_id, sid, name, kind, start_s, end_s, parent=None, **attributes):
    return {
        "name": name,
        "span_kind": kind,
        "context": {"trace_id": "b" * 32, "span_id": sid},
        "parent_id": parent,
        "start_time": f"2026-10-01T00:00:{start_s:06.3f}+00:00",
        "end_time": f"2026-10-01T00:00:{end_s:06.3f}+00:00",
        "status_code": "UNSET",
        "attributes": {"session.id": session_id, **attributes},
    }


def test_since_requires_explicit_timezone_and_mutually_excludes_ident(tmp_path, capsys):
    """--since fails fast on missing target, conflicting <ident>, malformed time, or naive time."""
    spans_file = tmp_path / "spans.json"
    spans_file.write_text(json.dumps({"data": []}))

    # Neither <ident> nor --since
    assert pt.main(["--from-file", str(spans_file)]) == pt.EXIT_CONFIG
    assert "error:" in capsys.readouterr().err

    # Both <ident> and --since
    assert (
        pt.main([SESSION[:8], "--since", "2026-10-01T00:00:00Z", "--from-file", str(spans_file)])
        == pt.EXIT_CONFIG
    )
    assert "error:" in capsys.readouterr().err

    # Naive timestamp without timezone offset must fail fast rather than guessing local/UTC
    assert (
        pt.main(["--since", "2026-10-01T00:00:00", "--from-file", str(spans_file)])
        == pt.EXIT_CONFIG
    )
    assert "timezone" in capsys.readouterr().err.lower()

    # Unparseable timestamp
    assert pt.main(["--since", "not-a-timestamp", "--from-file", str(spans_file)]) == pt.EXIT_CONFIG


def test_since_from_file_discovers_human_prompts_across_surfaces_and_writes_outlines(tmp_path):
    """--since extracts human prompts across CLI, channel, and agy surfaces while dropping subagent and system traffic."""
    s_cli = "aaaaaaaa-1111-4111-8111-111111111111"
    s_tg = "bbbbbbbb-2222-4222-8222-222222222222"
    s_agy = "cccccccc-3333-4333-8333-333333333333"
    s_sub = "dddddddd-4444-4444-8444-444444444444"
    s_worker = "eeeeeeee-5555-4555-8555-555555555555"

    universe = [
        # 1. Pre-cursor human prompt in s_cli (Turn 1 at 02.0s < cursor 05.0s) -> excluded from prompts.md
        _session_span(
            s_cli,
            "cli_t1",
            "claude-code-turn",
            "CHAIN",
            2.0,
            3.0,
            **{"input.value": "Earlier ask before cursor", "output.value": "Done earlier."},
        ),
        # 2. Post-cursor automated notification in s_cli (Turn 2 at 06.0s) -> excluded as wrapper
        _session_span(
            s_cli,
            "cli_t2",
            "claude-code-turn",
            "CHAIN",
            6.0,
            6.5,
            **{
                "input.value": "<task-notification>\nBackground job done\n</task-notification>",
                "output.value": "Noted.",
            },
        ),
        # 3. Post-cursor human terminal prompt in s_cli (Turn 3 at 08.0s) -> matched (#t3)!
        _session_span(
            s_cli,
            "cli_t3",
            "claude-code-turn",
            "CHAIN",
            8.0,
            9.5,
            **{
                "host.name": "workstation",
                "input.value": "Check /home/alice/repo status and summarize",
                "output.value": "Clean branch.",
            },
        ),
        # 4. Telegram channel message + duplicate delivery + reaction in s_tg -> matched once (#t1)!
        _session_span(
            s_tg,
            "tg_t1",
            "claude-code-turn",
            "CHAIN",
            10.0,
            11.0,
            **{
                "input.value": (
                    '<channel source="plugin:ida-telegram:telegram" event="message" '
                    'message_id="901" thread_id="55">\n'
                    "Please queue the bibliography export fix\n</channel>"
                ),
                "output.value": "Queued.",
            },
        ),
        _session_span(
            s_tg,
            "tg_dup",
            "claude-code-turn",
            "CHAIN",
            11.5,
            12.0,
            **{
                "input.value": (
                    '<channel source="plugin:ida-telegram:telegram" event="message" '
                    'message_id="901" thread_id="55">\n'
                    "Please queue the bibliography export fix\n</channel>"
                ),
                "output.value": "Already queued.",
            },
        ),
        _session_span(
            s_tg,
            "tg_react",
            "claude-code-turn",
            "CHAIN",
            12.5,
            13.0,
            **{
                "input.value": (
                    '<channel source="plugin:ida-telegram:telegram" event="reaction" '
                    'message_id="902">\n👍\n</channel>'
                ),
                "output.value": "",
            },
        ),
        # 5. Top-level agy session: UserPromptSubmit x2 + <USER_REQUEST> root CHAIN + invoke_subagent + <SYSTEM_MESSAGE>
        _session_span(
            s_agy,
            "agy_root1",
            "<USER_REQUEST>\n/ida:q make the sweeper lean\n</USER_REQUEST>",
            "CHAIN",
            14.0,
            20.0,
            **{
                "input.value": (
                    "<USER_REQUEST>\n/ida:q make the sweeper lean\n</USER_REQUEST>\n"
                    "<ADDITIONAL_METADATA>\n2026-10-01\n</ADDITIONAL_METADATA>"
                ),
                "output.value": "Delegated to custodian.",
            },
        ),
        _session_span(
            s_agy,
            "agy_ups1",
            "aops-debug.UserPromptSubmit",
            "CHAIN",
            14.1,
            14.2,
            parent="agy_root1",
            **{
                "hook.client": "agy",
                "input.value": json.dumps(
                    {
                        "conversationId": s_agy,
                        "lastUserInput": "/ida:q make the sweeper lean",
                    }
                ),
            },
        ),
        _session_span(
            s_agy,
            "agy_ups_empty",
            "aops-debug.UserPromptSubmit",
            "CHAIN",
            14.3,
            14.4,
            parent="agy_root1",
            **{
                "hook.client": "agy",
                "input.value": json.dumps({"conversationId": s_agy, "lastUserInput": ""}),
            },
        ),
        _session_span(
            s_agy,
            "agy_spawn",
            "invoke_subagent",
            "TOOL",
            15.0,
            15.5,
            parent="agy_root1",
            **{
                "tool.name": "invoke_subagent",
                "input.value": json.dumps({"TypeName": "pauli", "Prompt": "Subagent brief text"}),
                "output.value": (
                    'Created the following subagent:\n{\n  "conversationId": "' + s_sub + '"\n}'
                ),
            },
        ),
        _session_span(
            s_agy,
            "agy_sys",
            "The following is a <SYSTEM_MESSAGE> not actually sent by the user.",
            "CHAIN",
            21.0,
            22.0,
            **{
                "input.value": (
                    "The following is a <SYSTEM_MESSAGE> not actually sent by the user.\n"
                    "<SYSTEM_MESSAGE>[Message] sender=" + s_sub + " content=Done</SYSTEM_MESSAGE>"
                ),
                "output.value": "Verified.",
            },
        ),
        # 6. Spawned agy subagent session s_sub -> must be excluded via invoke_subagent provenance!
        _session_span(
            s_sub,
            "sub_ups",
            "aops-debug.UserPromptSubmit",
            "CHAIN",
            15.6,
            15.7,
            **{
                "hook.client": "agy",
                "input.value": json.dumps(
                    {"conversationId": s_sub, "lastUserInput": "Subagent brief text"}
                ),
            },
        ),
        # 7. Bare headless worker container launch prompt -> excluded!
        _session_span(
            s_worker,
            "wk_t1",
            "claude-code-turn",
            "CHAIN",
            25.0,
            30.0,
            **{"input.value": "/ida:supervise proj_deadbeef\n", "output.value": "Completed."},
        ),
    ]

    spans_file = tmp_path / "universe.json"
    spans_file.write_text(json.dumps({"data": universe}))
    out_dir = tmp_path / "sweep_out"

    rc = pt.main(
        [
            "--since",
            "2026-10-01T00:00:05Z",
            "--from-file",
            str(spans_file),
            "--out",
            str(out_dir),
            "--base-url",
            "https://mcp.example.com/mcp",
            "--sanitize-paths",
        ]
    )
    assert rc == 0

    prompts_md = (out_dir / "prompts.md").read_text()
    # Exactly the 3 post-cursor human prompts appear
    assert "Check ~/repo status and summarize" in prompts_md
    assert "/home/alice" not in prompts_md
    assert "Please queue the bibliography export fix" in prompts_md
    assert "/ida:q make the sweeper lean" in prompts_md

    # Excluded non-user / pre-cursor / subagent / headless traffic does NOT appear
    assert "Earlier ask before cursor" not in prompts_md
    assert "Background job done" not in prompts_md
    assert "Subagent brief text" not in prompts_md
    assert "/ida:supervise proj_deadbeef" not in prompts_md
    assert "SYSTEM_MESSAGE" not in prompts_md

    # Deep turn anchors and Phoenix UI links are present
    assert f"({s_cli[:8]}.outline.md#t3)" in prompts_md
    assert f"({s_tg[:8]}.outline.md#t1)" in prompts_md
    assert f"({s_agy[:8]}.outline.md#t1)" in prompts_md
    assert f"https://phoenix.example.com/redirects/sessions/{s_cli}" in prompts_md

    # Outline files generated ONLY for the 3 matched human sessions
    outline_names = sorted(p.name for p in out_dir.glob("*.outline.md"))
    assert outline_names == sorted(
        [f"{s_cli[:8]}.outline.md", f"{s_tg[:8]}.outline.md", f"{s_agy[:8]}.outline.md"]
    )
    assert "~/repo" in (out_dir / f"{s_cli[:8]}.outline.md").read_text()


def test_since_live_mcp_uses_indexed_sql_and_hydrates_oversized_spans(tmp_path, monkeypatch):
    """Live --since queries executeSql via phoenix_execute and hydrates oversized rows by span_id, never calling attribute=['session.id:...']."""
    import phoenix_token_cost as ptc

    ptc._MCP_SESSIONS.clear()
    executed_codes: list[str] = []

    matched_sid = "99999999-8888-4777-8666-555555555555"

    class FakeResponse:
        def __init__(self, body: str, headers: dict[str, str] | None = None):
            self._body = body.encode("utf-8")
            self.headers = headers or {}

        def read(self) -> bytes:
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def wrap_rpc(inner_obj) -> FakeResponse:
        return FakeResponse(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(inner_obj)}],
                        "isError": False,
                    },
                }
            )
        )

    def fake_urlopen(req, timeout=None):
        payload = json.loads(req.data.decode("utf-8"))
        if payload.get("method") == "initialize":
            return FakeResponse(
                json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}}),
                headers={"mcp-session-id": "mcp-live-1"},
            )
        code = payload["params"]["arguments"]["code"]
        executed_codes.append(code)
        assert "session.id:" not in code, "must not use unindexed attribute=session.id getSpans"
        for sql_comp in pt.re.findall(
            r"(?:p\.name|ps\.session_id|ps\.end_time|t\.end_time|s\.start_time)\s*(?:=|>=)\s*([^\s)]+)",
            code,
        ):
            assert sql_comp.startswith("'"), (
                f"SQLite strict parser requires single-quoted SQL literals, got {sql_comp}"
            )

        # 1. Discovery call (--since)
        if "aops-debug.UserPromptSubmit" in code:
            return wrap_rpc(
                {
                    "subagent_ids": [],
                    "chains": [
                        {
                            "id": 101,
                            "span_id": "sp_root",
                            "start_time": "2026-10-01T01:00:00Z",
                            "name_prefix": "claude-code-turn",
                            "session_id": matched_sid,
                            "host_name": "box1",
                            "agent_name": "ida",
                            "input_value": "Audit the bibliography parser",
                        }
                    ],
                    "ups": [],
                }
            )
        # 2. Session-spans indexed SQL + oversized hydration
        return wrap_rpc(
            {
                "data": [
                    {
                        "name": "claude-code-turn",
                        "span_kind": "CHAIN",
                        "context": {"trace_id": "c" * 32, "span_id": "sp_root"},
                        "parent_id": None,
                        "start_time": "2026-10-01T01:00:00Z",
                        "end_time": "2026-10-01T01:00:05Z",
                        "status_code": "OK",
                        "status_message": "",
                        "attributes": {
                            "session.id": matched_sid,
                            "input.value": "Audit the bibliography parser",
                            "output.value": "Parser audited.",
                        },
                    },
                    {
                        "name": "llm_call",
                        "span_kind": "LLM",
                        "context": {"trace_id": "c" * 32, "span_id": "sp_big"},
                        "parent_id": "sp_root",
                        "start_time": "2026-10-01T01:00:01Z",
                        "end_time": "2026-10-01T01:00:04Z",
                        "status_code": "OK",
                        "status_message": "",
                        "attributes": {
                            "session.id": matched_sid,
                            "llm.model_name": "claude-sonnet-5",
                            "llm.token_count.prompt": 500,
                            "llm.token_count.completion": 50,
                            "output.value": "Parser audited.",
                        },
                    },
                ],
                "next_cursor": None,
            }
        )

    monkeypatch.setattr(ptc.urllib.request, "urlopen", fake_urlopen)
    out_dir = tmp_path / "live_out"
    rc = pt.main(
        [
            "--since",
            "2026-10-01T00:30:00Z",
            "--out",
            str(out_dir),
            "--base-url",
            "https://mcp.example.com/mcp",
            "--project",
            "academicOps",
        ]
    )
    assert rc == 0
    assert (out_dir / f"{matched_sid[:8]}.outline.md").exists()
    assert "Audit the bibliography parser" in (out_dir / "prompts.md").read_text()
    assert len(executed_codes) == 2


def test_since_drops_stale_pre_cursor_agy_hook_echo_and_handles_empty_window(tmp_path):
    """A post-cursor UserPromptSubmit echoing an earlier pre-cursor turn prompt is dropped, and 0 matches exits 0."""
    s_agy = "77777777-6666-4555-8444-333333333333"
    spans_data = [
        # Pre-cursor human turn at 01.0s (< cursor 05.0s)
        _session_span(
            s_agy,
            "r_old",
            "<USER_REQUEST>\nOld pre-cursor ask\n</USER_REQUEST>",
            "CHAIN",
            1.0,
            3.0,
            **{
                "input.value": "<USER_REQUEST>\nOld pre-cursor ask\n</USER_REQUEST>",
                "output.value": "Working.",
            },
        ),
        # Post-cursor SYSTEM_MESSAGE wakeup at 07.0s whose hook echoes lastUserInput from Turn 1
        _session_span(
            s_agy,
            "r_sys",
            "The following is a <SYSTEM_MESSAGE> not actually sent by the user.",
            "CHAIN",
            7.0,
            9.0,
            **{
                "input.value": "The following is a <SYSTEM_MESSAGE> not actually sent by the user.\n<SYSTEM_MESSAGE>done</SYSTEM_MESSAGE>",
                "output.value": "Finished.",
            },
        ),
        _session_span(
            s_agy,
            "ups_echo",
            "aops-debug.UserPromptSubmit",
            "CHAIN",
            7.1,
            7.2,
            parent="r_sys",
            **{
                "hook.client": "agy",
                "input.value": json.dumps(
                    {"conversationId": s_agy, "lastUserInput": "Old pre-cursor ask"}
                ),
            },
        ),
    ]
    spans_file = tmp_path / "echo.json"
    spans_file.write_text(json.dumps({"data": spans_data}))
    out_dir = tmp_path / "quiet_out"

    rc = pt.main(
        ["--since", "2026-10-01T00:00:05Z", "--from-file", str(spans_file), "--out", str(out_dir)]
    )
    assert rc == 0
    prompts_md = (out_dir / "prompts.md").read_text()
    assert "No human user prompts recorded since this cursor." in prompts_md
    assert "Old pre-cursor ask" not in prompts_md
    assert list(out_dir.glob("*.outline.md")) == []
