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
