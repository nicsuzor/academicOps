"""Offline checks for the Phoenix token-cost report. No test reaches the network."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).parent.parent
    / "plugins"
    / "aops"
    / "skills"
    / "session-trace"
    / "scripts"
    / "phoenix_token_cost.py"
)
S1 = "aaaaaaaa-1111-1111-1111-111111111111"
S2 = "bbbbbbbb-2222-2222-2222-222222222222"


def _load():
    spec = importlib.util.spec_from_file_location("phoenix_token_cost", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _llm(
    sid, start, prompt, completion, cache_read, cache_write, output="o", model="claude-opus-5"
):
    return {
        "span_kind": "LLM",
        "start_time": start,
        "attributes": {
            "session.id": sid,
            "llm.model_name": model,
            "llm.token_count.prompt": prompt,
            "llm.token_count.completion": completion,
            "llm.token_count.prompt_details.cache_read": cache_read,
            "llm.token_count.prompt_details.cache_write": cache_write,
            "llm.token_count.total": prompt + completion,
            "output.value": output,
        },
    }


def _tool(sid, start, name, payload, output=""):
    return {
        "span_kind": "TOOL",
        "name": name,
        "start_time": start,
        "attributes": {
            "session.id": sid,
            "tool.name": name,
            "input.value": json.dumps(payload),
            "output.value": output,
        },
    }


def _fixture():
    return {
        "project": "fixture",
        "llm": [
            # S1: 1000 prompt of which 800 cache read + 100 cache write -> 100 fresh.
            _llm(S1, "2026-09-12T00:00:01+00:00", 1000, 50, 800, 100),
            # Exact duplicate of the span above: same session, start, output. Must collapse.
            _llm(S1, "2026-09-12T00:00:01+00:00", 1000, 50, 800, 100),
            # Second call after a claim_task -> attributed to the claimed task under --by task.
            _llm(S1, "2026-09-12T00:00:10+00:00", 2000, 100, 1900, 0, output="p"),
            # S2 is Gemini: no token counts, counted as a call only.
            {
                "span_kind": "LLM",
                "start_time": "2026-09-12T00:00:02+00:00",
                "attributes": {"session.id": S2, "llm.model_name": "gemini-pro-agent"},
            },
        ],
        "tools": [
            _tool(
                S1,
                "2026-09-12T00:00:00+00:00",
                "ListAgents",
                {},
                "This session is desk-1 [abc123] — peers",
            ),
            _tool(
                S1, "2026-09-12T00:00:05+00:00", "mcp__x__pkb__claim_task", {"id": "aops_deadbeef"}
            ),
            _tool(
                S1, "2026-09-12T00:00:06+00:00", "mcp__x__pkb__get_task", {"id": "aops_cafef00d"}
            ),
        ],
        "chains": [
            {
                "span_kind": "CHAIN",
                "name": "agy session",
                "start_time": "2026-09-12T00:00:00+00:00",
                "attributes": {"session.id": S2, "host.name": "box"},
            }
        ],
        "agents": [],
    }


def test_tokens_fresh_in_excludes_cache():
    m = _load()
    tokens = m.tokens_of(_llm(S1, "t", 1000, 50, 800, 100))
    assert tokens == {"in": 100, "out": 50, "cache_read": 800, "cache_write": 100}


def test_dedupe_collapses_exact_reemissions():
    m = _load()
    kept, dropped = m.dedupe_llm(_fixture()["llm"])
    assert dropped == 1
    assert len(kept) == 3


def test_price_row_aliases_dated_ids():
    m = _load()
    assert m.price_row("claude-opus-5-20990101", m.PRICES) is m.PRICES["claude-opus-5"]
    assert m.price_row("gemini-pro-agent", m.PRICES) is None


def test_cost_uses_four_price_components():
    m = _load()
    tokens = {"in": 1_000_000, "out": 1_000_000, "cache_read": 1_000_000, "cache_write": 1_000_000}
    row = {"in": 1.0, "out": 2.0, "cache_read": 3.0, "cache_write": 4.0}
    assert m.cost_usd(tokens, row) == 10.0


def test_task_attribution_prefers_claim_over_read():
    m = _load()
    timeline = m.build_task_timeline(_fixture()["tools"])
    entries = timeline[S1]
    assert m.task_at(entries, "2026-09-12T00:00:01+00:00") == "unknown"
    assert m.task_at(entries, "2026-09-12T00:00:10+00:00") == "aops_deadbeef"
    assert m.task_summary(entries).startswith("aops_deadbeef,aops_cafef00d")


def test_label_from_list_agents_then_labels_file():
    m = _load()
    fx = _fixture()
    assert m.label_session(S1, [], fx["tools"], [], {}) == "desk-1 [abc123]"
    assert m.label_session(S1, [], fx["tools"], [], {"aaaaaaaa": "override"}) == "override"
    assert m.label_session(S2, fx["chains"], [], [], {}) == "agy polecat @box"


def test_cli_from_file_ranks_by_cost_and_flags_uncounted(tmp_path):
    fixture = tmp_path / "spans.json"
    fixture.write_text(json.dumps(_fixture()))
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--since",
            "2026-09-12",
            "--from-file",
            str(fixture),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    rows = payload["rows"]
    assert [r["session"][:8] for r in rows] == ["aaaaaaaa", "bbbbbbbb"]
    top = rows[0]
    assert top["role"] == "desk-1 [abc123]"
    assert top["task"].startswith("aops_deadbeef")
    assert top["calls"] == 2
    assert (top["in"], top["out"], top["cache_read"], top["cache_write"]) == (200, 150, 2700, 100)
    assert payload["meta"]["duplicates_dropped"] == 1
    assert payload["meta"]["uncounted_models"] == {"gemini-pro-agent": 1}
    assert rows[1]["cost"] == 0.0


def test_cli_by_task_splits_session(tmp_path):
    fixture = tmp_path / "spans.json"
    fixture.write_text(json.dumps(_fixture()))
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--since",
            "2026-09-12",
            "--from-file",
            str(fixture),
            "--by",
            "task",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    tasks = {(r["session"][:8], r["task"]): r["calls"] for r in json.loads(result.stdout)["rows"]}
    assert tasks[("aaaaaaaa", "unknown")] == 1
    assert tasks[("aaaaaaaa", "aops_deadbeef")] == 1


def test_missing_base_url_fails_closed():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--since", "2026-09-12", "--base-url", "", "--project", "x"],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 2
    assert "PHOENIX_BASE_URL" in result.stderr
