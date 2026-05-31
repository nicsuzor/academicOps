#!/usr/bin/env python3
import os
from datetime import datetime, timedelta
from pathlib import Path

# canonical locations
SESSIONS_REPO = os.environ.get("AOPS_SESSIONS", str(Path.home() / "src" / "sessions"))
SURFACES = {
    "orchestrator": "transcripts",
    "subagent": "subagent-transcripts",
    "polecat": "polecats",
    "gha": "github",
}

# The target definition:
# A retrieval-gap instance = the agent needed information that already existed in the PKB
# or a durable doc, but didn't retrieve it — so it re-derived, guessed, confabulated, or burned effort/tokens.


def is_false_positive(line: str) -> bool:
    """Filter out mechanical file-not-found errors that aren't PKB retrieval gaps."""
    line_lower = line.lower()
    # Exclude typical missing dependency / binary / environment errors
    if any(
        x in line_lower
        for x in [
            "node_modules",
            ".cache",
            "ld-linux",
            "cannot access",
            "no such file or directory",
            "file does not exist",
            "command not found",
        ]
    ):
        # If it's a raw bash missing file error, it's usually not a PKB retrieval gap
        # unless it was trying to guess a path that was documented in the PKB.
        # This is a heuristic.
        if (
            "pkb" not in line_lower
            and "memory.md" not in line_lower
            and "gemini.md" not in line_lower
        ):
            return True

    # Exclude rule text matching
    if "if you cannot do what was asked" in line_lower or "missing paths:" in line_lower:
        return True
    if "does not exist as an inspectable artefact" in line_lower:
        return True

    return False


def scan_surface(surface_name: str, rel_path: str, days: int = 7):
    base_dir = Path(SESSIONS_REPO) / rel_path
    if not base_dir.exists():
        print(f"Warning: Surface directory {base_dir} does not exist.")
        return []

    cutoff = datetime.now() - timedelta(days=days)
    candidates = []

    # We look for markdown files
    for root, _, files in os.walk(base_dir):
        for f in files:
            if not f.endswith(".md"):
                continue
            path = Path(root) / f
            # Check recency (use file modification time or parse date from path)
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime < cutoff:
                    continue
            except Exception:
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Simple heuristic for "confabulation" or "path guessing"
            # Instead of simple "not found" which is noisy, we look for cases where
            # an agent is trying to grep home directory or search broadly
            # instead of querying the PKB. Or where an agent uses a tool and fails,
            # then apologizes or makes a wrong assumption.
            lines = content.split("\n")
            for i, line in enumerate(lines):
                # Search for broad greps which indicate path discovery failure
                if (
                    "grep -r" in line or "find /" in line or "find ~" in line
                ) and "context-map.json" not in line:
                    if not is_false_positive(line):
                        candidates.append(
                            {
                                "surface": surface_name,
                                "path": str(path),
                                "line": i + 1,
                                "context": "\n".join(lines[max(0, i - 2) : min(len(lines), i + 3)]),
                                "reason": "Agent used broad search instead of PKB/context map",
                            }
                        )
                # Search for false assertions about SSoT
                if (
                    "I cannot find the documentation" in line
                    or "no instructions provided" in line.lower()
                ):
                    if not is_false_positive(line):
                        candidates.append(
                            {
                                "surface": surface_name,
                                "path": str(path),
                                "line": i + 1,
                                "context": "\n".join(lines[max(0, i - 2) : min(len(lines), i + 3)]),
                                "reason": "Agent hallucinated missing documentation",
                            }
                        )
    return candidates


def main():
    print("Running Evidence Gathering Workflow for Retrieval Gaps")
    print(f"Scanning sessions repo at {SESSIONS_REPO} for the last 7 days...")

    all_candidates = []
    for surface, rel_path in SURFACES.items():
        print(f"Scanning surface: {surface}...")
        candidates = scan_surface(surface, rel_path)
        all_candidates.extend(candidates)
        print(f"Found {len(candidates)} candidates in {surface}")

    print("\n--- Summary ---")
    for c in all_candidates[:10]:
        print(f"\nSurface: {c['surface']} | {c['path']}:{c['line']}")
        print(f"Reason: {c['reason']}")
        print(f"Context:\n{c['context']}")

    print(f"\nTotal candidates extracted: {len(all_candidates)}")
    print("These candidates should be mapped to the 3 seed hypotheses:")
    print("1) Mechanical hydration-search injection on UserPromptSubmit")
    print("2) /sleep transcript-mining into the PKB")
    print("3) /sleep consolidation into durable notes")


if __name__ == "__main__":
    main()
