import json

from lib.transcript_pricing import DEFAULT_RATE_CARD
from lib.transcripts.extractor import extract_cost_data


def test_claude_adapter_sums_usage_across_entries(tmp_path):
    # Fable 5 Rate Card: $10/$50/$12.50/$1.00 (M-tokens In/Out/Cache-write/Cache-read)
    # 1000 input * 10/M = 0.01
    # 2000 output * 50/M = 0.10
    # 3000 cache-write * 12.5/M = 0.0375
    # 4000 cache-read * 1/M = 0.004
    # Sum: 0.1515 -> $0.15
    fixture_path = tmp_path / "transcript.jsonl"
    with open(fixture_path, "w") as f:
        # Two usage-bearing assistant entries in the same session must both count.
        f.write(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "usage": {
                            "input_tokens": 400,
                            "output_tokens": 800,
                            "cache_creation_input_tokens": 1000,
                            "cache_read_input_tokens": 1500,
                        }
                    },
                }
            )
            + "\n"
        )
        f.write(json.dumps({"type": "user", "message": "dummy"}) + "\n")
        f.write(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "usage": {
                            "input_tokens": 600,
                            "output_tokens": 1200,
                            "cache_creation_input_tokens": 2000,
                            "cache_read_input_tokens": 2500,
                        }
                    },
                }
            )
            + "\n"
        )

    stats = extract_cost_data(fixture_path)

    assert stats.input_tokens == 1000
    assert stats.output_tokens == 2000
    assert stats.cache_creation_input_tokens == 3000
    assert stats.cache_read_input_tokens == 4000

    cost = DEFAULT_RATE_CARD.calculate_cost(stats)
    assert round(cost, 2) == 0.15


def test_agy_adapter_contract(tmp_path):
    fixture_path = tmp_path / "transcript.jsonl"
    with open(fixture_path, "w") as f:
        f.write(
            json.dumps(
                {"timestamp": "2026-07-08T04:42:31Z", "sender": "system", "type": "assistant"}
            )
            + "\n"
        )

    stats = extract_cost_data(fixture_path)
    # Agy currently returns dummy usage stats (0)
    assert stats.input_tokens == 0
    assert stats.output_tokens == 0
