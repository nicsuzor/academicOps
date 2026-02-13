"""
Session Labor Extraction - Extract detailed work units from session transcripts.

This module extracts granular work units from session data, capturing:
- What was delegated to each subagent (delegation_prompt)
- What each subagent produced (output)
- What the main agent did between delegations
- Chronological flow with line numbers for ordering

The output enables reviewers to understand session flow and work distribution.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from lib.transcript_parser import Entry, SessionProcessor


@dataclass
class WorkUnit:
    """Represents a single unit of work (action, delegation, or subagent output)."""

    line_number: int
    timestamp: datetime | None
    unit_type: (
        str  # "delegation", "subagent_output", "main_agent_work", "skill_invocation", "tool_call"
    )
    actor: str  # "main_agent", "subagent:{id}", "skill:{name}", "tool:{name}"
    description: str
    delegation_prompt: str | None = None  # For delegations: the prompt parameter from Task()
    output: str | None = None  # For subagent_output: the section content
    tool_name: str | None = None  # For tool_calls: the specific tool name
    tool_params: dict[str, Any] | None = (
        None  # For tool_calls: extracted parameters (at least file_path if present)
    )
    skills_invoked: list[str] = field(default_factory=list)  # Skills triggered in this unit
    commands_invoked: list[str] = field(default_factory=list)  # Slash commands (/skill, etc)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Convert datetime to ISO string
        if result["timestamp"]:
            result["timestamp"] = result["timestamp"].isoformat()
        return result


@dataclass
class SessionLaborData:
    """Complete extracted labor data from a session."""

    session_id: str
    project: str
    timestamp: str | None  # ISO 8601 timestamp
    work_units: list[WorkUnit] = field(default_factory=list)
    subagent_ids: list[str] = field(default_factory=list)
    total_delegations: int = 0
    total_main_agent_units: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "project": self.project,
            "timestamp": self.timestamp,
            "work_units": [unit.to_dict() for unit in self.work_units],
            "subagent_ids": self.subagent_ids,
            "total_delegations": self.total_delegations,
            "total_main_agent_units": self.total_main_agent_units,
        }


class LaborExtractor:
    """Extract detailed work units from session data."""

    def __init__(self, processor: SessionProcessor | None = None):
        self.processor = processor or SessionProcessor()
        self.line_counter = 0

    def extract_session_labor(
        self,
        session_path: Path | str,
        session_id: str | None = None,
        project: str | None = None,
    ) -> SessionLaborData:
        """
        Extract labor units from a session file.

        Args:
            session_path: Path to session JSONL file
            session_id: Optional session ID (8 chars)
            project: Optional project name

        Returns:
            SessionLaborData with extracted work units
        """
        session_path = Path(session_path)

        # Parse the session
        session_summary, entries, agent_entries = self.processor.parse_session_file(
            str(session_path)
        )

        # Extract metadata
        if not session_id:
            session_id = session_path.stem[:8]
        if not project:
            # Infer from parent directory
            project = (
                session_path.parent.name.split("-")[-1] if session_path.parent.name else "unknown"
            )

        # Get timestamp from first entry
        timestamp = None
        for entry in entries:
            if entry.timestamp:
                timestamp = entry.timestamp.isoformat()
                break

        # Create labor data container
        labor_data = SessionLaborData(
            session_id=session_id,
            project=project,
            timestamp=timestamp,
        )

        # Extract work units from entries
        self.line_counter = 0
        subagent_ids = set()

        # Process entries chronologically
        for entry in entries:
            self._process_entry(entry, labor_data, subagent_ids)

        # Process agent/subagent entries
        if agent_entries:
            for agent_id, agent_entry_list in agent_entries.items():
                subagent_ids.add(agent_id)
                for entry in agent_entry_list:
                    self._process_entry(entry, labor_data, subagent_ids, agent_id=agent_id)

        # Set metadata
        labor_data.subagent_ids = sorted(list(subagent_ids))
        labor_data.total_delegations = sum(
            1 for unit in labor_data.work_units if unit.unit_type == "delegation"
        )
        labor_data.total_main_agent_units = sum(
            1 for unit in labor_data.work_units if unit.unit_type == "main_agent_work"
        )

        # Sort work units by line number for chronological ordering
        labor_data.work_units.sort(key=lambda u: u.line_number)

        return labor_data

    def _process_entry(
        self,
        entry: Entry,
        labor_data: SessionLaborData,
        subagent_ids: set,
        agent_id: str | None = None,
    ) -> None:
        """Process a single entry and extract work units."""
        self.line_counter += 1

        # Skip system messages and non-meaningful entries
        if entry.type in ("system", "system_reminder", "meta"):
            return

        # Extract user prompts (potential delegations)
        if entry.type == "user":
            self._process_user_entry(entry, labor_data, subagent_ids)

        # Extract assistant work and tool calls
        elif entry.type == "assistant":
            self._process_assistant_entry(entry, labor_data, agent_id)

    def _process_user_entry(
        self,
        entry: Entry,
        labor_data: SessionLaborData,
        subagent_ids: set,
    ) -> None:
        """Extract work units from user entries (delegations/prompts)."""
        text = self._extract_text_from_entry(entry)
        if not text:
            return

        # Check if this looks like a Task() delegation with a prompt parameter
        delegation_prompt = self._extract_task_prompt(text)

        # Create work unit for user prompt/delegation
        actor = "main_agent"  # User is prompting the main agent
        unit_type = "delegation" if delegation_prompt else "main_agent_work"

        unit = WorkUnit(
            line_number=self.line_counter,
            timestamp=entry.timestamp,
            unit_type=unit_type,
            actor=actor,
            description=text[:200] + ("..." if len(text) > 200 else ""),
            delegation_prompt=delegation_prompt,
        )

        # Extract any skill invocations from the prompt
        unit.skills_invoked = self._extract_skill_invocations(text)
        unit.commands_invoked = self._extract_commands_invoked(text)

        labor_data.work_units.append(unit)

    def _process_assistant_entry(
        self,
        entry: Entry,
        labor_data: SessionLaborData,
        agent_id: str | None = None,
    ) -> None:
        """Extract work units from assistant entries."""
        text = self._extract_text_from_entry(entry)

        # Determine actor
        if agent_id:
            actor = f"subagent:{agent_id}"
        else:
            actor = "main_agent"

        # Extract tool calls from the message
        tool_calls = self._extract_tool_calls(entry)
        has_tool_work = bool(tool_calls)

        if tool_calls:
            # Create work unit for each tool call
            for (
                tool_name,
                tool_params,
                tool_description,
                is_delegation,
                delegation_prompt,
            ) in tool_calls:
                if is_delegation:
                    # Create delegation work unit with prompt captured
                    unit = WorkUnit(
                        line_number=self.line_counter,
                        timestamp=entry.timestamp,
                        unit_type="delegation",
                        actor=actor,
                        description=tool_description,
                        delegation_prompt=delegation_prompt,
                        tool_name=tool_name,
                        tool_params=tool_params,
                    )
                else:
                    unit = WorkUnit(
                        line_number=self.line_counter,
                        timestamp=entry.timestamp,
                        unit_type="tool_call",
                        actor=actor,
                        description=tool_description,
                        tool_name=tool_name,
                        tool_params=tool_params,
                    )
                labor_data.work_units.append(unit)

        # Extract subagent output - capture what the subagent produced
        if agent_id and text:
            # For subagent entries, the text content IS the subagent output
            # First try to extract explicit section headers, fall back to full text
            subagent_output = self._extract_subagent_output(text) or text.strip()
            if subagent_output:
                # Summarize the output for the description
                first_line = subagent_output.split("\n")[0][:100]
                description = (
                    f"Subagent produced: {first_line}"
                    if first_line
                    else "Subagent execution result"
                )
                unit = WorkUnit(
                    line_number=self.line_counter,
                    timestamp=entry.timestamp,
                    unit_type="subagent_output",
                    actor=f"subagent:{agent_id}",
                    description=description,
                    output=subagent_output[:2000] + ("..." if len(subagent_output) > 2000 else ""),
                )
                labor_data.work_units.append(unit)

        # Extract skill invocations from assistant response
        skills = self._extract_skill_invocations(text) if text else []
        if skills:
            for skill in skills:
                unit = WorkUnit(
                    line_number=self.line_counter,
                    timestamp=entry.timestamp,
                    unit_type="skill_invocation",
                    actor=actor,
                    description=f"Invoked skill: {skill}",
                    skills_invoked=[skill],
                )
                labor_data.work_units.append(unit)

        # For main agent: capture text work when there's meaningful content
        # but no tool calls (reasoning, explanations, planning between actions)
        if not agent_id and text and not has_tool_work and not skills:
            # Only capture substantive text (skip short acknowledgments)
            stripped_text = text.strip()
            if len(stripped_text) > 50:
                first_line = stripped_text.split("\n")[0][:100]
                unit = WorkUnit(
                    line_number=self.line_counter,
                    timestamp=entry.timestamp,
                    unit_type="main_agent_work",
                    actor=actor,
                    description=f"Agent response: {first_line}{'...' if len(first_line) >= 100 else ''}",
                    output=stripped_text[:1000] + ("..." if len(stripped_text) > 1000 else ""),
                )
                labor_data.work_units.append(unit)

    def _extract_text_from_entry(self, entry: Entry) -> str:
        """Extract text content from an entry."""
        text = ""
        if entry.message:
            content = entry.message.get("content", "")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                # Handle content blocks
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text += block.get("text", "")
        elif entry.content:
            if isinstance(entry.content, dict):
                text = str(entry.content.get("content", ""))
            else:
                text = str(entry.content)
        return text

    def _extract_task_prompt(self, text: str) -> str | None:
        """
        Extract prompt parameter from Task() calls in text.

        Looks for patterns like:
            Task(prompt="...")
            Task(
              prompt="..."
            )
        """
        # Match Task() calls with prompt parameter
        # Pattern: Task(...prompt=([^,)]+)...) or Task(...prompt="..."...)
        patterns = [
            r'Task\s*\(\s*[^)]*prompt\s*=\s*["\']([^"\']+)["\']',  # prompt="..." or prompt='...'
            r"Task\s*\(\s*[^)]*prompt\s*=\s*([^,\)]+)",  # prompt=value (without quotes)
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_tool_calls(
        self, entry: Entry
    ) -> list[tuple[str, dict[str, Any], str, bool, str | None]]:
        """
        Extract tool calls from an entry.

        Returns:
            List of (tool_name, tool_params, description, is_delegation, delegation_prompt) tuples
        """
        tool_calls = []

        # Check tool_input from entry (hook-based)
        if entry.tool_input and entry.tool_name:
            tool_params = self._extract_tool_params(entry.tool_input)
            is_delegation = entry.tool_name == "Task"
            delegation_prompt = None

            if is_delegation:
                # Extract prompt and subagent_type for Task delegations
                delegation_prompt = entry.tool_input.get("prompt", "")
                subagent_type = entry.tool_input.get("subagent_type")
                if subagent_type is None:
                    subagent_type = "unspecified"
                task_desc = entry.tool_input.get("description", "")
                description = (
                    f"Delegated to {subagent_type}: {task_desc}"
                    if task_desc
                    else f"Delegated to {subagent_type}"
                )
                tool_params["prompt"] = delegation_prompt
                tool_params["subagent_type"] = subagent_type
            else:
                description = f"Called {entry.tool_name}"
                if "file_path" in tool_params:
                    description += f": {tool_params['file_path']}"

            tool_calls.append(
                (
                    entry.tool_name,
                    tool_params,
                    description,
                    is_delegation,
                    delegation_prompt,
                )
            )

        # Parse tool use blocks from message content
        if entry.message:
            content = entry.message.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type")
                        if block_type == "tool_use":
                            tool_name = block.get("name")
                            if tool_name is None:
                                continue  # Skip malformed tool_use blocks
                            tool_input = block.get("input", {})
                            tool_params = self._extract_tool_params(tool_input)
                            is_delegation = tool_name == "Task"
                            delegation_prompt = None

                            if is_delegation:
                                # Extract prompt and subagent_type for Task delegations
                                delegation_prompt = tool_input.get("prompt", "")
                                subagent_type = tool_input.get("subagent_type")
                                if subagent_type is None:
                                    subagent_type = "unspecified"
                                task_desc = tool_input.get("description", "")
                                description = (
                                    f"Delegated to {subagent_type}: {task_desc}"
                                    if task_desc
                                    else f"Delegated to {subagent_type}"
                                )
                                tool_params["prompt"] = delegation_prompt
                                tool_params["subagent_type"] = subagent_type
                            else:
                                description = f"Called {tool_name}"
                                if "file_path" in tool_params:
                                    description += f": {tool_params['file_path']}"
                                elif "path" in tool_params:
                                    description += f": {tool_params['path']}"

                            tool_calls.append(
                                (
                                    tool_name,
                                    tool_params,
                                    description,
                                    is_delegation,
                                    delegation_prompt,
                                )
                            )

        return tool_calls

    def _extract_tool_params(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Extract key parameters from tool input, especially file paths."""
        params = {}

        if not isinstance(tool_input, dict):
            return params

        # Always extract file_path if present
        if "file_path" in tool_input:
            params["file_path"] = tool_input["file_path"]

        # Also check for 'path' key
        if "path" in tool_input and "file_path" not in tool_input:
            params["path"] = tool_input["path"]

        # Extract other common parameters
        for key in ["command", "args", "pattern", "format"]:
            if key in tool_input:
                params[key] = tool_input[key]

        return params

    def _extract_subagent_output(self, text: str) -> str | None:
        """
        Extract subagent output section from assistant response.

        Looks for sections like:
            ## Subagent Output
            [content]

        Or marks like:
            Subagent Result:
            [content]
        """
        # Look for explicit subagent section headers
        patterns = [
            r"##\s*Subagent Output\s*\n(.*?)(?=\n##|\Z)",
            r"###\s*Subagent\s*\n(.*?)(?=\n##|\n###|\Z)",
            r"Subagent Result[:\s]+(.*?)(?=\n##|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_skill_invocations(self, text: str) -> list[str]:
        """Extract skill invocations like /skill_name or Skill(skill=...)."""
        skills = []

        # Match /skill_name patterns at start of line or after whitespace
        # Excludes file paths like /home/user or /src/main.py
        skill_calls = re.findall(
            r"(?:^|(?<=\s))/([a-z][a-z0-9]*(?:-[a-z0-9]+)*)", text, re.MULTILINE
        )
        skills.extend(skill_calls)

        # Match Skill(skill="...") patterns
        skill_patterns = re.findall(
            r'Skill\s*\(\s*skill\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE
        )
        skills.extend(skill_patterns)

        return list(set(skills))  # Deduplicate

    def _extract_commands_invoked(self, text: str) -> list[str]:
        """Extract slash commands like /pull, /commit, etc."""
        # Match /command patterns at start of line or after whitespace
        # Excludes file paths
        commands = re.findall(r"(?:^|(?<=\s))/([a-z][a-z0-9]*(?:-[a-z0-9]+)*)", text, re.MULTILINE)
        return list(set(commands))  # Deduplicate


def extract_labor_from_session(
    session_path: Path | str,
    session_id: str | None = None,
    project: str | None = None,
    output_format: str = "dict",
) -> SessionLaborData | dict:
    """
    Convenience function to extract labor from a session.

    Args:
        session_path: Path to session JSONL file
        session_id: Optional session ID
        project: Optional project name
        output_format: "dict" or "object" (default: "dict")

    Returns:
        SessionLaborData or dict depending on output_format
    """
    extractor = LaborExtractor()
    labor_data = extractor.extract_session_labor(session_path, session_id, project)

    if output_format == "dict":
        return labor_data.to_dict()
    return labor_data


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract_labor.py <session_file> [output_file]")
        sys.exit(1)

    session_file = Path(sys.argv[1])
    if not session_file.exists():
        print(f"Error: File not found: {session_file}")
        sys.exit(1)

    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    extractor = LaborExtractor()
    labor_data = extractor.extract_session_labor(session_file)

    # Output as JSON
    output_json = json.dumps(labor_data.to_dict(), indent=2)

    if output_file:
        output_file.write_text(output_json, encoding="utf-8")
        print(f"Labor data written to: {output_file}")
    else:
        print(output_json)
