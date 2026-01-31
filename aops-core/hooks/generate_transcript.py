#!/usr/bin/env python3
"""
Simple hook to run transcript.py on session end.
"""

import json
import subprocess
import sys
from pathlib import Path


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # Empty or malformed stdin - expected in some invocations
        print(f"DEBUG: generate_transcript.py - no valid JSON input: {e}", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        # Unexpected error - log before exit
        print(f"ERROR: generate_transcript.py stdin read failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(0)

    transcript_path = data.get("transcript_path")
    if not transcript_path:
        # Silent exit if no transcript path
        print(json.dumps({}))
        sys.exit(0)

    # Locate transcript.py
    # This hook is in aops-core/hooks/
    # transcript.py is in aops-core/scripts/
    root_dir = Path(__file__).parent.parent
    script_path = root_dir / "scripts" / "transcript.py"

    if script_path.exists():
        # Run transcript.py
        # We don't capture output because we don't want to interfere with the hook output
        # unless debug logging is needed.
        result = subprocess.run(
            [sys.executable, str(script_path), transcript_path],
            check=False,
            text=True,
            capture_output=True,  # Capture to avoid polluting stdout
        )

        if result.returncode != 0:
            print(f"Error generating transcript: {result.stderr}", file=sys.stderr)

    # Hooks must return JSON
    print(json.dumps({}))


if __name__ == "__main__":
    main()
