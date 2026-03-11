#!/usr/bin/env python3
"""Merge and write session insights.

Reads new insights JSON from stdin and:
1. Merges with existing file if present (appending lists, updating scalars)
2. Writes atomically to target path
3. Handles errors by saving debug output

Usage:
    cat new_insights.json | merge_insights.py <target_path>
"""

import argparse
import json
import sys
from pathlib import Path

# Add aops-core to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.insights_generator import merge_insights, write_insights_file


def main():
    parser = argparse.ArgumentParser(description="Merge and write session insights")
    parser.add_argument("path", help="Target insights JSON file path")
    args = parser.parse_args()

    target_path = Path(args.path)

    # Read new insights from stdin
    try:
        new_json_str = sys.stdin.read()
        if not new_json_str.strip():
            print("ERROR: No input provided on stdin", file=sys.stderr)
            sys.exit(1)
        new_insights = json.loads(new_json_str)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read input: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        final_insights = new_insights

        # Check if file exists to merge
        if target_path.exists():
            print(f"Merging with existing file: {target_path}")
            try:
                with open(target_path) as f:
                    existing_insights = json.load(f)

                final_insights = merge_insights(existing_insights, new_insights)
            except Exception as e:
                print(
                    f"WARNING: Failed to load existing file, overwriting: {e}",
                    file=sys.stderr,
                )
                # Fallback to overwrite if existing is corrupt
                final_insights = new_insights

        # Write result
        write_insights_file(target_path, final_insights)
        print(f"✓ Insights written to {target_path}")

    except Exception as e:
        print(f"❌ Error merging/writing insights: {e}", file=sys.stderr)

        # Save debug info
        debug_path = target_path.with_suffix(".merge_error.txt")
        try:
            with open(debug_path, "w") as f:
                f.write(str(e))
                f.write("\n\nNew JSON Input:\n")
                f.write(new_json_str)
            print(f"Debug info saved to: {debug_path}", file=sys.stderr)
        except Exception:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
