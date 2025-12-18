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
from lib.session_analyzer import SessionAnalyzer

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


def get_project_git_activity(project_path: str) -> list[str]:
    """Get recent git commits from project directory."""
    import subprocess
    # Convert project path format: -Users-suzor-src-buttermilk -> /Users/suzor/src/buttermilk
    if project_path.startswith('-'):
        path = '/' + project_path[1:].replace('-', '/')
    else:
        path = project_path

    try:
        result = subprocess.run(
            ['git', 'log', '--oneline', '-3', '--since=24 hours ago'],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[:2]  # Max 2 commits
    except Exception:
        pass
    return []



def get_session_state(session_info, analyzer: SessionAnalyzer) -> dict:
    """Extract current state from a session for display."""
    try:
        state = analyzer.extract_dashboard_state(session_info.path)
        # Return last 3 bmem notes max (matching old behavior)
        if state.get('bmem_notes'):
            state['bmem_notes'] = state['bmem_notes'][-3:]
        return state
    except Exception:
        return {
            'first_prompt': 'Unable to parse session',
            'first_prompt_full': 'Unable to parse session',
            'last_prompt': 'Unable to parse session',
            'todos': None,
            'bmem_notes': [],
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

    .task-item.all-done {
        border-left-color: #22c55e;
        opacity: 0.6;
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
        flex: 1;
    }

    .task-title.all-done {
        text-decoration: line-through;
        color: #888;
    }

    .task-progress {
        font-size: 0.75em;
        color: #4ade80;
        margin-left: 8px;
        white-space: nowrap;
    }

    .task-progress.complete {
        color: #22c55e;
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

    /* Todo items - prominent current work */
    .session-todo {
        font-size: 0.9em;
        padding: 4px 8px;
        border-radius: 4px;
        margin: 3px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .session-todo.in-progress {
        background: #2d4a3e;
        color: #4ade80;
        font-weight: 500;
    }

    .session-todo.pending {
        background: #3d3d1a;
        color: #facc15;
        font-size: 0.8em;
    }

    .session-todo.completed {
        background: #1a3d1a;
        color: #22c55e;
        font-size: 0.8em;
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

    /* Active Now section */
    .active-now-item {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        background: #1a2d1a;
        border-left: 3px solid #4ade80;
        margin: 4px 0;
        border-radius: 0 4px 4px 0;
    }

    .active-now-status {
        margin-right: 10px;
        font-size: 1.1em;
    }

    .active-now-content {
        color: #4ade80;
        font-weight: 500;
        flex: 1;
    }

    .active-now-project {
        color: #888;
        font-size: 0.8em;
        margin-left: 10px;
    }

    /* Git commits */
    .session-git {
        color: #f97316;
        font-size: 0.75em;
        margin-top: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Timestamp */
    .timestamp {
        color: #666;
        font-size: 0.8em;
        text-align: right;
        margin-top: 20px;
    }

    /* Tooltip popup styles */
    .tooltip-container {
        position: relative;
        cursor: pointer;
    }

    .tooltip-container .tooltip-popup {
        visibility: hidden;
        opacity: 0;
        position: absolute;
        left: 0;
        top: 100%;
        z-index: 100;
        background: #2a2a2a;
        border: 1px solid #444;
        border-radius: 6px;
        padding: 10px 12px;
        min-width: 300px;
        max-width: 500px;
        max-height: 400px;
        overflow-y: auto;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        white-space: pre-wrap;
        word-wrap: break-word;
        font-style: normal;
        color: #e0e0e0;
        font-size: 0.9em;
        line-height: 1.4;
        transition: opacity 0.2s ease, visibility 0.2s ease;
    }

    .tooltip-container:hover .tooltip-popup {
        visibility: visible;
        opacity: 1;
    }

    /* Todo items in popup */
    .tooltip-popup .todo-item {
        padding: 4px 0;
        border-bottom: 1px solid #333;
    }

    .tooltip-popup .todo-item:last-child {
        border-bottom: none;
    }

    .tooltip-popup .todo-in-progress {
        color: #4ade80;
    }

    .tooltip-popup .todo-pending {
        color: #facc15;
    }

    .tooltip-popup .todo-completed {
        color: #22c55e;
        text-decoration: line-through;
        opacity: 0.7;
    }

</style>
""", unsafe_allow_html=True)

# Helper to escape HTML
def esc(text):
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

# TODAY'S PROGRESS - Daily note summaries
st.markdown("<div class='section-header'>TODAY'S PROGRESS</div>", unsafe_allow_html=True)
try:
    analyzer = SessionAnalyzer()
    daily_note = analyzer.read_daily_note()
    if daily_note and daily_note.get('sessions'):
        col1, col2 = st.columns(2)
        for i, session in enumerate(daily_note['sessions']):
            project = session.get('project', 'Unknown')
            color = get_project_color(project)
            accomplishments = session.get('accomplishments', [])

            # Build accomplishments list
            acc_items = []
            for acc in accomplishments[:5]:  # Max 5 accomplishments per session
                acc_items.append(f"<div style='color: #4ade80; font-size: 0.85em; padding: 2px 0;'>✓ {esc(acc)}</div>")

            acc_html = '\n'.join(acc_items) if acc_items else "<div style='color: #666; font-size: 0.85em;'>No accomplishments recorded</div>"

            session_html = f"""
            <div class='session-card' style='border-left-color: {color};'>
                <div class='session-header'>
                    <span class='session-project' style='color: {color};'>{esc(project)}</span>
                    <span class='session-status'>{session.get('duration', '')}</span>
                </div>
                {acc_html}
            </div>
            """
            with col1 if i % 2 == 0 else col2:
                st.markdown(session_html, unsafe_allow_html=True)
    else:
        st.markdown("<div style='color: #666; padding: 8px;'>No daily note for today. Run /analyze-session to create one.</div>", unsafe_allow_html=True)
except Exception as e:
    st.error(f"Error loading daily note: {e}")

# ACTIVE PROJECTS - Aggregated by project (includes priority tasks)
st.markdown("<div class='section-header'>ACTIVE PROJECTS</div>", unsafe_allow_html=True)

try:
    sessions = find_sessions()
    analyzer = SessionAnalyzer()

    # Load priority tasks and group by project
    focus_tasks = load_focus_tasks(count=20)
    tasks_by_project: dict[str, list] = {}
    for task in focus_tasks:
        proj = task.project or 'unassigned'
        if proj not in tasks_by_project:
            tasks_by_project[proj] = []
        tasks_by_project[proj].append(task)

    # Group sessions by project
    projects: dict[str, dict] = {}
    for session in sessions:
        age = datetime.now(timezone.utc) - session.last_modified
        if age.total_seconds() > 86400 * 7:
            continue
        if '-tmp' in session.project or '-var-folders' in session.project:
            continue

        proj = session.project_display
        state = get_session_state(session, analyzer)

        if proj not in projects:
            projects[proj] = {
                'last_modified': session.last_modified,
                'todos': [],
                'bmem_notes': [],
                'goals': [],
                'git_project': session.project,
                'session_count': 0
            }

        projects[proj]['session_count'] += 1
        if session.last_modified > projects[proj]['last_modified']:
            projects[proj]['last_modified'] = session.last_modified

        # Aggregate todos (dedupe by content)
        if state['todos']:
            existing = {t.get('content') for t in projects[proj]['todos']}
            for todo in state['todos']:
                if todo.get('content') not in existing:
                    projects[proj]['todos'].append(todo)
                    existing.add(todo.get('content'))

        # Aggregate bmem notes (dedupe by title)
        existing_titles = {n['title'] for n in projects[proj]['bmem_notes']}
        for note in state.get('bmem_notes', []):
            if note['title'] not in existing_titles:
                projects[proj]['bmem_notes'].append(note)
                existing_titles.add(note['title'])

        # Collect goals
        goal = (state.get('first_prompt') or '').strip()
        if goal and len(goal) > 15 and not goal.startswith('<') and 'Expanded:' not in goal:
            if not (goal.startswith('/') and ' ' not in goal[:50]):
                if goal not in projects[proj]['goals']:
                    projects[proj]['goals'].append(goal)

    # Build project cards
    project_cards = []
    for proj, data in sorted(projects.items(), key=lambda x: x[1]['last_modified'], reverse=True):
        status_emoji, status_text = get_activity_status(data['last_modified'])
        color = get_project_color(proj)
        content_parts = []

        # Show aggregated todos
        todos = data['todos']
        if todos:
            in_progress = [t for t in todos if t.get('status') == 'in_progress']
            pending = [t for t in todos if t.get('status') == 'pending']

            for todo in in_progress[:3]:
                content_parts.append(f"<div class='session-todo in-progress'>🔄 {esc(todo.get('activeForm', todo.get('content', '')))}</div>")
            if len(in_progress) > 3:
                content_parts.append(f"<div class='session-todo'>+{len(in_progress)-3} more</div>")
            if pending:
                content_parts.append(f"<div class='session-todo pending'>⏳ {len(pending)} pending</div>")

        # Show recent goal if no todos
        if not content_parts and data['goals']:
            goal = data['goals'][-1][:100]
            content_parts.append(f"<div class='session-prompt'><b>Goal:</b> \"{esc(goal)}\"</div>")

        # Show priority tasks for this project
        project_tasks = tasks_by_project.get(proj, [])
        for task in project_tasks[:3]:
            priority_text = f"P{task.priority}" if task.priority is not None else ""
            progress = ""
            if task.subtasks:
                done = sum(1 for s in task.subtasks if s.completed)
                progress = f" ({done}/{len(task.subtasks)})"
            content_parts.append(f"<div class='task-item'><span class='task-priority'>{priority_text}</span> {esc(task.title)}{progress}</div>")
        if len(project_tasks) > 3:
            content_parts.append(f"<div class='task-item'>+{len(project_tasks)-3} more tasks</div>")

        # Show bmem notes
        for note in data['bmem_notes'][-2:]:
            content_parts.append(f"<div class='session-bmem'>📝 {esc(note['title'])}</div>")

        # Show git activity
        git_commits = get_project_git_activity(data['git_project'])
        if git_commits:
            commits_display = ' | '.join([c[:40] for c in git_commits[:2]])
            content_parts.append(f"<div class='session-git'>📦 {esc(commits_display)}</div>")

        if not content_parts:
            continue

        sessions_label = f"{data['session_count']} session{'s' if data['session_count'] > 1 else ''}"
        content_html = '\n'.join(content_parts)

        project_cards.append(f"""
        <div class='session-card' style='border-left-color: {color};'>
            <div class='session-header'>
                <span class='session-project' style='color: {color};'>{status_emoji} {proj}</span>
                <span class='session-status'>{status_text} · {sessions_label}</span>
            </div>
            {content_html}
        </div>
        """)

        if len(project_cards) >= 10:
            break

    # Add cards for projects with tasks but no sessions
    for proj, tasks in tasks_by_project.items():
        if proj in projects or len(project_cards) >= 10:
            continue
        color = get_project_color(proj)
        content_parts = []
        for task in tasks[:3]:
            priority_text = f"P{task.priority}" if task.priority is not None else ""
            progress = ""
            if task.subtasks:
                done = sum(1 for s in task.subtasks if s.completed)
                progress = f" ({done}/{len(task.subtasks)})"
            content_parts.append(f"<div class='task-item'><span class='task-priority'>{priority_text}</span> {esc(task.title)}{progress}</div>")
        if len(tasks) > 3:
            content_parts.append(f"<div class='task-item'>+{len(tasks)-3} more tasks</div>")
        if content_parts:
            content_html = '\n'.join(content_parts)
            project_cards.append(f"""
            <div class='session-card' style='border-left-color: {color};'>
                <div class='session-header'>
                    <span class='session-project' style='color: {color};'>📋 {proj}</span>
                    <span class='session-status'>{len(tasks)} tasks</span>
                </div>
                {content_html}
            </div>
            """)

    # Render in two columns
    if project_cards:
        col1, col2 = st.columns(2)
        for i, card in enumerate(project_cards):
            with col1 if i % 2 == 0 else col2:
                st.markdown(card, unsafe_allow_html=True)
    else:
        st.info("No active projects in last 7 days")

except Exception as e:
    st.error(f"Error loading projects: {e}")

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
