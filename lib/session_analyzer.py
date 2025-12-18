"""
Session Analyzer - Extract and structure session data for LLM analysis.

This module provides data extraction only - no LLM calls.
The session-analyzer skill uses this to prepare context for Claude's semantic analysis.

Uses lib/session_reader.py for JSONL parsing.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from lib.session_reader import (
    ConversationTurn,
    SessionProcessor,
    find_sessions,
)


@dataclass
class PromptInfo:
    """Information about a single user prompt."""

    text: str
    timestamp: datetime | None
    turn_number: int
    tools_triggered: list[str]
    tool_count: int


@dataclass
class SessionOutcomes:
    """Concrete outcomes from a session."""

    files_edited: list[str]
    files_created: list[str]
    bmem_notes: list[dict[str, str]]  # [{title, folder}]
    todos_final: list[dict[str, Any]] | None
    git_commits: list[str]
    duration_minutes: float | None


@dataclass
class SessionData:
    """Complete extracted session data for analysis."""

    session_id: str
    project: str
    prompts: list[PromptInfo]
    outcomes: SessionOutcomes
    start_time: datetime | None
    end_time: datetime | None
    turn_count: int


class SessionAnalyzer:
    """Extract and structure session data for LLM analysis."""

    def __init__(self, processor: SessionProcessor | None = None):
        self.processor = processor or SessionProcessor()

    def find_session(
        self,
        session_id: str | None = None,
        project: str | None = None,
    ) -> Path | None:
        """
        Find a session file.

        Args:
            session_id: Specific session ID (partial match OK)
            project: Filter by project name

        Returns:
            Path to session JSONL or None if not found
        """
        sessions = find_sessions(project=project)

        if not sessions:
            return None

        if session_id:
            # Find by ID (partial match)
            for s in sessions:
                if session_id in s.session_id:
                    return s.path
            return None

        # Return most recent
        return sessions[0].path

    def extract_session_data(self, session_path: Path) -> SessionData:
        """
        Extract all relevant data from a session.

        Args:
            session_path: Path to session JSONL file

        Returns:
            SessionData with prompts, outcomes, and metadata
        """
        summary, entries, agent_entries = self.processor.parse_jsonl(session_path)
        turns = self.processor.group_entries_into_turns(entries, agent_entries)

        # Extract prompts
        prompts = self._extract_prompts(turns)

        # Extract outcomes
        outcomes = self._extract_outcomes(session_path, turns)

        # Calculate timing
        start_time = None
        end_time = None
        for turn in turns:
            if isinstance(turn, ConversationTurn):
                if turn.start_time and not start_time:
                    start_time = turn.start_time
                if turn.end_time:
                    end_time = turn.end_time

        # Get project name from path
        project = session_path.parent.name
        if project.startswith("-"):
            # Convert "-home-nic-src-aOps" to "aOps"
            parts = project.split("-")
            project = parts[-1] if parts else project

        return SessionData(
            session_id=session_path.stem,
            project=project,
            prompts=prompts,
            outcomes=outcomes,
            start_time=start_time,
            end_time=end_time,
            turn_count=len([t for t in turns if isinstance(t, ConversationTurn)]),
        )

    def _extract_prompts(self, turns: list) -> list[PromptInfo]:
        """Extract user prompts with context."""
        prompts = []
        turn_number = 0

        for turn in turns:
            if not isinstance(turn, ConversationTurn):
                continue
            if not turn.user_message:
                continue

            turn_number += 1

            # Skip pseudo-commands and hook expansions
            text = turn.user_message.strip()
            if text.startswith("<") or "Expanded:" in text:
                continue
            if len(text) < 5:
                continue

            # Extract tools triggered in this turn
            tools = []
            for item in turn.assistant_sequence:
                if item.get("type") == "tool":
                    tool_name = item.get("tool_name", "")
                    if tool_name and tool_name not in tools:
                        tools.append(tool_name)

            prompts.append(
                PromptInfo(
                    text=text,
                    timestamp=turn.start_time,
                    turn_number=turn_number,
                    tools_triggered=tools,
                    tool_count=len(turn.assistant_sequence),
                )
            )

        return prompts

    def _extract_outcomes(self, session_path: Path, turns: list) -> SessionOutcomes:
        """Extract concrete outcomes from a session."""
        files_edited: list[str] = []
        files_created: list[str] = []
        bmem_notes: list[dict[str, str]] = []
        todos_final: list[dict[str, Any]] | None = None
        git_commits: list[str] = []

        for turn in turns:
            if not isinstance(turn, ConversationTurn):
                continue

            for item in turn.assistant_sequence:
                if item.get("type") != "tool":
                    continue

                tool_name = item.get("tool_name", "")
                tool_input = item.get("tool_input", {})

                # Track file edits
                if tool_name == "Edit":
                    file_path = tool_input.get("file_path", "")
                    if file_path and file_path not in files_edited:
                        files_edited.append(file_path)

                # Track file creates
                elif tool_name == "Write":
                    file_path = tool_input.get("file_path", "")
                    if file_path and file_path not in files_created:
                        files_created.append(file_path)

                # Track bmem notes
                elif tool_name == "mcp__bmem__write_note":
                    title = tool_input.get("title", "")
                    folder = tool_input.get("folder", "")
                    if title:
                        bmem_notes.append({"title": title, "folder": folder})

                # Track TodoWrite (keep latest)
                elif tool_name == "TodoWrite":
                    todos = tool_input.get("todos", [])
                    if todos:
                        todos_final = todos

                # Track git commits
                elif tool_name == "Bash":
                    cmd = tool_input.get("command", "")
                    if "git commit" in cmd:
                        # Extract commit message if possible
                        result = item.get("result", "")
                        if result:
                            # Look for commit hash in output
                            for line in result.split("\n"):
                                if line.strip().startswith("["):
                                    git_commits.append(line.strip()[:80])
                                    break

        # Calculate duration
        duration = None
        start_time = None
        end_time = None
        for turn in turns:
            if isinstance(turn, ConversationTurn):
                if turn.start_time and not start_time:
                    start_time = turn.start_time
                if turn.end_time:
                    end_time = turn.end_time
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds() / 60

        return SessionOutcomes(
            files_edited=files_edited,
            files_created=files_created,
            bmem_notes=bmem_notes,
            todos_final=todos_final,
            git_commits=git_commits,
            duration_minutes=duration,
        )

    def read_daily_note(self, date_str: str | None = None) -> dict[str, Any] | None:
        """
        Read and parse a daily note file.

        Daily notes are stored at $ACA_DATA/sessions/{YYYYMMDD}-daily.md
        Format is markdown with YAML frontmatter and session summaries.

        Args:
            date_str: Date string in YYYYMMDD format. If None, uses today's date.

        Returns:
            Dict with keys:
                - date: Date of the daily note
                - title: Title from frontmatter
                - sessions: List of session dicts with:
                    - session_id: Short session ID
                    - project: Project name
                    - duration: Duration string (optional)
                    - accomplishments: List of accomplishment strings
                    - decisions: List of decision strings
                    - topics: Topics string
                    - blockers: Blockers string
            Returns None if file doesn't exist or ACA_DATA not set.

        Raises:
            ValueError: If ACA_DATA environment variable not set
        """
        # Get ACA_DATA directory (fail-fast)
        aca_data = os.environ.get("ACA_DATA")
        if not aca_data:
            raise ValueError("ACA_DATA environment variable not set")

        data_path = Path(aca_data)
        if not data_path.exists():
            return None

        # Use today's date if not specified
        if date_str is None:
            date_str = date.today().strftime("%Y%m%d")

        # Find the daily note file
        daily_note_path = data_path / "sessions" / f"{date_str}-daily.md"
        if not daily_note_path.exists():
            return None

        # Read file content
        content = daily_note_path.read_text()

        # Parse frontmatter
        frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        title = ""
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            title_match = re.search(r"^title:\s*(.+)$", frontmatter, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()

        # Extract sessions
        sessions = []
        # Match: ### Session: {id} ({project}, {duration})
        session_pattern = r"###\s+Session:\s+(\w+)\s+\(([^,]+)(?:,\s*([^)]+))?\)"
        session_matches = list(re.finditer(session_pattern, content))

        for i, match in enumerate(session_matches):
            session_id = match.group(1)
            project = match.group(2).strip()
            duration = match.group(3).strip() if match.group(3) else None

            # Extract content between this session and the next
            start_pos = match.end()
            end_pos = session_matches[i + 1].start() if i + 1 < len(session_matches) else len(content)
            section = content[start_pos:end_pos]

            # Parse accomplishments
            accomplishments = []
            acc_match = re.search(r"\*\*Accomplishments:\*\*\n((?:- .+\n?)+)", section)
            if acc_match:
                acc_lines = acc_match.group(1).strip().split("\n")
                accomplishments = [line.strip("- ").strip() for line in acc_lines if line.strip().startswith("-")]

            # Parse decisions
            decisions = []
            dec_match = re.search(r"\*\*Decisions:\*\*\n((?:- .+\n?)+)", section)
            if dec_match:
                dec_lines = dec_match.group(1).strip().split("\n")
                decisions = [line.strip("- ").strip() for line in dec_lines if line.strip().startswith("-")]

            # Parse topics
            topics = ""
            topics_match = re.search(r"\*\*Topics:\*\*\s+(.+?)(?:\n\n|\*\*|$)", section, re.DOTALL)
            if topics_match:
                topics = topics_match.group(1).strip()

            # Parse blockers
            blockers = ""
            blockers_match = re.search(r"\*\*Blockers:\*\*\s+(.+?)(?:\n\n|---|$)", section, re.DOTALL)
            if blockers_match:
                blockers = blockers_match.group(1).strip()

            session_dict = {
                "session_id": session_id,
                "project": project,
                "accomplishments": accomplishments,
                "decisions": decisions,
                "topics": topics,
                "blockers": blockers,
            }
            if duration:
                session_dict["duration"] = duration

            sessions.append(session_dict)

        return {
            "date": date_str,
            "title": title,
            "sessions": sessions,
        }

    def extract_dashboard_state(self, session_path: Path) -> dict[str, Any]:
        """
        Extract dashboard state from a session file.

        Args:
            session_path: Path to session JSONL file

        Returns:
            Dict with keys:
                - first_prompt: Truncated first user message (200 chars)
                - first_prompt_full: Complete first user message
                - last_prompt: Most recent user message
                - todos: Current TODO list state (or None)
                - bmem_notes: List of created knowledge base notes
                - in_progress_count: Count of in-progress todos
        """
        summary, entries, agent_entries = self.processor.parse_jsonl(session_path)
        turns = self.processor.group_entries_into_turns(entries, agent_entries)

        # Extract prompts and outcomes
        prompts = self._extract_prompts(turns)
        outcomes = self._extract_outcomes(session_path, turns)

        # Get first and last prompts
        first_prompt_full = prompts[0].text if prompts else ""
        first_prompt = first_prompt_full[:200]
        if len(first_prompt_full) > 200:
            first_prompt += "..."

        last_prompt = prompts[-1].text if prompts else ""

        # Count in-progress todos
        in_progress_count = 0
        if outcomes.todos_final:
            in_progress_count = sum(
                1 for t in outcomes.todos_final if t.get("status") == "in_progress"
            )

        return {
            "first_prompt": first_prompt,
            "first_prompt_full": first_prompt_full,
            "last_prompt": last_prompt,
            "todos": outcomes.todos_final,
            "bmem_notes": outcomes.bmem_notes,
            "in_progress_count": in_progress_count,
        }

    def format_for_analysis(self, session_data: SessionData) -> str:
        """
        Format session data as context for LLM analysis.

        Returns markdown summary suitable for in-context analysis.
        """
        lines = []

        # Header
        lines.append(f"# Session: {session_data.session_id[:8]}")
        lines.append(f"**Project**: {session_data.project}")
        if session_data.start_time:
            lines.append(
                f"**Started**: {session_data.start_time.strftime('%Y-%m-%d %H:%M')}"
            )
        if session_data.outcomes.duration_minutes:
            lines.append(
                f"**Duration**: {session_data.outcomes.duration_minutes:.0f} minutes"
            )
        lines.append(f"**Turns**: {session_data.turn_count}")
        lines.append("")

        # User prompts
        lines.append("## User Prompts")
        lines.append("")
        for i, prompt in enumerate(session_data.prompts, 1):
            # Truncate long prompts for analysis context
            text = prompt.text[:500]
            if len(prompt.text) > 500:
                text += "..."

            timestamp = ""
            if prompt.timestamp:
                timestamp = f" ({prompt.timestamp.strftime('%H:%M')})"

            lines.append(f"{i}. {text}{timestamp}")

            if prompt.tools_triggered:
                tools_str = ", ".join(prompt.tools_triggered[:5])
                lines.append(f"   → Tools: {tools_str}")
            lines.append("")

        # Outcomes
        lines.append("## Outcomes")
        lines.append("")

        outcomes = session_data.outcomes

        if outcomes.files_edited:
            lines.append("**Files edited:**")
            for f in outcomes.files_edited[:10]:
                # Show just filename for brevity
                name = Path(f).name
                lines.append(f"- {name}")
            lines.append("")

        if outcomes.files_created:
            lines.append("**Files created:**")
            for f in outcomes.files_created[:10]:
                name = Path(f).name
                lines.append(f"- {name}")
            lines.append("")

        if outcomes.bmem_notes:
            lines.append("**Knowledge documented (bmem):**")
            for note in outcomes.bmem_notes:
                lines.append(f"- {note['title']} ({note['folder']})")
            lines.append("")

        if outcomes.git_commits:
            lines.append("**Git commits:**")
            for commit in outcomes.git_commits[:5]:
                lines.append(f"- {commit}")
            lines.append("")

        if outcomes.todos_final:
            completed = [t for t in outcomes.todos_final if t.get("status") == "completed"]
            in_progress = [t for t in outcomes.todos_final if t.get("status") == "in_progress"]

            if completed:
                lines.append("**Completed todos:**")
                for t in completed:
                    lines.append(f"- ✅ {t.get('content', '')}")
                lines.append("")

            if in_progress:
                lines.append("**Still in progress:**")
                for t in in_progress:
                    lines.append(f"- 🔄 {t.get('content', '')}")
                lines.append("")

        return "\n".join(lines)


def get_recent_sessions(
    project: str | None = None,
    hours: int = 24,
) -> list[SessionData]:
    """
    Get session data for recent sessions.

    Args:
        project: Filter by project name
        hours: How far back to look

    Returns:
        List of SessionData for matching sessions
    """
    since = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    if hours < 24:
        from datetime import timedelta

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

    sessions = find_sessions(project=project, since=since)
    analyzer = SessionAnalyzer()

    results = []
    for session_info in sessions[:10]:  # Limit to 10 most recent
        try:
            data = analyzer.extract_session_data(session_info.path)
            results.append(data)
        except Exception:
            continue

    return results
