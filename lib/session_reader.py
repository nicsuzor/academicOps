"""
Session Reader - Unified parser for Claude Code session files.

Reads and combines:
- Main session JSONL (*.jsonl)
- Agent transcripts (agent-*.jsonl)
- Hook logs (*-hooks.jsonl)

Used by:
- /transcript skill for markdown export
- Dashboard for live activity display
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class Entry:
    """Represents a single JSONL entry from any source."""
    type: str
    uuid: str = ""
    parent_uuid: str = ""
    message: dict = field(default_factory=dict)
    content: dict = field(default_factory=dict)
    is_sidechain: bool = False
    is_meta: bool = False
    tool_use_result: dict = field(default_factory=dict)
    hook_context: dict = field(default_factory=dict)
    subagent_id: str | None = None
    summary_text: str | None = None
    timestamp: datetime | None = None

    # Hook-specific fields
    additional_context: str | None = None
    hook_event_name: str | None = None
    hook_exit_code: int | None = None
    skills_matched: list[str] | None = None
    files_loaded: list[str] | None = None
    tool_name: str | None = None
    agent_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entry":
        """Create Entry from JSONL dict."""
        entry = cls(
            type=data.get('type', 'unknown'),
            uuid=data.get('uuid', ''),
            parent_uuid=data.get('parentUuid', ''),
            message=data.get('message', {}),
            content=data.get('content', {}),
            is_sidechain=data.get('isSidechain', False),
            is_meta=data.get('isMeta', False),
            tool_use_result=data.get('toolUseResult', {}),
            hook_context=data.get('hook_context', {}),
            subagent_id=data.get('subagentId'),
            summary_text=data.get('summary'),
        )

        # Extract hook data from system_reminder entries
        if entry.type == 'system_reminder':
            hook_output = data.get('hookSpecificOutput', {})
            if isinstance(hook_output, dict) and hook_output:
                entry.additional_context = hook_output.get('additionalContext', '')
                entry.hook_event_name = hook_output.get('hookEventName')
                entry.hook_exit_code = hook_output.get('exitCode')
                entry.skills_matched = hook_output.get('skillsMatched')
                entry.files_loaded = hook_output.get('filesLoaded')
                entry.tool_name = hook_output.get('toolName')
                entry.agent_id = hook_output.get('agentId')
            # Fall back to content.additionalContext
            if not entry.additional_context and isinstance(entry.content, dict):
                entry.additional_context = entry.content.get('additionalContext', '')
            if not entry.hook_event_name and isinstance(entry.content, dict):
                entry.hook_event_name = entry.content.get('hookEventName')
            if entry.hook_exit_code is None and isinstance(entry.content, dict):
                entry.hook_exit_code = entry.content.get('exitCode')

        # Parse timestamp
        if 'timestamp' in data:
            try:
                timestamp_str = data['timestamp']
                if timestamp_str.endswith('Z'):
                    timestamp_str = timestamp_str[:-1] + '+00:00'
                entry.timestamp = datetime.fromisoformat(timestamp_str)
            except (ValueError, TypeError):
                pass

        return entry


@dataclass
class SessionSummary:
    """Summary information about a session."""
    uuid: str
    summary: str = "Claude Code Session"
    artifact_type: str = "unknown"
    created_at: str = ""
    edited_files: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


@dataclass
class TimingInfo:
    """Timing information for turns."""
    is_first: bool = False
    start_time_local: datetime | None = None
    offset_from_start: str | None = None
    duration: str | None = None


@dataclass
class ConversationTurn:
    """A single conversation turn."""
    user_message: str | None = None
    assistant_sequence: list[dict[str, Any]] = field(default_factory=list)
    timing_info: TimingInfo | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    hook_context: dict[str, Any] = field(default_factory=dict)
    inline_hooks: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SessionInfo:
    """Information about a discovered session."""
    path: Path
    project: str
    session_id: str
    last_modified: datetime

    @property
    def project_display(self) -> str:
        """Human-readable project name."""
        # Convert "-home-nic-src-aOps" to "aOps"
        if self.project.startswith('-'):
            parts = self.project.split('-')
            return parts[-1] if parts else self.project
        return self.project


def find_sessions(
    project: str | None = None,
    since: datetime | None = None,
    claude_projects_dir: Path | None = None,
) -> list[SessionInfo]:
    """
    Find all Claude Code sessions.

    Args:
        project: Filter to specific project (partial match)
        since: Only sessions modified after this time
        claude_projects_dir: Override default ~/.claude/projects/

    Returns:
        List of SessionInfo, sorted by last_modified descending (newest first)
    """
    if claude_projects_dir is None:
        claude_projects_dir = Path.home() / ".claude" / "projects"

    if not claude_projects_dir.exists():
        return []

    sessions = []

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
            if session_file.name.endswith("-hooks.jsonl"):
                continue

            # Get modification time
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc)

            # Filter by time if specified
            if since and mtime < since:
                continue

            sessions.append(SessionInfo(
                path=session_file,
                project=project_name,
                session_id=session_file.stem,
                last_modified=mtime,
            ))

    # Sort by last modified, newest first
    sessions.sort(key=lambda s: s.last_modified, reverse=True)
    return sessions


class SessionProcessor:
    """Processes JSONL sessions into structured data."""

    def parse_jsonl(self, file_path: str | Path) -> tuple[SessionSummary, list[Entry], dict[str, list[Entry]]]:
        """
        Parse JSONL file into session summary and entries.

        Also loads related agent files and hook files.

        Returns:
            (session_summary, entries, agent_entries)
        """
        file_path = Path(file_path)
        entries = []
        session_summary = None
        session_uuid = file_path.stem

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = Entry.from_dict(data)
                    entries.append(entry)

                    # Extract summary if available
                    if entry.type == 'summary':
                        summary_text = entry.content.get('summary', 'Claude Code Session')
                        session_summary = SessionSummary(
                            uuid=session_uuid,
                            summary=summary_text
                        )
                except json.JSONDecodeError:
                    continue

        # Create default summary if none found
        if not session_summary:
            session_summary = SessionSummary(uuid=session_uuid)

        # Load agent entries from agent-*.jsonl files
        agent_entries = self._load_agent_files(file_path)

        # Load hook entries if hook file exists
        hook_file = self._find_hook_file(file_path)
        if hook_file:
            hook_entries = self._load_hook_entries(hook_file)
            entries.extend(hook_entries)
            # Sort by timestamp to maintain chronological order
            entries.sort(key=lambda e: e.timestamp if e.timestamp else datetime.min.replace(tzinfo=timezone.utc))

        return session_summary, entries, agent_entries

    def _load_agent_files(self, main_file_path: Path) -> dict[str, list[Entry]]:
        """Load agent-*.jsonl files that belong to this session."""
        agent_entries: dict[str, list[Entry]] = {}

        session_dir = main_file_path.parent
        main_session_uuid = main_file_path.stem

        for agent_file in session_dir.glob("agent-*.jsonl"):
            agent_id = agent_file.stem.replace("agent-", "")

            # Check if this agent file belongs to the current session
            belongs_to_session = False
            with open(agent_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line:
                    try:
                        first_entry_data = json.loads(first_line)
                        if first_entry_data.get('sessionId') == main_session_uuid:
                            belongs_to_session = True
                    except json.JSONDecodeError:
                        pass

            if not belongs_to_session:
                continue

            # Load all entries from this agent file
            entries = []
            with open(agent_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = Entry.from_dict(data)
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue

            if entries:
                agent_entries[agent_id] = entries

        return agent_entries

    def _find_hook_file(self, session_file_path: Path) -> Path | None:
        """Find hook file by searching for transcript_path match."""
        session_path = Path(session_file_path)

        # Search locations for hook files
        search_locations = [
            session_path.parent / "hooks",  # Test location
            Path.home() / ".cache" / "aops" / "sessions",  # Production
        ]

        for hook_dir in search_locations:
            if not hook_dir.exists():
                continue

            for hook_file in hook_dir.glob("*-hooks.jsonl"):
                try:
                    with open(hook_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                if data.get('transcript_path') == str(session_file_path):
                                    return hook_file
                            except json.JSONDecodeError:
                                continue
                except (OSError, IOError):
                    continue

        return None

    def _load_hook_entries(self, hook_file_path: Path) -> list[Entry]:
        """Load ALL hook entries from JSONL file."""
        entries = []

        with open(hook_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                hook_output = data.get('hookSpecificOutput') or {}

                if not hook_output.get('hookEventName'):
                    hook_output['hookEventName'] = data.get('hook_event', 'Unknown')

                if 'exit_code' in data and 'exitCode' not in hook_output:
                    hook_output['exitCode'] = data['exit_code']

                if 'tool_name' in data:
                    hook_output['toolName'] = data['tool_name']

                if 'agent_id' in data:
                    hook_output['agentId'] = data['agent_id']

                entry_data = {
                    'type': 'system_reminder',
                    'timestamp': data.get('logged_at'),
                    'hookSpecificOutput': hook_output
                }

                entries.append(Entry.from_dict(entry_data))

        return entries

    def group_entries_into_turns(
        self,
        entries: list[Entry],
        agent_entries: dict[str, list[Entry]] | None = None
    ) -> list[ConversationTurn | dict]:
        """Group JSONL entries into conversational turns."""
        main_entries = [e for e in entries if not e.is_sidechain]
        sidechain_entries = [e for e in entries if e.is_sidechain]

        sidechain_groups = self._group_sidechain_entries(sidechain_entries)

        turns: list[dict] = []
        current_turn: dict = {}
        conversation_start_time = None

        for entry in main_entries:
            if entry.type == 'user':
                user_content = self._extract_user_content(entry)
                if not user_content.strip() or 'tool_use_id' in str(entry.message):
                    continue

                if current_turn:
                    turns.append(current_turn)

                if conversation_start_time is None:
                    conversation_start_time = entry.timestamp

                current_turn = {
                    'user_message': user_content,
                    'assistant_sequence': [],
                    'start_time': entry.timestamp,
                    'end_time': entry.timestamp,
                    'hook_context': entry.hook_context,
                    'inline_hooks': []
                }

            elif entry.type == 'system_reminder':
                hook_turn = {
                    'type': 'hook_context',
                    'hook_event_name': entry.hook_event_name,
                    'content': entry.additional_context or '',
                    'exit_code': entry.hook_exit_code,
                    'skills_matched': entry.skills_matched,
                    'files_loaded': entry.files_loaded,
                    'tool_name': entry.tool_name,
                    'agent_id': entry.agent_id,
                    'start_time': entry.timestamp,
                    'end_time': entry.timestamp
                }
                if current_turn and current_turn.get('user_message'):
                    current_turn['inline_hooks'].append(hook_turn)
                else:
                    turns.append(hook_turn)

            elif entry.type == 'summary':
                summary_text = entry.summary_text or ''
                if summary_text:
                    summary_turn = {
                        'type': 'summary',
                        'content': summary_text,
                        'subagent_id': entry.subagent_id,
                        'start_time': entry.timestamp,
                        'end_time': entry.timestamp
                    }
                    if current_turn:
                        turns.append(current_turn)
                        current_turn = {}
                    turns.append(summary_turn)

            elif entry.type == 'assistant':
                if not current_turn:
                    continue

                message = entry.message or {}
                content = message.get('content', [])

                if not isinstance(content, list):
                    content = [content]

                for block in content:
                    if isinstance(block, dict):
                        if block.get('type') == 'text':
                            text_content = block.get('text', '').strip()
                            if text_content:
                                current_turn['assistant_sequence'].append({
                                    'type': 'text',
                                    'content': text_content,
                                    'subagent_id': entry.subagent_id
                                })
                        elif block.get('type') == 'tool_use':
                            tool_op = self._format_tool_operation(block)
                            if tool_op:
                                tool_item = {
                                    'type': 'tool',
                                    'content': tool_op,
                                    'tool_name': block.get('name', ''),
                                    'tool_input': block.get('input', {})
                                }

                                tool_id = block.get('id')
                                tool_name = block.get('name', '')

                                error_result = self._get_tool_error(tool_id, entries)
                                if error_result:
                                    tool_item['error'] = error_result
                                else:
                                    tool_result = self._get_tool_result(tool_id, entries)
                                    if tool_result:
                                        tool_item['result'] = tool_result

                                if tool_name == 'Task' and tool_id:
                                    agent_id = self._extract_agent_id_from_result(tool_id, entries)
                                    if agent_id and agent_entries and agent_id in agent_entries:
                                        tool_item['sidechain_summary'] = self._extract_sidechain(agent_entries[agent_id])
                                    else:
                                        related_sidechain = self._find_related_sidechain(entry, sidechain_groups)
                                        if related_sidechain:
                                            tool_item['sidechain_summary'] = self._summarize_sidechain(related_sidechain)

                                current_turn['assistant_sequence'].append(tool_item)
                    else:
                        text_content = str(block).strip()
                        if text_content:
                            current_turn['assistant_sequence'].append({
                                'type': 'text',
                                'content': text_content,
                                'subagent_id': entry.subagent_id
                            })

                if entry.timestamp and current_turn:
                    current_turn['end_time'] = entry.timestamp

        if current_turn and (current_turn.get('user_message') or current_turn.get('assistant_sequence')):
            turns.append(current_turn)

        # Add timing information
        first_user_turn_found = False
        for turn in turns:
            if conversation_start_time and turn.get('start_time'):
                is_user_turn = turn.get('type') not in ('hook_context', 'summary')
                if is_user_turn and not first_user_turn_found:
                    first_user_turn_found = True
                    turn['timing_info'] = TimingInfo(
                        is_first=True,
                        start_time_local=turn['start_time'],
                        offset_from_start=None,
                        duration=self._calculate_duration(turn.get('start_time'), turn.get('end_time'))
                    )
                else:
                    offset_seconds = (turn['start_time'] - conversation_start_time).total_seconds()
                    turn['timing_info'] = TimingInfo(
                        is_first=False,
                        start_time_local=None,
                        offset_from_start=self._format_time_offset(offset_seconds),
                        duration=self._calculate_duration(turn.get('start_time'), turn.get('end_time'))
                    )

        # Convert to ConversationTurn objects
        conversation_turns: list[ConversationTurn | dict] = []
        for turn in turns:
            if turn.get('type') in ('hook_context', 'summary'):
                conversation_turns.append(turn)
            elif (turn.get('user_message', '').strip() or turn.get('assistant_sequence')):
                conversation_turns.append(ConversationTurn(
                    user_message=turn.get('user_message'),
                    assistant_sequence=turn.get('assistant_sequence', []),
                    timing_info=turn.get('timing_info'),
                    start_time=turn.get('start_time'),
                    end_time=turn.get('end_time'),
                    hook_context=turn.get('hook_context', {}),
                    inline_hooks=turn.get('inline_hooks', [])
                ))

        return conversation_turns

    def format_session_as_markdown(
        self,
        session: SessionSummary,
        entries: list[Entry],
        agent_entries: dict[str, list[Entry]] | None = None,
        include_tool_results: bool = True,
        variant: str = "full"
    ) -> str:
        """Format session entries as readable markdown."""
        session_uuid = session.uuid
        details = session.details or {}

        first_timestamp = None
        for entry in entries:
            if entry.timestamp:
                first_timestamp = entry.timestamp
                break
        date_str = first_timestamp.strftime('%Y-%m-%d') if first_timestamp else 'unknown'

        turns = self.group_entries_into_turns(entries, agent_entries)

        skipped_hooks: dict[str, int] = {}
        markdown = ""
        turn_number = 0
        context_summary_started = False

        for turn in turns:
            if isinstance(turn, dict) and turn.get('type') == 'hook_context':
                event_name = turn.get('hook_event_name')
                exit_code = turn.get('exit_code')
                content = turn.get('content', '').strip()
                skills_matched = turn.get('skills_matched')
                files_loaded = turn.get('files_loaded')

                if not content and not skills_matched and not files_loaded:
                    continue

                if exit_code is None:
                    status = ""
                elif exit_code == 0:
                    status = " ✓"
                else:
                    status = f" ✗ (exit {exit_code})"

                hook_name = event_name or "Hook"
                markdown += f"- Hook({hook_name}){status}\n"

                if skills_matched:
                    skills_str = ", ".join(f"`{s}`" for s in skills_matched)
                    markdown += f"  - Skills matched: {skills_str}\n"
                if files_loaded:
                    for f in files_loaded:
                        markdown += f"  - Loaded `{f}` (content injected)\n"
                elif content:
                    markdown += f"  - {content[:200]}\n"
                markdown += "\n"
                continue

            if isinstance(turn, dict) and turn.get('type') == 'summary':
                content = turn.get('content', '').strip()
                if content:
                    if not context_summary_started:
                        markdown += f"## Context Summary\n\n"
                        context_summary_started = True
                    markdown += f"- {content}\n"
                continue

            if context_summary_started:
                markdown += "\n"
                context_summary_started = False

            turn_number += 1
            timing_info = turn.timing_info if isinstance(turn, ConversationTurn) else turn.get('timing_info')
            timing_str = ""
            if timing_info:
                parts = []
                if timing_info.is_first and timing_info.start_time_local:
                    local_time = timing_info.start_time_local.strftime('%I:%M %p')
                    parts.append(local_time)
                elif timing_info.offset_from_start:
                    parts.append(f"at +{timing_info.offset_from_start}")
                if timing_info.duration:
                    parts.append(f"took {timing_info.duration}")
                if parts:
                    timing_str = f" ({', '.join(parts)})"

            user_message = turn.user_message if isinstance(turn, ConversationTurn) else turn.get('user_message')
            if user_message:
                markdown += f"## User (Turn {turn_number}{timing_str})\n\n{user_message}\n\n"

                inline_hooks = turn.inline_hooks if isinstance(turn, ConversationTurn) else turn.get('inline_hooks', [])
                if inline_hooks:
                    for hook in inline_hooks:
                        event_name = hook.get('hook_event_name') or 'Hook'
                        exit_code = hook.get('exit_code') if hook.get('exit_code') is not None else 0
                        content = hook.get('content', '').strip()
                        skills_matched = hook.get('skills_matched')
                        files_loaded = hook.get('files_loaded')

                        has_useful_content = content or skills_matched or files_loaded
                        is_error = exit_code is not None and exit_code != 0
                        if not has_useful_content and not is_error:
                            tool_name = hook.get('tool_name')
                            key = f"{event_name} ({tool_name})" if tool_name else event_name
                            skipped_hooks[key] = skipped_hooks.get(key, 0) + 1
                            continue

                        checkmark = " ✓" if exit_code == 0 else f" ✗ (exit {exit_code})"

                        tool_name = hook.get('tool_name')
                        agent_id = hook.get('agent_id')
                        if tool_name:
                            hook_label = f"{event_name}, {tool_name}"
                        elif agent_id:
                            hook_label = f"{event_name}, {agent_id}"
                        else:
                            hook_label = event_name

                        markdown += f"- Hook({hook_label}){checkmark}\n"

                        if skills_matched:
                            skills_str = ", ".join(f"`{s}`" for s in skills_matched)
                            markdown += f"  - Skills matched: {skills_str}\n"
                        if files_loaded:
                            for f in files_loaded:
                                markdown += f"  - Loaded `{f}` (content injected)\n"
                        elif content:
                            markdown += f"  - {content[:200]}\n"
                        markdown += "\n"

            assistant_sequence = turn.assistant_sequence if isinstance(turn, ConversationTurn) else turn.get('assistant_sequence', [])
            if assistant_sequence:
                in_assistant_response = False
                in_actions_section = False
                agent_header_emitted = False

                for item in assistant_sequence:
                    item_type = item.get('type')
                    content = item.get('content', '')
                    subagent_id = item.get('subagent_id')

                    if item_type == 'text':
                        if in_actions_section:
                            in_actions_section = False
                            markdown += "\n"

                        if not agent_header_emitted:
                            if subagent_id:
                                agent_header = f"## Agent ({subagent_id})"
                            else:
                                agent_header = f"## Agent (Turn {turn_number})"
                            markdown += f"{agent_header}\n\n"
                            agent_header_emitted = True

                        markdown += f"{content}\n\n"
                        in_assistant_response = True

                    elif item_type == 'tool':
                        if in_assistant_response:
                            in_assistant_response = False

                        if not in_actions_section:
                            in_actions_section = True

                        if item.get('error'):
                            content = content.rstrip('\n')
                            markdown += f"- **❌ ERROR:** {content.lstrip('- ')}: `{item['error']}`\n"
                        else:
                            if include_tool_results and item.get('result'):
                                result_text = item['result']
                                result_text = self._maybe_pretty_print_json(result_text)
                                code_lang = "json" if result_text.strip().startswith(('{', '[')) else ""
                                tool_call = content.strip().lstrip('- ').rstrip('\n')
                                markdown += f"### Tool result: {tool_call}\n\n```{code_lang}\n{result_text}\n```\n\n"
                            else:
                                markdown += content

                        if item.get('sidechain_summary'):
                            markdown += f"\n**Agent Conversation:**\n\n"
                            indented_lines = [f"  {line}" if line.strip() else ""
                                            for line in item['sidechain_summary'].split('\n')]
                            markdown += '\n'.join(indented_lines) + '\n'

        edited_files = details.get('edited_files', session.edited_files)
        files_list = edited_files if edited_files and isinstance(edited_files, list) else []

        title = session.summary or "Claude Code Session"
        permalink = f"sessions/claude/{session_uuid[:8]}-{variant}"

        hooks_yaml = ""
        if skipped_hooks:
            hooks_yaml = "hooks_fired:\n"
            for k, v in sorted(skipped_hooks.items()):
                hooks_yaml += f"  {k}: {v}\n"

        files_yaml = ""
        if files_list:
            files_yaml = "files_modified:\n"
            for f in files_list:
                files_yaml += f"  - {f}\n"

        frontmatter = f"""---
title: "{title} ({variant})"
type: session
permalink: {permalink}
tags:
  - claude-session
  - transcript
  - {variant}
date: {date_str}
session_id: {session_uuid}
{hooks_yaml}{files_yaml}---

"""

        header = f"# {title}\n\n"

        return frontmatter + header + markdown

    # Helper methods
    def _group_sidechain_entries(self, sidechain_entries: list[Entry]) -> dict[datetime, list[Entry]]:
        """Group sidechain entries by conversation thread."""
        groups: dict[datetime, list[Entry]] = {}
        for entry in sidechain_entries:
            timestamp = entry.timestamp
            if timestamp:
                minute_key = timestamp.replace(second=0, microsecond=0)
                if minute_key not in groups:
                    groups[minute_key] = []
                groups[minute_key].append(entry)
        return groups

    def _find_related_sidechain(self, main_entry: Entry, sidechain_groups: dict[datetime, list[Entry]]) -> list[Entry] | None:
        """Find sidechain entries related to a main thread tool use."""
        if not main_entry.timestamp:
            return None

        main_minute = main_entry.timestamp.replace(second=0, microsecond=0)

        for time_offset in [0, 1]:
            check_time = main_minute + timedelta(minutes=time_offset)
            if check_time in sidechain_groups:
                return sidechain_groups[check_time]

        return None

    def _summarize_sidechain(self, sidechain_entries: list[Entry]) -> str:
        """Create a summary of what happened in the sidechain."""
        if not sidechain_entries:
            return "No sidechain details available"

        tool_count = 0
        file_operations = []

        for entry in sidechain_entries:
            if entry.type == 'assistant' and entry.message:
                content = entry.message.get('content', [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'tool_use':
                            tool_count += 1
                            tool_name = block.get('name', '')
                            if tool_name in ['Read', 'Edit', 'Write', 'Grep']:
                                tool_input = block.get('input', {})
                                file_path = tool_input.get('file_path', '')
                                if file_path:
                                    file_operations.append(f"{tool_name}: {file_path}")

        summary_parts = []
        if tool_count > 0:
            summary_parts.append(f"Executed {tool_count} tool operations")

        if file_operations:
            shown_ops = file_operations[:3]
            summary_parts.append("Key operations: " + ", ".join(shown_ops))
            if len(file_operations) > 3:
                summary_parts.append(f"... and {len(file_operations) - 3} more")

        return "; ".join(summary_parts) if summary_parts else "Parallel task execution"

    def _extract_sidechain(self, sidechain_entries: list[Entry]) -> str:
        """Extract full conversation from sidechain entries."""
        if not sidechain_entries:
            return "No sidechain details available"

        output_parts = []

        for entry in sidechain_entries:
            if entry.type == 'assistant' and entry.message:
                content = entry.message.get('content', [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get('type') == 'text':
                                text = block.get('text', '').strip()
                                if text:
                                    output_parts.append(text + '\n')
                            elif block.get('type') == 'tool_use':
                                formatted_tool = self._format_tool_operation(block)
                                if formatted_tool:
                                    output_parts.append(formatted_tool)

        return '\n'.join(output_parts)

    def _extract_agent_id_from_result(self, tool_id: str, all_entries: list[Entry]) -> str | None:
        """Find the agentId from the tool result."""
        for entry in all_entries:
            if entry.type != 'user':
                continue

            message = entry.message or {}
            content = message.get('content', [])
            if not isinstance(content, list):
                continue

            for block in content:
                if isinstance(block, dict):
                    if (block.get('type') == 'tool_result' and
                        block.get('tool_use_id') == tool_id):
                        if isinstance(entry.tool_use_result, dict):
                            return entry.tool_use_result.get('agentId')

        return None

    def _get_tool_result(self, tool_id: str, all_entries: list[Entry]) -> str | None:
        """Get successful tool result content."""
        for entry in all_entries:
            if entry.type != 'user':
                continue

            message = entry.message or {}
            content = message.get('content', [])
            if not isinstance(content, list):
                continue

            for block in content:
                if isinstance(block, dict):
                    if (block.get('type') == 'tool_result' and
                        block.get('tool_use_id') == tool_id and
                        not block.get('is_error')):
                        result_content = block.get('content', '')
                        if isinstance(result_content, list):
                            texts = []
                            for item in result_content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    texts.append(item.get('text', ''))
                            return '\n'.join(texts)
                        elif isinstance(result_content, str):
                            return result_content
        return None

    def _get_tool_error(self, tool_id: str, all_entries: list[Entry]) -> str | None:
        """Get error message if tool failed."""
        for entry in all_entries:
            if entry.type != 'user':
                continue

            message = entry.message or {}
            content = message.get('content', [])
            if not isinstance(content, list):
                continue

            for block in content:
                if isinstance(block, dict):
                    if (block.get('type') == 'tool_result' and
                        block.get('tool_use_id') == tool_id and
                        block.get('is_error')):
                        result_content = block.get('content', '')
                        if isinstance(result_content, list):
                            texts = []
                            for item in result_content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    texts.append(item.get('text', ''))
                            return '\n'.join(texts)[:500]
                        elif isinstance(result_content, str):
                            return result_content[:500]
        return None

    def _extract_user_content(self, entry: Entry) -> str:
        """Extract clean user content from entry."""
        message = entry.message or {}
        content = message.get('content', '')

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                else:
                    text_parts.append(str(item))
            content = '\n'.join(text_parts)

        content = content.strip()

        if self._is_pseudo_command(content):
            return ""

        if entry.is_meta and content:
            return self._condense_skill_expansion(content)

        return content

    def _condense_skill_expansion(self, content: str) -> str:
        """Condense skill/command expansions."""
        if content.startswith('Base directory for this skill:'):
            first_line = content.split('\n')[0]
            if '/skills/' in first_line:
                skill_path = first_line.split(':', 1)[1].strip()
                skill_file = f"{skill_path}/SKILL.md"
                line_count = len(content.split('\n'))
                return f"<Expanded: {skill_file} ({line_count} lines)>"

        if content.startswith('##'):
            lines = content.split('\n')
            title = lines[0].strip('# ').strip()
            line_count = len(lines)
            return f"<Expanded: /{title.lower().replace(' ', '-')} command ({line_count} lines)>"

        line_count = len(content.split('\n'))
        preview = content[:80].replace('\n', ' ')
        return f"<Expanded: {preview}... ({line_count} lines)>"

    def _is_pseudo_command(self, content: str) -> bool:
        """Check if content is a pseudo-command recording."""
        if not content:
            return False

        pseudo_command_patterns = [
            '<command-name>', '<command-message>', '<command-args>', '<local-command-stdout>',
            '</command-name>', '</command-message>', '</command-args>', '</local-command-stdout>'
        ]

        for pattern in pseudo_command_patterns:
            if pattern in content:
                return True

        return False

    def _calculate_duration(self, start_time: datetime | None, end_time: datetime | None) -> str:
        """Calculate human-friendly duration."""
        if not start_time or not end_time:
            return "Unknown duration"

        duration_seconds = (end_time - start_time).total_seconds()
        return self._format_duration(duration_seconds)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-friendly format."""
        if seconds < 1:
            return "< 1 second"
        elif seconds < 60:
            return f"{int(seconds)} second{'s' if int(seconds) != 1 else ''}"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            if remaining_seconds == 0:
                return f"{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                return f"{minutes} minute{'s' if minutes != 1 else ''} {remaining_seconds} second{'s' if remaining_seconds != 1 else ''}"
        else:
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            if remaining_minutes == 0:
                return f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                return f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"

    def _format_time_offset(self, seconds: float) -> str:
        """Format time offset from conversation start."""
        return self._format_duration(seconds)

    def _format_compact_args(self, tool_input: dict[str, Any], max_length: int = 60) -> str:
        """Format tool arguments as compact Python-like syntax."""
        if not tool_input:
            return ""

        args = []
        for key, value in tool_input.items():
            if key == 'description':
                continue
            if key in ('old_string', 'new_string', 'prompt', 'content') and isinstance(value, str) and len(value) > 100:
                continue

            if isinstance(value, str):
                if len(value) > max_length:
                    if '/' in value and key in ('file_path', 'path'):
                        value = value.split('/')[-1]
                    else:
                        value = value[:max_length-3] + "..."
                value = value.replace('"', '\\"').replace('\n', '\\n')
                args.append(f'{key}="{value}"')
            elif isinstance(value, bool):
                args.append(f'{key}={str(value)}')
            elif isinstance(value, (int, float)):
                args.append(f'{key}={value}')
            elif isinstance(value, list):
                if len(value) > 3:
                    args.append(f'{key}=[{len(value)} items]')
                else:
                    args.append(f'{key}={value}')
            elif isinstance(value, dict):
                args.append(f'{key}={{...{len(value)} keys}}')
            else:
                args.append(f'{key}=...')

        return ", ".join(args)

    def _format_tool_operation(self, tool_block: dict[str, Any]) -> str:
        """Format a single tool operation."""
        tool_name = tool_block.get('name', 'Unknown')
        tool_input = tool_block.get('input', {})

        if tool_name == 'TodoWrite':
            return self._format_todowrite_operation(tool_input)

        description = tool_input.get('description', '')

        args = self._format_compact_args(tool_input, max_length=60)
        tool_call = f"{tool_name}({args})" if args else f"{tool_name}()"

        if description:
            return f"- {description}: {tool_call}\n"
        else:
            return f"- {tool_call}\n"

    def _format_todowrite_operation(self, tool_input: dict[str, Any]) -> str:
        """Format TodoWrite operations in compact checkbox format."""
        todos = tool_input.get('todos', [])

        result = f"- **TodoWrite** ({len(todos)} items):\n"

        for todo in todos:
            status = todo.get('status', 'pending')
            content = todo.get('content', 'No description')

            if status == 'completed':
                symbol = '✓'
            elif status == 'in_progress':
                symbol = '▶'
            else:
                symbol = '□'

            content_preview = self._truncate_for_display(content, 80)

            result += f"  {symbol} {content_preview}\n"

        return result

    def _maybe_pretty_print_json(self, text: str) -> str:
        """Try to pretty-print JSON."""
        text = text.strip()
        if not text:
            return text
        if not (text.startswith('{') or text.startswith('[')):
            return text
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            return text

    def _truncate_for_display(self, text: str, max_length: int) -> str:
        """Truncate text for display."""
        text = text.replace('\\n', '\n')

        if len(text) <= max_length:
            return text

        truncated = text[:max_length]

        if len(text) > max_length and text[max_length] != ' ':
            last_space = truncated.rfind(' ')
            if last_space > max_length * 0.7:
                truncated = truncated[:last_space]

        return truncated + "..."
