#!/usr/bin/env python3
"""Detect under-specified tasks that need decomposition or deletion.

Scans task files for quality signals: meaningful body content, title clarity,
and proper specification. Classifies tasks as:
  - needs-decomposition: reasonable title but no actionable body
  - needs-deletion: vague title AND no body (opaque to anyone picking it up)
  - ok: self-explanatory from title or has sufficient body content

Usage:
    python triage_tasks.py <path> [--recursive] [--min-body 100] [--format table|json]
    python triage_tasks.py /opt/nic/brain --recursive
    python triage_tasks.py /opt/nic/brain --recursive --format json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

# Statuses that matter — skip completed/cancelled work
ACTIVE_STATUSES = {"active", "in_progress", "inbox", "ready", "review", "paused"}

# Lines that don't count as meaningful content
BOILERPLATE_PATTERNS = [
    re.compile(r"^#+\s"),  # Markdown headings
    re.compile(r"^-\s*\[(parent|child|depends|blocks|unlocker)\]"),  # Relationship links
    re.compile(r"^##\s*Relationships?\s*$"),  # Relationship section header
    re.compile(r"^Project:\s*\[\["),  # Project links
    re.compile(r"^\s*$"),  # Empty lines
]

# Title patterns that suggest self-explanatory tasks (verb + specific object)
CLEAR_TITLE_PATTERNS = [
    # "X should Y" — specific behavior description
    re.compile(r"should\s+\w+", re.IGNORECASE),
    # "Fix X" / "Add X" / "Implement X" / "Update X" with specific object
    re.compile(
        r"^(fix|add|implement|update|remove|delete|rename|refactor|migrate)\s+.{15,}",
        re.IGNORECASE,
    ),
    # "Respond to X" — clear action
    re.compile(r"^respond\s+to\s+", re.IGNORECASE),
]

# Title patterns that suggest vagueness
VAGUE_TITLE_PATTERNS = [
    # Single word titles
    re.compile(r"^[a-zA-Z]+$"),
    # Very short titles (< 15 chars)
    re.compile(r"^.{1,14}$"),
    # Pure noun phrases with no verb or specificity
    re.compile(r"^(the|a|an)?\s*\w+\s*$", re.IGNORECASE),
]


@dataclass
class TriageResult:
    """Result of triaging a single task file."""

    path: str
    task_id: str
    title: str
    status: str
    verdict: str  # "needs-decomposition", "needs-deletion", "ok"
    reason: str
    meaningful_chars: int
    body_preview: str


def extract_meaningful_content(body: str) -> tuple[str, int]:
    """Extract content that's not boilerplate, return it and its char count.

    Handles escaped newlines in YAML values (e.g., body stored as a YAML
    scalar with literal \\n characters).
    """
    # Detect escaped newlines — if body has literal \n but few actual newlines,
    # it's probably a YAML scalar with real content
    if r"\n" in body and body.count("\n") < 3:
        body = body.replace(r"\n", "\n")

    lines = body.split("\n")
    meaningful = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(p.match(stripped) for p in BOILERPLATE_PATTERNS):
            continue
        meaningful.append(stripped)

    text = "\n".join(meaningful)
    return text, len(text)


def is_title_self_explanatory(title: str) -> bool:
    """Check if the title alone provides enough context to act on."""
    return any(p.search(title) for p in CLEAR_TITLE_PATTERNS)


def is_title_vague(title: str) -> bool:
    """Check if the title is too vague to be useful."""
    return any(p.match(title) for p in VAGUE_TITLE_PATTERNS)


def triage_file(path: Path, min_body: int = 100) -> TriageResult | None:
    """Triage a single task file. Returns None if not a relevant task."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None

    if not isinstance(fm, dict):
        return None

    status = str(fm.get("status", ""))
    if status not in ACTIVE_STATUSES:
        return None

    # Skip container types — hubs/projects/goals/epics are intentionally sparse
    node_type = str(fm.get("type", "task"))
    if node_type in ("project", "goal", "hub", "epic"):
        return None

    task_id = fm.get("id", fm.get("task_id", ""))
    if not task_id:
        return None

    title = str(fm.get("title", path.stem))
    body = parts[2].strip()

    meaningful_text, meaningful_chars = extract_meaningful_content(body)
    preview = meaningful_text[:150].replace("\n", " | ")

    result_kwargs = {
        "path": str(path),
        "task_id": task_id,
        "title": title,
        "status": status,
        "meaningful_chars": meaningful_chars,
        "body_preview": preview,
    }

    # Has sufficient body content — it's fine
    if meaningful_chars >= min_body:
        return TriageResult(**result_kwargs, verdict="ok", reason="has body content")

    # Empty/near-empty body — classify by title quality
    if is_title_vague(title):
        return TriageResult(
            **result_kwargs, verdict="needs-deletion", reason="vague title, no body"
        )

    if is_title_self_explanatory(title):
        return TriageResult(**result_kwargs, verdict="ok", reason="self-explanatory title")

    # Reasonable but not self-explanatory title, no body
    return TriageResult(
        **result_kwargs,
        verdict="needs-decomposition",
        reason="title not self-explanatory, no actionable body",
    )


def scan_tasks(root: Path, recursive: bool, min_body: int) -> list[TriageResult]:
    """Scan directory for task files and triage them."""
    pattern = "**/*.md" if recursive else "*.md"
    results = []
    for path in sorted(root.glob(pattern)):
        result = triage_file(path, min_body)
        if result and result.verdict != "ok":
            results.append(result)
    return results


def print_table(results: list[TriageResult]) -> None:
    """Print results as a readable table."""
    if not results:
        print("No under-specified tasks found.")
        return

    deletions = [r for r in results if r.verdict == "needs-deletion"]
    decompositions = [r for r in results if r.verdict == "needs-decomposition"]

    if deletions:
        print(f"\n{'=' * 80}")
        print(f"NEEDS DELETION ({len(deletions)} tasks) — vague title, no body")
        print(f"{'=' * 80}")
        for r in deletions:
            print(f"  [{r.status:11}] {r.task_id}")
            print(f"  Title: {r.title}")
            if r.body_preview:
                print(f"  Body:  {r.body_preview}")
            print()

    if decompositions:
        print(f"\n{'=' * 80}")
        print(
            f"NEEDS DECOMPOSITION ({len(decompositions)} tasks) — unclear title, no actionable body"
        )
        print(f"{'=' * 80}")
        for r in decompositions:
            print(f"  [{r.status:11}] {r.task_id}")
            print(f"  Title: {r.title}")
            if r.body_preview:
                print(f"  Body:  {r.body_preview}")
            print()

    print(f"\nSummary: {len(deletions)} delete, {len(decompositions)} decompose")


def print_json(results: list[TriageResult]) -> None:
    """Print results as JSON."""
    print(json.dumps([asdict(r) for r in results], indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect under-specified tasks needing decomposition or deletion."
    )
    parser.add_argument("path", type=Path, help="File or directory to scan")
    parser.add_argument("--recursive", "-r", action="store_true", help="Scan subdirectories")
    parser.add_argument(
        "--min-body",
        type=int,
        default=100,
        help="Minimum meaningful body chars (default: 100)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: {args.path} does not exist", file=sys.stderr)
        sys.exit(1)

    if args.path.is_file():
        result = triage_file(args.path, args.min_body)
        results = [result] if result and result.verdict != "ok" else []
    else:
        results = scan_tasks(args.path, args.recursive, args.min_body)

    if args.format == "json":
        print_json(results)
    else:
        print_table(results)

    # Exit code: 1 if issues found
    sys.exit(1 if results else 0)


if __name__ == "__main__":
    main()
