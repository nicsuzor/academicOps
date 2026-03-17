#!/usr/bin/env python3
"""Extract subagent interactions from Claude Code and Gemini session logs.

Generic extraction tool — works for any subagent type (prompt-hydrator,
custodiet, qa, etc.). Outputs JSON to stdout for downstream consumption.

Usage:
    # Extract hydrator interactions from a specific Claude hooks log
    extract_agent_interactions.py --hooks-log PATH

    # Extract recent interactions across all Claude projects
    extract_agent_interactions.py --recent 10

    # Filter by agent type (default: all)
    extract_agent_interactions.py --recent 5 --agent-type prompt-hydrator

    # Extract from a Gemini session
    extract_agent_interactions.py --gemini-session PATH

    # Include context file contents
    extract_agent_interactions.py --recent 5 --include-context

    # Both clients
    extract_agent_interactions.py --recent 5 --client all
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from lib.session_paths import find_recent_hooks_logs

# Only allow reading context files from temporary directories.
# This prevents arbitrary file read if logs contain crafted paths.
_ALLOWED_CONTEXT_DIRS: list[Path] = list(
    {
        Path("/tmp"),
        Path(os.environ.get("TMPDIR", "/tmp")),
        Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")),
    }
)


@dataclass
class AgentInteraction:
    """A single subagent invocation and its response."""

    session_id: str
    date: str
    project: str
    client: str  # "claude" or "gemini"
    agent_type: str
    delegation_prompt: str
    agent_output: str
    context_file_path: str | None = None
    context_file_content: str | None = None
    trigger: str | None = None  # user prompt or hook event
    agent_id: str | None = None
    duration_ms: int | None = None
    total_tokens: int | None = None
    timestamp: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Claude extraction (hooks log based)
# ---------------------------------------------------------------------------


def _extract_from_hooks_log(
    hooks_log_path: Path,
    agent_type_filter: str | None,
    include_context: bool,
) -> list[AgentInteraction]:
    """Extract agent interactions from a Claude Code hooks log."""
    interactions: list[AgentInteraction] = []

    events: list[dict] = []
    with open(hooks_log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Find PostToolUse events where tool_output has status=completed
    # and subagent_type matches filter
    for event in events:
        if event.get("hook_event") != "PostToolUse":
            continue

        tool_output = event.get("tool_output", {})
        if not isinstance(tool_output, dict):
            continue
        if tool_output.get("status") != "completed":
            continue

        subagent_type = event.get("subagent_type", "")
        if not subagent_type:
            continue

        # Apply filter
        if agent_type_filter and agent_type_filter not in subagent_type:
            continue

        # Extract the agent's response text
        content_blocks = tool_output.get("content", [])
        output_text = _extract_text_from_content(content_blocks)
        if not output_text:
            continue

        # Extract metadata
        session_id = event.get("session_short_hash", "unknown")
        logged_at = event.get("logged_at", "")
        date = logged_at[:10] if logged_at else "unknown"
        prompt = tool_output.get("prompt", "")

        # Determine project from cwd
        cwd = event.get("cwd", "")
        project = Path(cwd).name if cwd else "unknown"

        # Find the user prompt that triggered this session
        trigger = _find_trigger_prompt(events, event)

        # Context file handling
        context_path = None
        context_content = None
        if _looks_like_file_path(prompt):
            context_path = prompt
            if include_context:
                context_content = _read_file_safe(Path(prompt))

        interaction = AgentInteraction(
            session_id=session_id,
            date=date,
            project=project,
            client="claude",
            agent_type=subagent_type,
            delegation_prompt=prompt,
            agent_output=output_text,
            context_file_path=context_path,
            context_file_content=context_content,
            trigger=trigger,
            agent_id=tool_output.get("agentId"),
            duration_ms=tool_output.get("totalDurationMs"),
            total_tokens=tool_output.get("totalTokens"),
            timestamp=logged_at,
        )
        interactions.append(interaction)

    return interactions


def _extract_text_from_content(content_blocks: list) -> str:
    """Join text blocks from a content array."""
    if not isinstance(content_blocks, list):
        return ""
    parts = []
    for block in content_blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def _find_trigger_prompt(events: list[dict], target_event: dict) -> str | None:
    """Find the user prompt that preceded this agent invocation."""
    target_time = target_event.get("logged_at", "")
    # Walk backwards to find most recent UserPromptSubmit
    for event in reversed(events):
        if event.get("hook_event") != "UserPromptSubmit":
            continue
        event_time = event.get("logged_at", "")
        if event_time <= target_time:
            raw_input = event.get("raw_input", {})
            prompt = raw_input.get("prompt", "")
            if prompt:
                return prompt[:500]  # Truncate long prompts
            break
    return None


def _looks_like_file_path(s: str) -> bool:
    """Check if a string looks like a file path."""
    return bool(s) and s.startswith("/") and not s.startswith("//")


def _read_file_safe(path: Path) -> str | None:
    """Read a file only if it resides within an allowed temp directory.

    Prevents arbitrary file read if session logs contain crafted paths
    (path traversal / prompt injection via log content).
    """
    try:
        resolved = path.resolve()
        if not any(
            str(resolved).startswith(str(d.resolve()) + os.sep) for d in _ALLOWED_CONTEXT_DIRS
        ):
            return None
        return resolved.read_text()
    except (OSError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------------------------
# Claude: find recent hooks logs across all projects
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Gemini extraction
# ---------------------------------------------------------------------------


def _extract_from_gemini_session(
    session_path: Path,
    agent_type_filter: str | None,
    include_context: bool,
) -> list[AgentInteraction]:
    """Extract agent interactions from a Gemini session JSON file.

    Gemini stores subagent calls in messages[i].toolCalls[j] with structure:
      - name: agent name (e.g. "prompt-hydrator")
      - args: {query: "/path/to/context.md"}
      - result[0].functionResponse.response.output: the agent's full output text
    """
    interactions: list[AgentInteraction] = []

    try:
        with open(session_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    messages = data.get("messages", [])
    session_id = data.get("sessionId", "unknown")[:8]

    # Extract date from session data
    date = "unknown"
    start_time = data.get("startTime", "")
    if start_time:
        date = start_time[:10]

    # Infer project from path — assumes layout: .../{project}/tmp/session-*.json
    project = session_path.parent.parent.name if session_path.parent.parent else "unknown"

    for i, msg in enumerate(messages):
        tool_calls = msg.get("toolCalls", [])
        for tc in tool_calls:
            agent_name = tc.get("name", "")
            if not agent_name:
                continue

            # Extract the agent's output from result
            agent_output = _extract_gemini_tool_output(tc)
            if not agent_output:
                continue

            # Distinguish subagent delegations from regular tool calls.
            # Relies on Gemini's output format: "Subagent '{name}' finished."
            # If Gemini changes this format, this heuristic will need updating.
            is_subagent = agent_output.startswith("Subagent '")
            if not is_subagent:
                continue

            # Apply filter
            if agent_type_filter and agent_type_filter not in agent_name:
                continue

            # Extract delegation prompt from args
            args = tc.get("args", {})
            query = args.get("query", "") or args.get("prompt", "")

            # Find trigger (user message before this)
            trigger = _find_gemini_trigger(messages, i)

            # Context file handling
            context_path = query if _looks_like_file_path(query) else None
            context_content = None
            if context_path and include_context:
                context_content = _read_file_safe(Path(context_path))

            timestamp = tc.get("timestamp", "") or msg.get("timestamp", "")

            interaction = AgentInteraction(
                session_id=session_id,
                date=date,
                project=project,
                client="gemini",
                agent_type=agent_name,
                delegation_prompt=query,
                agent_output=agent_output,
                context_file_path=context_path,
                context_file_content=context_content,
                trigger=trigger,
                timestamp=timestamp,
            )
            interactions.append(interaction)

    return interactions


def _extract_gemini_tool_output(tool_call: dict) -> str | None:
    """Extract the agent output text from a Gemini toolCall result."""
    results = tool_call.get("result", [])
    if not isinstance(results, list):
        return None
    for result in results:
        if not isinstance(result, dict):
            continue
        fr = result.get("functionResponse", {})
        response = fr.get("response", {})
        output = response.get("output", "")
        if output:
            return output
    return None


def _gemini_msg_text(msg: dict) -> str:
    """Extract text from a Gemini message."""
    content = msg.get("content", [])
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(parts)
    return ""


def _find_gemini_trigger(messages: list[dict], before_idx: int) -> str | None:
    """Find the user message that triggered this agent call."""
    for j in range(before_idx - 1, -1, -1):
        msg = messages[j]
        if msg.get("type") == "user":
            text = _gemini_msg_text(msg)
            # Strip hook context
            text = re.sub(r"<hook_context>.*?</hook_context>", "", text, flags=re.DOTALL)
            text = text.strip()
            if text:
                return text[:500]
    return None


def _find_recent_gemini_sessions(n: int) -> list[Path]:
    """Find the N most recent Gemini session files."""
    gemini_tmp = Path.home() / ".gemini" / "tmp"
    if not gemini_tmp.exists():
        return []

    sessions: list[tuple[float, Path]] = []
    for session_path in gemini_tmp.rglob("session-*.json"):
        try:
            mtime = session_path.stat().st_mtime
            sessions.append((mtime, session_path))
        except OSError:
            continue

    sessions.sort(key=lambda x: x[0], reverse=True)
    return [path for _, path in sessions[:n]]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Extract subagent interactions from session logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--hooks-log",
        type=Path,
        help="Path to a specific Claude hooks log file",
    )
    parser.add_argument(
        "--gemini-session",
        type=Path,
        help="Path to a specific Gemini session JSON file",
    )
    parser.add_argument(
        "--recent",
        type=int,
        metavar="N",
        help="Extract from the N most recent sessions",
    )
    parser.add_argument(
        "--agent-type",
        help="Filter by agent type substring (e.g. 'prompt-hydrator', 'custodiet')",
    )
    parser.add_argument(
        "--client",
        choices=["claude", "gemini", "all"],
        default="claude",
        help="Which client's sessions to scan (default: claude)",
    )
    parser.add_argument(
        "--include-context",
        action="store_true",
        help="Include context file contents in output",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()

    interactions: list[AgentInteraction] = []

    # Specific file modes
    if args.hooks_log:
        interactions.extend(
            _extract_from_hooks_log(args.hooks_log, args.agent_type, args.include_context)
        )
    elif args.gemini_session:
        interactions.extend(
            _extract_from_gemini_session(args.gemini_session, args.agent_type, args.include_context)
        )
    elif args.recent:
        n = args.recent
        if args.client in ("claude", "all"):
            for log_path in find_recent_hooks_logs(n):
                interactions.extend(
                    _extract_from_hooks_log(log_path, args.agent_type, args.include_context)
                )
        if args.client in ("gemini", "all"):
            for session_path in _find_recent_gemini_sessions(n):
                interactions.extend(
                    _extract_from_gemini_session(
                        session_path, args.agent_type, args.include_context
                    )
                )
    else:
        parser.error("Provide --hooks-log, --gemini-session, or --recent N")

    # Sort by timestamp
    interactions.sort(key=lambda x: x.timestamp or "", reverse=True)

    # Output
    output = [i.to_dict() for i in interactions]
    indent = 2 if args.pretty else None
    json.dump(output, sys.stdout, indent=indent, default=str)
    sys.stdout.write("\n")

    # Summary to stderr
    print(f"\nExtracted {len(interactions)} interaction(s)", file=sys.stderr)
    if interactions:
        agents = {}
        for i in interactions:
            agents[i.agent_type] = agents.get(i.agent_type, 0) + 1
        for agent, count in sorted(agents.items()):
            print(f"  {agent}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()
