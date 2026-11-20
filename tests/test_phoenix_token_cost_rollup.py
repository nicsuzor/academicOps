"""Harness/model rollup in phoenix_token_cost.py: SQL shape and timeout splitting."""

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1] / "plugins/ida/skills/phoenix/scripts/phoenix_token_cost.py"
)
spec = importlib.util.spec_from_file_location("phoenix_token_cost", SCRIPT)
ptc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ptc)

T0 = datetime(2026, 11, 12, tzinfo=UTC)


def test_rollup_sql_uses_nested_cache_keys_and_fits_sql_cap():
    sql = ptc.rollup_sql(T0, T0 + timedelta(hours=6))
    assert "llm.token_count.prompt_details.cache_read" in sql
    assert "llm.prompt_details" not in sql
    assert "aops.surface" in sql and "llm.message.id" in sql
    assert "2026-11-12 00:00:00+00:00" in sql
    assert len(sql) < 2048


def test_rollup_halves_chunk_on_timeout(monkeypatch):
    calls = []

    def fake(_base, sql):
        calls.append(sql)
        if len(calls) == 1:
            raise ptc.ConfigError("Phoenix MCP tool executeSql failed: {'code': 'timeout'}")
        return [["claude-code", "claude-opus-5-5", 2, 100, 10, 60, 20]]

    monkeypatch.setattr(ptc, "sql_rows", fake)
    totals, splits = ptc.rollup("http://x", T0, T0 + timedelta(hours=6), 6)
    assert splits == 1 and len(calls) == 3
    t = totals[("claude-code", "claude-opus-5-5")]
    assert t["calls"] == 4 and t["cache_read"] == 120
    (row,) = ptc.rollup_rows(totals, dict(ptc.PRICES))
    assert row["in"] == 40 and row["priced"]


def test_gemini_aliases_and_long_context_tier():
    prices = dict(ptc.PRICES)
    assert ptc.price_row("gemini-4-argon-high", prices) is prices["gemini-4-argon"]
    assert ptc.price_row("gemini-3.8-flash-tiered", prices) is prices["gemini-3.8-flash"]
    assert ptc.price_row("gemini-4-hydrogen-medium", prices) is prices["gemini-4-hydrogen"]
    row = ptc.price_row("gemini-3.1-pro-preview", prices)
    short = {"in": 100_000, "out": 0, "cache_read": 0, "cache_write": 0}
    long_ = {"in": 300_000, "out": 0, "cache_read": 0, "cache_write": 0}
    assert ptc.cost_usd(short, row) == 0.2
    assert ptc.cost_usd(long_, row) == 1.2
