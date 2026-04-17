"""Context map loader and keyword matcher.

Loads .agents/context-map.json from a repo root and matches user prompts
against entry keywords to surface relevant documentation paths.

The context map is a plain JSON file — any agent on any platform can read it
directly. This module provides keyword matching for the aops hydration pipeline.

Design note (P#49): The matching here is curated-index lookup, not free-text
NLP. Keywords are explicitly authored in context-map.json for this exact
purpose — they're an index, like tags in a library catalog. The agent still
decides what to do with the matched entries.

Exit behavior: Functions return empty results on failure (graceful degradation).
The context map is a discovery aid, not a critical path.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Maximum entries to return from a single search (avoid context bloat)
MAX_RESULTS = 5

# Minimum keyword match score to include an entry
MIN_SCORE = 1


def load_context_map(repo_root: Path) -> list[dict[str, Any]]:
    """Load context-map.json from .agents/ directory.

    Args:
        repo_root: Path to the repository root.

    Returns:
        List of doc entries, or empty list if file missing/invalid.
    """
    map_path = repo_root / ".agents" / "context-map.json"
    if not map_path.exists():
        return []
    try:
        data = json.loads(map_path.read_text())
        return data.get("docs", [])
    except (json.JSONDecodeError, OSError):
        return []


def _tokenize(text: str) -> set[str]:
    """Extract lowercase word tokens from text."""
    return set(re.findall(r"[a-z][a-z0-9_-]*", text.lower()))


def _score_entry(entry: dict[str, Any], prompt_tokens: set[str]) -> int:
    """Score a context map entry against prompt tokens.

    Scoring uses curated keyword fields (not free-text extraction):
    - Each keyword phrase where all tokens appear in prompt: +2
    - Each keyword phrase with partial token overlap: +1
    - Topic token overlap: +2
    - Description word overlap: +1 per word (capped at 3)

    Args:
        entry: A context map doc entry with topic, keywords, description.
        prompt_tokens: Lowercase word tokens from the user prompt.

    Returns:
        Integer relevance score (0 = no match).
    """
    score = 0

    keywords = [k.lower() for k in entry.get("keywords", [])]
    topic = entry.get("topic", "").lower().replace("_", " ")
    topic_tokens = _tokenize(topic)
    description_tokens = _tokenize(entry.get("description", ""))

    # Keyword exact matches (strongest signal)
    for kw in keywords:
        kw_tokens = _tokenize(kw)
        if kw_tokens and kw_tokens.issubset(prompt_tokens):
            score += 2
        elif kw_tokens & prompt_tokens:
            score += 1

    # Topic match
    if topic_tokens & prompt_tokens:
        score += 2

    # Description overlap (weak signal, capped)
    desc_overlap = len(description_tokens & prompt_tokens)
    score += min(desc_overlap, 3)

    return score


def search_context_map(
    docs: list[dict[str, Any]],
    prompt: str,
    max_results: int = MAX_RESULTS,
    min_score: int = MIN_SCORE,
) -> list[dict[str, Any]]:
    """Match user prompt against context map entries by keyword relevance.

    Args:
        docs: List of context map doc entries.
        prompt: Raw user prompt text.
        max_results: Maximum entries to return.
        min_score: Minimum score threshold.

    Returns:
        List of matching entries sorted by score (highest first),
        each augmented with a '_score' key.
    """
    if not docs or not prompt:
        return []

    prompt_tokens = _tokenize(prompt)
    if not prompt_tokens:
        return []

    scored = []
    for entry in docs:
        s = _score_entry(entry, prompt_tokens)
        if s >= min_score:
            scored.append({**entry, "_score": s})

    scored.sort(key=lambda e: e["_score"], reverse=True)
    return scored[:max_results]


def format_context_hints(matches: list[dict[str, Any]]) -> str:
    """Format matched context map entries as a compact hint for injection.

    Args:
        matches: Scored entries from search_context_map().

    Returns:
        Markdown-formatted hint string, or empty string if no matches.
    """
    if not matches:
        return ""

    lines = ["# Relevant Documentation (from .agents/context-map.json)", ""]
    for entry in matches:
        path = entry.get("path", "?")
        desc = entry.get("description", "")
        lines.append(f"- **`{path}`**: {desc}")

    lines.append("")
    lines.append(
        "_Read these files for authoritative context. "
        "The full map is at `.agents/context-map.json`._"
    )
    return "\n".join(lines)
