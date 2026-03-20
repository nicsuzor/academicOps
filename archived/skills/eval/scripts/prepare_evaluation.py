#!/usr/bin/env python3
"""Dumb session extractor for agent performance evaluation.

Reads Claude Code hooks logs and outputs raw session data as JSON.
Run with PYTHONPATH=aops-core.

The LLM evaluator classifies workflow type, filters maintenance sessions,
and decides what to evaluate — no heuristics here.

Usage:
    prepare_evaluation.py --recent 5
    prepare_evaluation.py --session-id abc12345
    prepare_evaluation.py --recent 10 --pretty
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from lib.session_paths import find_recent_hooks_logs

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_PROMPT_LENGTH = 2000
_MIN_AGENT_RESPONSE_LENGTH = 100
_MAX_AGENT_RESPONSE_LENGTH = 5000
_SESSION_SEARCH_LIMIT = 100


@dataclass
class SessionSummary:
    """A session prepared for evaluation."""

    session_id: str
    date: str
    project: str
    client: str
    user_prompts: list[str] = field(default_factory=list)
    agent_responses: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    subagent_types: list[str] = field(default_factory=list)
    file_path: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Claude session extraction
# ---------------------------------------------------------------------------


def _extract_claude_session(hooks_log: Path) -> SessionSummary | None:
    """Extract a session summary from a Claude Code hooks log."""
    events: list[dict] = []
    try:
        with open(hooks_log) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return None

    if not events:
        return None

    user_prompts: list[str] = []
    agent_responses: list[str] = []
    tools_used: list[str] = []
    subagent_types: list[str] = []
    session_id = "unknown"
    date = "unknown"
    project = "unknown"

    for event in events:
        hook = event.get("hook_event", "")

        # Session metadata
        if session_id == "unknown":
            session_id = event.get("session_short_hash", "unknown")
        if date == "unknown":
            logged_at = event.get("logged_at", "")
            if logged_at:
                date = logged_at[:10]
        if project == "unknown":
            cwd = event.get("cwd", "")
            if cwd:
                project = Path(cwd).name

        # User prompts
        if hook == "UserPromptSubmit":
            raw_input = event.get("raw_input", {})
            prompt = raw_input.get("prompt", "")
            if prompt:
                user_prompts.append(prompt[:_MAX_PROMPT_LENGTH])

        # Tool usage
        if hook in ("PreToolUse", "PostToolUse"):
            tool_name = event.get("tool_name", "")
            if tool_name and tool_name not in tools_used:
                tools_used.append(tool_name)

        # Subagent interactions — only capture Agent tool outputs
        if hook == "PostToolUse" and event.get("tool_name") == "Agent":
            subagent_type = event.get("subagent_type", "")
            if subagent_type and subagent_type not in subagent_types:
                subagent_types.append(subagent_type)

            tool_output = event.get("tool_output", {})
            if isinstance(tool_output, dict) and tool_output.get("status") == "completed":
                content_blocks = tool_output.get("content", [])
                if isinstance(content_blocks, list):
                    for block in content_blocks:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "")
                            if text and len(text) > _MIN_AGENT_RESPONSE_LENGTH:
                                agent_responses.append(text[:_MAX_AGENT_RESPONSE_LENGTH])

    if not user_prompts:
        return None

    return SessionSummary(
        session_id=session_id,
        date=date,
        project=project,
        client="claude",
        user_prompts=user_prompts,
        agent_responses=agent_responses,
        tools_used=tools_used,
        subagent_types=subagent_types,
        file_path=str(hooks_log),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Extract sessions as JSON for agent performance evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--recent",
        type=int,
        metavar="N",
        help="Extract up to N most recent valid sessions",
    )
    parser.add_argument(
        "--session-id",
        help="Extract a specific session by ID prefix",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()

    if not args.recent and not args.session_id:
        parser.error("Provide --recent N or --session-id ID")

    sessions: list[SessionSummary] = []

    if args.recent:
        for log_path in find_recent_hooks_logs(_SESSION_SEARCH_LIMIT):
            summary = _extract_claude_session(log_path)
            if summary is not None:
                sessions.append(summary)
            if len(sessions) >= args.recent:
                break
    else:
        for log_path in find_recent_hooks_logs(_SESSION_SEARCH_LIMIT):
            summary = _extract_claude_session(log_path)
            if summary and summary.session_id.startswith(args.session_id):
                sessions.append(summary)
                break

    output = [s.to_dict() for s in sessions]
    indent = 2 if args.pretty else None
    json.dump(output, sys.stdout, indent=indent, default=str)
    sys.stdout.write("\n")

    print(f"\nExtracted {len(sessions)} session(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
