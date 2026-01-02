#!/usr/bin/env python3
"""Extract narrative signals from session transcripts for daily note enrichment.

Extracts:
- Session intents (first user prompt per session)
- Abandoned todos (pending/in_progress at session end)
- Timestamps for context reconstruction

Usage:
    uv run python skills/session-insights/scripts/extract_narrative.py
    uv run python skills/session-insights/scripts/extract_narrative.py --date 20260101

Output:
    Markdown sections ready to append to daily note:
    - ## Session Context (timestamped intents)
    - ## Abandoned Todos (unchecked items from session end)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path for lib imports
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ),
)

from lib.session_reader import find_sessions


@dataclass
class SessionNarrative:
    """Narrative signals extracted from a single session."""

    session_id: str
    project: str
    start_time: datetime | None
    first_prompt: str  # Intent - what the session started with
    abandoned_todos: list[str]  # Items left pending/in_progress


def parse_todowrite_final_state(entries: list[dict]) -> list[str]:
    """Extract abandoned todos from final TodoWrite state.

    Returns list of task descriptions that were pending or in_progress.
    """
    abandoned = []

    # Scan in reverse to find last TodoWrite
    for entry in reversed(entries):
        if entry.get("type") != "assistant":
            continue

        message = entry.get("message", {})
        content = message.get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                if block.get("name") == "TodoWrite":
                    todos = block.get("input", {}).get("todos", [])
                    for todo in todos:
                        status = todo.get("status", "pending")
                        task = todo.get("content", "")
                        if status in ("pending", "in_progress") and task:
                            abandoned.append(task)
                    return abandoned

    return abandoned


def extract_first_prompt(entries: list[dict]) -> str:
    """Extract first substantive user prompt (session intent)."""
    for entry in entries:
        if entry.get("type") != "user":
            continue
        if entry.get("isMeta", False):
            continue

        message = entry.get("message", {})
        content = message.get("content", [])

        # Handle string content (commands)
        if isinstance(content, str):
            text = content.strip()
            # Skip command XML, extract args if present
            if "<command-args>" in text:
                match = re.search(r"<command-args>(.*?)</command-args>", text, re.DOTALL)
                if match:
                    return match.group(1).strip()[:100]
            elif not text.startswith("<"):
                return text[:100]

        # Handle list content (API format)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if text and not text.startswith("<"):
                        return text[:100]

    return ""


def extract_session_start_time(entries: list[dict]) -> datetime | None:
    """Extract session start timestamp from first entry."""
    for entry in entries:
        ts = entry.get("timestamp")
        if ts:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
    return None


def process_session_jsonl(jsonl_path: Path, session_id: str, project: str) -> SessionNarrative | None:
    """Process a single session JSONL file."""
    entries = []
    try:
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return None

    if not entries:
        return None

    abandoned = parse_todowrite_final_state(entries)
    first_prompt = extract_first_prompt(entries)
    start_time = extract_session_start_time(entries)

    return SessionNarrative(
        session_id=session_id[:8],
        project=project.split("-")[-1],  # Short project name
        start_time=start_time,
        first_prompt=first_prompt,
        abandoned_todos=abandoned,
    )


def format_narrative_sections(narratives: list[SessionNarrative]) -> str:
    """Format extracted narratives as daily note sections."""
    lines = []

    # Session Context section - only if we have intents
    sessions_with_intent = [n for n in narratives if n.start_time and n.first_prompt]
    if sessions_with_intent:
        lines.append("## Session Context")
        lines.append("")
        for n in sorted(sessions_with_intent, key=lambda x: x.start_time or datetime.min):
            time_str = n.start_time.strftime("%I:%M %p")  # type: ignore
            lines.append(f"- {time_str}: {n.first_prompt}")
        lines.append("")

    # Abandoned Todos section - only if we have abandoned items
    all_abandoned = []
    for n in narratives:
        for todo in n.abandoned_todos:
            all_abandoned.append(f"- [ ] {todo} (from {n.session_id})")

    if all_abandoned:
        lines.append("## Abandoned Todos")
        lines.append("")
        lines.extend(all_abandoned)
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract narrative signals from sessions")
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y%m%d"),
        help="Date to process (YYYYMMDD, default: today)",
    )
    args = parser.parse_args()

    # Parse target date
    target_date = datetime.strptime(args.date, "%Y%m%d").date()

    # Find sessions for the target date using existing discovery
    all_sessions = find_sessions()
    day_sessions = [
        s
        for s in all_sessions
        if s.last_modified.date() == target_date
        and "claude-test" not in s.project
        and os.path.getsize(s.path) > 5000
    ]

    if not day_sessions:
        print(f"No sessions found for {args.date}", file=sys.stderr)
        return 0

    # Process each session
    narratives = []
    for s in day_sessions:
        narrative = process_session_jsonl(Path(s.path), s.session_id, s.project)
        if narrative:
            narratives.append(narrative)

    if not narratives:
        print(f"No narrative signals extracted for {args.date}", file=sys.stderr)
        return 0

    # Output formatted sections
    output = format_narrative_sections(narratives)
    print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
