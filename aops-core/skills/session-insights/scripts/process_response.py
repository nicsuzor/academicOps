#!/usr/bin/env python3
"""Process LLM response for session insights.

1. Extracts JSON from response (handling markdown fences)
2. Validates against schema
3. Prints valid JSON to stdout
4. Saves raw response to debug file on failure

Usage:
    cat raw_response.txt | process_response.py <date> <session_id>
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add aops-core to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.insights_generator import (
    extract_json_from_response,
    validate_insights_schema,
    get_insights_file_path,
)


def main():
    parser = argparse.ArgumentParser(
        description="Process and validate insights LLM response"
    )
    parser.add_argument("date", help="Session date (YYYY-MM-DD)")
    parser.add_argument("session_id", help="Session ID (8-char hash)")
    parser.add_argument("--project", default="", help="Project name for filename")
    args = parser.parse_args()

    # Read raw response from stdin
    raw_response = sys.stdin.read()
    if not raw_response.strip():
        print("ERROR: No input provided", file=sys.stderr)
        sys.exit(1)

    try:
        # Extract JSON
        json_str = extract_json_from_response(raw_response)

        # Parse
        insights = json.loads(json_str)

        # Validate
        validate_insights_schema(insights)

        # Valid! Print formatted JSON to stdout
        print(json.dumps(insights, indent=2))

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)

        # Save raw response for debugging
        # We need to construct path manually or use library helper (but helper returns .json)
        # We want .debug.txt alongside where the json would be
        try:
            target_path = get_insights_file_path(args.date, args.session_id, project=args.project)
            # E.g. .../YYYY-MM-DD-hash.json -> .../YYYY-MM-DD-hash.debug.txt
            debug_path = target_path.parent / f"{args.date}-{args.session_id}.debug.txt"

            with open(debug_path, "w") as f:
                f.write(raw_response)
                f.write(f"\n\nERROR: {e}")

            print(f"Raw response saved to: {debug_path}", file=sys.stderr)
        except Exception as save_err:
            print(f"Failed to save debug file: {save_err}", file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    main()
