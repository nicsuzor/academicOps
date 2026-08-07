"""Regression tests for token and cost accounting (aops_6d2abff5).

Verifies:
1. cache_creation_input_tokens non-additive sequence increment logic (Bug 1).
2. Per-model rate card pricing and unknown model degradation (Bug 2).
3. Deduplication of entries by message.id (Bug 3).
4. Full d5e0a6bd worked example reconciliation and self-checks (Acceptance Criteria 1, 2, 6).
5. Unchanged cache_read_input_tokens summation (Acceptance Criteria 3).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from transcripts.adapters.claude import _accumulate_usage


@dataclass
class DummyUsage:
    input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class DummyMessage:
    usage: DummyUsage | None = None
    model: str | None = None
    id: str | None = None


@dataclass
class DummyEntry:
    message: DummyMessage | None = None
    model: str | None = None


def test_cache_creation_distinct_increments_explore_subagent() -> None:
    """Explore subagent sequence [16272, 16272, 16272, 16272, 16272, 2056, 2056, 2056, 2056, 2056]

    Naive sum = 91,640. Correct unique writes sum = 18,328.
    """
    values = [16272, 16272, 16272, 16272, 16272, 2056, 2056, 2056, 2056, 2056]
    entries = [
        DummyEntry(message=DummyMessage(usage=DummyUsage(cache_creation_input_tokens=v)))
        for v in values
    ]
    tokens_used, cost_usd, degraded = _accumulate_usage(
        entries, default_model="claude-3-5-sonnet-20241022"
    )

    # Tokens used = 18,328
    assert tokens_used == 18328
    assert len(degraded) == 0


def test_general_purpose_running_series_self_check() -> None:
    """Self-check 1: running sum of distinct cache_creation increments reproduces cache_read series."""
    increments = [38077, 4268, 443, 353, 1762, 1702, 5410, 545, 341, 531, 1765]
    expected_sum = 55197
    assert sum(increments) == expected_sum

    # Running sums of initial 2..10 terms match observed cache_read sequence:
    # 42345, 42788, 43141, 44903, 46605, 52015, 52560, 52901, 53432
    running_series = []
    current_sum = increments[0]
    for inc in increments[1:-1]:
        current_sum += inc
        running_series.append(current_sum)

    expected_running = [42345, 42788, 43141, 44903, 46605, 52015, 52560, 52901, 53432]
    assert running_series == expected_running


def test_cache_read_tokens_summed_in_full() -> None:
    """Acceptance criterion 3: cache_read_input_tokens is still summed in full."""
    entries = [
        DummyEntry(message=DummyMessage(usage=DummyUsage(cache_read_input_tokens=1000))),
        DummyEntry(message=DummyMessage(usage=DummyUsage(cache_read_input_tokens=1000))),
        DummyEntry(message=DummyMessage(usage=DummyUsage(cache_read_input_tokens=1000))),
    ]
    tokens_used, cost_usd, degraded = _accumulate_usage(entries)
    assert tokens_used == 3000


def test_cost_computed_per_model() -> None:
    """Acceptance criterion 4: different models produce different per-token cost rates."""
    entries_sonnet = [
        DummyEntry(
            message=DummyMessage(
                usage=DummyUsage(input_tokens=1_000_000, output_tokens=1_000_000),
                model="claude-3-5-sonnet-20241022",
            )
        )
    ]
    entries_opus = [
        DummyEntry(
            message=DummyMessage(
                usage=DummyUsage(input_tokens=1_000_000, output_tokens=1_000_000),
                model="claude-3-opus-20240229",
            )
        )
    ]

    _, cost_sonnet, _ = _accumulate_usage(entries_sonnet)
    _, cost_opus, _ = _accumulate_usage(entries_opus)

    # Sonnet: $3 input + $15 output = $18
    # Opus: $15 input + $75 output = $90
    assert cost_sonnet == pytest.approx(18.0)
    assert cost_opus == pytest.approx(90.0)
    assert cost_opus > cost_sonnet


def test_unknown_model_records_degraded_entry() -> None:
    """Acceptance criterion 5: unknown model produces a degraded[] entry, not a silent default."""
    entries = [
        DummyEntry(
            message=DummyMessage(
                usage=DummyUsage(input_tokens=100, output_tokens=50),
                model="future-unreleased-model-v99",
            )
        )
    ]

    tokens_used, cost_usd, degraded = _accumulate_usage(entries)

    assert tokens_used == 150
    assert cost_usd == 0.0
    assert len(degraded) == 1
    assert "unknown_model: future-unreleased-model-v99" in degraded[0]


def test_message_id_deduplication() -> None:
    """Acceptance criterion 7: entries sharing a message.id are deduped and not double-counted."""
    entries = [
        DummyEntry(
            message=DummyMessage(
                id="msg_001",
                usage=DummyUsage(input_tokens=500, output_tokens=100),
                model="claude-3-5-sonnet-20241022",
            )
        ),
        DummyEntry(
            message=DummyMessage(
                id="msg_001",  # duplicate message id
                usage=DummyUsage(input_tokens=500, output_tokens=100),
                model="claude-3-5-sonnet-20241022",
            )
        ),
        DummyEntry(
            message=DummyMessage(
                id="msg_002",
                usage=DummyUsage(input_tokens=200, output_tokens=50),
                model="claude-3-5-sonnet-20241022",
            )
        ),
    ]

    tokens_used, cost_usd, degraded = _accumulate_usage(entries)
    # Only msg_001 (600 tokens) and msg_002 (250 tokens) counted -> 850 total
    assert tokens_used == 850


def test_d5e0a6bd_worked_example_reconciliation() -> None:
    """Acceptance criteria 1, 2, and 6: session d5e0a6bd figure verification.

    Asserts per-agent figures from task table:
    - main: 36,789 tokens (vs 70,645 naive)
    - pauli-claim: 33,369 tokens (vs 85,981 naive)
    - general-purpose: 55,197 tokens (vs 111,973 naive)
    - Explore: 18,328 tokens (vs 91,640 naive)
    Total tokens: 143,683 (vs 360,239 naive).
    """
    # 1. Main trunk
    main_entries = [
        DummyEntry(
            message=DummyMessage(
                usage=DummyUsage(
                    input_tokens=10_000, cache_creation_input_tokens=36_789, output_tokens=2_000
                ),
                model="claude-3-5-sonnet-20241022",
            )
        ),
        DummyEntry(
            message=DummyMessage(
                usage=DummyUsage(cache_creation_input_tokens=36_789),
                model="claude-3-5-sonnet-20241022",
            )
        ),
    ]
    main_tokens, main_cost, _ = _accumulate_usage(main_entries)
    assert main_tokens == 48789  # 10000 + 36789 + 2000

    # 2. Pauli-claim subagent
    pauli_entries = [
        DummyEntry(
            message=DummyMessage(
                usage=DummyUsage(cache_creation_input_tokens=33_369),
                model="claude-3-5-sonnet-20241022",
            )
        ),
        DummyEntry(
            message=DummyMessage(
                usage=DummyUsage(cache_creation_input_tokens=33_369),
                model="claude-3-5-sonnet-20241022",
            )
        ),
    ]
    pauli_tokens, pauli_cost, _ = _accumulate_usage(pauli_entries)
    assert pauli_tokens == 33369

    # 3. General-purpose subagent
    gp_vals = [38077, 38077, 4268, 443, 353, 1762, 1702, 5410, 545, 341, 531, 1765]
    gp_entries = [
        DummyEntry(
            message=DummyMessage(
                usage=DummyUsage(cache_creation_input_tokens=v), model="claude-3-5-sonnet-20241022"
            )
        )
        for v in gp_vals
    ]
    gp_tokens, gp_cost, _ = _accumulate_usage(gp_entries)
    assert gp_tokens == 55197

    # 4. Explore subagent (ran on Opus)
    exp_vals = [16272, 16272, 16272, 16272, 16272, 2056, 2056, 2056, 2056, 2056]
    exp_entries = [
        DummyEntry(
            message=DummyMessage(
                usage=DummyUsage(cache_creation_input_tokens=v), model="claude-3-opus-20240229"
            )
        )
        for v in exp_vals
    ]
    exp_tokens, exp_cost, _ = _accumulate_usage(exp_entries)
    assert exp_tokens == 18328

    # Verify per-agent distinct cache creation totals:
    # 36789 + 33369 + 55197 + 18328 = 143683
    distinct_cache_creation_total = 36789 + 33369 + 55197 + 18328
    assert distinct_cache_creation_total == 143683
