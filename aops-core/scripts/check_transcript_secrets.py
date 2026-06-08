#!/usr/bin/env python3
"""Pre-commit hook: block committed secrets in session transcript/summary artifacts.

Entrypoint for the sessions repo's pre-commit config. Imports the canonical
pattern set from lib/secret_redaction.py so both write-time scrubbing (Layer 1)
and commit-time blocking (Layer 2) share one pattern source — aops-00c0fa10.

Usage (called by pre-commit with pass_filenames: true):
    check_transcript_secrets.py [file ...]

Exit codes:
    0 — no secrets detected
    1 — one or more files contain a secret pattern (commit blocked)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Resolve aops-core root from this script's location (scripts/ → aops-core/)
_AOPS_CORE = Path(__file__).resolve().parent.parent
if str(_AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(_AOPS_CORE))

from lib.secret_redaction import redact_secrets  # noqa: E402


def _scan_file(path: Path) -> list[int]:
    """Return 1-indexed line numbers that contain a detected secret."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"check-transcript-secrets: cannot read {path}: {exc}", file=sys.stderr)
        return []

    return [i for i, line in enumerate(text.splitlines(), start=1) if redact_secrets(line) != line]


def main(argv: list[str] | None = None) -> int:
    files = argv if argv is not None else sys.argv[1:]
    if not files:
        return 0

    found_any = False
    for filename in files:
        path = Path(filename)
        bad = _scan_file(path)
        if bad:
            found_any = True
            lines_desc = ", ".join(str(n) for n in bad[:5])
            if len(bad) > 5:
                lines_desc += f", … ({len(bad)} total)"
            plural = "s" if len(bad) > 1 else ""
            print(
                f"check-transcript-secrets: secret detected in {path} "
                f"(line{plural} {lines_desc}) — commit blocked",
                file=sys.stderr,
            )

    return 1 if found_any else 0


if __name__ == "__main__":
    sys.exit(main())
