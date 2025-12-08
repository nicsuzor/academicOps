#!/usr/bin/env python3
"""
Claude Session Transcript Generator

Converts Claude Code JSONL session files to readable markdown transcripts.

Usage:
    uv run python $AOPS/scripts/claude_transcript.py session.jsonl
    uv run python $AOPS/scripts/claude_transcript.py session.jsonl -o output.md
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


class Entry:
    """Represents a single JSONL entry"""
    def __init__(self, data: Dict[str, Any]):
        self.type = data.get('type', 'unknown')
        self.uuid = data.get('uuid', '')
        self.parent_uuid = data.get('parentUuid', '')
        self.message = data.get('message', {})
        self.content = data.get('content', {})
        self.is_sidechain = data.get('isSidechain', False)
        self.is_meta = data.get('isMeta', False)
        self.tool_use_result = data.get('toolUseResult', {})
        self.hook_context = data.get('hook_context', {})
        self.subagent_id = data.get('subagentId')  # Track which subagent produced this
        self.summary_text = data.get('summary')  # Summary content for summary messages

        # Extract hook data from system_reminder entries
        self.additional_context = None
        self.hook_event_name = None
        self.hook_exit_code = None
        self.skills_matched = None
        self.files_loaded = None
        self.tool_name = None
        self.agent_id = None
        if self.type == 'system_reminder':
            # Try hookSpecificOutput first (real session format)
            hook_output = data.get('hookSpecificOutput', {})
            if isinstance(hook_output, dict) and hook_output:
                self.additional_context = hook_output.get('additionalContext', '')
                self.hook_event_name = hook_output.get('hookEventName')
                self.hook_exit_code = hook_output.get('exitCode')
                self.skills_matched = hook_output.get('skillsMatched')
                self.files_loaded = hook_output.get('filesLoaded')
                self.tool_name = hook_output.get('toolName')
                self.agent_id = hook_output.get('agentId')
            # Fall back to content.additionalContext (test format) - only if not already set
            if not self.additional_context and isinstance(self.content, dict):
                self.additional_context = self.content.get('additionalContext', '')
            if not self.hook_event_name and isinstance(self.content, dict):
                self.hook_event_name = self.content.get('hookEventName')
            if self.hook_exit_code is None and isinstance(self.content, dict):
                self.hook_exit_code = self.content.get('exitCode')

        # Parse timestamp
        self.timestamp = None
        if 'timestamp' in data:
            try:
                timestamp_str = data['timestamp']
                if timestamp_str.endswith('Z'):
                    timestamp_str = timestamp_str[:-1] + '+00:00'
                self.timestamp = datetime.fromisoformat(timestamp_str)
            except (ValueError, TypeError):
                pass


class SessionSummary:
    """Summary information about a session"""
    def __init__(self, uuid: str, summary: str = "Claude Code Session", 
                 artifact_type: str = "unknown", created_at: str = "", 
                 edited_files: List[str] = None):
        self.uuid = uuid
        self.summary = summary
        self.artifact_type = artifact_type
        self.created_at = created_at
        self.edited_files = edited_files or []
        self.details = {}


class TimingInfo:
    """Timing information for turns"""
    def __init__(self, is_first: bool = False, start_time_local: Optional[datetime] = None,
                 offset_from_start: Optional[str] = None, duration: Optional[str] = None):
        self.is_first = is_first
        self.start_time_local = start_time_local
        self.offset_from_start = offset_from_start
        self.duration = duration


class ConversationTurn:
    """A single conversation turn"""
    def __init__(self, user_message: Optional[str] = None,
                 assistant_sequence: List[Dict[str, Any]] = None,
                 timing_info: Optional[TimingInfo] = None,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None,
                 hook_context: Optional[Dict[str, Any]] = None,
                 inline_hooks: Optional[List[Dict[str, Any]]] = None):
        self.user_message = user_message
        self.assistant_sequence = assistant_sequence or []
        self.timing_info = timing_info
        self.start_time = start_time
        self.end_time = end_time
        self.hook_context = hook_context or {}
        self.inline_hooks = inline_hooks or []


class SessionProcessor:
    """Processes JSONL sessions into markdown transcripts with exact same logic as backend"""
    
    def parse_jsonl(self, file_path: str) -> Tuple[SessionSummary, List[Entry], Dict[str, List[Entry]]]:
        """Parse JSONL file into session summary and entries, plus agent entries"""
        entries = []
        session_summary = None
        session_uuid = Path(file_path).stem
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = Entry(data)
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
            # Sort by timestamp to maintain chronological order (None timestamps come first)
            from datetime import timezone
            entries.sort(key=lambda e: e.timestamp if e.timestamp else datetime.min.replace(tzinfo=timezone.utc))

        return session_summary, entries, agent_entries

    def _load_agent_files(self, main_file_path: str) -> Dict[str, List[Entry]]:
        """Load agent-*.jsonl files that belong to this session (matching sessionId)"""
        agent_entries: Dict[str, List[Entry]] = {}

        main_path = Path(main_file_path)
        session_dir = main_path.parent
        # Get main session UUID from filename
        main_session_uuid = main_path.stem

        for agent_file in session_dir.glob("agent-*.jsonl"):
            agent_id = agent_file.stem.replace("agent-", "")

            # Check if this agent file belongs to the current session
            # by reading the first entry's sessionId
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
                        entry = Entry(data)
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue

            if entries:
                agent_entries[agent_id] = entries

        return agent_entries

    def _find_hook_file(self, session_file_path: str) -> Optional[str]:
        """Find hook file by searching for transcript_path match in hook JSONL files.

        Args:
            session_file_path: Path to the session JSONL file

        Returns:
            Path to matching hook file, or None if not found
        """
        session_path = Path(session_file_path)

        # Search multiple locations for hook files
        search_locations = [
            # 1. Session file's parent directory / "hooks" subdirectory (for tests)
            session_path.parent / "hooks",
            # 2. ~/.cache/aops/sessions/ (for production)
            Path.home() / ".cache" / "aops" / "sessions",
        ]

        # Search each location for matching hook file
        for hook_dir in search_locations:
            # Skip if directory doesn't exist
            if not hook_dir.exists():
                continue

            # Search all *-hooks.jsonl files in this location
            for hook_file in hook_dir.glob("*-hooks.jsonl"):
                try:
                    with open(hook_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                # Check if transcript_path field matches session file
                                if 'transcript_path' not in data:
                                    continue
                                if data['transcript_path'] == session_file_path:
                                    return str(hook_file)
                            except json.JSONDecodeError:
                                continue
                except (OSError, IOError):
                    continue

        return None

    def _load_hook_entries(self, hook_file_path: str) -> List[Entry]:
        """Load ALL hook entries from JSONL file and convert to Entry objects.

        Reads hook JSONL file line by line and creates Entry objects for ALL hooks,
        not just ones with additionalContext. This shows when hooks were triggered
        even if they output nothing.

        Args:
            hook_file_path: Path to hook JSONL file

        Returns:
            List of Entry objects representing all hook executions
        """
        entries = []

        with open(hook_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue  # Skip malformed lines

                # Create Entry for ALL hooks, not just ones with additionalContext
                hook_output = data.get('hookSpecificOutput') or {}

                # Ensure hookEventName is set (fall back to top-level hook_event)
                if not hook_output.get('hookEventName'):
                    hook_output['hookEventName'] = data.get('hook_event', 'Unknown')

                # Add exit_code to hookSpecificOutput if present at top level
                if 'exit_code' in data and 'exitCode' not in hook_output:
                    hook_output['exitCode'] = data['exit_code']

                # Add tool_name for PreToolUse/PostToolUse hooks
                if 'tool_name' in data:
                    hook_output['toolName'] = data['tool_name']

                # Add agent_id for SubagentStop hooks
                if 'agent_id' in data:
                    hook_output['agentId'] = data['agent_id']

                # Convert to Entry format
                entry_data = {
                    'type': 'system_reminder',
                    'timestamp': data['logged_at'],
                    'hookSpecificOutput': hook_output
                }

                entries.append(Entry(entry_data))

        return entries

    def group_entries_into_turns(self, entries: List[Entry], agent_entries: Optional[Dict[str, List[Entry]]] = None) -> List[ConversationTurn]:
        """Group JSONL entries into conversational turns, correlating sidechains with main thread"""
        # First, separate main thread from sidechains
        # Include system_reminder (hook context) and summary messages in main flow
        # Keep isMeta entries - they're part of conversation (e.g., user-memory-input)
        main_entries = [e for e in entries if not e.is_sidechain]
        sidechain_entries = [e for e in entries if e.is_sidechain]
        
        # Group sidechain entries by their conversation thread
        sidechain_groups = self._group_sidechain_entries(sidechain_entries)
        
        # Build main conversation turns with timing information
        turns = []
        current_turn = {}
        conversation_start_time = None
        
        for entry in main_entries:
            if entry.type == 'user':
                # Check if this is a tool result (should be part of current turn)
                user_content = self._extract_user_content(entry)
                if not user_content.strip() or 'tool_use_id' in str(entry.message):
                    # This is likely a tool result, skip it for turn grouping
                    continue
                
                # Start a new turn for real user messages
                if current_turn:
                    turns.append(current_turn)
                
                # Set conversation start time from first user message
                if conversation_start_time is None:
                    conversation_start_time = entry.timestamp
                
                current_turn = {
                    'user_message': user_content,
                    'assistant_sequence': [],  # Chronological sequence of text and tool operations
                    'start_time': entry.timestamp,
                    'end_time': entry.timestamp,  # Will be updated as we process assistant responses
                    'hook_context': entry.hook_context
                }

            elif entry.type == 'system_reminder':
                # Hook context - create a turn for ALL hooks, even empty ones
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
                # If we have a current turn with user message, add hook inline (don't break turn)
                if current_turn and current_turn.get('user_message'):
                    if 'inline_hooks' not in current_turn:
                        current_turn['inline_hooks'] = []
                    current_turn['inline_hooks'].append(hook_turn)
                else:
                    # No current turn - add as standalone (e.g., SessionStart before first message)
                    turns.append(hook_turn)

            elif entry.type == 'summary':
                # Summary message - create a turn for it
                summary_text = entry.summary_text or ''
                if summary_text:
                    summary_turn = {
                        'type': 'summary',
                        'content': summary_text,
                        'subagent_id': entry.subagent_id,
                        'start_time': entry.timestamp,
                        'end_time': entry.timestamp
                    }
                    # Append current turn if exists, then add summary turn
                    if current_turn:
                        turns.append(current_turn)
                        current_turn = {}
                    turns.append(summary_turn)

            elif entry.type == 'assistant':
                # Only process assistant entries if we have a current turn
                if not current_turn:
                    continue
                    
                # Process assistant content
                message = entry.message or {}
                content = message.get('content', [])
                
                if not isinstance(content, list):
                    content = [content]
                
                # Process content blocks in chronological order
                for block in content:
                    if isinstance(block, dict):
                        if block.get('type') == 'text':
                            text_content = block.get('text', '').strip()
                            if text_content:
                                current_turn['assistant_sequence'].append({
                                    'type': 'text',
                                    'content': text_content,
                                    'subagent_id': entry.subagent_id  # Preserve subagent attribution
                                })
                        elif block.get('type') == 'tool_use':
                            # Format tool operation
                            tool_op = self._format_tool_operation(block)
                            if tool_op:
                                tool_item = {
                                    'type': 'tool',
                                    'content': tool_op
                                }

                                tool_id = block.get('id')
                                tool_name = block.get('name', '')

                                # Check if tool failed and capture error
                                error_result = self._get_tool_error(tool_id, entries)
                                if error_result:
                                    tool_item['error'] = error_result
                                else:
                                    # Capture successful tool result
                                    tool_result = self._get_tool_result(tool_id, entries)
                                    if tool_result:
                                        tool_item['result'] = tool_result

                                # Check if this tool use has an associated sidechain
                                if tool_name == 'Task' and tool_id:
                                    # First try: explicit agentId from tool result
                                    agent_id = self._extract_agent_id_from_result(tool_id, entries)
                                    if agent_id and agent_entries and agent_id in agent_entries:
                                        tool_item['sidechain_summary'] = self._extract_sidechain(agent_entries[agent_id])
                                    else:
                                        # Fallback: existing timestamp-based sidechain lookup
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
                                'subagent_id': entry.subagent_id  # Preserve subagent attribution
                            })
                
                # Update turn end time with this assistant entry
                if entry.timestamp and current_turn:
                    current_turn['end_time'] = entry.timestamp
        
        # Add the final turn if it has content
        if current_turn and (current_turn.get('user_message') or current_turn.get('assistant_sequence')):
            turns.append(current_turn)
        
        # Add timing information to each turn
        first_user_turn_found = False
        for turn in turns:
            if conversation_start_time and turn.get('start_time'):
                # Skip hook_context/summary for "first turn" designation
                is_user_turn = turn.get('type') not in ('hook_context', 'summary')
                if is_user_turn and not first_user_turn_found:
                    # First user turn shows actual local time
                    first_user_turn_found = True
                    turn['timing_info'] = TimingInfo(
                        is_first=True,
                        start_time_local=turn['start_time'],
                        offset_from_start=None,
                        duration=self._calculate_duration(turn.get('start_time'), turn.get('end_time'))
                    )
                else:
                    # Subsequent turns show offset from conversation start
                    offset_seconds = (turn['start_time'] - conversation_start_time).total_seconds()
                    turn['timing_info'] = TimingInfo(
                        is_first=False,
                        start_time_local=None,
                        offset_from_start=self._format_time_offset(offset_seconds),
                        duration=self._calculate_duration(turn.get('start_time'), turn.get('end_time'))
                    )
        
        # Convert to ConversationTurn objects and filter out empty turns
        # Keep hook_context and summary turns as dicts
        conversation_turns = []
        for turn in turns:
            # Hook context and summary turns stay as dicts
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
    
    def format_session_as_markdown(self, session: SessionSummary, entries: List[Entry],
                                     agent_entries: Optional[Dict[str, List[Entry]]] = None,
                                     include_tool_results: bool = True,
                                     variant: str = "full") -> str:
        """Format session entries as readable markdown with proper turn structure"""
        session_uuid = session.uuid
        details = session.details or {}

        # Extract first timestamp for date
        first_timestamp = None
        for entry in entries:
            if entry.timestamp:
                first_timestamp = entry.timestamp
                break
        date_str = first_timestamp.strftime('%Y-%m-%d') if first_timestamp else 'unknown'

        # Group entries into conversational turns first (to count hooks)
        turns = self.group_entries_into_turns(entries, agent_entries)

        # Track skipped hooks for metadata summary
        skipped_hooks = {}  # event_name -> count

        # Body markdown built from turns
        markdown = ""
        turn_number = 0  # Track actual conversation turns separately
        context_summary_started = False  # Track if we've started context summary section
        for i, turn in enumerate(turns):
            # Handle hook context turns specially
            if isinstance(turn, dict) and turn.get('type') == 'hook_context':
                event_name = turn.get('hook_event_name')
                exit_code = turn.get('exit_code')
                content = turn.get('content', '').strip()
                skills_matched = turn.get('skills_matched')
                files_loaded = turn.get('files_loaded')

                # Skip hook turns with no content and no metadata
                if not content and not skills_matched and not files_loaded:
                    continue

                # Format hook like a tool call
                if exit_code is None:
                    status = ""
                elif exit_code == 0:
                    status = " ✓"
                else:
                    status = f" ✗ (exit {exit_code})"

                hook_name = event_name or "Hook"
                markdown += f"- Hook({hook_name}){status}\n"

                # Show metadata as indented items
                if skills_matched:
                    skills_str = ", ".join(f"`{s}`" for s in skills_matched)
                    markdown += f"  - Skills matched: {skills_str}\n"
                if files_loaded:
                    for f in files_loaded:
                        markdown += f"  - Loaded `{f}` (content injected)\n"
                elif content:
                    # Show short content inline
                    markdown += f"  - {content[:200]}\n"
                markdown += "\n"
                continue

            # Handle summary messages (context given to model after memory break)
            if isinstance(turn, dict) and turn.get('type') == 'summary':
                content = turn.get('content', '').strip()
                if content:
                    if not context_summary_started:
                        markdown += f"## Context Summary\n\n"
                        context_summary_started = True
                    markdown += f"- {content}\n"
                continue

            # Close context summary section if we were in one
            if context_summary_started:
                markdown += "\n"
                context_summary_started = False

            # Format turn header with timing inline
            turn_number += 1
            timing_info = turn.timing_info
            timing_str = ""
            if timing_info:
                # Build timing with clear labels
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
            # User message with timing in H2
            if turn.user_message:
                markdown += f"## User (Turn {turn_number}{timing_str})\n\n{turn.user_message}\n\n"

                # Add inline hooks from hook entries that fired after this user message
                if turn.inline_hooks:
                    for hook in turn.inline_hooks:
                        event_name = hook.get('hook_event_name') or 'Hook'
                        exit_code = hook.get('exit_code') if hook.get('exit_code') is not None else 0
                        content = hook.get('content', '').strip()
                        skills_matched = hook.get('skills_matched')
                        files_loaded = hook.get('files_loaded')

                        # Skip successful hooks with no useful content
                        has_useful_content = content or skills_matched or files_loaded
                        is_error = exit_code is not None and exit_code != 0
                        if not has_useful_content and not is_error:
                            # Track skipped hook
                            tool_name = hook.get('tool_name')
                            key = f"{event_name} ({tool_name})" if tool_name else event_name
                            skipped_hooks[key] = skipped_hooks.get(key, 0) + 1
                            continue

                        checkmark = " ✓" if exit_code == 0 else f" ✗ (exit {exit_code})"

                        # Format hook name with context
                        tool_name = hook.get('tool_name')
                        agent_id = hook.get('agent_id')
                        if tool_name:
                            hook_label = f"{event_name}, {tool_name}"
                        elif agent_id:
                            hook_label = f"{event_name}, {agent_id}"
                        else:
                            hook_label = event_name

                        markdown += f"- Hook({hook_label}){checkmark}\n"

                        # Show metadata as indented items
                        if skills_matched:
                            skills_str = ", ".join(f"`{s}`" for s in skills_matched)
                            markdown += f"  - Skills matched: {skills_str}\n"
                        if files_loaded:
                            for f in files_loaded:
                                markdown += f"  - Loaded `{f}` (content injected)\n"
                        elif content:
                            markdown += f"  - {content[:200]}\n"
                        markdown += "\n"

                # Legacy hook_context (from entry itself, rarely used)
                if turn.hook_context:
                    for hook_name, hook_data in turn.hook_context.items():
                        exit_code = hook_data.get('exit_code', 0)
                        content = hook_data.get('content', '')
                        if exit_code == 0 and not content.strip():
                            continue
                        checkmark = "✓" if exit_code == 0 else "✗"
                        markdown += f"* {checkmark} {hook_name} hook: {content}\n"
                    markdown += "\n"

            # Assistant sequence (chronological text and tool operations)
            assistant_sequence = turn.assistant_sequence
            if assistant_sequence:
                in_assistant_response = False
                in_actions_section = False
                agent_header_emitted = False  # Only emit agent header once per turn

                for item in assistant_sequence:
                    item_type = item.get('type')
                    content = item.get('content', '')
                    subagent_id = item.get('subagent_id')

                    if item_type == 'text':
                        # Close actions section if we were in one
                        if in_actions_section:
                            in_actions_section = False
                            markdown += "\n"

                        # Format agent response as H2 (only once per turn)
                        if not agent_header_emitted:
                            if subagent_id:
                                agent_header = f"## Agent ({subagent_id})"
                            else:
                                agent_header = f"## Agent (Turn {turn_number})"
                            markdown += f"{agent_header}\n\n"
                            agent_header_emitted = True

                        # Content as regular paragraph
                        markdown += f"{content}\n\n"
                        in_assistant_response = True

                    elif item_type == 'tool':
                        # Close assistant response section if we were in one
                        if in_assistant_response:
                            in_assistant_response = False

                        # Don't add "Actions Taken:" header, just list tools
                        if not in_actions_section:
                            in_actions_section = True

                        # Show error inline if tool failed
                        if item.get('error'):
                            # content already ends with \n, so strip it and append error inline
                            content = content.rstrip('\n')
                            markdown += f"- **❌ ERROR:** {content.lstrip('- ')}: `{item['error']}`\n"
                        else:
                            # Show tool result if present (only in full version)
                            if include_tool_results and item.get('result'):
                                result_text = item['result']
                                # Pretty-print JSON if possible
                                result_text = self._maybe_pretty_print_json(result_text)
                                # Determine code block language
                                code_lang = "json" if result_text.strip().startswith(('{', '[')) else ""
                                # Extract tool call from content (format: "- tool_call\n")
                                tool_call = content.strip().lstrip('- ').rstrip('\n')
                                markdown += f"### Tool result: {tool_call}\n\n```{code_lang}\n{result_text}\n```\n\n"
                            else:
                                markdown += content

                        # Add sidechain details if present
                        if item.get('sidechain_summary'):
                            markdown += f"\n**Agent Conversation:**\n\n"
                            # Indent each line by 2 spaces
                            indented_lines = [f"  {line}" if line.strip() else ""
                                            for line in item['sidechain_summary'].split('\n')]
                            markdown += '\n'.join(indented_lines) + '\n'

        # Collect edited files
        edited_files = details.get('edited_files', session.edited_files)
        files_list = edited_files if edited_files and isinstance(edited_files, list) else []

        # Build YAML frontmatter (bmem-compliant) with all metadata
        title = session.summary or "Claude Code Session"
        permalink = f"sessions/claude/{session_uuid[:8]}-{variant}"

        # Format hooks for YAML
        hooks_yaml = ""
        if skipped_hooks:
            hooks_yaml = "hooks_fired:\n"
            for k, v in sorted(skipped_hooks.items()):
                hooks_yaml += f"  {k}: {v}\n"

        # Format files for YAML
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

        # Simple header - just the title
        header = f"# {title}\n\n"

        return frontmatter + header + markdown
    
    # Helper methods (extracted from SessionProcessor)
    def _group_sidechain_entries(self, sidechain_entries: List[Entry]) -> Dict[datetime, List[Entry]]:
        """Group sidechain entries by conversation thread"""
        groups = {}
        for entry in sidechain_entries:
            # Use a simple heuristic - group by timestamp proximity (within 1 minute)
            timestamp = entry.timestamp
            if timestamp:
                # Round to minute for grouping
                minute_key = timestamp.replace(second=0, microsecond=0)
                if minute_key not in groups:
                    groups[minute_key] = []
                groups[minute_key].append(entry)
        return groups
    
    def _find_related_sidechain(self, main_entry: Entry, sidechain_groups: Dict[datetime, List[Entry]]) -> Optional[List[Entry]]:
        """Find sidechain entries related to a main thread tool use"""
        if not main_entry.timestamp:
            return None
        
        # Look for sidechains that started around the same time
        main_minute = main_entry.timestamp.replace(second=0, microsecond=0)
        
        # Check the same minute and next minute
        for time_offset in [0, 1]:
            check_time = main_minute + timedelta(minutes=time_offset)
            if check_time in sidechain_groups:
                return sidechain_groups[check_time]
        
        return None
    
    def _summarize_sidechain(self, sidechain_entries: List[Entry]) -> str:
        """Create a summary of what happened in the sidechain"""
        if not sidechain_entries:
            return "No sidechain details available"
        
        # Count tool operations and extract key actions
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
            # Show first few file operations
            shown_ops = file_operations[:3]
            summary_parts.append("Key operations: " + ", ".join(shown_ops))
            if len(file_operations) > 3:
                summary_parts.append(f"... and {len(file_operations) - 3} more")
        
        return "; ".join(summary_parts) if summary_parts else "Parallel task execution"

    def _extract_sidechain(self, sidechain_entries: List[Entry]) -> str:
        """Extract full conversation from sidechain entries with text and tool operations"""
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
                                # Add text blocks as paragraphs
                                text = block.get('text', '').strip()
                                if text:
                                    output_parts.append(text + '\n')
                            elif block.get('type') == 'tool_use':
                                # Format tool operations using existing formatter
                                formatted_tool = self._format_tool_operation(block)
                                if formatted_tool:
                                    output_parts.append(formatted_tool)

        return '\n'.join(output_parts)

    def _extract_agent_id_from_result(self, tool_id: str, all_entries: List[Entry]) -> Optional[str]:
        """Find the agentId from the tool result corresponding to this tool use"""
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
                        # Found it - get agentId from tool_use_result
                        if isinstance(entry.tool_use_result, dict):
                            return entry.tool_use_result.get('agentId')

        return None

    def _get_tool_result(self, tool_id: str, all_entries: List[Entry]) -> Optional[str]:
        """Get successful tool result content"""
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
                        # Extract result content
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

    def _get_tool_error(self, tool_id: str, all_entries: List[Entry]) -> Optional[str]:
        """Get error message if tool failed"""
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
                        # Extract error content
                        result_content = block.get('content', '')
                        if isinstance(result_content, list):
                            # Content is list of blocks
                            texts = []
                            for item in result_content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    texts.append(item.get('text', ''))
                            return '\n'.join(texts)[:500]  # Truncate long errors
                        elif isinstance(result_content, str):
                            return result_content[:500]
        return None

    def _extract_user_content(self, entry: Entry) -> str:
        """Extract clean user content from entry"""
        message = entry.message or {}
        content = message.get('content', '')

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                    # Skip tool results in user display
                else:
                    text_parts.append(str(item))
            content = '\n'.join(text_parts)

        content = content.strip()

        # Filter out pseudo-command recordings
        if self._is_pseudo_command(content):
            return ""

        # Condense isMeta skill/command expansions
        if entry.is_meta and content:
            return self._condense_skill_expansion(content)

        return content
    
    def _condense_skill_expansion(self, content: str) -> str:
        """Condense skill/command expansions to show file loaded without full text"""
        # Check for skill expansion pattern
        if content.startswith('Base directory for this skill:'):
            # Extract path from first line
            first_line = content.split('\n')[0]
            if '/skills/' in first_line:
                # Extract skill path
                skill_path = first_line.split(':', 1)[1].strip()
                skill_file = f"{skill_path}/SKILL.md"
                line_count = len(content.split('\n'))
                return f"<Expanded: {skill_file} ({line_count} lines)>"

        # Check for slash command expansion (starts with ## or other markdown headers)
        if content.startswith('##'):
            lines = content.split('\n')
            # Try to extract a title
            title = lines[0].strip('# ').strip()
            line_count = len(lines)
            return f"<Expanded: /{title.lower().replace(' ', '-')} command ({line_count} lines)>"

        # Default: show first 80 chars + line count
        line_count = len(content.split('\n'))
        preview = content[:80].replace('\n', ' ')
        return f"<Expanded: {preview}... ({line_count} lines)>"

    def _is_pseudo_command(self, content: str) -> bool:
        """Check if content is a pseudo-command recording that should be filtered out"""
        if not content:
            return False
            
        # Check for command execution XML tags
        pseudo_command_patterns = [
            '<command-name>', '<command-message>', '<command-args>', '<local-command-stdout>',
            '</command-name>', '</command-message>', '</command-args>', '</local-command-stdout>'
        ]
        
        # If content contains any pseudo-command XML tags, filter it out
        for pattern in pseudo_command_patterns:
            if pattern in content:
                return True
                
        return False
    
    def _calculate_duration(self, start_time: Optional[datetime], end_time: Optional[datetime]) -> str:
        """Calculate human-friendly duration between two timestamps"""
        if not start_time or not end_time:
            return "Unknown duration"
        
        duration_seconds = (end_time - start_time).total_seconds()
        return self._format_duration(duration_seconds)
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-friendly format"""
        if seconds < 1:
            return "< 1 second"
        elif seconds < 60:
            return f"{int(seconds)} second{'s' if int(seconds) != 1 else ''}"
        elif seconds < 3600:  # Less than 1 hour
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            if remaining_seconds == 0:
                return f"{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                return f"{minutes} minute{'s' if minutes != 1 else ''} {remaining_seconds} second{'s' if remaining_seconds != 1 else ''}"
        else:  # 1 hour or more
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            if remaining_minutes == 0:
                return f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                return f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"
    
    def _format_time_offset(self, seconds: float) -> str:
        """Format time offset from conversation start in human-friendly format"""
        return self._format_duration(seconds)

    def _format_compact_args(self, tool_input: Dict[str, Any], max_length: int = 60) -> str:
        """Format tool arguments as compact Python-like syntax"""
        if not tool_input:
            return ""

        args = []
        for key, value in tool_input.items():
            # Skip description (shown separately as narration)
            if key == 'description':
                continue
            # Skip very verbose parameters for certain tools
            if key in ('old_string', 'new_string', 'prompt', 'content') and isinstance(value, str) and len(value) > 100:
                continue  # Skip these verbose params

            if isinstance(value, str):
                # Truncate long strings intelligently
                if len(value) > max_length:
                    # For paths, just show filename
                    if '/' in value and key in ('file_path', 'path'):
                        value = value.split('/')[-1]
                    else:
                        value = value[:max_length-3] + "..."
                # Escape quotes and newlines
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
                # For dicts, just show key count
                args.append(f'{key}={{...{len(value)} keys}}')
            else:
                # For complex types, just indicate presence
                args.append(f'{key}=...')

        return ", ".join(args)

    def _format_tool_operation(self, tool_block: Dict[str, Any]) -> str:
        """Format a single tool operation with special handling for specific tools"""
        tool_name = tool_block.get('name', 'Unknown')
        tool_input = tool_block.get('input', {})

        # Special formatting for specific tools
        if tool_name == 'TodoWrite':
            return self._format_todowrite_operation(tool_input)

        # Extract description for narration-first format
        description = tool_input.get('description', '')

        # Compact Python-like syntax for most tools
        args = self._format_compact_args(tool_input, max_length=60)
        tool_call = f"{tool_name}({args})" if args else f"{tool_name}()"

        # Put description first if present
        if description:
            return f"- {description}: {tool_call}\n"
        else:
            return f"- {tool_call}\n"
    
    def _format_todowrite_operation(self, tool_input: Dict[str, Any]) -> str:
        """Format TodoWrite operations in a compact checkbox format"""
        todos = tool_input.get('todos', [])

        result = f"- **TodoWrite** ({len(todos)} items):\n"

        for todo in todos:
            status = todo.get('status', 'pending')
            content = todo.get('content', 'No description')

            # Use checkbox symbols
            if status == 'completed':
                symbol = '✓'
            elif status == 'in_progress':
                symbol = '▶'
            else:
                symbol = '□'

            # Truncate long content
            content_preview = self._truncate_for_display(content, 80)

            result += f"  {symbol} {content_preview}\n"

        return result

    def _maybe_pretty_print_json(self, text: str) -> str:
        """Try to pretty-print JSON, return original if not valid JSON"""
        text = text.strip()
        if not text:
            return text
        # Quick check for JSON-like content
        if not (text.startswith('{') or text.startswith('[')):
            return text
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            return text

    def _truncate_for_display(self, text: str, max_length: int) -> str:
        """Truncate text for display, handling newlines properly"""
        # Replace \n with proper newlines for markdown
        text = text.replace('\\n', '\n')
        
        # If text is short, return as-is
        if len(text) <= max_length:
            return text
        
        # For longer text, try to break at word boundaries
        truncated = text[:max_length]
        
        # If we're in the middle of a word, back up to the last space
        if len(text) > max_length and text[max_length] != ' ':
            last_space = truncated.rfind(' ')
            if last_space > max_length * 0.7:  # Don't go too far back
                truncated = truncated[:last_space]
        
        return truncated + "..."


def main():
    parser = argparse.ArgumentParser(
        description="Convert Claude Code JSONL sessions to markdown transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python claude_transcript.py session.jsonl                    # Generates session_XXX-full.md and session_XXX-abridged.md
  python claude_transcript.py session.jsonl -o transcript      # Generates transcript-full.md and transcript-abridged.md
  python claude_transcript.py session.jsonl --full-only        # Only full version with tool results
  python claude_transcript.py session.jsonl --abridged-only    # Only abridged version without tool results
        """
    )

    parser.add_argument('jsonl_file', help='Path to Claude Code JSONL session file')
    parser.add_argument('-o', '--output', help='Output base name (generates -full.md and -abridged.md)')
    parser.add_argument('--full-only', action='store_true', help='Generate only the full version')
    parser.add_argument('--abridged-only', action='store_true', help='Generate only the abridged version')
    
    args = parser.parse_args()
    
    # Validate input file
    jsonl_path = Path(args.jsonl_file)
    if not jsonl_path.exists():
        print(f"❌ Error: File not found: {jsonl_path}")
        return 1
    
    # Generate output base name
    if args.output:
        base_name = args.output
        # Strip .md suffix if provided
        if base_name.endswith('.md'):
            base_name = base_name[:-3]
        # Strip -full or -abridged suffix if provided
        if base_name.endswith('-full') or base_name.endswith('-abridged'):
            base_name = base_name.rsplit('-', 1)[0]
    else:
        session_id = jsonl_path.stem[:8]
        base_name = f"session_{session_id}"

    # Determine which versions to generate
    generate_full = not args.abridged_only
    generate_abridged = not args.full_only

    # Process the session
    processor = SessionProcessor()

    try:
        print(f"📝 Processing session: {jsonl_path}")
        session_summary, entries, agent_entries = processor.parse_jsonl(str(jsonl_path))

        print(f"📊 Found {len(entries)} entries")

        # Generate full version
        if generate_full:
            full_path = Path(f"{base_name}-full.md")
            markdown_full = processor.format_session_as_markdown(
                session_summary, entries, agent_entries, include_tool_results=True, variant="full"
            )
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(markdown_full)
            file_size = full_path.stat().st_size
            print(f"✅ Full transcript: {full_path} ({file_size:,} bytes)")

        # Generate abridged version
        if generate_abridged:
            abridged_path = Path(f"{base_name}-abridged.md")
            markdown_abridged = processor.format_session_as_markdown(
                session_summary, entries, agent_entries, include_tool_results=False, variant="abridged"
            )
            with open(abridged_path, 'w', encoding='utf-8') as f:
                f.write(markdown_abridged)
            file_size = abridged_path.stat().st_size
            print(f"✅ Abridged transcript: {abridged_path} ({file_size:,} bytes)")

        return 0
        
    except Exception as e:
        print(f"❌ Error processing session: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())