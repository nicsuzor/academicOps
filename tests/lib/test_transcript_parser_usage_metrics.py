"""Regression tests for derived token-usage metrics (aops_b190be1c).

A 2026-07-07 audit (memory mem_4389c498) confirmed the CORE token counting
in `lib.transcript_parser` is accurate — these tests only cover the
*derived*/summary metrics layered on top, which were wrong:

1. `cache_hit_rate` mixed non-cache `input_tokens` into the numerator/denominator
   and omitted `cache_creation_input_tokens`, inflating the reported rate.
2. `tokens_per_minute` silently excluded cache tokens (~600x larger than
   input+output on a typical session).
3. `totals` had no canonical `total_tokens` field.
4. `<synthetic>`/API-error placeholder entries polluted `by_model` with a
   fake all-zero bucket.
5. Malformed (non-numeric) usage fields could raise deep inside aggregation.
6. `_aggregate_session_usage` + `_compute_session_duration` were called as an
   identical pair at three call sites in scripts/transcript.py.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from lib.transcript_parser import Entry, SessionProcessor, UsageStats


class TestCacheHitRate:
    """#1: cache_hit_rate = cache_read / (cache_read + cache_creation)."""

    def test_denominator_excludes_fresh_input_tokens(self) -> None:
        stats = UsageStats(
            input_tokens=1_000,
            output_tokens=200,
            cache_creation_input_tokens=5_000,
            cache_read_input_tokens=90_000,
        )
        metrics = stats.to_token_metrics()

        # Old (buggy) formula: cache_read / (input + cache_read)
        #   = 90_000 / 91_000 = 0.989 (inflated — ignores cache_creation entirely)
        old_bogus_rate = round(90_000 / 91_000, 3)
        # New formula: cache_read / (cache_read + cache_creation)
        expected = round(90_000 / (90_000 + 5_000), 3)

        assert metrics["efficiency"]["cache_hit_rate"] == expected
        assert metrics["efficiency"]["cache_hit_rate"] != old_bogus_rate

    def test_zero_denominator_is_zero_not_error(self) -> None:
        stats = UsageStats(input_tokens=100, output_tokens=50)
        metrics = stats.to_token_metrics()
        assert metrics["efficiency"]["cache_hit_rate"] == 0.0


class TestTokensPerMinute:
    """#2: fresh_tokens_per_minute excludes cache; total_tokens_per_minute includes it."""

    def test_fresh_vs_total_split(self) -> None:
        stats = UsageStats(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=1_000,
            cache_read_input_tokens=2_000,
        )
        metrics = stats.to_token_metrics(session_duration_minutes=10.0)
        efficiency = metrics["efficiency"]

        assert efficiency["fresh_tokens_per_minute"] == 15.0  # (100 + 50) / 10
        assert efficiency["total_tokens_per_minute"] == 315.0  # (100+50+1000+2000) / 10
        assert "tokens_per_minute" not in efficiency

    def test_omitted_without_duration(self) -> None:
        stats = UsageStats(input_tokens=100, output_tokens=50)
        metrics = stats.to_token_metrics(session_duration_minutes=None)
        assert "fresh_tokens_per_minute" not in metrics["efficiency"]
        assert "total_tokens_per_minute" not in metrics["efficiency"]


class TestCanonicalTotalTokens:
    """#3: totals.total_tokens = input + output + cache_create + cache_read."""

    def test_total_tokens_present_and_correct(self) -> None:
        stats = UsageStats(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=10,
            cache_read_input_tokens=20,
        )
        metrics = stats.to_token_metrics()
        assert metrics["totals"]["total_tokens"] == 180


class TestSyntheticAndApiErrorPollution:
    """#4: <synthetic> model / isApiErrorMessage entries must not pollute by_model."""

    def test_synthetic_model_entry_skipped(self) -> None:
        stats = UsageStats()
        entry = Entry.from_dict(
            {
                "type": "assistant",
                "message": {"model": "<synthetic>", "usage": {}},
            }
        )
        stats.add_entry(entry)
        assert stats.by_model == {}
        assert not stats.has_data()

    def test_api_error_message_entry_skipped_even_with_usage(self) -> None:
        stats = UsageStats()
        entry = Entry.from_dict(
            {
                "type": "assistant",
                "isApiErrorMessage": True,
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            }
        )
        stats.add_entry(entry)
        assert stats.by_model == {}
        assert stats.input_tokens == 0
        assert stats.output_tokens == 0

    def test_normal_entry_still_aggregates(self) -> None:
        """Sanity check the guard doesn't over-broadly suppress real entries."""
        stats = UsageStats()
        entry = Entry.from_dict(
            {
                "type": "assistant",
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            }
        )
        stats.add_entry(entry)
        assert stats.by_model == {
            "claude-sonnet-5": {"input": 10, "output": 5, "cache_create": 0, "cache_read": 0}
        }
        assert stats.input_tokens == 10


class TestMalformedUsageCoercion:
    """#5: non-numeric usage fields coerce to None instead of raising later."""

    def test_non_numeric_fields_become_none(self) -> None:
        entry = Entry.from_dict(
            {
                "type": "assistant",
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {
                        "input_tokens": "not-a-number",
                        "output_tokens": [1, 2, 3],
                        "cache_creation_input_tokens": None,
                        "cache_read_input_tokens": 42,
                    },
                },
            }
        )
        assert entry.input_tokens is None
        assert entry.output_tokens is None
        assert entry.cache_creation_input_tokens is None
        assert entry.cache_read_input_tokens == 42

    def test_malformed_payload_does_not_raise_during_aggregation(self) -> None:
        entry = Entry.from_dict(
            {
                "type": "assistant",
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {
                        "input_tokens": {"bad": "shape"},
                        "output_tokens": 5,
                    },
                },
            }
        )
        stats = UsageStats()
        stats.add_entry(entry)  # must not raise
        assert stats.input_tokens == 0
        assert stats.output_tokens == 5

    def test_bool_is_not_accepted_as_int(self) -> None:
        # bool is an int subclass in Python; usage fields must reject it anyway.
        entry = Entry.from_dict(
            {
                "type": "assistant",
                "message": {"model": "x", "usage": {"input_tokens": True}},
            }
        )
        assert entry.input_tokens is None


def _load_transcript_script():
    """Dynamically import scripts/transcript.py (not a package-relative module)."""
    repo_root = Path(__file__).parent.parent.parent
    script_path = repo_root / "aops-core" / "scripts" / "transcript.py"
    spec = importlib.util.spec_from_file_location("transcript_script_usage_metrics", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["transcript_script_usage_metrics"] = module
    spec.loader.exec_module(module)
    return module


class TestAggregateUsageDedup:
    """#6: _compute_usage_and_duration must behave identically to the three
    inlined call sites it replaces — a behaviour-preserving refactor."""

    def test_helper_matches_manual_composition(self) -> None:
        transcript_script = _load_transcript_script()
        processor = SessionProcessor()

        entries = [
            Entry.from_dict(
                {
                    "type": "assistant",
                    "timestamp": "2026-07-07T00:00:00+00:00",
                    "message": {
                        "model": "claude-sonnet-5",
                        "usage": {"input_tokens": 100, "output_tokens": 50},
                    },
                }
            ),
            Entry.from_dict(
                {
                    "type": "assistant",
                    "timestamp": "2026-07-07T00:05:00+00:00",
                    "message": {
                        "model": "claude-sonnet-5",
                        "usage": {"input_tokens": 200, "output_tokens": 75},
                    },
                }
            ),
        ]
        agent_entries: dict = {}

        usage_stats, duration = transcript_script._compute_usage_and_duration(
            processor, entries, agent_entries
        )
        manual_usage = processor._aggregate_session_usage(entries, agent_entries)
        manual_duration = transcript_script._compute_session_duration(entries)

        assert duration == manual_duration == 5.0
        assert usage_stats.input_tokens == manual_usage.input_tokens == 300
        assert usage_stats.output_tokens == manual_usage.output_tokens == 125
        assert usage_stats.by_model == manual_usage.by_model
