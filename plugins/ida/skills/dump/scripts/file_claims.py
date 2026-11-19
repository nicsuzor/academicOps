#!/usr/bin/env python3
"""CLI runner to file argdown claims to OTEL/Phoenix, invoked during /dump."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Resolve hooks directory from either source tree or packaged distribution
_HERE = Path(__file__).resolve()
_CANDIDATES = [
    _HERE.parents[3] / "hooks",  # plugins/ida/hooks/
    _HERE.parents[2] / "hooks",  # distribution layout dist/ida-*/hooks/
]

_HOOKS_DIR = None
for candidate in _CANDIDATES:
    if (candidate / "premise_check_verdict.py").is_file():
        _HOOKS_DIR = candidate
        break

if _HOOKS_DIR and str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

for parent in _HERE.parents:
    lib_candidate = parent / "lib" / "hooks"
    if (lib_candidate / "dispatch.py").is_file():
        if str(lib_candidate) not in sys.path:
            sys.path.insert(0, str(lib_candidate))
        break

try:
    import premise_check_verdict as pcv
except ImportError as exc:
    print(f"file_claims.py: failed to import premise_check_verdict ({exc})", file=sys.stderr)
    sys.exit(1)


def _read_argdown(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="file_claims.py",
        description="File premise-check argdown claims to OTEL/Phoenix span collector.",
    )
    parser.add_argument(
        "--claim",
        "--task",
        dest="claim",
        required=True,
        help="Task ID or claim ID.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional short title.",
    )
    content_group = parser.add_mutually_exclusive_group(required=True)
    content_group.add_argument("--argdown", help="The argdown block, inline.")
    content_group.add_argument(
        "--argdown-file",
        help="Read argdown from this file, or from stdin when '-'.",
    )
    parser.add_argument(
        "--session",
        default=os.environ.get("AOPS_SESSION_ID", ""),
        help="Session id. Defaults to $AOPS_SESSION_ID.",
    )

    args = parser.parse_args(argv)

    try:
        text = args.argdown if args.argdown is not None else _read_argdown(args.argdown_file)
        result = pcv.record_claims(
            session_id=args.session,
            claim_id=args.claim,
            argdown_text=text,
            title=args.title,
        )
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"file_claims.py: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
