"""Cognitive Load Dashboard - Session cards + single focus task."""
from __future__ import annotations

import streamlit as st
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

# Add aOps root to path for imports
aops_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(aops_root))

from skills.tasks.task_loader import load_focus_tasks
from lib.session_reader import find_sessions, SessionProcessor, ConversationTurn

# Project color scheme (matching Peacock)
PROJECT_COLORS = {
    'aops': '#00ff88',      # Green
    'writing': '#bb86fc',   # Purple
    'buttermilk': '#f5deb3', # Butter yellow
}
DEFAULT_COLOR = '#ffb000'  # Amber for unknown projects


def get_project_color(project: str) -> str:
    """Get color for project, matching Peacock scheme."""
    project_lower = project.lower()
    for key, color in PROJECT_COLORS.items():
        if key in project_lower:
            return color
    return DEFAULT_COLOR


def get_session_bmem_summary(project_dir: Path) -> dict | None:
    """Get most recent bmem write_note call for a session's project directory."""
    # Find hooks log for this project
    for hooks_log in project_dir.glob("*-hooks.jsonl"):
        try:
            latest_bmem = None
            with open(hooks_log) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if entry.get("tool_name") == "mcp__bmem__write_note":
                        tool_input = entry.get("tool_input", {})
                        content = tool_input.get("content", "")
                        # Extract meaningful content (skip frontmatter and headers)
                        preview_lines = []
                        in_frontmatter = False
                        for content_line in content.split("\n"):
                            stripped = content_line.strip()
                            if stripped == "---":
                                in_frontmatter = not in_frontmatter
                                continue
                            if in_frontmatter or not stripped:
                                continue
                            if stripped.startswith("#"):
                                continue
                            preview_lines.append(stripped)
                        preview = " ".join(preview_lines)[:500]
                        latest_bmem = {
                            "title": tool_input.get("title", "Untitled"),
                            "folder": tool_input.get("folder", ""),
                            "preview": preview,
                        }
            if latest_bmem:
                return latest_bmem
        except Exception:
            continue
    return None


def get_session_state(session_info, processor: SessionProcessor) -> dict:
    """Extract current state from a session for display."""
    try:
        session_summary, entries, agent_entries = processor.parse_jsonl(session_info.path)
        turns = processor.group_entries_into_turns(entries, agent_entries)

        # Find first and last user prompts
        first_prompt = None
        last_prompt = None

        for turn in turns:
            if isinstance(turn, ConversationTurn) and turn.user_message:
                if not first_prompt:
                    first_prompt = turn.user_message[:100]
                    if len(turn.user_message) > 100:
                        first_prompt += "..."
                # Always update last_prompt to get the most recent
                last_prompt = turn.user_message[:100]
                if len(turn.user_message) > 100:
                    last_prompt += "..."

        # Get session's bmem summary (most recent write_note call)
        bmem_summary = get_session_bmem_summary(session_info.path.parent)

        return {
            'first_prompt': first_prompt or 'No activity',
            'last_prompt': last_prompt or 'No activity',
            'bmem_summary': bmem_summary,
        }
    except Exception:
        return {
            'first_prompt': 'Unable to parse session',
            'last_prompt': 'Unable to parse session',
            'bmem_summary': None,
        }


def get_activity_status(last_modified: datetime) -> tuple[str, str]:
    """Return (status_emoji, status_text) based on session age."""
    now = datetime.now(timezone.utc)
    age = now - last_modified
    minutes = age.total_seconds() / 60
    hours = age.total_seconds() / 3600
    days = hours / 24

    if minutes < 5:
        return '🟢', 'Active'
    elif hours < 2:
        return '🟡', f'{int(minutes)}m ago'
    elif days < 1:
        return '⚪', f'{int(hours)}h ago'
    else:
        return '⚪', f'{int(days)}d ago'




# Page config
st.set_page_config(page_title="Cognitive Load Dashboard", layout="wide")

# Custom CSS
st.markdown("""
<style>
    /* Dark theme */
    .stApp {
        background-color: #1a1a1a;
        color: #e0e0e0;
    }

    /* Priority tasks - compact list */
    .task-item {
        display: flex;
        align-items: center;
        padding: 6px 12px;
        border-left: 3px solid #ff6b6b;
        margin: 2px 0;
        background: #1a1a1a;
    }

    .task-priority {
        background: #ff6b6b;
        color: #000;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 0.8em;
        font-weight: bold;
        margin-right: 10px;
        min-width: 24px;
        text-align: center;
    }

    .task-title {
        color: #e0e0e0;
        font-size: 0.95em;
    }

    /* Session card - compact */
    .session-card {
        background-color: #0a0a0a;
        border-radius: 6px;
        padding: 10px 12px;
        margin: 6px 0;
        border-left: 3px solid;
    }

    .session-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }

    .session-project {
        font-size: 0.95em;
        font-weight: bold;
    }

    .session-status {
        font-size: 0.8em;
        color: #888;
    }

    .session-prompt {
        color: #888;
        font-size: 0.85em;
        font-style: italic;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin: 2px 0;
    }

    .session-bmem {
        color: #4ecdc4;
        font-size: 0.8em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-top: 4px;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .session-bmem:hover {
        white-space: normal;
        overflow: visible;
        background: #1a1a1a;
        padding: 4px;
        border-radius: 4px;
        z-index: 10;
        position: relative;
    }

    /* Section headers */
    .section-header {
        color: #888;
        font-size: 0.85em;
        letter-spacing: 0.1em;
        margin: 24px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid #333;
    }

    /* Timestamp */
    .timestamp {
        color: #666;
        font-size: 0.8em;
        text-align: right;
        margin-top: 20px;
    }

</style>
""", unsafe_allow_html=True)

# PRIORITY TASKS - Compact list
st.markdown("<div class='section-header'>PRIORITY TASKS</div>", unsafe_allow_html=True)
try:
    focus_tasks = load_focus_tasks(count=5)
    if focus_tasks:
        for task in focus_tasks:
            priority_text = f"P{task.priority}" if task.priority is not None else ""
            st.markdown(f"""
            <div class='task-item'>
                <span class='task-priority'>{priority_text}</span>
                <span class='task-title'>{task.title}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='color: #666; padding: 8px;'>No priority tasks</div>", unsafe_allow_html=True)
except Exception as e:
    st.error(f"Error loading tasks: {e}")

# ACTIVE SESSIONS - Two columns
st.markdown("<div class='section-header'>ACTIVE SESSIONS</div>", unsafe_allow_html=True)

try:
    sessions = find_sessions()
    processor = SessionProcessor()

    # Collect session cards - all sessions in reverse date order
    session_cards = []
    for session in sessions:
        age = datetime.now(timezone.utc) - session.last_modified

        if age.total_seconds() > 86400 * 7:
            continue

        proj = session.project_display
        status_emoji, status_text = get_activity_status(session.last_modified)
        color = get_project_color(proj)
        state = get_session_state(session, processor)

        # Build content: first prompt, last prompt, bmem summary
        content_parts = []
        content_parts.append(f"<div class='session-prompt'><b>Start:</b> \"{state['first_prompt']}\"</div>")
        if state['first_prompt'] != state['last_prompt']:
            content_parts.append(f"<div class='session-prompt'><b>Latest:</b> \"{state['last_prompt']}\"</div>")
        if state['bmem_summary']:
            folder = state['bmem_summary']['folder'].split('/')[-1] if state['bmem_summary']['folder'] else 'notes'
            title = state['bmem_summary']['title']
            preview = state['bmem_summary'].get('preview', '')
            if preview:
                content_parts.append(f"<div class='session-bmem'>📝 {folder}/{title}: {preview}</div>")
            else:
                content_parts.append(f"<div class='session-bmem'>📝 {folder}/{title}</div>")
        content_html = '\n'.join(content_parts)

        session_cards.append(f"""
        <div class='session-card' style='border-left-color: {color};'>
            <div class='session-header'>
                <span class='session-project' style='color: {color};'>{status_emoji} {proj}</span>
                <span class='session-status'>{status_text}</span>
            </div>
            {content_html}
        </div>
        """)

        if len(session_cards) >= 10:
            break

    # Render in two columns
    if session_cards:
        col1, col2 = st.columns(2)
        for i, card in enumerate(session_cards):
            with col1 if i % 2 == 0 else col2:
                st.markdown(card, unsafe_allow_html=True)
    else:
        st.info("No active sessions in last 7 days")

except Exception as e:
    st.error(f"Error loading sessions: {e}")

# Timestamp
st.markdown(f"<div class='timestamp'>Updated: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

# Auto-refresh every 10 seconds
import time
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

current_time = time.time()
if current_time - st.session_state.last_refresh >= 10:
    st.session_state.last_refresh = current_time
    st.rerun()
