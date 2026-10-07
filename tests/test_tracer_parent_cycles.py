"""The Claude Code tracer never emits spans whose parent links form a loop.

Phoenix's span insertion walks a new span's ancestors with a recursive CTE
that has no loop guard, so two spans that name each other as parent stall its
writer. These tests drive the real hook handlers and the real OTel SDK, and
inspect the parent ids of the spans that reach the exporter.

Concurrency is real (threads, each taking the tracer's own flock); the
interleaving is forced by a barrier inside the stand-in exporter, so the
schedule two parallel hook processes can produce is reproduced on every run.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import claude_code_tracer as cct

CONFIG = {"endpoint": "http://collector.invalid:4318", "project_name": "test"}
SESSION = "sess-parent-cycles"
BARRIER_TIMEOUT_S = 1.0


class _CollectingExporter(SpanExporter):
    """Records every exported span; optionally holds named spans at a barrier."""

    def __init__(self, hold: set[str] | None = None, parties: int = 2) -> None:
        self.spans: list[ReadableSpan] = []
        self._lock = threading.Lock()
        self._hold = hold or set()
        self._barrier = threading.Barrier(parties)

    def export(self, spans):
        for sp in spans:
            if sp.name in self._hold:
                # Wait until the other hook process has reached its export too.
                # A timeout only means the code under test serialised the two
                # calls; it is not a failure in itself.
                try:
                    self._barrier.wait(timeout=BARRIER_TIMEOUT_S)
                except threading.BrokenBarrierError:
                    pass
            with self._lock:
                self.spans.append(sp)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


@pytest.fixture
def tracer_env(tmp_path, monkeypatch):
    monkeypatch.setattr(cct, "STATE_DIR", tmp_path / "tracer")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    return tmp_path


def _agent_input(desc: str) -> dict:
    return {"description": desc, "prompt": f"do {desc}", "subagent_type": "general-purpose"}


def _pre(tool_name: str, tool_input: dict) -> None:
    cct.handle_pre_tool(
        {"session_id": SESSION, "tool_name": tool_name, "tool_input": tool_input},
        CONFIG,
    )


def _post(tool_name: str, tool_input: dict) -> None:
    cct.handle_post_tool(
        {
            "session_id": SESSION,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_response": {"status": "ok"},
        },
        CONFIG,
    )


def _run_parallel(*fns) -> None:
    errors: list[BaseException] = []

    def wrap(fn):
        def run():
            try:
                fn()
            except BaseException as e:
                errors.append(e)

        return run

    threads = [threading.Thread(target=wrap(fn)) for fn in fns]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors, errors


def _parent_map(spans: list[ReadableSpan]) -> dict[int, int | None]:
    out: dict[int, int | None] = {}
    for sp in spans:
        assert sp.context is not None
        out[sp.context.span_id] = sp.parent.span_id if sp.parent else None
    return out


def _cycles(parents: dict[int, int | None]) -> list[int]:
    """Span ids whose parent chain (within the exported set) returns to them."""
    looping = []
    for start in parents:
        seen: set[int] = set()
        cur = parents.get(start)
        while cur is not None and cur not in seen:
            if cur == start:
                looping.append(start)
                break
            seen.add(cur)
            cur = parents.get(cur)
    return looping


def _turn_root_span_id() -> int:
    state = cct._load_state(SESSION)
    return int(state["current_trace"]["root_span_id"], 16)


def test_parallel_agent_calls_completing_together_do_not_parent_each_other(tracer_env):
    """Two background Agent dispatches whose PostToolUse hooks run concurrently."""
    a, b = _agent_input("email sweep A"), _agent_input("email sweep B")
    _pre("Agent", a)
    _pre("Agent", b)
    root = _turn_root_span_id()

    exporter = _CollectingExporter(hold={"Agent"})
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _run_parallel(lambda: _post("Agent", a), lambda: _post("Agent", b))

    agents = [sp for sp in exporter.spans if sp.name == "Agent"]
    assert len(agents) == 2
    parents = _parent_map(agents)
    print(
        "agent span -> parent:",
        {f"{k:016x}": f"{v:016x}" if v else None for k, v in parents.items()},
    )
    assert _cycles(parents) == [], "Agent spans form a parent cycle"
    assert all(p == root for p in parents.values()), "Agent span parented under another Agent span"


def test_sequential_parallel_agents_are_both_parented_under_turn_root(tracer_env):
    """Even without a race, a finished Agent call is never nested under a sibling still running."""
    a, b = _agent_input("A"), _agent_input("B")
    _pre("Agent", a)
    _pre("Agent", b)
    root = _turn_root_span_id()

    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _post("Agent", a)
        _post("Agent", b)

    agents = [sp for sp in exporter.spans if sp.name == "Agent"]
    assert len(agents) == 2
    assert set(_parent_map(agents).values()) == {root}


def test_tool_call_inside_pending_agent_is_still_nested_under_it(tracer_env):
    """Inline subagent tool calls keep their Agent parent."""
    a = _agent_input("A")
    _pre("Agent", a)
    agent_span_id = int(
        cct._load_state(SESSION)["pending_tools"].popitem()[1]["pre_allocated_span_id"], 16
    )
    _pre("Read", {"file_path": "/x"})

    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _post("Read", {"file_path": "/x"})
        _post("Agent", a)

    (read_span,) = [sp for sp in exporter.spans if sp.name == "Read"]
    assert read_span.parent is not None
    assert read_span.parent.span_id == agent_span_id


def test_parallel_pre_tool_hooks_keep_every_pending_agent(tracer_env):
    """Concurrent PreToolUse hooks must not lose each other's pending entries."""
    a, b = _agent_input("A"), _agent_input("B")
    _pre("Read", {"file_path": "/warm"})  # create the turn so both hooks start from the same state

    barrier = threading.Barrier(2)
    real_load = cct._load_state

    def load_then_wait(session_id: str) -> dict:
        state = real_load(session_id)
        try:
            barrier.wait(timeout=BARRIER_TIMEOUT_S)
        except threading.BrokenBarrierError:
            pass
        return state

    with patch.object(cct, "_load_state", side_effect=load_then_wait):
        _run_parallel(lambda: _pre("Agent", a), lambda: _pre("Agent", b))

    pending = cct._load_state(SESSION)["pending_tools"]
    agent_inputs = [v["tool_input"] for k, v in pending.items() if k.startswith("Agent#")]
    assert a in agent_inputs and b in agent_inputs


def _export_records(records: list[dict]) -> dict[int, int | None]:
    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        cct._build_and_export_spans(
            config=CONFIG,
            session_id=SESSION,
            username="u",
            span_records=records,
            agent_name="a",
            cwd="/tmp",
        )
    return _parent_map(exporter.spans)


def _rec(span_id: str, parent: str | None) -> dict:
    return {
        "trace_id_hex": "0123456789abcdef0123456789abcdef",
        "span_id_hex": span_id,
        "parent_span_id_hex": parent,
        "name": "Agent",
        "kind": None,
        "start_ns": 1_000,
        "end_ns": 2_000,
        "attributes": {},
        "force_span_id": True,
    }


def test_export_never_emits_a_self_parented_span(tracer_env):
    parents = _export_records([_rec("00000000000000aa", "00000000000000aa")])
    assert parents == {0xAA: None}


def test_export_never_emits_a_mutual_parent_pair_in_one_batch(tracer_env):
    parents = _export_records(
        [_rec("00000000000000aa", "00000000000000bb"), _rec("00000000000000bb", "00000000000000aa")]
    )
    assert _cycles(parents) == []
    assert parents[0xAA] == 0xBB  # the first link stands; the one closing the loop is cut


def test_turn_root_whose_parent_chain_leads_back_to_it_is_emitted_unparented(tracer_env):
    """A loop through spans emitted earlier this turn is cut using the tracer's own record."""
    a = _agent_input("A")
    _pre("Agent", a)
    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _post("Agent", a)

    (agent_span,) = [sp for sp in exporter.spans if sp.name == "Agent"]
    assert agent_span.context is not None and agent_span.parent is not None
    root_id = agent_span.parent.span_id
    # The turn root names the Agent span (already recorded as root's child) as its parent.
    state = cct._load_state(SESSION)
    state["current_trace"]["parent_span_id"] = f"{agent_span.context.span_id:016x}"
    cct._save_state(SESSION, state)

    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        cct.handle_stop({"session_id": SESSION}, CONFIG)

    (turn,) = [sp for sp in exporter.spans if sp.name == "claude-code-turn"]
    assert turn.context is not None and turn.context.span_id == root_id
    assert turn.parent is None
