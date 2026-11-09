"""phoenix_transcript.py: turns, deduplicated tool calls, token normalisation, outline."""

import importlib.util
import json
import sys
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


def span(
    sid, name, kind, start, end, parent=None, status_code="UNSET", status_message="", **attributes
):
    return {
        "name": name,
        "span_kind": kind,
        "context": {"trace_id": "a" * 32, "span_id": sid},
        "parent_id": parent,
        "start_time": f"2026-10-01T00:00:{start:06.3f}+00:00",
        "end_time": f"2026-10-01T00:00:{end:06.3f}+00:00",
        "status_code": status_code,
        "status_message": status_message,
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
    code = "async () => { const a = await codemode.pkb_claim_task({ id: 'aops_fa4c6994' }); }"
    agy = {
        "ServerName": "services",
        "ToolName": "portal_codemode_execute",
        "Arguments": {"code": code, "toolSummary": "Claim task aops_fa4c6994"},
    }
    assert pt.tool_action(json.dumps(agy)) == "Claim task aops_fa4c6994"

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


def test_get_json_routes_through_services_mcp_proxy(monkeypatch):
    """get_json translates Phoenix /v1/projects REST URLs into phoenix_execute MCP JSON-RPC calls with CF Access headers."""
    import phoenix_token_cost as ptc

    monkeypatch.setenv("DISPATCHER_MCP_TOKEN_ID", "test-cf-id")
    monkeypatch.setenv("DISPATCHER_MCP_TOKEN_SECRET", "test-cf-secret")
    ptc._MCP_SESSIONS.clear()

    recorded_requests = []

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

    def fake_urlopen(req, timeout=None):
        payload = json.loads(req.data.decode("utf-8"))
        headers = {k.lower(): v for k, v in req.header_items()}
        recorded_requests.append((req.full_url, headers, payload))
        if payload.get("method") == "initialize":
            return FakeResponse(
                json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}}),
                headers={"mcp-session-id": "mcp-sess-123"},
            )
        inner = json.dumps({"data": [{"id": "proj-1", "name": "academicOps"}], "next_cursor": None})
        sse = (
            "event: message\n"
            + "data: "
            + json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "result": {"content": [{"type": "text", "text": inner}], "isError": False},
                }
            )
            + "\n\n"
        )
        return FakeResponse(sse)

    monkeypatch.setattr(ptc.urllib.request, "urlopen", fake_urlopen)

    url = (
        "https://mcp.example.test/mcp/v1/projects/academicOps/spans"
        "?attribute=session.id%3Asess-42&limit=500"
    )
    res = pt.get_json(url)
    assert res == {"data": [{"id": "proj-1", "name": "academicOps"}], "next_cursor": None}
    assert len(recorded_requests) == 2

    init_url, init_headers, init_payload = recorded_requests[0]
    assert init_url == "https://mcp.example.test/mcp"
    assert init_headers["cf-access-client-id"] == "test-cf-id"
    assert init_headers["cf-access-client-secret"] == "test-cf-secret"
    assert init_payload["method"] == "initialize"

    call_url, call_headers, call_payload = recorded_requests[1]
    assert call_url == "https://mcp.example.test/mcp"
    assert call_headers["mcp-session-id"] == "mcp-sess-123"
    assert call_payload["params"]["name"] == "phoenix_execute"
    assert (
        call_payload["params"]["arguments"]["code"]
        == 'return await call_tool("getSpans", {"project_identifier": "academicOps", "limit": 500, "attribute": ["session.id:sess-42"]})'
    )


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
                "input.value": json.dumps({"command": "ls /home/nic/academicOps"}),
                "output.value": "/home/nic/academicOps/README.md",
            },
        ),
        span("i1", "interaction", "AGENT", 0.5, 2.5, user_prompt="Check /home/nic/academicOps"),
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
    assert "/home/nic" not in transcript
    assert "~/academicOps" in transcript
    assert "/home/nic" not in outline
    assert "~/academicOps" in outline


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
    assert pt.resolve_ui_base_url(None, "https://mcp.suzor.com/mcp") == "https://phoenix.suzor.com"
    assert (
        pt.resolve_ui_base_url(None, "https://mcp.example.com/mcp") == "https://phoenix.example.com"
    )

    # Explicit flag overrides everything
    assert (
        pt.resolve_ui_base_url("https://custom.ui", "https://mcp.suzor.com/mcp")
        == "https://custom.ui"
    )

    # Environment variable PHOENIX_UI_URL overrides base_url derivation
    monkeypatch.setenv("PHOENIX_UI_URL", "https://env.ui")
    assert pt.resolve_ui_base_url(None, "https://mcp.suzor.com/mcp") == "https://env.ui"

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


def test_extract_mcp_call_types():
    """Verify extraction of services proxy MCP call types across harnesses and conventions."""
    import phoenix_token_cost as ptc

    # 1. Code-mode block with codemode.<tool>
    code1 = "async () => { return await codemode.pkb_get_document({ id: 'doc_1' }); }"
    assert ptc.extract_mcp_call_types(
        "call_mcp_tool",
        {
            "ServerName": "services",
            "ToolName": "portal_codemode_execute",
            "Arguments": {"code": code1},
        },
    ) == ["pkb_get_document"]

    # 2. Code-mode block with call_tool("<tool>")
    code2 = 'res = await call_tool("executeSql", {"sql": "SELECT 1"})'
    assert ptc.extract_mcp_call_types(
        "portal_codemode_execute",
        {"code": code2},
    ) == ["executeSql"]

    # 3. Direct agy call_mcp_tool to services
    assert ptc.extract_mcp_call_types(
        "call_mcp_tool",
        {"ServerName": "services", "ToolName": "portal_list_servers"},
    ) == ["portal_list_servers"]

    # 4. Claude Code mcp__ convention
    assert ptc.extract_mcp_call_types("mcp__services__portal_list_servers") == [
        "portal_list_servers"
    ]
    assert ptc.extract_mcp_call_types("mcp__pkb__get_task") == ["get_task"]

    # 5. Direct prefix convention
    assert ptc.extract_mcp_call_types("pkb_search") == ["pkb_search"]
    assert ptc.extract_mcp_call_types("phoenix_trace") == ["phoenix_trace"]
    assert ptc.extract_mcp_call_types("mcp.search") == ["mcp.search"]

    # 6. Non-MCP tools
    assert ptc.extract_mcp_call_types("Bash", {"command": "ls"}) == []
    assert ptc.extract_mcp_call_types("run_command", {"CommandLine": "pytest"}) == []


def test_audit_artifact_and_mcp_metrics(tmp_path, capsys):
    """AC1 & AC2: phoenix_transcript produces pre-aggregated audit artifact with tool latency and proxy MCP token spend."""
    spans_data = [
        span("i1", "interaction", "AGENT", 1.0, 10.0, user_prompt="Audit test"),
        span(
            "l1",
            "llm_request",
            "LLM",
            1.1,
            2.0,
            "i1",
            model="claude-opus-5-5",
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=500,
            cache_creation_tokens=50,
            request_id="req_1",
            **{"response.model_output": "Calling tools."},
        ),
        # Services proxy MCP tool call 1: pkb_get_task via portal_codemode_execute
        span(
            "t1",
            "call_mcp_tool",
            "TOOL",
            2.1,
            3.1,
            "i1",
            **{
                "tool.call_id": "call_1",
                "input.value": json.dumps(
                    {
                        "ServerName": "services",
                        "ToolName": "portal_codemode_execute",
                        "Arguments": {
                            "code": "async () => { return await codemode.pkb_get_task({ id: 'aops_123' }); }"
                        },
                    }
                ),
            },
        ),
        # Services proxy MCP tool call 2: executeSql via portal_codemode_execute with error
        span(
            "t2",
            "portal_codemode_execute",
            "TOOL",
            3.2,
            5.2,
            "i1",
            status_code="ERROR",
            status_message="timeout connecting to phoenix",
            **{
                "tool.call_id": "call_2",
                "input.value": json.dumps(
                    {"code": 'res = await call_tool("executeSql", {"sql": "SELECT 1"})'}
                ),
            },
        ),
        # Non-MCP tool: Bash
        span(
            "t3",
            "Bash",
            "TOOL",
            5.5,
            6.0,
            "i1",
            **{
                "tool.call_id": "call_3",
                "input.value": json.dumps({"command": "echo done"}),
            },
        ),
    ]

    spans_file = tmp_path / "spans.json"
    spans_file.write_text(json.dumps({"data": spans_data}))
    out = tmp_path / "session.transcript.md"

    # Run phoenix_transcript CLI with --audit flag
    ret = pt.main(
        [
            SESSION[:8],
            "--from-file",
            str(spans_file),
            "--out",
            str(out),
            "--audit",
        ]
    )
    assert ret == 0

    # 1. Audit artifact is written beside transcript
    audit_file = tmp_path / "session.audit.md"
    assert audit_file.exists()
    audit_text = audit_file.read_text()

    # 2. Contains Model Token Spend table
    assert "## Model Token Spend" in audit_text
    assert "claude-opus-5-5" in audit_text

    # 3. Contains Tool Execution & Latency table (AC1)
    assert "## Tool Execution & Latency" in audit_text
    assert "portal_codemode_execute" in audit_text
    assert "call_mcp_tool" in audit_text
    assert "Bash" in audit_text

    # 4. Contains Services Proxy MCP Calls table (AC2)
    assert "## Services Proxy MCP Calls" in audit_text
    assert "pkb_get_task" in audit_text
    assert "executeSql" in audit_text

    # 5. Efficiency analysis
    assert "## Efficiency Analysis" in audit_text
    assert "Most expensive MCP call type:" in audit_text
    assert "Slowest MCP call type (avg):" in audit_text

    # 6. Errors section
    assert "## Errors" in audit_text
    assert "timeout connecting to phoenix" in audit_text

    # 7. Captured stdout carries audit summary because --audit was supplied
    captured = capsys.readouterr().out
    assert "# Session Audit" in captured
    assert "audit: " in captured


def test_phoenix_token_cost_by_mcp(tmp_path, capsys):
    """AC2: phoenix_token_cost --by mcp groups token spend by services proxy MCP call type."""
    import phoenix_token_cost as ptc

    saved_payload = {
        "project": "academicOps",
        "window": ["2026-10-01T00:00:00Z", "2026-10-01T00:01:00Z"],
        "llm": [
            span(
                "l1",
                "llm_request",
                "LLM",
                1.0,
                2.0,
                model="claude-opus-5",
                input_tokens=1000,
                output_tokens=100,
                cache_read_tokens=5000,
                cache_creation_tokens=200,
            ),
            span(
                "l2",
                "llm_request",
                "LLM",
                3.0,
                4.0,
                model="claude-opus-5",
                input_tokens=2000,
                output_tokens=200,
                cache_read_tokens=8000,
                cache_creation_tokens=0,
            ),
        ],
        "tools": [
            span(
                "t1",
                "call_mcp_tool",
                "TOOL",
                1.5,
                2.5,
                **{
                    "input.value": json.dumps(
                        {
                            "ServerName": "services",
                            "ToolName": "portal_codemode_execute",
                            "Arguments": {"code": "await codemode.pkb_search({ query: 'test' })"},
                        }
                    )
                },
            ),
            span(
                "t2",
                "portal_codemode_execute",
                "TOOL",
                3.5,
                4.5,
                **{
                    "input.value": json.dumps(
                        {"code": 'call_tool("executeSql", {"sql": "SELECT 1"})'}
                    )
                },
            ),
        ],
        "chains": [span("c1", "chain", "CHAIN", 0.5, 5.0)],
        "agents": [],
    }

    spans_file = tmp_path / "spans_mcp.json"
    spans_file.write_text(json.dumps(saved_payload))

    # 1. Plain text rendering
    ret = ptc.main(
        ["--since", "2026-10-01T00:00:00Z", "--from-file", str(spans_file), "--by", "mcp"]
    )
    assert ret == 0
    out = capsys.readouterr().out
    assert "Token cost by services proxy MCP call type" in out
    assert "pkb_search" in out
    assert "executeSql" in out

    # 2. Markdown rendering
    ret = ptc.main(
        [
            "--since",
            "2026-10-01T00:00:00Z",
            "--from-file",
            str(spans_file),
            "--by",
            "mcp",
            "--markdown",
        ]
    )
    assert ret == 0
    md_out = capsys.readouterr().out
    assert "| mcp_call_type | calls | in | out | cache_rd | cache_wr | USD |" in md_out
    assert "| pkb_search |" in md_out
    assert "| executeSql |" in md_out

    # 3. JSON rendering
    ret = ptc.main(
        [
            "--since",
            "2026-10-01T00:00:00Z",
            "--from-file",
            str(spans_file),
            "--by",
            "mcp",
            "--json",
        ]
    )
    assert ret == 0
    parsed = json.loads(capsys.readouterr().out)
    assert "rows" in parsed and "meta" in parsed
    assert parsed["meta"]["by"] == "mcp"
    mcp_names = {r["mcp_call_type"] for r in parsed["rows"]}
    assert "pkb_search" in mcp_names
    assert "executeSql" in mcp_names


def test_audit_custom_out_and_sanitize_paths(tmp_path):
    """Verify custom audit output destination and host path sanitization in audit artifact."""
    spans_data = [
        span(
            "t1",
            "call_mcp_tool",
            "TOOL",
            1,
            2,
            **{
                "tool.call_id": "toolu_1",
                "input.value": json.dumps(
                    {
                        "ServerName": "services",
                        "ToolName": "portal_codemode_execute",
                        "Arguments": {
                            "code": "async () => { return await codemode.pkb_get_document({ path: '/home/nic/test.md' }); }"
                        },
                    }
                ),
            },
        ),
        span("i1", "interaction", "AGENT", 0.5, 2.5, user_prompt="Check file"),
    ]
    spans_file = tmp_path / "spans.json"
    spans_file.write_text(json.dumps({"data": spans_data}))
    out_transcript = tmp_path / "custom.transcript.md"
    custom_audit = tmp_path / "reports" / "my_session_audit.md"

    ret = pt.main(
        [
            SESSION[:8],
            "--from-file",
            str(spans_file),
            "--out",
            str(out_transcript),
            "--audit-out",
            str(custom_audit),
            "--sanitize-paths",
        ]
    )
    assert ret == 0
    assert custom_audit.exists()
    audit_content = custom_audit.read_text()
    assert "/home/nic" not in audit_content
    assert "~/test.md" in audit_content or "pkb_get_document" in audit_content
