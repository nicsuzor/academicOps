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

from lib.session_reader import find_sessions, parse_todowrite_state
from lib.transcript_parser import ConversationTurn, SessionProcessor, TodoWriteState


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
    memory_notes: list[dict[str, str]]  # [{title, folder}]
    todos_final: list[dict[str, Any]] | None
    todos_completed: list[str]  # Completed todo content strings
    git_commits: list[str]
    skills_invoked: list[str]  # Skills used in session
    commands_invoked: list[str]  # Slash commands used
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
        memory_notes: list[dict[str, str]] = []
        todos_final: list[dict[str, Any]] | None = None
        todos_completed: list[str] = []
        git_commits: list[str] = []
        skills_invoked: list[str] = []
        commands_invoked: list[str] = []

        # Track all todos across session to find completed ones
        all_todos_seen: dict[str, str] = {}  # content -> last status

        for turn in turns:
            if not isinstance(turn, ConversationTurn):
                continue

            # Track slash commands from user messages
            if turn.user_message:
                msg = turn.user_message.strip()
                if msg.startswith("/") and " " not in msg[:20]:
                    cmd = msg.split()[0] if msg.split() else msg
                    if cmd not in commands_invoked:
                        commands_invoked.append(cmd)

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

                # Track memory notes
                elif tool_name == "mcp__memory__store_memory":
                    title = tool_input.get("title", "")
                    folder = tool_input.get("folder", "")
                    if title:
                        memory_notes.append({"title": title, "folder": folder})

                # Track skill invocations
                elif tool_name == "Skill":
                    skill = tool_input.get("skill", "")
                    if skill and skill not in skills_invoked:
                        skills_invoked.append(skill)

                # Track TodoWrite - track all todos to find completed ones
                elif tool_name == "TodoWrite":
                    todos = tool_input.get("todos", [])
                    if todos:
                        todos_final = todos
                        for todo in todos:
                            content = todo.get("content", "")
                            status = todo.get("status", "")
                            if content:
                                all_todos_seen[content] = status

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

        # Extract completed todos
        for content, status in all_todos_seen.items():
            if status == "completed" and content not in todos_completed:
                todos_completed.append(content)

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
            memory_notes=memory_notes,
            todos_final=todos_final,
            todos_completed=todos_completed,
            git_commits=git_commits,
            skills_invoked=skills_invoked,
            commands_invoked=commands_invoked,
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
            end_pos = (
                session_matches[i + 1].start()
                if i + 1 < len(session_matches)
                else len(content)
            )
            section = content[start_pos:end_pos]

            # Parse accomplishments
            accomplishments = []
            acc_match = re.search(r"\*\*Accomplishments:\*\*\n((?:- .+\n?)+)", section)
            if acc_match:
                acc_lines = acc_match.group(1).strip().split("\n")
                accomplishments = [
                    line.strip("- ").strip()
                    for line in acc_lines
                    if line.strip().startswith("-")
                ]

            # Parse decisions
            decisions = []
            dec_match = re.search(r"\*\*Decisions:\*\*\n((?:- .+\n?)+)", section)
            if dec_match:
                dec_lines = dec_match.group(1).strip().split("\n")
                decisions = [
                    line.strip("- ").strip()
                    for line in dec_lines
                    if line.strip().startswith("-")
                ]

            # Parse topics
            topics = ""
            topics_match = re.search(
                r"\*\*Topics:\*\*\s+(.+?)(?:\n\n|\*\*|$)", section, re.DOTALL
            )
            if topics_match:
                topics = topics_match.group(1).strip()

            # Parse blockers
            blockers = ""
            blockers_match = re.search(
                r"\*\*Blockers:\*\*\s+(.+?)(?:\n\n|---|$)", section, re.DOTALL
            )
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

    def parse_daily_log(self, date_str: str | None = None) -> dict[str, Any] | None:
        """
        Parse daily log for dashboard display (new markdown format).

        Extracts:
        - Primary focus and first incomplete task
        - All blockers
        - Completed items and outcomes
        - Progress counts

        Args:
            date_str: Date string in YYYYMMDD format. If None, uses today's date.

        Returns:
            Dict with keys:
                - primary_title: Title of PRIMARY section (e.g., "TJA Paper")
                - primary_link: Wikilink if present (e.g., "[[projects/tja]]")
                - next_action: First incomplete task under PRIMARY
                - incomplete: List of all incomplete tasks
                - completed: List of all completed tasks
                - blockers: List of blocker items
                - outcomes: List of outcome items
                - progress: Tuple of (completed_count, total_count)
            Returns None if file doesn't exist.
        """
        aca_data = os.environ.get("ACA_DATA")
        if not aca_data:
            return None

        if date_str is None:
            date_str = date.today().strftime("%Y%m%d")

        daily_path = Path(aca_data) / "sessions" / f"{date_str}-daily.md"
        if not daily_path.exists():
            return None

        content = daily_path.read_text()

        result: dict[str, Any] = {
            "primary_title": None,
            "primary_link": None,
            "next_action": None,
            "incomplete": [],
            "completed": [],
            "blockers": [],
            "outcomes": [],
            "progress": (0, 0),
        }

        # Find PRIMARY section title and link
        primary_match = re.search(
            r"###\s+PRIMARY:\s*([^→\n]+?)(?:\s*→\s*(\[\[[^\]]+\]\]))?\s*\n", content
        )
        if primary_match:
            result["primary_title"] = primary_match.group(1).strip()
            result["primary_link"] = (
                primary_match.group(2) if primary_match.group(2) else None
            )

        # Find all incomplete tasks: - [ ]
        incomplete_pattern = re.compile(r"^-\s*\[ \]\s*(.+)$", re.MULTILINE)
        result["incomplete"] = [
            m.group(1).strip() for m in incomplete_pattern.finditer(content)
        ]

        # Find all completed tasks: - [x]
        completed_pattern = re.compile(
            r"^-\s*\[x\]\s*(.+)$", re.MULTILINE | re.IGNORECASE
        )
        result["completed"] = [
            m.group(1).strip() for m in completed_pattern.finditer(content)
        ]

        # Find blockers: lines containing [blocker]
        blocker_pattern = re.compile(
            r"^-\s*\[blocker\]\s*(.+)$", re.MULTILINE | re.IGNORECASE
        )
        result["blockers"] = [
            m.group(1).strip() for m in blocker_pattern.finditer(content)
        ]

        # Also check for **Blockers:** section items
        blockers_section = re.search(
            r"\*\*Blockers?:\*\*\n((?:-\s*\[[ x]?\]\s*.+\n?)+)", content
        )
        if blockers_section:
            for line in blockers_section.group(1).strip().split("\n"):
                line = line.strip()
                if line.startswith("- [ ]"):
                    item = line[5:].strip()
                    if item not in result["blockers"]:
                        result["blockers"].append(item)

        # Find outcomes: lines containing [outcome]
        outcome_pattern = re.compile(
            r"^-\s*\[outcome\]\s*(.+)$", re.MULTILINE | re.IGNORECASE
        )
        result["outcomes"] = [
            m.group(1).strip() for m in outcome_pattern.finditer(content)
        ]

        # First incomplete task under PRIMARY becomes next_action
        # Prefer tasks from "Today's subtasks:" section, fall back to any incomplete
        if primary_match:
            primary_start = primary_match.end()
            # Find next ### or ## or end
            next_section = re.search(r"\n##", content[primary_start:])
            primary_end = (
                primary_start + next_section.start() if next_section else len(content)
            )
            primary_section = content[primary_start:primary_end]

            # First look in Today's subtasks section
            subtasks_match = re.search(
                r"\*\*Today's subtasks:\*\*\n((?:-\s*\[[ x]?\].+\n?)+)", primary_section
            )
            if subtasks_match:
                subtasks_text = subtasks_match.group(1)
                first_subtask = re.search(
                    r"^-\s*\[ \]\s*(.+)$", subtasks_text, re.MULTILINE
                )
                if first_subtask:
                    result["next_action"] = first_subtask.group(1).strip()

            # Fall back to first incomplete in section if no subtask found
            if not result["next_action"]:
                first_incomplete = re.search(
                    r"^-\s*\[ \]\s*(.+)$", primary_section, re.MULTILINE
                )
                if first_incomplete:
                    result["next_action"] = first_incomplete.group(1).strip()

        # Calculate progress
        total = len(result["incomplete"]) + len(result["completed"])
        done = len(result["completed"])
        result["progress"] = (done, total)

        return result

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
                - memory_notes: List of created knowledge base notes
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
            "memory_notes": outcomes.memory_notes,
            "in_progress_count": in_progress_count,
        }

    def format_for_analysis(self, session_data: SessionData) -> str:
        """
        Format session data as context for LLM analysis.

        Returns markdown summary optimized for semantic analysis.
        Leads with ACCOMPLISHED WORK to guide the LLM toward accomplishment extraction.
        """
        lines = []
        outcomes = session_data.outcomes

        # Header
        lines.append(f"# Session: {session_data.session_id[:8]}")
        lines.append(f"**Project**: {session_data.project}")
        if session_data.start_time:
            lines.append(
                f"**Started**: {session_data.start_time.strftime('%Y-%m-%d %H:%M')}"
            )
        if outcomes.duration_minutes:
            lines.append(f"**Duration**: {outcomes.duration_minutes:.0f} minutes")
        lines.append(f"**Turns**: {session_data.turn_count}")
        lines.append("")

        # ACCOMPLISHMENTS FIRST - what was completed
        lines.append("## What Was Accomplished")
        lines.append("")

        has_accomplishments = False

        # Completed todos (explicit completions)
        if outcomes.todos_completed:
            has_accomplishments = True
            lines.append("**Completed tasks:**")
            for content in outcomes.todos_completed:
                lines.append(f"- ✅ {content}")
            lines.append("")

        # Git commits (concrete deliverables)
        if outcomes.git_commits:
            has_accomplishments = True
            lines.append("**Commits made:**")
            for commit in outcomes.git_commits[:5]:
                lines.append(f"- {commit}")
            lines.append("")

        # Knowledge documented
        if outcomes.memory_notes:
            has_accomplishments = True
            lines.append("**Knowledge documented:**")
            for note in outcomes.memory_notes:
                lines.append(f"- {note['title']} ({note['folder']})")
            lines.append("")

        # Files created (new work)
        if outcomes.files_created:
            has_accomplishments = True
            lines.append("**Files created:**")
            for f in outcomes.files_created[:10]:
                name = Path(f).name
                lines.append(f"- {name}")
            lines.append("")

        if not has_accomplishments:
            lines.append(
                "*No explicit completions recorded - analyze prompts for implicit accomplishments*"
            )
            lines.append("")

        # WORK IN PROGRESS - what's still pending
        if outcomes.todos_final:
            in_progress = [
                t for t in outcomes.todos_final if t.get("status") == "in_progress"
            ]
            pending = [t for t in outcomes.todos_final if t.get("status") == "pending"]
            if in_progress or pending:
                lines.append("## Still In Progress")
                lines.append("")
                for t in in_progress:
                    lines.append(f"- 🔄 {t.get('content', '')}")
                for t in pending:
                    lines.append(f"- ⏳ {t.get('content', '')}")
                lines.append("")

        # CONTEXT - skills and commands used
        if outcomes.skills_invoked or outcomes.commands_invoked:
            lines.append("## Context")
            lines.append("")
            if outcomes.skills_invoked:
                lines.append(f"**Skills used**: {', '.join(outcomes.skills_invoked)}")
            if outcomes.commands_invoked:
                lines.append(f"**Commands**: {', '.join(outcomes.commands_invoked)}")
            lines.append("")

        # FILES MODIFIED - what was touched
        if outcomes.files_edited:
            lines.append("## Files Modified")
            lines.append("")
            for f in outcomes.files_edited[:10]:
                name = Path(f).name
                lines.append(f"- {name}")
            lines.append("")

        # USER PROMPTS - the conversation arc
        lines.append("## User Prompts (Conversation Arc)")
        lines.append("")
        lines.append(
            "*Read these to understand what was requested and the flow of work:*"
        )
        lines.append("")
        for i, prompt in enumerate(session_data.prompts, 1):
            # Truncate long prompts for analysis context
            text = prompt.text[:400]
            if len(prompt.text) > 400:
                text += "..."

            timestamp = ""
            if prompt.timestamp:
                timestamp = f" ({prompt.timestamp.strftime('%H:%M')})"

            lines.append(f"{i}. {text}{timestamp}")
            lines.append("")

        # ANALYSIS GUIDANCE
        lines.append("---")
        lines.append("## Analysis Instructions")
        lines.append("")
        lines.append("Based on the above, extract:")
        lines.append(
            "1. **Accomplishments**: What concrete work was completed? (not just started)"
        )
        lines.append("2. **Decisions**: What choices or design decisions were made?")
        lines.append("3. **Topics**: What areas/systems were worked on?")
        lines.append("4. **Blockers**: What issues remain unresolved?")
        lines.append("5. **Next steps**: What should happen next?")
        lines.append("")

        return "\n".join(lines)


def progress_bar(completed: int, total: int, width: int = 20) -> str:
    """
    Generate ASCII progress bar.

    Args:
        completed: Number of completed items
        total: Total number of items
        width: Width of bar in characters (default 20)

    Returns:
        String like "████████░░░░░░░░░░░░ 6/29"
    """
    if total == 0:
        return "░" * width + " 0/0"
    filled = int(width * completed / total)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {completed}/{total}"


@dataclass
class SectionProgress:
    """Progress data for a single priority section."""

    heading: (
        str  # Full heading line (e.g., "## 🎯 PRIMARY: TJA Paper → [[projects/tja]]")
    )
    completed: int
    total: int
    start_pos: int  # Position in file where heading starts
    end_pos: int  # Position where next section starts


def parse_priority_sections(content: str) -> list[SectionProgress]:
    """
    Parse priority sections from daily note content.

    Finds all ## headings above ## Session Details that contain task lists.
    Returns progress data for each section.

    Args:
        content: Full daily note content

    Returns:
        List of SectionProgress for each priority section
    """
    sections: list[SectionProgress] = []

    # Find where Session Details starts (boundary of user zone)
    session_details_match = re.search(r"^## Session Details", content, re.MULTILINE)
    user_zone_end = (
        session_details_match.start() if session_details_match else len(content)
    )

    # Find all ## headings in user zone
    heading_pattern = re.compile(r"^(## .+)$", re.MULTILINE)
    headings = list(heading_pattern.finditer(content[:user_zone_end]))

    for i, match in enumerate(headings):
        heading = match.group(1)
        start_pos = match.start()

        # Section ends at next heading or user zone end
        if i + 1 < len(headings):
            end_pos = headings[i + 1].start()
        else:
            end_pos = user_zone_end

        section_content = content[start_pos:end_pos]

        # Count tasks in this section
        completed = len(
            re.findall(r"^-\s*\[x\]", section_content, re.MULTILINE | re.IGNORECASE)
        )
        incomplete = len(re.findall(r"^-\s*\[ \]", section_content, re.MULTILINE))
        total = completed + incomplete

        sections.append(
            SectionProgress(
                heading=heading,
                completed=completed,
                total=total,
                start_pos=start_pos,
                end_pos=end_pos,
            )
        )

    return sections


def update_daily_note_dashboard(date_str: str | None = None) -> bool:
    """
    Update progress bars in each priority section of a daily note.

    For each ## section above ## Session Details, inserts or updates
    a progress bar on the line immediately after the heading.

    Args:
        date_str: Date string in YYYYMMDD format. If None, uses today.

    Returns:
        True if successful, False if file doesn't exist.

    Safety: Never modifies content below ## Session Details.
            Only touches progress bar lines (identified by █░ characters).
    """
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        return False

    if date_str is None:
        date_str = date.today().strftime("%Y%m%d")

    daily_path = Path(aca_data) / "sessions" / f"{date_str}-daily.md"
    if not daily_path.exists():
        return False

    content = daily_path.read_text()

    # Parse sections to get progress data
    sections = parse_priority_sections(content)
    if not sections:
        return False

    # Process sections in reverse order (so positions remain valid)
    for section in reversed(sections):
        # Skip sections with no tasks (like FILLER which might just have bullets)
        if section.total == 0:
            continue

        # Find the end of the heading line
        heading_end = section.start_pos + len(section.heading)

        # Check if there's already a progress bar on the next line
        after_heading = content[heading_end:]
        existing_bar_match = re.match(r"\n([█░]+ \d+/\d+)\n", after_heading)

        new_bar = progress_bar(section.completed, section.total)

        if existing_bar_match:
            # Replace existing progress bar
            bar_start = heading_end + 1  # +1 for newline
            bar_end = bar_start + len(existing_bar_match.group(1))
            content = content[:bar_start] + new_bar + content[bar_end:]
        else:
            # Insert new progress bar after heading
            content = content[:heading_end] + "\n" + new_bar + content[heading_end:]

    daily_path.write_text(content)
    return True


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


def extract_todowrite_from_session(session_path: Path) -> TodoWriteState | None:
    """
    Extract TodoWrite state from a session JSONL file.

    Convenience function for dashboard to get current TodoWrite state
    without loading full session analysis.

    Args:
        session_path: Path to session JSONL file

    Returns:
        TodoWriteState with todos list, counts, and in_progress task.
        Returns None if session doesn't exist or has no TodoWrite.
    """
    import json

    if not session_path.exists():
        return None

    entries = []
    try:
        with open(session_path, encoding="utf-8") as f:
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

    return parse_todowrite_state(entries)
