"""
Session Reader - Unified parser for Claude Code session files.

Reads and combines:
- Main session JSONL (*.jsonl)
- Agent transcripts (agent-*.jsonl)
- Hook logs (*-hooks.jsonl)

Used by:
- /transcript skill for markdown export
- Dashboard for live activity display
- Intent router context extraction
"""

from __future__ import annotations

import glob
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from lib.transcript_parser import (
    SessionInfo,
    SessionProcessor,
    SessionState,
    TodoWriteState,
    _summarize_tool_input,
)

# Configuration constants for router context extraction
_MAX_TURNS = 5
_SKILL_LOOKBACK = 10
_PROMPT_TRUNCATE = (
    400  # Increased from 100 to preserve more context (validated 2026-01-11)
)
_MAX_TOOL_CALLS = 10  # Max recent tool calls to include in context


def parse_todowrite_state(entries: list[Any]) -> TodoWriteState | None:
    """
    Parse the most recent TodoWrite state from session entries.

    Scans entries in reverse order to find the most recent TodoWrite call
    and extracts the full state.

    Args:
        entries: List of session entries (dicts with type, message, etc.)

    Returns:
        TodoWriteState with todos list, counts, and in_progress task.
        Returns None if no TodoWrite found.
    """
    for entry in reversed(entries):
        # Handle both Entry objects and raw dicts
        if hasattr(entry, "type"):
            entry_type = entry.type
            message = entry.message or {}
        else:
            entry_type = entry.get("type")
            message = entry.get("message", {})

        if entry_type != "assistant":
            continue

        content = message.get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                if block.get("name") == "TodoWrite":
                    tool_input = block.get("input", {})
                    todos = tool_input.get("todos", [])
                    if todos:
                        counts = {"pending": 0, "in_progress": 0, "completed": 0}
                        in_progress_task = None
                        for todo in todos:
                            status = todo.get("status", "pending")
                            if status in counts:
                                counts[status] += 1
                            if status == "in_progress" and not in_progress_task:
                                in_progress_task = todo.get("content", "")

                        return TodoWriteState(
                            todos=todos,
                            counts=counts,
                            in_progress_task=in_progress_task,
                        )

    return None


def extract_router_context(transcript_path: Path, max_turns: int = _MAX_TURNS) -> str:
    """Extract compact context for intent router.

    Parses the JSONL transcript and extracts:
    - Last N user prompts (truncated)
    - Most recent Skill invocation
    - TodoWrite task status counts

    Args:
        transcript_path: Path to session JSONL file
        max_turns: Maximum number of recent prompts to include

    Returns:
        Formatted markdown context or empty string if file doesn't exist/is empty

    Raises:
        Exception: On parsing errors (fail-fast per AXIOM #7)
    """
    if not transcript_path.exists():
        return ""
    return _extract_router_context_impl(transcript_path, max_turns)


def _is_system_injected_context(text: str) -> bool:
    """Check if text is system-injected context (not actual user input).

    These are automatically added by Claude Code, not typed by user:
    - <agent-notification> - task completion notifications
    - <ide_selection> - user's IDE selection
    - <ide_opened_file> - file user has open in IDE
    - <system-reminder> - hook-injected reminders
    """
    stripped = text.strip()
    system_prefixes = (
        "<agent-notification>",
        "<ide_selection>",
        "<ide_opened_file>",
        "<system-reminder>",
    )
    return any(stripped.startswith(prefix) for prefix in system_prefixes)


def _clean_prompt_text(text: str) -> str:
    """Clean prompt text by stripping command XML markup.

    Commands like /do wrap content in XML:
    <command-message>do</command-message>
    <command-name>/do</command-name>
    <command-args>actual user intent here</command-args>

    This extracts just the args content.
    """

    # Check for command XML format
    args_match = re.search(r"<command-args>(.*?)</command-args>", text, re.DOTALL)
    if args_match:
        return args_match.group(1).strip()

    # Not a command, return as-is
    return text


def _extract_router_context_impl(transcript_path: Path, max_turns: int) -> str:
    """Implementation of router context extraction."""
    # Use SessionProcessor to parse and group turns (DRY compliant)
    # Skip agents and hooks for speed - we only need main conversation
    processor = SessionProcessor()
    _, entries, _ = processor.parse_session_file(
        transcript_path, load_agents=False, load_hooks=False
    )

    if not entries:
        return ""

    # Group into turns to handle command expansion properly
    turns = processor.group_entries_into_turns(entries, full_mode=True)

    # Extract user prompts (skip system injected)
    recent_prompts: list[str] = []

    # Process turns in reverse to find recent info
    # (But group_entries_into_turns returns chronological)

    # Extract prompts from turns
    for turn in turns:
        # Check for user message
        user_message = (
            turn.get("user_message") if isinstance(turn, dict) else turn.user_message
        )
        is_meta = turn.get("is_meta") if isinstance(turn, dict) else turn.is_meta

        if user_message and not is_meta:
            text = user_message.strip()
            # Restore aggressive filtering lost in refactor
            if text and not _is_system_injected_context(text):
                cleaned = _clean_prompt_text(text)
                if cleaned:
                    recent_prompts.append(cleaned)

    # Keep only last N prompts
    recent_prompts = recent_prompts[-max_turns:] if recent_prompts else []

    # Find most recent Skill invocation
    recent_skill: str | None = None

    # Find active task (TodoWrite)
    todowrite_state = parse_todowrite_state(entries)
    todo_counts = todowrite_state.counts if todowrite_state else None
    in_progress_task = todowrite_state.in_progress_task if todowrite_state else None

    # Extract recent tool calls
    recent_tools: list[str] = []
    agent_responses: list[str] = []

    # Iterate reversed for recent tools/skills
    # We iterate turns reversed
    for turn in reversed(turns):
        assistant_sequence = (
            turn.get("assistant_sequence")
            if isinstance(turn, dict)
            else turn.assistant_sequence
        )
        if not assistant_sequence:
            continue

        # Collect response text for context (limit to 3 turns)
        if len(agent_responses) < 3:
            # Join text parts
            texts = [
                item["content"]
                for item in assistant_sequence
                if item.get("type") == "text"
            ]
            if texts:
                full_text = " ".join(texts)
                # Truncate if too long
                if len(full_text) > 300:
                    full_text = full_text[:300] + "..."
                agent_responses.append(full_text)

        # Scan for tools
        for item in reversed(assistant_sequence):
            if item.get("type") == "tool":
                tool_call = item.get("content", "")

                # Extract tool name from content "Name(args)" or similar
                # group_entries_into_turns formats it as "Name(input)" or just "Name"
                # But it provides 'tool_name' and 'tool_input' in the item dict too!
                tool_name = item.get("tool_name", "")
                tool_input = item.get("tool_input", {})

                # If tool_name is missing from item (legacy parser might not add it?), try to parse content
                if not tool_name and "(" in tool_call:
                    tool_name = tool_call.split("(")[0]

                if tool_name == "Skill":
                    if not recent_skill:
                        recent_skill = tool_input.get("skill")
                    continue

                if tool_name == "TodoWrite":
                    continue

                if len(recent_tools) < _MAX_TOOL_CALLS:
                    recent_tools.append(tool_call)  # Use the pre-formatted content

    # Reverse back to chronological
    agent_responses.reverse()
    recent_tools.reverse()

    # Format output (same as before)
    if (
        not recent_prompts
        and not recent_skill
        and not todo_counts
        and not recent_tools
        and not agent_responses
    ):
        return ""

    lines = ["## Session Context", ""]

    if recent_prompts:
        lines.append("Recent prompts:")
        for i, prompt in enumerate(recent_prompts, 1):
            # Truncate long prompts
            truncated = (
                prompt[:_PROMPT_TRUNCATE] + "..."
                if len(prompt) > _PROMPT_TRUNCATE
                else prompt
            )
            # Escape backticks
            truncated = truncated.replace("```", "'''")
            lines.append(f'{i}. "{truncated}"')
        lines.append("")

    if agent_responses:
        lines.append("Recent agent responses:")
        for i, response in enumerate(agent_responses, 1):
            lines.append(f'{i}. "{response}"')
        lines.append("")

    if recent_tools:
        lines.append("Recent tools:")
        for tool in recent_tools:
            lines.append(f"  - {tool}")
        lines.append("")

    if recent_skill:
        lines.append(f'Active: Skill("{recent_skill}") invoked recently')

    if todo_counts:
        task_desc = f' ("{in_progress_task}")' if in_progress_task else ""
        lines.append(
            f"Tasks: {todo_counts['pending']} pending, "
            f"{todo_counts['in_progress']} in_progress{task_desc}, "
            f"{todo_counts['completed']} completed"
        )

    return "\n".join(lines)


def extract_gate_context(
    transcript_path: Path,
    include: set[str],
    max_turns: int = _MAX_TURNS,
) -> dict[str, Any]:
    """Extract configurable context for gate agents.

    Provides targeted extraction for gate functions per gate-agent-architecture.md.
    Each gate requests only the context it needs via the include parameter.

    Args:
        transcript_path: Path to session JSONL file
        include: Set of extraction types (prompts, skill, todos, intent, errors, tools)
        max_turns: Lookback limit for prompts/tools

    Returns:
        Dict with requested context sections. Empty dict on error.

    Example:
        >>> result = extract_gate_context(path, include={"prompts", "skill"})
        >>> result["prompts"]  # List of recent user prompts
        >>> result["skill"]    # Most recent Skill invocation or None
    """
    if not include:
        return {}

    if not transcript_path.exists():
        return {}

    try:
        return _extract_gate_context_impl(transcript_path, include, max_turns)
    except Exception:
        return {}


def _extract_gate_context_impl(
    transcript_path: Path,
    include: set[str],
    max_turns: int,
) -> dict[str, Any]:
    """Implementation of gate context extraction using SessionProcessor."""
    processor = SessionProcessor()
    _, entries, _ = processor.parse_session_file(
        transcript_path, load_agents=False, load_hooks=False
    )

    if not entries:
        return {}

    # Group into turns for consistent parsing
    turns = processor.group_entries_into_turns(entries, full_mode=True)

    result = {}

    # Extract prompts using Turns logic
    if "prompts" in include:
        prompts = []
        for turn in turns:
            user_message = (
                turn.get("user_message")
                if isinstance(turn, dict)
                else turn.user_message
            )
            is_meta = turn.get("is_meta") if isinstance(turn, dict) else turn.is_meta
            if user_message and not is_meta:
                text = user_message.strip()
                if text and not _is_system_injected_context(text):
                    cleaned = _clean_prompt_text(text)
                    if cleaned:
                        prompts.append(cleaned)
        result["prompts"] = prompts[-max_turns:]

    # For skill we can use raw entries or turns. TodoWrite needs raw entries currently.
    if "skill" in include:
        result["skill"] = _extract_recent_skill(entries)

    if "todos" in include:
        result["todos"] = _extract_todos(entries)

    if "intent" in include:
        # Improve intent extraction to look for first non-meta user turn
        result["intent"] = processor._extract_first_user_request(entries)

    if "tools" in include:
        # Extract tools from turns
        tools = []
        for turn in reversed(turns):
            assistant_sequence = (
                turn.get("assistant_sequence")
                if isinstance(turn, dict)
                else turn.assistant_sequence
            )
            if not assistant_sequence:
                continue
            for item in reversed(assistant_sequence):
                if item.get("type") == "tool":
                    tools.append(
                        {
                            "name": item.get("tool_name", "unknown"),
                            "input": item.get("tool_input", {}),
                            "content": item.get("content", ""),
                        }
                    )
            if len(tools) >= max_turns:  # approximate limits
                break
        result["tools"] = list(reversed(tools[:max_turns]))

    if "errors" in include:
        result["errors"] = _extract_errors(entries, max_turns)

    if "files" in include:
        result["files"] = _extract_files_modified(entries)

    if "conversation" in include:
        # Generate unified conversation log (ns-52v)
        # Returns list of strings [User]: ..., [Agent]: ...
        log_lines: list[str] = []

        # Use reversed turns to efficiently get last N
        count = 0
        for turn in reversed(turns):
            if count >= max_turns:
                break

            turn_lines = []

            # Assistant part (happens after user message in turn)
            assistant_sequence = (
                turn.get("assistant_sequence")
                if isinstance(turn, dict)
                else turn.assistant_sequence
            )
            if assistant_sequence:
                for item in reversed(
                    assistant_sequence
                ):  # Reversed again to push to front of turn lines? No.
                    # We want chronological order within the turn.
                    pass

            # Actually easier to process chronological turns and then slice.
            pass

        # Linear pass chronological
        chronological_lines = []
        for turn in turns:
            user_msg = (
                turn.get("user_message")
                if isinstance(turn, dict)
                else turn.user_message
            )
            is_meta = turn.get("is_meta") if isinstance(turn, dict) else turn.is_meta

            if user_msg and not is_meta:
                msg = user_msg.strip()
                if len(msg) > 400:
                    msg = msg[:400] + "..."
                chronological_lines.append(f"[User]: {msg}")

            assistant_sequence = (
                turn.get("assistant_sequence")
                if isinstance(turn, dict)
                else turn.assistant_sequence
            )
            if assistant_sequence:
                for item in assistant_sequence:
                    type_ = item.get("type")
                    if type_ == "text":
                        content = item.get("content", "").strip()
                        if content:
                            if len(content) > 400:
                                content = content[:400] + "..."
                            chronological_lines.append(f"[Agent]: {content}")
                    elif type_ == "tool":
                        tool_name = item.get("tool_name", "")
                        comp = item.get("content", "")
                        if not tool_name:
                            if "(" in comp:
                                tool_name = comp.split("(")[0]
                            else:
                                tool_name = comp

                        if tool_name not in ("TodoWrite", "Skill"):
                            # Truncate tool args
                            if len(comp) > 100:
                                comp = comp[:100] + "..."
                            chronological_lines.append(f"[Tool:{tool_name}]: {comp}")

        # Keep last N *lines*? Or turns?
        # Custodiet shows last 5 turns.
        # But if we return list of strings, Custodiet might just show last N output lines?
        # Or we return all lines for last N turns.

        # Let's return lines corresponding to last max_turns turns.
        # Recalculate:
        processed_turns = turns[-max_turns:] if len(turns) > max_turns else turns
        final_log = []
        for turn in processed_turns:
            # User
            user_msg = (
                turn.get("user_message")
                if isinstance(turn, dict)
                else turn.user_message
            )
            is_meta = turn.get("is_meta") if isinstance(turn, dict) else turn.is_meta
            if user_msg and not is_meta:
                msg = user_msg.strip()
                if len(msg) > 400:
                    msg = msg[:400] + "..."
                final_log.append(f"[User]: {msg}")

            # Assistant
            assistant_sequence = (
                turn.get("assistant_sequence")
                if isinstance(turn, dict)
                else turn.assistant_sequence
            )
            if assistant_sequence:
                for item in assistant_sequence:
                    type_ = item.get("type")
                    if type_ == "text":
                        content = item.get("content", "").strip()
                        if content:
                            if len(content) > 400:
                                content = content[:400] + "..."
                            final_log.append(f"[Agent]: {content}")
                    elif type_ == "tool":
                        tool_name = item.get("tool_name", "")
                        comp = item.get("content", "")
                        if not tool_name:
                            if "(" in comp:
                                tool_name = comp.split("(")[0]
                            else:
                                tool_name = comp

                        if tool_name not in ("TodoWrite", "Skill"):
                            # Extract content part for display
                            # comp includes Name(args).
                            # We want [Tool:Name]: args
                            # But keeping it simple [Tool:Name]: Name(args) is duplicative
                            # AC says: [Tool:Read]: ...

                            # If comp is "Read(file_path=...)"
                            # We want [Tool:Read]: file_path=...

                            display_args = comp
                            # Strip leading bullet if present
                            if display_args.startswith("- "):
                                display_args = display_args[2:]

                            if tool_name and display_args.startswith(tool_name):
                                display_args = (
                                    display_args[len(tool_name) :].strip().strip("()")
                                )

                            if len(display_args) > 100:
                                display_args = display_args[:100] + "..."
                            final_log.append(f"[Tool:{tool_name}]: {display_args}")

        result["conversation"] = final_log

    return result


def _extract_recent_skill(entries: list[Any]) -> str | None:
    """Extract most recent Skill invocation."""
    for entry in reversed(entries):
        etype = entry.type if hasattr(entry, "type") else entry.get("type")
        if etype != "assistant":
            continue

        message = (
            entry.message if hasattr(entry, "message") else entry.get("message", {})
        )
        content = message.get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                if block.get("name") == "Skill":
                    return block.get("input", {}).get("skill")

    return None


def _extract_todos(entries: list[dict]) -> dict[str, Any] | None:
    """Extract current TodoWrite state with full todo list.

    Returns complete todo information for compliance checking,
    not just counts - custodiet needs to see the full plan.
    """
    state = parse_todowrite_state(entries)
    if state is None:
        return None

    return {
        "counts": state.counts,
        "in_progress_task": state.in_progress_task,
        "todos": state.todos,  # Full list for drift analysis
    }


def _extract_errors(entries: list[Any], max_turns: int) -> list[dict[str, Any]]:
    """Extract recent tool errors with tool name and input context.

    Correlates tool_result errors with their corresponding tool_use blocks
    to provide actionable context for custodiet compliance checking.
    """
    # First pass: build map of tool_use_id -> tool info
    tool_use_map: dict[str, dict[str, Any]] = {}
    for entry in entries:
        etype = entry.type if hasattr(entry, "type") else entry.get("type")
        if etype != "assistant":
            continue
        message = (
            entry.message if hasattr(entry, "message") else entry.get("message", {})
        )
        content = message.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_id = block.get("id", "")
                if tool_id:
                    tool_input = block.get("input", {})
                    # Extract key input for context
                    input_summary = _summarize_tool_input(
                        block.get("name", ""), tool_input
                    )
                    tool_use_map[tool_id] = {
                        "name": block.get("name", "unknown"),
                        "input_summary": input_summary,
                    }

    # Second pass: extract errors and correlate with tool info
    errors: list[dict[str, Any]] = []
    for entry in entries:
        etype = entry.type if hasattr(entry, "type") else entry.get("type")
        if etype != "user":
            continue

        message = (
            entry.message if hasattr(entry, "message") else entry.get("message", {})
        )
        content = message.get("content", [])
        if not isinstance(content, list):
            continue

        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_result":
                if item.get("is_error") or item.get("isError"):
                    tool_id = item.get("tool_use_id") or item.get("toolUseId")
                    tool_info = tool_use_map.get(tool_id, {})
                    error_content = item.get("content", "")

                    errors.append(
                        {
                            "tool_name": tool_info.get("name", "unknown"),
                            "input_summary": tool_info.get("input_summary", ""),
                            "error": str(error_content)[:300],
                        }
                    )

    return errors[-max_turns:] if errors else []


def _extract_files_modified(entries: list[Any]) -> list[str]:
    """Extract unique list of files modified via Edit/Write tools.

    Used by custodiet for scope assessment - are we touching files
    unrelated to the original request?
    """
    files: set[str] = set()

    for entry in entries:
        etype = entry.type if hasattr(entry, "type") else entry.get("type")
        if etype != "assistant":
            continue

        message = (
            entry.message if hasattr(entry, "message") else entry.get("message", {})
        )
        content = message.get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_name = block.get("name", "")
                tool_input = block.get("input", {})

                # Track Edit and Write operations
                if tool_name in ("Edit", "Write"):
                    file_path = tool_input.get("file_path", "")
                    if file_path:
                        files.add(file_path)

    return sorted(files)


def _extract_text_from_content(content: Any) -> str:
    """Extract text from various content formats."""
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "").strip()

    return ""


def find_sessions(
    project: str | None = None,
    since: datetime | None = None,
    claude_projects_dir: Path | None = None,
    include_gemini: bool = True,
) -> list[SessionInfo]:
    """
    Find all Claude Code and optionally Gemini sessions.

    Args:
        project: Filter to specific project (partial match)
        since: Only sessions modified after this time
        claude_projects_dir: Override default ~/.claude/projects/
        include_gemini: Whether to include sessions from ~/.gemini/tmp/

    Returns:
        List of SessionInfo, sorted by last_modified descending (newest first)
    """
    sessions = []

    # 1. Find Claude Code sessions
    if claude_projects_dir is None:
        claude_projects_dir = Path.home() / ".claude" / "projects"

    if claude_projects_dir.exists():
        for project_dir in claude_projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_name = project_dir.name

            # Filter by project if specified
            if project and project.lower() not in project_name.lower():
                continue

            # Find session files (exclude agent-* files)
            for session_file in project_dir.glob("*.jsonl"):
                if session_file.name.startswith("agent-"):
                    continue

                # Determine session_id
                session_id = session_file.stem

                # For hook logs, the filename is a date-hash, not the full session ID.
                if session_file.name.endswith("-hooks.jsonl"):
                    try:
                        with open(session_file, encoding="utf-8") as f:
                            first_line = f.readline()
                            if first_line:
                                data = json.loads(first_line)
                                internal_id = data.get("session_id", "")
                                if internal_id:
                                    session_id = internal_id
                    except (OSError, json.JSONDecodeError):
                        pass

                # Get modification time
                mtime = datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC)

                # Filter by time if specified
                if since and mtime < since:
                    continue

                sessions.append(
                    SessionInfo(
                        path=session_file,
                        project=project_name,
                        session_id=session_id,
                        last_modified=mtime,
                        source="claude",
                    )
                )

    # 2. Find Gemini sessions
    if include_gemini:
        gemini_tmp_dir = Path.home() / ".gemini" / "tmp"
        if gemini_tmp_dir.exists():
            # Gemini structure: ~/.gemini/tmp/{hash}/chats/session-*.json
            for chat_file in gemini_tmp_dir.glob("**/chats/session-*.json"):
                # Determine session_id from filename or content
                # session-2026-01-08T08-18-a5234d3e -> a5234d3e
                session_id = chat_file.stem
                if session_id.startswith("session-") and "-" in session_id:
                    session_id = session_id.split("-")[-1]

                # Get project from parent of chats dir (the hash)
                hash_dir = chat_file.parent.parent.name
                project_name = f"gemini-{hash_dir[:8]}"

                # Filter by project if specified
                if project and project.lower() not in project_name.lower():
                    continue

                # Get modification time
                mtime = datetime.fromtimestamp(chat_file.stat().st_mtime, tz=UTC)

                # Filter by time if specified
                if since and mtime < since:
                    continue

                sessions.append(
                    SessionInfo(
                        path=chat_file,
                        project=project_name,
                        session_id=session_id,
                        last_modified=mtime,
                        source="gemini",
                    )
                )

    # Sort by last modified, newest first
    sessions.sort(key=lambda s: s.last_modified, reverse=True)
    return sessions


def get_session_state(session: SessionInfo, aca_data: Path) -> SessionState:
    """Determine the current processing state of a session.

    Authoritative logic for idempotency and re-processing requirements.
    """

    session_id = session.session_id
    session_prefix = session_id[:8] if len(session_id) >= 8 else session_id

    # 1. Check for Transcript
    # Patterns vary by source
    if session.source == "gemini":
        transcript_dir = aca_data / "sessions" / "gemini"
    else:
        transcript_dir = aca_data / "sessions" / "claude"

    transcript_path = None
    if transcript_dir.exists():
        # Match EXACT session ID prefix
        pattern = str(transcript_dir / f"*-*-{session_prefix}*-abridged.md")
        matches = glob.glob(pattern)
        if matches:
            transcript_path = Path(matches[0])

    # Missing transcript or session updated since last transcript
    if not transcript_path:
        return SessionState.PENDING_TRANSCRIPT

    if session.path.stat().st_mtime > transcript_path.stat().st_mtime:
        return SessionState.PENDING_TRANSCRIPT

    # 2. Check for Mining JSON
    # Pattern: $ACA_DATA/sessions/insights/{date}-{session_id}.json
    insights_dir = aca_data / "sessions" / "insights"
    has_mining = False

    if insights_dir.exists():
        # New format: {date}-{session_id}.json (e.g., 2025-01-12-a1b2c3d4.json)
        pattern = str(insights_dir / f"*-{session_prefix}.json")
        import glob as glob_module

        matches = glob_module.glob(pattern)
        has_mining = bool(matches)

    if not has_mining:
        return SessionState.PENDING_MINING

    return SessionState.PROCESSED
