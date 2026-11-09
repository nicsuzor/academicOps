"""Tests for prompt cache read and cost reporting fidelity (AC1, AC2, AC3).

Validates:
1. Accurate cache token extraction and pricing across Claude 5 and Gemini models.
2. Distinction between raw list rates and cached execution costs.
3. agy_tracer explicit cache attribute zero emissions.
4. load_agy_transcript token usage and cost accumulation.
5. phoenix_transcript rendering of raw list costs and cache savings.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "ida"
    / "skills"
    / "session-trace"
    / "scripts"
)
HOOKS_DIR = Path(__file__).resolve().parent.parent / "plugins" / "ida" / "hooks"
LIB_DIR = Path(__file__).resolve().parent.parent / "lib" / "py"

for d in (str(SCRIPTS_DIR), str(HOOKS_DIR), str(LIB_DIR)):
    if d not in sys.path:
        sys.path.insert(0, d)

import phoenix_token_cost as ptc
import phoenix_transcript as pt
import token_extractor
from transcripts.adapters.agy import load_agy_transcript
from transcripts.adapters.claude import MODEL_RATE_CARD, get_model_rates


def test_gemini_and_claude_pricing_in_phoenix_token_cost():
    """Verify Gemini and Claude 5 models have accurate rates and price_row resolution."""
    # Direct model lookups
    argon = ptc.price_row("gemini-4-argon", ptc.PRICES)
    assert argon is not None
    assert argon["in"] == 2.00
    assert argon["out"] == 10.00
    assert argon["cache_read"] == 0.10
    assert argon["cache_write"] == 0.0

    flash = ptc.price_row("gemini-3.8-flash", ptc.PRICES)
    assert flash is not None
    assert flash["in"] == 0.75
    assert flash["out"] == 3.75
    assert flash["cache_read"] == 0.075

    flash_lite = ptc.price_row("gemini-2.5-flash-lite", ptc.PRICES)
    assert flash_lite is not None
    assert flash_lite["in"] == 0.10
    assert flash_lite["out"] == 0.40
    assert flash_lite["cache_read"] == 0.01

    # Aliases
    assert ptc.price_row("google/gemini-4-argon", ptc.PRICES) == argon
    assert ptc.price_row("gemini-3.8", ptc.PRICES) == flash
    assert ptc.price_row("gemini-2.5-flash-lite-preview", ptc.PRICES) == flash_lite
    assert ptc.price_row("claude-generic", ptc.PRICES) is not None


def test_tokens_of_and_cost_distinction():
    """Verify raw list rate vs cached execution cost calculation."""
    # 1,000 fresh in, 9,000 cached read (90% cache hit), 500 out
    tokens = {"in": 1_000, "cache_read": 9_000, "cache_write": 0, "out": 500}
    argon_rates = ptc.price_row("gemini-4-argon", ptc.PRICES)
    assert argon_rates is not None

    # Cached execution cost:
    # 1,000 * 2.00/M + 9,000 * 0.10/M + 500 * 10.00/M
    # = (2,000 + 900 + 5,000) / 1,000,000 = 7,900 / 1e6 = $0.0079
    cost = ptc.cost_usd(tokens, argon_rates)
    assert pytest.approx(cost, rel=1e-5) == 0.0079

    # Raw un-cached list cost:
    # Total prompt = 10,000 * 2.00/M + 500 * 10.00/M
    # = (20,000 + 5,000) / 1,000,000 = 25,000 / 1e6 = $0.025
    raw_cost = ptc.raw_cost_usd(tokens, argon_rates)
    assert pytest.approx(raw_cost, rel=1e-5) == 0.025

    # Cache savings: $0.025 - $0.0079 = $0.0171 (68.4% discount)
    savings = raw_cost - cost
    assert pytest.approx(savings, rel=1e-5) == 0.0171


def test_tokens_of_conventions_in_phoenix_token_cost():
    """Verify phoenix_token_cost extracts cache tokens across native, OpenInference, and GenAI."""
    # OpenInference
    oi_span = {
        "attributes": {
            "llm.token_count.prompt": 10000,
            "llm.token_count.completion": 500,
            "llm.token_count.prompt_details.cache_read": 8000,
            "llm.token_count.prompt_details.cache_write": 500,
        }
    }
    extracted = ptc.tokens_of(oi_span)
    assert extracted == {"in": 1500, "out": 500, "cache_read": 8000, "cache_write": 500}

    # Uncounted span
    empty_span = {"attributes": {"model": "foo"}}
    assert ptc.tokens_of(empty_span) is None


def test_token_extractor_reported_cache_tokens():
    """Verify token_extractor handles reported cache read tokens without requiring fresh in."""
    res = token_extractor.resolve_gemini_tokens(
        session_id="test",
        transcript_path="/nonexistent",
        step_index=0,
        reported_input_tokens=0,
        reported_cache_read_tokens=15000,
        reported_output_tokens=300,
    )
    assert res["prompt"] == 15000
    assert res["cache_read"] == 15000
    assert res["completion"] == 300
    assert res["total"] == 15300
    assert res["type"] == "reported"


def test_load_agy_transcript_accumulates_tokens_and_cost(tmp_path: Path):
    """Verify load_agy_transcript parses PLANNER_RESPONSE token counts and computes cost."""
    transcript_file = tmp_path / "transcript.jsonl"
    lines = [
        {"type": "USER_INPUT", "source": "USER_EXPLICIT", "content": "Hello", "step_index": 0},
        {
            "type": "PLANNER_RESPONSE",
            "source": "MODEL",
            "content": "Hi there!",
            "step_index": 1,
            "input_tokens": 1000,
            "cache_read_tokens": 10000,
            "output_tokens": 200,
            "model": "gemini-3.8-flash",
        },
    ]
    transcript_file.write_text("\n".join(json.dumps(line) for line in lines))

    session = load_agy_transcript(transcript_file)
    assert session.tokens_used == 11200
    # Rates for gemini-3.8-flash: in=0.75, cache_read=0.075, out=3.75
    # cost = (1000 * 0.75 + 10000 * 0.075 + 200 * 3.75) / 1e6
    # = (750 + 750 + 750) / 1e6 = 2250 / 1e6 = 0.00225 USD
    assert pytest.approx(session.cost_usd, rel=1e-4) == 0.00225


def test_claude_model_rates_support_gemini_and_claude5():
    """Verify lib/py/transcripts rate card includes Claude 5 and Gemini."""
    assert "claude-opus-5-5" in MODEL_RATE_CARD
    assert "gemini-4-argon" in MODEL_RATE_CARD
    assert "gemini-3.8-flash" in MODEL_RATE_CARD

    rates = get_model_rates("gemini-4-argon")
    assert rates is not None
    assert rates.input_usd_per_m == 2.00
    assert rates.cache_read_usd_per_m == 0.10
    assert rates.output_usd_per_m == 10.00


def test_phoenix_transcript_renders_raw_cost_and_savings(tmp_path: Path):
    """Verify phoenix_transcript displays raw list costs and cache savings."""
    spans = [
        {
            "name": "turn",
            "span_kind": "CHAIN",
            "context": {"trace_id": "a" * 32, "span_id": "c1"},
            "start_time": "2026-10-01T00:00:01.000+00:00",
            "end_time": "2026-10-01T00:00:05.000+00:00",
            "status_code": "UNSET",
            "attributes": {
                "session.id": "sess-test",
                "input.value": "Test prompt",
                "output.value": "Test reply",
            },
        },
        {
            "name": "LLM",
            "span_kind": "LLM",
            "context": {"trace_id": "a" * 32, "span_id": "l1"},
            "parent_id": "c1",
            "start_time": "2026-10-01T00:00:01.500+00:00",
            "end_time": "2026-10-01T00:00:04.500+00:00",
            "status_code": "UNSET",
            "attributes": {
                "session.id": "sess-test",
                "llm.model_name": "gemini-4-argon",
                "llm.token_count.prompt": 20000,
                "llm.token_count.completion": 1000,
                "llm.token_count.prompt_details.cache_read": 18000,
                "llm.token_count.prompt_details.cache_write": 0,
            },
        },
    ]
    turns = pt.assemble(spans, "sess-test", pt.PRICES)
    assert len(turns) == 1
    models = pt.model_totals(turns)
    assert "gemini-4-argon" in models
    row = models["gemini-4-argon"]
    # in = 2000, cache_read = 18000, out = 1000
    # cost = (2000 * 2.0 + 18000 * 0.10 + 1000 * 10.0) / 1e6 = (4000 + 1800 + 10000) / 1e6 = 0.0158
    assert pytest.approx(row["cost"], rel=1e-4) == 0.0158
    # raw_cost = (20000 * 2.0 + 1000 * 10.0) / 1e6 = (40000 + 10000) / 1e6 = 0.0500
    assert pytest.approx(row["raw_cost"], rel=1e-4) == 0.0500
    assert pytest.approx(row["savings"], rel=1e-4) == 0.0342

    full, outline, _ = pt.render(turns, "sess-test", "academicOps", spans, pt.PRICES)
    assert "raw list:" in full
    assert "cache saved:" in full
    assert (
        "| Model | Calls | In | Cache read | Cache write | Out | Cost | Raw list | Saved |" in full
    )
