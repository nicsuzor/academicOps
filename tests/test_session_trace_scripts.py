import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

SCRIPT = (
    Path(__file__).parent.parent
    / "plugins"
    / "aops"
    / "skills"
    / "session-trace"
    / "scripts"
    / "phoenix_trace.py"
)
FIXTURE = Path(__file__).parent / "fixtures" / "phoenix_spans_sample.json"
EDGE_FIXTURE = Path(__file__).parent / "fixtures" / "phoenix_spans_edge_cases.json"
SESSION = "11111111-2222-3333-4444-555555555555"
CYCLE_SESSION = "22222222-2222-2222-2222-222222222222"
CHAIN_ONLY_SESSION = "33333333-3333-3333-3333-333333333333"
SPAWN_SESSION = "44444444-4444-4444-4444-444444444444"

TRANSCRIPT = """---
session_id: 11111111-2222-3333-4444-555555555555
slug: 11111111
---
# Session 11111111-2222-3333-4444-555555555555 Controlling Agent Transcript

## 🧵 Subagents

## 📜 Chronological Events

#### 🛠️ Tool call: `Bash` `(2026-01-02T00:00:03.000Z)`

#### 🛠️ Tool call: `Agent` — *survey the docs* `(2026-01-02T00:00:04.000Z)`

#### 🛠️ Tool call: `Edit` `(2026-01-02T00:00:10.000Z)`

#### 🛠️ Tool call: `Write` `(2026-01-02T00:00:14.000Z)`
"""


def run_script(
    *args: str, expect: int = 0, project: str | None = "default"
) -> subprocess.CompletedProcess[str]:
    """Invoke the exporter with a clean environment; no test may reach the network.

    ``project`` supplies ``PHOENIX_PROJECT_NAME``, which the script now requires.
    Pass ``project=None`` to exercise the unset case.
    """
    env = {k: v for k, v in os.environ.items() if k not in ("AOPS_SESSIONS", "PHOENIX_BASE_URL")}
    env["PHOENIX_COLLECTOR_ENDPOINT"] = ""
    env.pop("PHOENIX_PROJECT_NAME", None)
    if project is not None:
        env["PHOENIX_PROJECT_NAME"] = project
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env
    )
    assert result.returncode == expect, f"rc={result.returncode}\n{result.stdout}\n{result.stderr}"
    return result


@pytest.fixture
def transcript(tmp_path: Path) -> Path:
    path = tmp_path / "20260102-00-adhoc-11111111.controller.md"
    path.write_text(TRANSCRIPT, encoding="utf-8")
    return path


def write_transcript(tmp_path: Path, session: str, lines: list[str]) -> Path:
    """A controller transcript holding exactly the given tool-call lines."""
    body = "\n\n".join(f"#### 🛠️ Tool call: `{name}` `({when})`" for name, when in lines)
    path = tmp_path / f"{session[:8]}.controller.md"
    path.write_text(
        f"---\nsession_id: {session}\n---\n\n## 📜 Chronological Events\n\n{body}\n",
        encoding="utf-8",
    )
    return path


class _PhoenixStub(BaseHTTPRequestHandler):
    """A minimal Phoenix API over loopback, so paging is exercisable without a server.

    Serves the sample fixture's spans one page at a time, honouring ``limit`` and
    ``cursor`` exactly as the real endpoint does, and filtering on ``attribute``,
    ``trace_id`` and ``span_id`` — the three filters the exporter issues. ``trace_id``
    and ``span_id`` are repeatable arrays in the Phoenix OpenAPI schema, so the stub
    matches against every value given.
    """

    spans: list[dict[str, object]] = []
    queries: list[dict[str, list[str]]] = []

    def log_message(self, *args: object) -> None:  # noqa: A003 - silence the access log
        pass

    def _send(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's contract
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/v1/projects":
            self._send({"data": [{"id": "proj-1", "name": "default"}]})
            return
        if parsed.path.endswith("/sessions"):
            self._send({"data": [{"session_id": SESSION, "traces": [1, 2]}], "next_cursor": None})
            return
        self.queries.append(query)
        matched = list(self.spans)
        for clause in query.get("attribute", []):
            key, _, value = clause.partition(":")
            matched = [s for s in matched if _attributes(s).get(key) == value]
        if "trace_id" in query:
            matched = [s for s in matched if _context(s)["trace_id"] in query["trace_id"]]
        if "span_id" in query:
            matched = [s for s in matched if _context(s)["span_id"] in query["span_id"]]

        limit = int(query.get("limit", ["1000"])[0])
        offset = int(query.get("cursor", ["0"])[0])
        page = matched[offset : offset + limit]
        nxt = offset + limit
        self._send({"data": page, "next_cursor": str(nxt) if nxt < len(matched) else None})


def _attributes(span: dict[str, object]) -> dict[str, object]:
    value = span.get("attributes", {})
    assert isinstance(value, dict)
    return value


def _context(span: dict[str, object]) -> dict[str, str]:
    value = span.get("context", {})
    assert isinstance(value, dict)
    return value


@pytest.fixture
def phoenix_stub() -> Iterator[str]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # The whole fixture, other sessions included: the stub filters, as the server does.
    _PhoenixStub.spans = payload["data"]
    _PhoenixStub.queries = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _PhoenixStub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_missing_base_url_exits_non_zero(tmp_path: Path):
    result = run_script(SESSION, "--out", str(tmp_path), expect=2)
    assert "no Phoenix base URL" in result.stderr
    assert "PHOENIX_BASE_URL" in result.stderr
    assert "PHOENIX_COLLECTOR_ENDPOINT" in result.stderr


def test_unknown_session_exits_non_zero(tmp_path: Path):
    result = run_script(
        "00000000-0000-0000-0000-000000000000",
        "--from-file",
        str(FIXTURE),
        "--out",
        str(tmp_path),
        expect=1,
    )
    assert "no spans for session" in result.stderr
    assert "--list-sessions" in result.stderr


def test_full_mode_nests_tree_and_reports_orphans(tmp_path: Path):
    run_script(SESSION, "--mode", "full", "--from-file", str(FIXTURE), "--out", str(tmp_path))
    doc = load(tmp_path / f"{SESSION}.trace.json")
    meta = doc["meta"]
    assert isinstance(meta, dict)
    roots = doc["roots"]
    orphans = doc["orphans"]
    assert isinstance(roots, list)
    assert isinstance(orphans, list)

    # The span from a different session is filtered out; twelve remain.
    assert meta["span_count"] == 12
    assert meta["error_count"] == 1
    assert meta["span_kind_counts"] == {"AGENT": 1, "CHAIN": 2, "LLM": 2, "TOOL": 7}
    assert meta["trace_count"] == 2
    assert meta["token_totals"] == {
        "prompt": 1400,
        "completion": 160,
        "total": 1560,
        "cache_read": 1100,
        "cache_write": 70,
    }

    # Roots come out oldest-first, and the parent_id forest nests.
    assert [r["context"]["span_id"] for r in roots] == [
        "aaaa000000000001",
        "aaaa000000000008",
    ]
    first_children = [c["context"]["span_id"] for c in roots[0]["children"]]
    assert first_children == [
        "aaaa000000000002",
        "aaaa000000000003",
        "aaaa000000000004",
    ]
    agent = roots[0]["children"][2]
    assert [c["context"]["span_id"] for c in agent["children"]] == [
        "aaaa000000000005",
        "aaaa000000000006",
    ]
    # Nesting is transitive, not one level deep.
    assert agent["children"][0]["children"][0]["context"]["span_id"] == "aaaa000000000007"

    # The span whose parent is absent from the fetch is reported, not dropped,
    # and says which of the two orphan causes applies.
    assert [o["context"]["span_id"] for o in orphans] == ["aaaa000000000010"]
    assert orphans[0]["orphan_reason"] == "parent_not_in_fetch"

    # Latency is computed, and attribute values are carried verbatim.
    assert roots[0]["children"][1]["duration_ms"] == pytest.approx(310.0)
    assert roots[0]["children"][1]["attributes"]["input.value"] == '{"command": "git status"}'


def test_controller_mode_joins_transcript_and_collapses_subagents(tmp_path: Path, transcript: Path):
    run_script(
        SESSION,
        "--mode",
        "controller",
        "--from-file",
        str(FIXTURE),
        "--transcript",
        str(transcript),
        "--out",
        str(tmp_path),
    )
    doc = load(tmp_path / f"{SESSION}.trace.controller.json")
    meta = doc["meta"]
    assert isinstance(meta, dict)
    attribution = meta["attribution"]
    assert isinstance(attribution, dict)
    events = doc["events"]
    subagents = doc["subagents"]
    assert isinstance(events, list)
    assert isinstance(subagents, list)

    assert attribution["method"] == "transcript-join"
    assert attribution["matched"] == 4
    assert attribution["ambiguous"] == 0
    assert attribution["unmatched"] == 0
    assert attribution["warnings"] == []
    assert attribution["transcript_path"] == str(transcript)

    # Two roots, four joined tool calls, and the two controller-turn LLM spans.
    assert [e["span_id"] for e in events] == [
        "aaaa000000000001",
        "aaaa000000000002",
        "aaaa000000000003",
        "aaaa000000000004",
        "aaaa000000000008",
        "aaaa000000000009",
        "aaaa000000000011",
        "aaaa000000000012",
    ]
    # Subagent tool calls never appear as controller events.
    assert {"aaaa000000000005", "aaaa000000000006", "aaaa000000000007"}.isdisjoint(
        e["span_id"] for e in events
    )

    dispatch = next(e for e in events if e["span_id"] == "aaaa000000000004")
    assert dispatch["collapsed_subagent_spans"] == 3
    failed = next(e for e in events if e["span_id"] == "aaaa000000000009")
    assert failed["status_code"] == "ERROR"
    assert failed["status_message"] == "String to replace not found in file."
    assert failed["output_chars"] == 49

    llm = next(e for e in events if e["span_id"] == "aaaa000000000002")
    assert llm["model"] == "test-model-1"
    assert llm["token_counts"]["cache_read"] == 800

    assert len(subagents) == 1
    assert subagents[0]["agent_name"] == "general-purpose"
    assert subagents[0]["collapsed_span_count"] == 3
    assert subagents[0]["status"] == "completed"
    assert subagents[0]["dispatch_prompt_chars"] == 50

    # Only the orphan is left unattributed to either trunk.
    assert doc["unattributed_span_count"] == 1


def test_controller_meta_names_session_and_controller_populations_apart(
    tmp_path: Path, transcript: Path
):
    """B1: whole-session figures must never be readable as describing this document."""
    run_script(
        SESSION,
        "--mode",
        "controller",
        "--from-file",
        str(FIXTURE),
        "--transcript",
        str(transcript),
        "--out",
        str(tmp_path),
    )
    doc = load(tmp_path / f"{SESSION}.trace.controller.json")
    meta = doc["meta"]
    events = doc["events"]
    assert isinstance(meta, dict)
    assert isinstance(events, list)

    # No bare, population-ambiguous name survives in the controller document.
    for bare in ("span_count", "error_count", "token_totals", "span_kind_counts", "status_counts"):
        assert bare not in meta, f"{bare} is ambiguous in a controller-only document"

    # Session figures cover all 12 spans; controller figures cover exactly events[].
    assert meta["session_span_count"] == 12
    assert meta["controller_span_count"] == len(events) == 8
    assert meta["session_error_count"] == 1
    assert meta["controller_error_count"] == 1  # the failed Edit is on the controller trunk
    assert meta["session_token_totals"]["total"] == 1560
    assert meta["controller_token_totals"]["total"] == 1560  # both LLM spans are controller spans
    # Subagent tool spans are in the session count and not in the controller count:
    # of the seven TOOL spans, three are on the trunk and the rest are subagent work.
    assert meta["session_span_kind_counts"]["TOOL"] == 7
    assert meta["controller_span_kind_counts"] == {"AGENT": 1, "CHAIN": 2, "LLM": 2, "TOOL": 3}


def test_subagent_duration_is_flagged_when_it_measures_only_the_spawn(tmp_path: Path):
    """B2: a teammate_spawned AGENT span's duration is a spawn ack, and says so."""
    run_script(
        SPAWN_SESSION,
        "--mode",
        "controller",
        "--from-file",
        str(EDGE_FIXTURE),
        "--out",
        str(tmp_path),
    )
    doc = load(tmp_path / f"{SPAWN_SESSION}.trace.controller.json")
    subagents = doc["subagents"]
    assert isinstance(subagents, list)
    by_name = {s["agent_name"]: s for s in subagents}

    spawned = by_name["pauli"]
    assert spawned["status"] == "teammate_spawned"
    assert spawned["duration_is_dispatch_only"] is True
    # 91 ms of "duration" against a session spanning over an hour.
    assert spawned["duration_ms"] == pytest.approx(91.1)
    assert spawned["collapsed_span_count"] == 0

    completed = by_name["general-purpose"]
    assert completed["status"] == "completed"
    assert completed["duration_is_dispatch_only"] is False
    assert completed["collapsed_span_count"] == 1

    # Lineage: every dispatch can be placed without a tree renderer.
    for entry in subagents:
        assert entry["parent_id"] == "eeee000000000001"
        assert entry["root_span_id"] == "eeee000000000001"
        assert entry["trace_id"] == "trace0000000000000000000000000006"


def test_claimed_span_collision_is_not_reported_as_a_tolerance_miss(tmp_path: Path):
    """D3: two calls competing for one span is a collision, and widening will not help."""
    path = write_transcript(
        tmp_path,
        SESSION,
        [("Bash", "2026-01-02T00:00:03.000Z"), ("Bash", "2026-01-02T00:00:03.050Z")],
    )
    run_script(
        SESSION,
        "--mode",
        "controller",
        "--from-file",
        str(FIXTURE),
        "--transcript",
        str(path),
        "--out",
        str(tmp_path),
    )
    doc = load(tmp_path / f"{SESSION}.trace.controller.json")
    meta = doc["meta"]
    assert isinstance(meta, dict)
    attribution = meta["attribution"]
    assert isinstance(attribution, dict)
    warnings = attribution["warnings"]
    assert isinstance(warnings, list)

    # Both calls are inside the 500 ms window; only one span exists for them.
    assert attribution["matched"] == 1
    assert attribution["unmatched"] == 1
    assert attribution["collisions"] == 1
    assert len(warnings) == 1
    assert "collision" in warnings[0]
    assert "matched no span within" not in warnings[0]
    assert "will NOT help" in warnings[0]


def test_cycle_disconnected_from_every_root_is_promoted_not_dropped(tmp_path: Path):
    """D4: the forest is a partition of the input, cycles included."""
    result = run_script(
        CYCLE_SESSION,
        "--mode",
        "full",
        "--from-file",
        str(EDGE_FIXTURE),
        "--out",
        str(tmp_path),
    )
    assert "4 spans, 1 roots, 1 orphans" in result.stdout
    doc = load(tmp_path / f"{CYCLE_SESSION}.trace.json")
    meta = doc["meta"]
    roots = doc["roots"]
    orphans = doc["orphans"]
    assert isinstance(meta, dict)
    assert isinstance(roots, list)
    assert isinstance(orphans, list)

    reached: list[str] = []

    def walk(node: dict[str, object]) -> None:
        context = node["context"]
        assert isinstance(context, dict)
        reached.append(str(context["span_id"]))
        children = node["children"]
        assert isinstance(children, list)
        for child in children:
            walk(child)

    for entry in [*roots, *orphans]:
        walk(entry)

    # Every input span is reachable exactly once — nothing silently dropped.
    assert len(reached) == meta["span_count"] == 4
    assert sorted(reached) == [
        "cccc00000000000a",
        "cccc00000000000b",
        "cccc00000000000r",
        "cccc00000000000s",
    ]
    assert [o["orphan_reason"] for o in orphans] == ["parent_cycle"]


def test_chain_only_session_emits_one_instrumentation_warning(tmp_path: Path):
    """D5: one warning naming the real cause, not one per unjoinable transcript line."""
    calls = [("Bash", f"2026-01-04T00:00:{n:02d}.000Z") for n in range(30)]
    path = write_transcript(tmp_path, CHAIN_ONLY_SESSION, calls)
    run_script(
        CHAIN_ONLY_SESSION,
        "--mode",
        "controller",
        "--from-file",
        str(EDGE_FIXTURE),
        "--transcript",
        str(path),
        "--out",
        str(tmp_path),
    )
    doc = load(tmp_path / f"{CHAIN_ONLY_SESSION}.trace.controller.json")
    meta = doc["meta"]
    assert isinstance(meta, dict)
    attribution = meta["attribution"]
    assert isinstance(attribution, dict)
    warnings = attribution["warnings"]
    assert isinstance(warnings, list)

    assert meta["session_span_kind_counts"] == {"CHAIN": 2}
    assert attribution["unmatched"] == 30
    assert len(warnings) == 1
    assert "no TOOL or AGENT spans in this session" in warnings[0]
    assert "instrumentation gap, not a tolerance problem" in warnings[0]
    assert "Changing --tolerance-ms cannot help" in warnings[0]


def test_per_line_warnings_are_capped_with_a_tail_count(tmp_path: Path):
    """D5: a readable warning block even when every line misses."""
    calls = [("Write", f"2026-01-03T12:00:{n:02d}.000Z") for n in range(25)]
    path = write_transcript(tmp_path, CYCLE_SESSION, calls)
    run_script(
        CYCLE_SESSION,
        "--mode",
        "controller",
        "--from-file",
        str(EDGE_FIXTURE),
        "--transcript",
        str(path),
        "--out",
        str(tmp_path),
    )
    doc = load(tmp_path / f"{CYCLE_SESSION}.trace.controller.json")
    meta = doc["meta"]
    assert isinstance(meta, dict)
    attribution = meta["attribution"]
    assert isinstance(attribution, dict)
    warnings = attribution["warnings"]
    assert isinstance(warnings, list)

    # This session does have TOOL spans, so the per-line path runs and is capped.
    assert attribution["unmatched"] == 25
    assert len(warnings) == 21
    assert "matched no span within 500 ms" in warnings[0]
    assert warnings[-1] == "…and 5 further per-line warnings, suppressed"


def test_page_limit_pages_to_the_same_span_set(tmp_path: Path, phoenix_stub: str):
    """--page-limit makes the paging loop exercisable from the CLI."""
    single = run_script(
        SESSION, "--mode", "full", "--base-url", phoenix_stub, "--out", str(tmp_path / "one")
    )
    assert "12 spans" in single.stdout
    whole = load(tmp_path / "one" / f"{SESSION}.trace.json")
    whole_meta = whole["meta"]
    assert isinstance(whole_meta, dict)
    assert whole_meta["fetch_pages"] == 1

    paged = run_script(
        SESSION,
        "--mode",
        "full",
        "--base-url",
        phoenix_stub,
        "--page-limit",
        "5",
        "--out",
        str(tmp_path / "many"),
    )
    assert "12 spans" in paged.stdout
    chunked = load(tmp_path / "many" / f"{SESSION}.trace.json")
    chunked_meta = chunked["meta"]
    assert isinstance(chunked_meta, dict)
    # 12 spans at 5 per page: three requests, the last one short.
    assert chunked_meta["fetch_pages"] == 3

    def span_ids(doc: dict[str, object]) -> set[str]:
        found: set[str] = set()
        stack = [*doc["roots"], *doc["orphans"]]  # pyright: ignore[reportGeneralTypeIssues]
        while stack:
            node = stack.pop()
            found.add(node["context"]["span_id"])
            stack.extend(node["children"])
        return found

    assert span_ids(chunked) == span_ids(whole)
    assert len(span_ids(whole)) == 12


def test_list_sessions_prints_what_the_server_retains(phoenix_stub: str):
    result = run_script("--list-sessions", "--base-url", phoenix_stub)
    assert "1 session(s) retained in project 'default'" in result.stdout
    assert SESSION in result.stdout
    assert "traces=2" in result.stdout


def test_unknown_project_names_the_ones_that_exist(tmp_path: Path, phoenix_stub: str):
    result = run_script(
        SESSION, "--base-url", phoenix_stub, "--project", "nope", "--out", str(tmp_path), expect=2
    )
    assert "project 'nope' not found" in result.stderr
    assert "default" in result.stderr


def test_controller_mode_reports_unmatched_calls(tmp_path: Path, transcript: Path):
    run_script(
        SESSION,
        "--mode",
        "controller",
        "--from-file",
        str(FIXTURE),
        "--transcript",
        str(transcript),
        "--tolerance-ms",
        "10",
        "--out",
        str(tmp_path),
    )
    doc = load(tmp_path / f"{SESSION}.trace.controller.json")
    meta = doc["meta"]
    assert isinstance(meta, dict)
    attribution = meta["attribution"]
    assert isinstance(attribution, dict)
    warnings = attribution["warnings"]
    assert isinstance(warnings, list)

    assert attribution["matched"] == 0
    assert attribution["unmatched"] == 4
    assert len(warnings) == 4
    assert "matched no span within 10 ms" in warnings[0]


def test_controller_mode_falls_back_without_transcript(tmp_path: Path):
    run_script(SESSION, "--mode", "controller", "--from-file", str(FIXTURE), "--out", str(tmp_path))
    doc = load(tmp_path / f"{SESSION}.trace.controller.json")
    meta = doc["meta"]
    assert isinstance(meta, dict)
    attribution = meta["attribution"]
    assert isinstance(attribution, dict)
    events = doc["events"]
    assert isinstance(events, list)

    assert attribution["method"] == "roots-only-fallback"
    assert "fidelity is reduced" in str(attribution["warning"])
    assert meta["transcript"] is None
    assert [e["span_id"] for e in events] == [
        "aaaa000000000001",
        "aaaa000000000004",
        "aaaa000000000008",
    ]


def test_missing_project_names_the_flag_and_the_env_var(tmp_path: Path):
    """No project is baked in (specs/ARCHITECTURE.md "No defaults"); it fails loudly."""
    result = run_script(
        SESSION,
        "--from-file",
        str(FIXTURE),
        "--out",
        str(tmp_path),
        project=None,
        expect=2,
    )
    assert "no Phoenix project" in result.stderr
    assert "--project" in result.stderr
    assert "PHOENIX_PROJECT_NAME" in result.stderr
    assert not list(tmp_path.glob("*.json"))


def test_missing_project_lists_what_the_server_holds(tmp_path: Path, phoenix_stub: str):
    """With a reachable server the error answers 'which one did you mean'."""
    result = run_script(
        SESSION,
        "--base-url",
        phoenix_stub,
        "--out",
        str(tmp_path),
        project=None,
        expect=2,
    )
    assert "PHOENIX_PROJECT_NAME" in result.stderr
    assert "Projects on this server: default" in result.stderr


def test_trace_contamination_is_reported_without_widening_the_export(tmp_path: Path):
    """One trace carries two sessions; the report says so and the export does not grow."""
    result = run_script(
        SESSION, "--mode", "full", "--from-file", str(FIXTURE), "--out", str(tmp_path)
    )
    doc = load(tmp_path / f"{SESSION}.trace.json")
    meta = doc["meta"]
    assert isinstance(meta, dict)
    report = meta["trace_contamination"]
    assert isinstance(report, dict)

    assert report["method"] == "from-file"
    assert report["contaminated_trace_count"] == 1
    assert report["foreign_span_count"] == 2
    assert report["traces"] == [
        {
            "trace_id": "trace0000000000000000000000000001",
            "in_session_spans": 7,
            "foreign_span_count": 0,
            "foreign_session_ids": [],
        },
        {
            "trace_id": "trace0000000000000000000000000002",
            "in_session_spans": 5,
            "foreign_span_count": 2,
            "foreign_session_ids": ["99999999-9999-9999-9999-999999999999"],
        },
    ]
    assert "1 of 2 trace(s) also carry other sessions' spans" in result.stdout

    # A report, not a widening: the exported set is still exactly the session's spans.
    assert meta["span_count"] == 12
    roots = doc["roots"]
    orphans = doc["orphans"]
    assert isinstance(roots, list)
    assert isinstance(orphans, list)
    exported: set[str] = set()
    stack = [*roots, *orphans]
    while stack:
        node = stack.pop()
        exported.add(node["context"]["span_id"])
        stack.extend(node["children"])
    assert len(exported) == 12
    assert "aaaa000000000013" not in exported
    assert "ffff0000deadbeef" not in exported


def test_contamination_check_queries_the_server_by_trace_id(tmp_path: Path, phoenix_stub: str):
    """Over HTTP the check is one batched trace_id query, not one request per trace."""
    run_script(SESSION, "--mode", "full", "--base-url", phoenix_stub, "--out", str(tmp_path))
    doc = load(tmp_path / f"{SESSION}.trace.json")
    meta = doc["meta"]
    assert isinstance(meta, dict)
    report = meta["trace_contamination"]
    assert isinstance(report, dict)

    assert report["method"] == "trace-id-fetch"
    assert report["contaminated_trace_count"] == 1
    assert report["foreign_span_count"] == 2
    assert meta["span_count"] == 12

    by_trace = [q for q in _PhoenixStub.queries if "trace_id" in q]
    assert len(by_trace) == 1, "both trace ids must be batched into one request"
    assert sorted(by_trace[0]["trace_id"]) == [
        "trace0000000000000000000000000001",
        "trace0000000000000000000000000002",
    ]
    # The session fetch still sends the bare, unquoted attribute filter.
    session_queries = [q for q in _PhoenixStub.queries if "attribute" in q]
    assert session_queries[0]["attribute"] == [f"session.id:{SESSION}"]


def test_contamination_check_can_be_skipped(tmp_path: Path):
    """Skipped is null, never confused with checked-and-clean."""
    run_script(
        SESSION,
        "--mode",
        "full",
        "--from-file",
        str(FIXTURE),
        "--no-contamination-check",
        "--out",
        str(tmp_path),
    )
    doc = load(tmp_path / f"{SESSION}.trace.json")
    meta = doc["meta"]
    assert isinstance(meta, dict)
    assert meta["trace_contamination"] is None


def test_orphan_parents_are_left_unresolved_by_default(tmp_path: Path):
    run_script(SESSION, "--mode", "full", "--from-file", str(FIXTURE), "--out", str(tmp_path))
    doc = load(tmp_path / f"{SESSION}.trace.json")
    assert doc["foreign_parents"] is None


def test_resolve_orphan_parents_keeps_them_out_of_roots_and_orphans(tmp_path: Path):
    """The orphan's parent belongs to another session, so it gets its own bucket."""
    run_script(
        SESSION,
        "--mode",
        "full",
        "--from-file",
        str(FIXTURE),
        "--resolve-orphan-parents",
        "--out",
        str(tmp_path),
    )
    doc = load(tmp_path / f"{SESSION}.trace.json")
    bucket = doc["foreign_parents"]
    assert isinstance(bucket, dict)
    resolved = bucket["resolved"]
    assert isinstance(resolved, list)

    assert bucket["method"] == "from-file"
    assert bucket["requested_parent_ids"] == ["ffff0000deadbeef"]
    assert bucket["unresolved_parent_ids"] == []
    assert len(resolved) == 1
    parent = resolved[0]
    assert parent["context"]["span_id"] == "ffff0000deadbeef"
    assert parent["owning_session_id"] == "99999999-9999-9999-9999-999999999999"
    assert parent["is_foreign_session"] is True
    assert parent["orphan_span_ids"] == ["aaaa000000000010"]

    # Never merged in as if it were ours.
    roots = doc["roots"]
    orphans = doc["orphans"]
    assert isinstance(roots, list)
    assert isinstance(orphans, list)
    assert all(r["context"]["span_id"] != "ffff0000deadbeef" for r in roots)
    assert [o["context"]["span_id"] for o in orphans] == ["aaaa000000000010"]
    meta = doc["meta"]
    assert isinstance(meta, dict)
    assert meta["span_count"] == 12


def test_resolve_orphan_parents_over_http_fetches_by_span_id(tmp_path: Path, phoenix_stub: str):
    run_script(
        SESSION,
        "--mode",
        "full",
        "--base-url",
        phoenix_stub,
        "--resolve-orphan-parents",
        "--out",
        str(tmp_path),
    )
    doc = load(tmp_path / f"{SESSION}.trace.json")
    bucket = doc["foreign_parents"]
    assert isinstance(bucket, dict)
    resolved = bucket["resolved"]
    assert isinstance(resolved, list)

    assert bucket["method"] == "span-id-fetch"
    assert [q["span_id"] for q in _PhoenixStub.queries if "span_id" in q] == [["ffff0000deadbeef"]]
    assert resolved[0]["owning_session_id"] == "99999999-9999-9999-9999-999999999999"


def test_both_modes_write_both_files(tmp_path: Path, transcript: Path):
    result = run_script(
        SESSION,
        "--mode",
        "both",
        "--from-file",
        str(FIXTURE),
        "--transcript",
        str(transcript),
        "--out",
        str(tmp_path),
    )
    assert (tmp_path / f"{SESSION}.trace.json").is_file()
    assert (tmp_path / f"{SESSION}.trace.controller.json").is_file()
    assert not (tmp_path / f"{SESSION}.controller.md").is_file()
    assert "12 spans, 2 roots, 1 orphans" in result.stdout
    assert "method=transcript-join, matched=4" in result.stdout


def test_markdown_mode_writes_controller_md(tmp_path: Path):
    result = run_script(
        SESSION,
        "--mode",
        "markdown",
        "--from-file",
        str(FIXTURE),
        "--out",
        str(tmp_path),
    )
    md_path = tmp_path / f"{SESSION}.controller.md"
    assert md_path.is_file()
    assert not (tmp_path / f"{SESSION}.trace.json").is_file()
    assert not (tmp_path / f"{SESSION}.trace.controller.json").is_file()
    content = md_path.read_text(encoding="utf-8")
    assert len(content) > 0
    assert f"markdown: {md_path}" in result.stdout


def test_all_mode_writes_all_three_files(tmp_path: Path, transcript: Path):
    result = run_script(
        SESSION,
        "--mode",
        "all",
        "--from-file",
        str(FIXTURE),
        "--transcript",
        str(transcript),
        "--out",
        str(tmp_path),
    )
    assert (tmp_path / f"{SESSION}.trace.json").is_file()
    assert (tmp_path / f"{SESSION}.trace.controller.json").is_file()
    md_path = tmp_path / f"{SESSION}.controller.md"
    assert md_path.is_file()
    content = md_path.read_text(encoding="utf-8")
    assert len(content) > 0
    assert "12 spans, 2 roots, 1 orphans" in result.stdout
    assert "method=transcript-join, matched=4" in result.stdout
    assert f"markdown: {md_path}" in result.stdout


def test_span_node_fallback_unique_id():
    from scripts.trace_to_markdown import SpanNode

    node1 = SpanNode({})
    node2 = SpanNode({})
    assert node1.span_id != ""
    assert node2.span_id != ""
    assert node1.span_id != node2.span_id


def test_trace_reconciler_orphan_turn_empty_timestamps():
    from scripts.trace_to_markdown import MarkdownRenderer, TraceReconciler

    trace_doc = {
        "meta": {"session_id": "test-session"},
        "roots": [],
        "orphans": [
            {
                "name": "orphan-1",
                "span_kind": "TOOL",
                "context": {"span_id": "o1", "trace_id": "t1"},
                "orphan_reason": "parent_not_in_fetch",
            },
            {
                "name": "orphan-2",
                "span_kind": "TOOL",
                "context": {"span_id": "o2", "trace_id": "t1"},
                "orphan_reason": "parent_not_in_fetch",
            },
        ],
    }
    reconciler = TraceReconciler(trace_doc)
    renderer = MarkdownRenderer(reconciler)
    md = renderer.render_controller_transcript()
    assert "test-session" in md
