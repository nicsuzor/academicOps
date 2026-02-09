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
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
_PROMPT_TRUNCATE = 400  # Increased from 100 to preserve more context (validated 2026-01-11)
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


def _extract_questions_from_text(text: str) -> list[str]:
    """Extract sentences ending with '?' from agent response text.

    Identifies questions in agent messages to help hydrator understand
    short user responses in context (e.g., user says "all" in response
    to agent's "which tasks?").

    Args:
        text: Agent response text

    Returns:
        List of question sentences found, deduplicated
    """
    if not text:
        return []

    # Split on common sentence boundaries, preserving question marks
    # Match sentences ending with ? (with possible punctuation/whitespace)
    questions = []
    # Look for text ending with ? - capture the full sentence leading up to it
    # Using regex to find sentence-like patterns ending with ?
    pattern = r"[^.!?\n]*\?"
    matches = re.findall(pattern, text)

    for match in matches:
        # Clean up the match - remove leading/trailing whitespace
        question = match.strip()
        if question and question not in questions:  # Deduplicate
            questions.append(question)

    return questions


def _extract_and_expand_prompts(turns: list, max_turns: int) -> list[str]:
    """Extracts user prompts from turns, expanding command invocations."""
    prompts = []
    for turn in turns:
        user_message = turn.get("user_message") if isinstance(turn, dict) else turn.user_message
        is_meta = turn.get("is_meta") if isinstance(turn, dict) else turn.is_meta

        if not user_message or is_meta:
            continue

        text = user_message.strip()

        if not text or _is_system_injected_context(text):
            continue

        command_name = None
        args = ""

        # Case 1: XML-wrapped command
        command_name_match = re.search(r"<command-name>(.*?)</command-name>", text, re.DOTALL)
        if command_name_match:
            command_name = command_name_match.group(1).strip()
            args_match = re.search(r"<command-args>(.*?)</command-args>", text, re.DOTALL)
            if args_match:
                args = f" {args_match.group(1).strip()}"
        # Case 2: Simple command prefix
        elif text.startswith("/"):
            parts = text.split(maxsplit=1)
            command_name = parts[0]
            if len(parts) > 1:
                args = f" {parts[1]}"

        if command_name:
            skill_name = command_name.lstrip("/")

            scope = load_skill_scope(skill_name)
            if scope:
                # The scope is a markdown summary. Let's clean it up for the prompt.
                # "Purpose: ..." or "Workflow: ..."
                summary = " ".join(scope.replace("**", "").split())
                prompts.append(f'{command_name}{args} → "{summary}"')
                continue

        # Fallback to old logic
        cleaned = _clean_prompt_text(text)
        if cleaned:
            prompts.append(cleaned)

    return prompts[-max_turns:] if prompts else []


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

    # Extract user prompts, expanding commands
    recent_prompts = _extract_and_expand_prompts(turns, max_turns)

    # Find most recent Skill invocation
    recent_skill: str | None = None

    # Find active task (TodoWrite)
    todowrite_state = parse_todowrite_state(entries)
    todo_counts = todowrite_state.counts if todowrite_state else None
    in_progress_task = todowrite_state.in_progress_task if todowrite_state else None

    # Extract recent tool calls
    recent_tools: list[str] = []
    agent_responses: list[str] = []
    agent_questions: list[str] = []  # Track questions separately for clarity

    # Iterate reversed for recent tools/skills
    # We iterate turns reversed
    for turn in reversed(turns):
        assistant_sequence = (
            turn.get("assistant_sequence") if isinstance(turn, dict) else turn.assistant_sequence
        )
        if not assistant_sequence:
            continue

        # Collect response text for context (limit to 3 turns)
        # IMPORTANT: We iterate reversed, so first responses found are MOST RECENT
        if len(agent_responses) < 3:
            # Join text parts
            texts = [item["content"] for item in assistant_sequence if item.get("type") == "text"]
            if texts:
                full_text = " ".join(texts)
                # Extract questions from this agent response (especially important for most recent)
                # This helps hydrator understand short user responses like "yes" or "all"
                questions = _extract_questions_from_text(full_text)
                if questions:
                    # For the most recent response, prioritize questions
                    if len(agent_responses) == 0:
                        # Most recent: add all unique questions found
                        for q in questions:
                            if q not in agent_questions:
                                agent_questions.append(q)
                    else:
                        # Older responses: add just first question if any
                        if questions[0] not in agent_questions:
                            agent_questions.append(questions[0])

                # Truncate - but preserve more for the most recent (first found)
                # This ensures short user prompts like "yes" can see the question
                #
                # When user prompt is short (≤10 chars), it's likely a confirmation
                # like "yes", "ok", "all", etc. Preserve much more context (2000 chars)
                # so the hydrator can see what question the user is responding to.
                current_prompt = recent_prompts[-1] if recent_prompts else ""
                is_short_response = len(current_prompt.strip()) <= 10

                if is_short_response and len(agent_responses) == 0:
                    max_len = 2000  # Preserve full context for short responses
                elif len(agent_responses) == 0:
                    max_len = 500
                else:
                    max_len = 300
                if len(full_text) > max_len:
                    full_text = full_text[:max_len] + "..."
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
    agent_questions.reverse()
    recent_tools.reverse()

    # Format output (same as before)
    if (
        not recent_prompts
        and not recent_skill
        and not todo_counts
        and not recent_tools
        and not agent_responses
        and not agent_questions
    ):
        return ""

    lines = ["## Session Context", ""]

    if recent_prompts:
        lines.append("Recent prompts:")
        for i, prompt in enumerate(recent_prompts, 1):
            # Truncate long prompts
            truncated = (
                prompt[:_PROMPT_TRUNCATE] + "..." if len(prompt) > _PROMPT_TRUNCATE else prompt
            )
            # Escape backticks
            truncated = truncated.replace("```", "'''")
            lines.append(f'{i}. "{truncated}"')
        lines.append("")

    # Show agent questions separately for clarity when responding to short prompts
    if agent_questions:
        lines.append("Agent questions (recent):")
        for i, question in enumerate(agent_questions, 1):
            # Ensure question ends with ? for clarity
            q = question if question.endswith("?") else question + "?"
            lines.append(f"{i}. {q}")
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


def build_rich_session_context(transcript_path: Path | str, max_turns: int = 15) -> str:
    """Build rich session context for compliance checks.

    Extracts recent conversation history, tool usage, files modified,
    and any errors to provide context for compliance evaluation.

    Args:
        transcript_path: Path to session transcript JSONL file
        max_turns: Number of recent turns to include (default 15)

    Returns:
        Formatted markdown context or error message
    """
    path = Path(transcript_path)
    if not path.exists():
        return "(No transcript path available)"

    lines: list[str] = []

    # Extract using library
    gate_ctx = extract_gate_context(
        path,
        include={"prompts", "errors", "tools", "files", "conversation", "skill"},
        max_turns=max_turns,
    )

    # ALL user requests (chronological) - enables scope drift detection
    prompts = gate_ctx.get("prompts", [])
    if prompts:
        lines.append("**All User Requests** (chronological):")
        for i, prompt in enumerate(prompts, 1):
            # Truncate very long prompts but preserve enough for scope checking
            truncated = prompt[:500] + "..." if len(prompt) > 500 else prompt
            lines.append(f"  {i}. {truncated}")
        lines.append("")
        # Also highlight the most recent for quick reference
        lines.append("**Most Recent User Request**:")
        lines.append(f"> {prompts[-1][:500]}")
        lines.append("")

    # Active skill context (if any)
    skill = gate_ctx.get("skill")
    if skill:
        lines.append(f"**Active Skill**: {skill}")
        lines.append("")

    # Recent tool usage WITH ARGUMENTS - enables action verification
    tools = gate_ctx.get("tools", [])
    if tools:
        lines.append("**Recent Tool Calls** (with arguments):")
        for tool in tools[-10:]:  # Last 10 tools
            tool_name = tool["name"]  # Required field - fail if missing
            tool_input = tool.get("input") or {}
            # Format tool arguments, truncate at 200 chars
            if tool_input:
                # Summarize key arguments
                arg_parts = []
                for k, v in list(tool_input.items())[:5]:  # Max 5 args shown
                    v_str = str(v)
                    if len(v_str) > 50:
                        v_str = v_str[:50] + "..."
                    arg_parts.append(f"{k}={v_str}")
                args_str = ", ".join(arg_parts)
                if len(args_str) > 200:
                    args_str = args_str[:200] + "..."
                lines.append(f"  - {tool_name}({args_str})")
            else:
                lines.append(f"  - {tool_name}()")
        lines.append("")

    # Files modified/read
    files = gate_ctx.get("files", [])
    if files:
        lines.append("**Files Accessed**:")
        for f in files[-10:]:  # Last 10 files
            # Handle both legacy list[str] shape and newer list[dict] shape
            if isinstance(f, dict) and "action" in f and "path" in f:
                lines.append(f"  - [{f['action']}] {f['path']}")
            else:
                path_str = str(f)
                if path_str:
                    lines.append(f"  - {path_str}")
        lines.append("")

    # Tool errors (important for compliance - Type A detection)
    errors = gate_ctx.get("errors", [])
    if errors:
        lines.append("**Tool Errors** (check for workaround attempts after these):")
        for e in errors[-5:]:
            lines.append(f"  - {e['tool_name']}: {e['error']}")
        lines.append("")

    # FULL agent responses for last 3 turns - enables phrase pattern detection
    # ("I'll just...", "While I'm at it...", etc.)
    conversation = gate_ctx.get("conversation", [])
    if conversation:
        lines.append("**Recent Agent Responses** (full text for phrase detection):")
        # Extract only agent responses, show last 3 with more content
        agent_responses = [
            turn for turn in conversation if (isinstance(turn, str) and turn.startswith("[Agent]:"))
        ]
        for turn in agent_responses[-3:]:  # Last 3 agent responses
            # String format: "[Agent]: content"
            content = turn[8:] if turn.startswith("[Agent]:") else turn
            # Allow up to 1000 chars per response for phrase detection
            if len(content) > 1000:
                content = content[:1000] + "..."
            if content.strip():
                lines.append(f"  {content.strip()}")
                lines.append("")

        # Also show recent conversation flow (condensed)
        lines.append("**Recent Conversation Summary**:")
        for turn in conversation[-5:]:
            # Handle both string and dict formats
            if isinstance(turn, dict):
                role = turn["role"]  # Required - fail if missing
                content = turn["content"][:200]  # Required - fail if missing
                lines.append(f"  [{role}]: {content}...")
            else:
                # String format - role unknown
                content = str(turn)[:200]
                if content:
                    lines.append(f"  [unknown]: {content}...")
        lines.append("")

    if not lines:
        return "(No session context extracted)"

    return "\n".join(lines)


def build_critic_session_context(transcript_path: Path | str) -> str:
    """Build deep session context for critic agent review.

    Unlike build_rich_session_context (designed for scope-drift detection with
    thin, wide context), this produces a chronological narrative of the entire
    session: user requests, agent reasoning, tool calls with results, and
    decisions made. The critic needs to see what actually happened to provide
    a grounded verdict.

    Design choices:
    - ALL turns included (no max_turns cap) — critic must see full history
    - Agent reasoning text preserved at length (2000 chars) — critic needs
      to see *why* decisions were made, not just what tools were called
    - Task/subagent prompts and results shown — these are major decision points
    - Edit diffs summarized — what changed matters for review
    - Noise filtered: TodoWrite, system-reminders, hook internals excluded
    - Tool results included for key tools (Task, Bash) — outcomes matter

    Args:
        transcript_path: Path to session transcript JSONL file

    Returns:
        Formatted markdown context suitable for critic agent consumption
    """
    path = Path(transcript_path)
    if not path.exists():
        return "(No transcript path available)"

    processor = SessionProcessor()
    _, entries, _ = processor.parse_session_file(
        path, load_agents=False, load_hooks=False
    )

    if not entries:
        return "(Empty session)"

    turns = processor.group_entries_into_turns(entries, full_mode=True)
    if not turns:
        return "(No conversation turns found)"

    lines: list[str] = []
    turn_num = 0

    # Noise tools the critic doesn't need to see individually
    _SKIP_TOOLS = {"TodoWrite", "Skill"}
    # Max chars for agent reasoning text per turn
    _AGENT_TEXT_LIMIT = 2000
    # Max chars for tool arguments
    _TOOL_ARG_LIMIT = 300
    # Max chars for tool results
    _TOOL_RESULT_LIMIT = 1000

    for turn in turns:
        # Skip non-conversation turns (hooks, summaries)
        turn_type = turn.get("type") if isinstance(turn, dict) else None
        if turn_type in ("hook_context", "summary"):
            continue

        user_msg = turn.get("user_message") if isinstance(turn, dict) else turn.user_message
        is_meta = turn.get("is_meta") if isinstance(turn, dict) else turn.is_meta
        assistant_sequence = (
            turn.get("assistant_sequence") if isinstance(turn, dict) else turn.assistant_sequence
        )

        # Skip meta-only turns (system injections without user content)
        if is_meta and not assistant_sequence:
            continue

        turn_num += 1

        # --- User message ---
        if user_msg and not is_meta:
            msg = user_msg.strip()
            # Clean command XML markup
            msg = _clean_prompt_text(msg)
            # Filter out system-injected context
            if not _is_system_injected_context(msg):
                # Generous truncation — user intent matters
                if len(msg) > 1000:
                    msg = msg[:1000] + "..."
                lines.append(f"### Turn {turn_num}")
                lines.append(f"**User**: {msg}")
                lines.append("")

        # --- Assistant sequence ---
        if not assistant_sequence:
            continue

        # Collect agent text blocks (reasoning/communication)
        text_parts: list[str] = []
        tool_entries: list[str] = []

        for item in assistant_sequence:
            item_type = item.get("type")

            if item_type == "text":
                content = item.get("content", "").strip()
                if content:
                    text_parts.append(content)

            elif item_type == "tool":
                tool_name = item.get("tool_name", "")
                tool_input = item.get("tool_input", {})

                if tool_name in _SKIP_TOOLS:
                    continue

                # Format tool call with meaningful detail
                if tool_name == "Task":
                    # Subagent calls are major decision points — show full prompt
                    desc = tool_input.get("description", "")
                    subagent = tool_input.get("subagent_type", "")
                    prompt = tool_input.get("prompt", "")
                    if len(prompt) > _TOOL_ARG_LIMIT:
                        prompt = prompt[:_TOOL_ARG_LIMIT] + "..."
                    tool_line = f"  - **Task**({subagent}): {desc}"
                    if prompt:
                        tool_line += f"\n    > {prompt}"
                    # Show result if available
                    result = item.get("result", "")
                    if result:
                        result_str = str(result)
                        if len(result_str) > _TOOL_RESULT_LIMIT:
                            result_str = result_str[:_TOOL_RESULT_LIMIT] + "..."
                        tool_line += f"\n    Result: {result_str}"

                elif tool_name in ("Edit", "Write"):
                    file_path = tool_input.get("file_path", "")
                    if tool_name == "Edit":
                        old = tool_input.get("old_string", "")
                        new = tool_input.get("new_string", "")
                        if len(old) > 200:
                            old = old[:200] + "..."
                        if len(new) > 200:
                            new = new[:200] + "..."
                        tool_line = f"  - **Edit** `{file_path}`"
                        if old or new:
                            tool_line += f"\n    `{old}` → `{new}`"
                    else:
                        tool_line = f"  - **Write** `{file_path}`"

                elif tool_name == "Read":
                    file_path = tool_input.get("file_path", "")
                    tool_line = f"  - **Read** `{file_path}`"

                elif tool_name == "Bash":
                    cmd = tool_input.get("command", "")
                    desc = tool_input.get("description", "")
                    if len(cmd) > _TOOL_ARG_LIMIT:
                        cmd = cmd[:_TOOL_ARG_LIMIT] + "..."
                    tool_line = f"  - **Bash**: `{cmd}`"
                    if desc:
                        tool_line += f" ({desc})"
                    # Show result/errors for bash
                    result = item.get("result", "")
                    if result:
                        result_str = str(result)
                        if len(result_str) > _TOOL_RESULT_LIMIT:
                            result_str = result_str[:_TOOL_RESULT_LIMIT] + "..."
                        tool_line += f"\n    Output: {result_str}"
                    if item.get("is_error"):
                        error = item.get("error", "")
                        if error:
                            tool_line += f"\n    ERROR: {error[:500]}"

                elif tool_name in ("Grep", "Glob"):
                    pattern = tool_input.get("pattern", "")
                    search_path = tool_input.get("path", "")
                    tool_line = f"  - **{tool_name}**(`{pattern}`"
                    if search_path:
                        tool_line += f", path={search_path}"
                    tool_line += ")"

                elif tool_name == "AskUserQuestion":
                    questions = tool_input.get("questions", [])
                    if questions:
                        q_text = questions[0].get("question", "") if questions else ""
                        tool_line = f"  - **AskUserQuestion**: {q_text}"
                    else:
                        tool_line = "  - **AskUserQuestion**"

                else:
                    # Generic tool — show name and key args
                    arg_parts = []
                    for k, v in list(tool_input.items())[:4]:
                        v_str = str(v)
                        if len(v_str) > 80:
                            v_str = v_str[:80] + "..."
                        arg_parts.append(f"{k}={v_str}")
                    args_str = ", ".join(arg_parts)
                    tool_line = f"  - **{tool_name}**({args_str})"

                tool_entries.append(tool_line)

        # Emit agent reasoning (joined, with generous limit)
        if text_parts:
            full_text = "\n".join(text_parts)
            if len(full_text) > _AGENT_TEXT_LIMIT:
                full_text = full_text[:_AGENT_TEXT_LIMIT] + "..."
            lines.append(f"**Agent**: {full_text}")
            lines.append("")

        # Emit tool calls
        if tool_entries:
            lines.append("Tools:")
            lines.extend(tool_entries)
            lines.append("")

    if not lines:
        return "(No meaningful session content extracted)"

    return "\n".join(lines)


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
        result["prompts"] = _extract_and_expand_prompts(turns, max_turns)

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
        # Linear pass chronological
        chronological_lines = []
        for turn in turns:
            user_msg = turn.get("user_message") if isinstance(turn, dict) else turn.user_message
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
            user_msg = turn.get("user_message") if isinstance(turn, dict) else turn.user_message
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
                                display_args = display_args[len(tool_name) :].strip().strip("()")

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

        message = entry.message if hasattr(entry, "message") else entry.get("message", {})
        content = message.get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                if block.get("name") == "Skill":
                    return block.get("input", {}).get("skill")

    return None


def load_skill_scope(skill_name: str) -> str | None:
    """Load a skill/command's authorized scope from its definition file.

    Searches for skill definitions in standard locations and extracts
    the workflow section to provide context for compliance checking.

    Args:
        skill_name: Name of the skill (e.g., "learn", "daily", "task-viz")

    Returns:
        Brief description of what the skill authorizes, or None if not found.
    """

    aops_root = Path(__file__).parent.parent.parent

    # Search locations for skill/command definitions
    search_paths = [
        aops_root / "aops-core" / "commands" / f"{skill_name}.md",
        aops_root / "aops-core" / f"skills/{skill_name}/SKILL.md",
        aops_root / "aops-tools" / f"skills/{skill_name}/SKILL.md",
    ]

    for path in search_paths:
        if path.exists():
            return _extract_skill_scope_from_file(path)

    return None


def _extract_skill_scope_from_file(path: Path) -> str | None:
    """Extract authorized scope summary from a skill/command definition file.

    Looks for:
    1. Frontmatter 'description' field
    2. First ## Workflow section (first 500 chars)

    Returns a brief summary suitable for custodiet context.
    """
    try:
        content = path.read_text()
    except OSError:
        return None

    lines: list[str] = []

    # Extract description from YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            for line in frontmatter.split("\n"):
                if line.startswith("description:"):
                    desc = line[len("description:") :].strip().strip("\"'")
                    lines.append(f"**Purpose**: {desc}")
                    break

    # Look for ## Workflow section and extract first few steps
    workflow_match = re.search(
        r"## Workflow\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL | re.IGNORECASE
    )
    if workflow_match:
        workflow_text = workflow_match.group(1).strip()
        # Extract numbered steps or subsections
        steps = re.findall(r"### \d+\.\s*([^\n]+)", workflow_text)
        if steps:
            lines.append("**Workflow steps**: " + ", ".join(steps[:6]))
        elif len(workflow_text) > 0:
            # Fallback: first 300 chars of workflow
            summary = workflow_text[:300].replace("\n", " ")
            if len(workflow_text) > 300:
                summary += "..."
            lines.append(f"**Workflow**: {summary}")

    if not lines:
        return None

    return "\n".join(lines)


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
        message = entry.message if hasattr(entry, "message") else entry.get("message", {})
        content = message.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_id = block.get("id", "")
                if tool_id:
                    tool_input = block.get("input", {})
                    # Extract key input for context
                    input_summary = _summarize_tool_input(block.get("name", ""), tool_input)
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

        message = entry.message if hasattr(entry, "message") else entry.get("message", {})
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

        message = entry.message if hasattr(entry, "message") else entry.get("message", {})
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
    include_antigravity: bool = True,
) -> list[SessionInfo]:
    """
    Find all Claude Code, Gemini, and optionally Antigravity sessions.

    Args:
        project: Filter to specific project (partial match)
        since: Only sessions modified after this time
        claude_projects_dir: Override default ~/.claude/projects/
        include_gemini: Whether to include sessions from ~/.gemini/tmp/
        include_antigravity: Whether to include sessions from ~/.gemini/antigravity/brain/

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

            # Skip hook log directories (e.g., -home-nic-writing-aops-hooks)
            if project_dir.name.endswith("-hooks"):
                continue

            project_name = project_dir.name

            # Filter by project if specified
            if project and project.lower() not in project_name.lower():
                continue

            # Find session files (exclude agent-* and *-hooks.jsonl files)
            for session_file in project_dir.glob("*.jsonl"):
                if session_file.name.startswith("agent-"):
                    continue
                if session_file.name.endswith("-hooks.jsonl"):
                    continue

                # Determine session_id
                session_id = session_file.stem

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

    # 3. Find Antigravity brain sessions
    if include_antigravity:
        antigravity_brain_dir = Path.home() / ".gemini" / "antigravity" / "brain"
        if antigravity_brain_dir.exists():
            # Antigravity structure: ~/.gemini/antigravity/brain/{uuid}/
            # Contains: task.md, implementation_plan.md, walkthrough.md
            for brain_dir in antigravity_brain_dir.iterdir():
                if not brain_dir.is_dir():
                    continue

                # Check if directory has any .md files (non-empty brain)
                md_files = list(brain_dir.glob("*.md"))
                if not md_files:
                    continue

                # Session ID is the directory name (UUID)
                session_id = brain_dir.name
                if len(session_id) > 8:
                    session_id = session_id[:8]

                # Project name from Antigravity
                project_name = "antigravity"

                # Filter by project if specified
                if project and project.lower() not in project_name.lower():
                    continue

                # Get modification time from most recently modified .md file
                mtime = max(datetime.fromtimestamp(f.stat().st_mtime, tz=UTC) for f in md_files)

                # Filter by time if specified
                if since and mtime < since:
                    continue

                sessions.append(
                    SessionInfo(
                        path=brain_dir,  # Path to brain directory
                        project=project_name,
                        session_id=session_id,
                        last_modified=mtime,
                        source="antigravity",
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

    # 2. Check for Mining JSON (unified session file)
    insights_dir = aca_data / "sessions" / "summaries"
    has_mining = False

    if insights_dir.exists():
        # Support various formats (with/without slug, project, hour)
        # Match anything containing the session_prefix and ending in .json
        pattern = str(insights_dir / f"*{session_prefix}*.json")
        import glob as glob_module

        matches = glob_module.glob(pattern)
        has_mining = bool(matches)

    if not has_mining:
        return SessionState.PENDING_MINING

    return SessionState.PROCESSED
