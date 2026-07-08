from dataclasses import dataclass

from lib.transcript_parser import UsageStats


@dataclass
class RateCard:
    input_cost_per_m: float
    output_cost_per_m: float
    cache_write_cost_per_m: float
    cache_read_cost_per_m: float

    def calculate_cost(self, stats: UsageStats) -> float:
        return (
            (stats.input_tokens / 1_000_000 * self.input_cost_per_m)
            + (stats.output_tokens / 1_000_000 * self.output_cost_per_m)
            + (stats.cache_creation_input_tokens / 1_000_000 * self.cache_write_cost_per_m)
            + (stats.cache_read_input_tokens / 1_000_000 * self.cache_read_cost_per_m)
        )


# Fable 5 Rate Card: $10/$50/$12.50/$1.00 (M-tokens In/Out/Cache-write/Cache-read)
FABLE_5 = RateCard(
    input_cost_per_m=10.0,
    output_cost_per_m=50.0,
    cache_write_cost_per_m=12.50,
    cache_read_cost_per_m=1.00,
)

DEFAULT_RATE_CARD = FABLE_5
