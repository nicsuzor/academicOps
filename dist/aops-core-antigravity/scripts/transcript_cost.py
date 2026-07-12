#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from lib.transcript_pricing import DEFAULT_RATE_CARD
from lib.transcripts.extractor import extract_cost_data


def main():
    parser = argparse.ArgumentParser(
        description="Extract token usage and cost from a session transcript"
    )
    parser.add_argument(
        "session_file", type=Path, help="Path to Session file (Claude .jsonl or Agy transcript)"
    )

    args = parser.parse_args()

    if not args.session_file.exists():
        print(f"File not found: {args.session_file}", file=sys.stderr)
        sys.exit(1)

    stats = extract_cost_data(args.session_file)
    cost = DEFAULT_RATE_CARD.calculate_cost(stats)

    print(f"Cost: ${cost:.2f}")
    print(
        f"Tokens: {stats.input_tokens} In / {stats.output_tokens} Out / {stats.cache_creation_input_tokens} Cache-Write / {stats.cache_read_input_tokens} Cache-Read"
    )


if __name__ == "__main__":
    main()
