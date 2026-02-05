"""Session Context Extraction for Dashboard Display.

Extracts conversation-centric context from Claude sessions to support the
overwhelm dashboard's session display. Answers the questions:

- "What terminal is this?" → Session identity from initial prompt
- "What was I trying to do?" → User intent, not agent state
- "What's the next step?" → Planned action when resuming

References:
- specs/overwhelm-dashboard.md (Session Context Model section)
- Task: aops-e9304452 (Session Context Extraction)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.session_reader import (
    _is_system_injected_context,
    parse_todowrite_state,
)
from lib.transcript_parser import SessionProcessor, TodoWriteState


@dataclass
class SessionContext:
    """Conversation-centric session context per overwhelm-dashboard.md spec.

    Attributes:
        session_id: Unique session identifier
        project: Project name (for grouping)
        initial_prompt: First user request (what they asked)
        follow_up_prompts: Subsequent user requests
        last_user_message: Most recent user prompt
        current_status: What agent is currently doing
        planned_next_step: Next planned action when resuming
        last_activity: Timestamp of last activity (UTC ISO)
        started: Session start timestamp (UTC ISO)
        todo_state: Current TodoWrite state if available
    """

    session_id: str
    project: str = ""
    initial_prompt: str = ""
    follow_up_prompts: list[str] = field(default_factory=list)
    last_user_message: str = ""
    current_status: str = ""
    planned_next_step: str = ""
    last_activity: str = ""
    started: str = ""
    todo_state: TodoWriteState | None = None

    def has_meaningful_context(self) -> bool:
        """Check if session has enough context to display meaningfully.

        Per spec: A session MUST have at least initial prompt OR current task status.
        Sessions showing "unknown: No specific task" provide zero value.
        """
        return bool(self.initial_prompt or self.current_status)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "session_id": self.session_id,
            "project": self.project,
            "initial_prompt": self.initial_prompt,
            "follow_up_prompts": self.follow_up_prompts,
            "last_user_message": self.last_user_message,
            "current_status": self.current_status,
            "planned_next_step": self.planned_next_step,
            "last_activity": self.last_activity,
            "started": self.started,
        }


def extract_session_context(
    transcript_path: Path,
    session_id: str = "",
    project: str = "",
    started: str = "",
    last_activity: str = "",
    max_follow_ups: int = 3,
) -> SessionContext:
    """Extract conversation-centric context from a session transcript.

    Args:
        transcript_path: Path to session JSONL file
        session_id: Session identifier (optional, for context)
        project: Project name (optional, for context)
        started: Session start timestamp (optional)
        last_activity: Last activity timestamp (optional)
        max_follow_ups: Maximum number of follow-up prompts to include

    Returns:
        SessionContext with extracted conversation data.
        Returns minimal context if transcript cannot be parsed.
    """
    context = SessionContext(
        session_id=session_id,
        project=project,
        started=started,
        last_activity=last_activity,
    )

    if not transcript_path.exists():
        return context

    try:
        return _extract_session_context_impl(
            transcript_path, context, max_follow_ups
        )
    except Exception:
        # Fail gracefully - return minimal context
        return context


def _extract_session_context_impl(
    transcript_path: Path,
    context: SessionContext,
    max_follow_ups: int,
) -> SessionContext:
    """Implementation of session context extraction."""
    processor = SessionProcessor()
    _, entries, _ = processor.parse_session_file(
        transcript_path, load_agents=False, load_hooks=False
    )

    if not entries:
        return context

    # Group into turns for consistent parsing
    turns = processor.group_entries_into_turns(entries, full_mode=True)

    # Extract all user prompts
    all_prompts = _extract_all_prompts(turns)

    if all_prompts:
        # Initial prompt is the first meaningful user message
        context.initial_prompt = all_prompts[0]

        # Follow-ups are subsequent prompts (limit to max_follow_ups)
        if len(all_prompts) > 1:
            context.follow_up_prompts = all_prompts[1 : max_follow_ups + 1]

        # Last user message is the most recent
        context.last_user_message = all_prompts[-1]

    # Extract TodoWrite state for current status
    todo_state = parse_todowrite_state(entries)
    context.todo_state = todo_state

    if todo_state:
        # Current status from in_progress task
        if todo_state.in_progress_task:
            context.current_status = todo_state.in_progress_task

        # Planned next step from first pending task
        pending_tasks = [
            t["content"] for t in todo_state.todos if t.get("status") == "pending"
        ]
        if pending_tasks:
            context.planned_next_step = pending_tasks[0]
        elif todo_state.in_progress_task:
            # If no pending, the current task IS the next step
            context.planned_next_step = f"Continue: {todo_state.in_progress_task}"

    # If no todo state, try to extract status from recent agent response
    if not context.current_status:
        context.current_status = _extract_status_from_response(turns)

    return context


def _extract_all_prompts(turns: list) -> list[str]:
    """Extract all meaningful user prompts from turns.

    Unlike _extract_and_expand_prompts which limits to N recent,
    this extracts ALL prompts for initial/follow-up/last categorization.
    """
    prompts = []
    for turn in turns:
        user_message = (
            turn.get("user_message") if isinstance(turn, dict) else turn.user_message
        )
        is_meta = turn.get("is_meta") if isinstance(turn, dict) else turn.is_meta

        if not user_message or is_meta:
            continue

        text = user_message.strip()

        if not text or _is_system_injected_context(text):
            continue

        # Clean command XML markup
        cleaned = _clean_prompt_for_display(text)
        if cleaned:
            prompts.append(cleaned)

    return prompts


def _clean_prompt_for_display(text: str) -> str:
    """Clean prompt text for display, extracting meaningful content.

    Handles:
    - XML command wrappers (<command-args>...</command-args>)
    - Skill invocations (/skill-name args)
    - Regular prompts
    """
    # Case 1: XML-wrapped command - extract args
    args_match = re.search(r"<command-args>(.*?)</command-args>", text, re.DOTALL)
    if args_match:
        args = args_match.group(1).strip()
        # Also check for command name to provide context
        name_match = re.search(r"<command-name>(.*?)</command-name>", text, re.DOTALL)
        if name_match and args:
            cmd = name_match.group(1).strip()
            return f"{cmd}: {args}"
        return args if args else ""

    # Case 2: Simple command prefix - preserve with args
    if text.startswith("/"):
        return text

    # Case 3: Regular prompt
    return text


def _extract_status_from_response(turns: list) -> str:
    """Extract current status from most recent agent response.

    Falls back to looking at what the agent said it was doing.
    """
    for turn in reversed(turns):
        assistant_sequence = (
            turn.get("assistant_sequence")
            if isinstance(turn, dict)
            else turn.assistant_sequence
        )
        if not assistant_sequence:
            continue

        # Get text responses
        texts = [
            item.get("content", "")
            for item in assistant_sequence
            if item.get("type") == "text"
        ]

        if texts:
            full_text = " ".join(texts)

            # Look for status indicators in agent response
            # Common patterns: "I'm now...", "Working on...", "Let me..."
            status_patterns = [
                r"(?:I'm now|I am now|Now I'm|Currently|Working on)\s+(.{20,100}?)[\.\n]",
                r"(?:Let me|I'll|I will)\s+(.{20,80}?)[\.\n]",
            ]

            for pattern in status_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

            # Fallback: use first sentence if short enough
            first_sentence = full_text.split(".")[0].strip()
            if 10 < len(first_sentence) < 120:
                return first_sentence

            break  # Only check most recent response

    return ""


def extract_context_from_session_state(
    state: dict[str, Any],
    transcript_path: Path | None = None,
) -> SessionContext:
    """Extract session context combining state file and transcript.

    Args:
        state: SessionState dict from session status file
        transcript_path: Optional path to transcript for full context

    Returns:
        SessionContext combining state metadata and transcript context
    """
    session_id = state.get("session_id", "")
    insights = state.get("insights") or {}
    main_agent = state.get("main_agent") or {}
    hydration = state.get("hydration") or {}

    # Get project from insights or state
    project = insights.get("project") or state.get("project") or ""

    # Get timestamps
    started = state.get("started_at") or ""
    last_activity = state.get("date") or ""

    # Create base context
    context = SessionContext(
        session_id=session_id,
        project=project,
        started=started,
        last_activity=last_activity,
    )

    # Extract from hydration if available (preferred source)
    if hydration:
        context.initial_prompt = hydration.get("original_prompt") or ""
        if hydration.get("hydrated_intent"):
            context.current_status = f"Intent: {hydration['hydrated_intent']}"

    # Get current task from main_agent
    current_task = main_agent.get("current_task")
    if current_task:
        context.planned_next_step = f"Working on task: {current_task}"

    # Get last prompt from main_agent
    last_prompt = main_agent.get("last_prompt")
    if last_prompt:
        context.last_user_message = last_prompt
        if not context.initial_prompt:
            context.initial_prompt = last_prompt

    # Enhance with transcript if available
    if transcript_path and transcript_path.exists():
        transcript_context = extract_session_context(
            transcript_path,
            session_id=session_id,
            project=project,
            started=started,
            last_activity=last_activity,
        )

        # Merge transcript data into context (transcript is more detailed)
        if transcript_context.initial_prompt and not context.initial_prompt:
            context.initial_prompt = transcript_context.initial_prompt
        if transcript_context.follow_up_prompts:
            context.follow_up_prompts = transcript_context.follow_up_prompts
        if transcript_context.last_user_message:
            context.last_user_message = transcript_context.last_user_message
        if transcript_context.current_status and not context.current_status:
            context.current_status = transcript_context.current_status
        if transcript_context.planned_next_step and not context.planned_next_step:
            context.planned_next_step = transcript_context.planned_next_step
        if transcript_context.todo_state:
            context.todo_state = transcript_context.todo_state

    return context
