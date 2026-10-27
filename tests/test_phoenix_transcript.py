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
