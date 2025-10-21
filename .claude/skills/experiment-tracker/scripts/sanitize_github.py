#!/usr/bin/env python3
"""
Sanitize conversation transcripts before posting to public GitHub using DataFog.

Replaces 163-line custom regex implementation with industry-standard DataFog library.
Per Axiom #11: Use Standard Tools - reduces maintenance, leverages community patterns.

Usage:
    uv run python sanitize_github.py <input_file> [--output output_file]

    # From stdin
    echo "My API key is sk_live_abc123" | uv run python sanitize_github.py -

Examples:
    uv run python sanitize_github.py conversation.txt --output sanitized.md
    cat error_log.txt | uv run python sanitize_github.py - > sanitized.md

Requires:
    uv add datafog  # Installs DataFog PII redaction library
"""

import argparse
import sys
from pathlib import Path


def sanitize_text(text: str) -> str:
    """
    Sanitize text using DataFog library for PII/secrets detection and redaction.

    Args:
        text: Raw text that may contain sensitive data

    Returns:
        Sanitized text safe for public posting

    Raises:
        ImportError: If datafog not installed
    """
    try:
        from datafog import DataFog
    except ImportError as e:
        raise ImportError(
            "DataFog library not installed. Install with: uv add datafog"
        ) from e

    # Use DataFog to redact sensitive information
    # Operations: scan (detect PII), redact (replace with [REDACTED])
    fog = DataFog(operations=["scan", "redact"])
    sanitized = fog.process_text(text)

    return sanitized


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Sanitize text for GitHub using DataFog",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        type=str,
        help="Input file path (use '-' for stdin)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file path (if not specified, prints to stdout)",
    )

    args = parser.parse_args()

    # Read input
    if args.input == "-":
        text = sys.stdin.read()
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: File not found: {input_path}", file=sys.stderr)
            return 1
        text = input_path.read_text()

    # Sanitize
    try:
        sanitized = sanitize_text(text)
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error during sanitization: {e}", file=sys.stderr)
        return 1

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(sanitized)
        print(f"Sanitized content written to: {output_path}", file=sys.stderr)
    else:
        print(sanitized)

    return 0


if __name__ == "__main__":
    sys.exit(main())
