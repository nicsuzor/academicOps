"""Context map loader and formatter.

Loads .agents/context-map.json from a repo root and formats the full entry
list as a hint for injection into the hydration pipeline.

The context map is a plain JSON file — any agent on any platform can read it
directly. This module provides loading and formatting for the aops hydration
pipeline. Relevance decisions are left to the LLM (P#49: no Python pre-filtering
for semantic decisions).

Exit behavior: Missing file → empty list. Malformed JSON or I/O errors raise
so callers can surface configuration problems (P#8 fail-fast).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_context_map(repo_root: Path) -> list[dict[str, Any]]:
    """Load context-map.json from .agents/ directory.

    Args:
        repo_root: Path to the repository root.

    Returns:
        List of doc entries, or empty list if file missing or non-dict JSON.

    Raises:
        json.JSONDecodeError: If file exists but contains invalid JSON.
        OSError: If file exists but cannot be read.
    """
    map_path = repo_root / ".agents" / "context-map.json"
    if not map_path.exists():
        return []
    data = json.loads(map_path.read_text())
    return data.get("docs", []) if isinstance(data, dict) else []


def audit_context_map_coverage(repo_root: Path) -> list[str]:
    """Audit the context map for staleness against the specs on disk.

    The context map is the discovery index agents read at cold-start. When a
    spec merges without a map update, agents cannot discover it and fall back
    to semantic search or from-scratch exploration (GitHub #1364). This audit
    is the enforcement surface that the manual context-map-audit workflow
    lacked: every spec under ``spec_dirs`` must be a conscious decision —
    indexed in ``docs[]`` (discoverable) or listed in ``exclude[]`` (knowingly
    not indexed). A spec that is neither is an unreviewed gap.

    The map is curated, not exhaustive, so ``exclude[]`` is a first-class part
    of the contract: it records the specs deliberately kept out of the index.

    Returns a list of human-readable issue strings (empty when the map is
    fresh). Three issue classes:
      - uncovered spec: under spec_dirs but in neither docs[] nor exclude[]
      - dangling docs[] entry: a mapped path that no longer exists
      - stale exclude[] entry: an excluded path that no longer exists

    Missing map or no ``spec_dirs`` → no issues (nothing to enforce).
    """
    map_path = repo_root / ".agents" / "context-map.json"
    if not map_path.exists():
        return []
    data = json.loads(map_path.read_text())
    if not isinstance(data, dict):
        return []

    spec_dirs = data.get("spec_dirs") or []
    docs = data.get("docs", [])
    exclude = data.get("exclude", [])

    mapped = {entry["path"] for entry in docs if isinstance(entry, dict) and entry.get("path")}
    excluded = set(exclude)

    issues: list[str] = []

    # Dangling docs[] / stale exclude[] entries — paths that no longer resolve.
    for path in sorted(mapped):
        if not (repo_root / path).exists():
            issues.append(f"docs[] entry '{path}' does not exist (remove or fix the path)")
    for path in sorted(excluded):
        if not (repo_root / path).exists():
            issues.append(f"exclude[] entry '{path}' does not exist (remove the stale exclusion)")

    # Uncovered specs — present on disk, classified nowhere.
    for spec_dir in spec_dirs:
        base = repo_root / spec_dir
        if not base.is_dir():
            continue
        for spec in sorted(base.rglob("*.md")):
            rel = str(spec.relative_to(repo_root))
            if rel not in mapped and rel not in excluded:
                issues.append(
                    f"{rel}: spec not in context-map.json — add a docs[] entry to make it "
                    f"discoverable, or add it to exclude[] if it should stay out of the index"
                )

    return issues


def format_context_hints(docs: list[dict[str, Any]]) -> str:
    """Format context map entries as a compact hint for injection.

    Injects the full entry list so the LLM can decide which are relevant
    (P#49 corollary: provide the index of choices, let the agent decide).

    Args:
        docs: Doc entries from load_context_map().

    Returns:
        Markdown-formatted hint string, or empty string if no entries.
    """
    if not docs:
        return ""

    lines = ["# Available Documentation (from .agents/context-map.json)", ""]
    for entry in docs:
        path = entry.get("path", "?")
        desc = entry.get("description", "")
        lines.append(f"- **`{path}`**: {desc}")

    lines.append("")
    lines.append(
        "_Read relevant files for authoritative context. "
        "The full map is at `.agents/context-map.json`._"
    )
    return "\n".join(lines)
