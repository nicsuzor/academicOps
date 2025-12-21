"""Cognitive Load Dashboard - Session cards + single focus task."""
from __future__ import annotations

import streamlit as st
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
from urllib.parse import quote

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


def make_obsidian_url(title: str, folder: str) -> str:
    """Create obsidian:// URL for a memory note."""
    # Obsidian uses actual title as filename, URL-encoded
    # quote() with safe='' encodes everything including slashes
    file_path = f"data/{folder}/{title}"
    return f"obsidian://open?vault=writing&file={quote(file_path, safe='')}"


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
        # Return last 3 memory notes max (matching old behavior)
        if state.get('memory_notes'):
            state['memory_notes'] = state['memory_notes'][-3:]
        return state
    except Exception:
        return {
            'first_prompt': 'Unable to parse session',
            'first_prompt_full': 'Unable to parse session',
            'last_prompt': 'Unable to parse session',
            'todos': None,
            'memory_notes': [],
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

    .session-memory {
        color: #4ecdc4;
        font-size: 0.8em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-top: 4px;
        cursor: pointer;
        transition: all 0.2s ease;
        text-decoration: none;
        display: block;
    }

    .session-memory:hover {
        color: #7eeee6;
        text-decoration: underline;
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

    /* NOW panel */
    .now-panel {
        background: linear-gradient(135deg, #1a2d1a 0%, #0a1a0a 100%);
        border: 2px solid #4ade80;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
    }

    .now-title {
        color: #4ade80;
        font-size: 1.1em;
        font-weight: bold;
        margin-bottom: 8px;
    }

    .now-action {
        color: #e0e0e0;
        font-size: 1.2em;
        padding-left: 20px;
    }

    .now-action::before {
        content: "→ ";
        color: #4ade80;
    }

    .progress-bar {
        margin-top: 12px;
        height: 8px;
        background: #333;
        border-radius: 4px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #4ade80, #22c55e);
        border-radius: 4px;
        transition: width 0.3s ease;
    }

    .progress-text {
        color: #888;
        font-size: 0.85em;
        margin-top: 4px;
        text-align: right;
    }

    /* Blockers panel */
    .blockers-panel {
        background: linear-gradient(135deg, #2d1a1a 0%, #1a0a0a 100%);
        border: 2px solid #ef4444;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 16px;
    }

    .blockers-title {
        color: #ef4444;
        font-size: 0.95em;
        font-weight: bold;
        margin-bottom: 8px;
    }

    .blocker-item {
        color: #fca5a5;
        font-size: 0.9em;
        padding: 4px 0;
        padding-left: 16px;
    }

    .blocker-item::before {
        content: "• ";
        color: #ef4444;
    }

    /* Done panel */
    .done-panel {
        background: #0a1a0a;
        border: 1px solid #22c55e;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 16px;
    }

    .done-title {
        color: #22c55e;
        font-size: 0.95em;
        font-weight: bold;
        margin-bottom: 8px;
    }

    .done-item {
        color: #86efac;
        font-size: 0.85em;
        padding: 2px 0;
        padding-left: 16px;
    }

    .done-item::before {
        content: "✓ ";
        color: #22c55e;
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

# Initialize analyzer for daily log
analyzer = SessionAnalyzer()

# === NOW PANEL ===
daily_log = analyzer.parse_daily_log()
if daily_log and daily_log.get('primary_title'):
    done, total = daily_log['progress']
    pct = (done / total * 100) if total > 0 else 0

    now_html = f"""
    <div class='now-panel'>
        <div class='now-title'>🎯 NOW: {esc(daily_log['primary_title'])}</div>
    """
    if daily_log.get('next_action'):
        now_html += f"<div class='now-action'>{esc(daily_log['next_action'])}</div>"

    if total > 0:
        now_html += f"""
        <div class='progress-bar'><div class='progress-fill' style='width: {pct}%;'></div></div>
        <div class='progress-text'>Progress: {done}/{total}</div>
        """
    now_html += "</div>"
    st.markdown(now_html, unsafe_allow_html=True)

# === BLOCKERS PANEL ===
if daily_log and daily_log.get('blockers'):
    blockers_html = f"""
    <div class='blockers-panel'>
        <div class='blockers-title'>⚠️ BLOCKERS ({len(daily_log['blockers'])})</div>
    """
    for blocker in daily_log['blockers'][:5]:
        blockers_html += f"<div class='blocker-item'>{esc(blocker[:80])}</div>"
    if len(daily_log['blockers']) > 5:
        blockers_html += f"<div class='blocker-item'>+{len(daily_log['blockers'])-5} more</div>"
    blockers_html += "</div>"
    st.markdown(blockers_html, unsafe_allow_html=True)

# === DONE TODAY PANEL ===
if daily_log:
    # Combine completed tasks and outcomes
    done_items = daily_log.get('completed', []) + daily_log.get('outcomes', [])
    if done_items:
        done_html = f"""
        <div class='done-panel'>
            <div class='done-title'>✅ DONE TODAY ({len(done_items)})</div>
        """
        for item in done_items[:6]:
            # Truncate long items
            display = item[:60] + '...' if len(item) > 60 else item
            done_html += f"<div class='done-item'>{esc(display)}</div>"
        if len(done_items) > 6:
            done_html += f"<div class='done-item' style='color: #888;'>+{len(done_items)-6} more</div>"
        done_html += "</div>"
        st.markdown(done_html, unsafe_allow_html=True)

# PROJECTS - Unified view with all info per project
st.markdown("<div class='section-header'>PROJECTS</div>", unsafe_allow_html=True)

try:
    sessions = find_sessions()
    # analyzer already initialized above for daily log

    # Load daily note accomplishments
    daily_note = analyzer.read_daily_note()
    accomplishments_by_project: dict[str, list] = {}
    if daily_note and daily_note.get('sessions'):
        for session in daily_note['sessions']:
            proj = session.get('project', 'Unknown')
            if proj not in accomplishments_by_project:
                accomplishments_by_project[proj] = []
            accomplishments_by_project[proj].extend(session.get('accomplishments', []))

    # Load priority tasks
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
                'memory_notes': [],
                'git_project': session.project,
                'session_count': 0
            }

        projects[proj]['session_count'] += 1
        if session.last_modified > projects[proj]['last_modified']:
            projects[proj]['last_modified'] = session.last_modified

        # Aggregate memory notes
        existing_titles = {n['title'] for n in projects[proj]['memory_notes']}
        for note in state.get('memory_notes', []):
            if note['title'] not in existing_titles:
                projects[proj]['memory_notes'].append(note)
                existing_titles.add(note['title'])

    # Ensure all projects with tasks or accomplishments are included
    all_projects = set(projects.keys()) | set(tasks_by_project.keys()) | set(accomplishments_by_project.keys())

    # Build project cards
    project_cards = []
    for proj in sorted(all_projects, key=lambda p: projects.get(p, {}).get('last_modified', datetime.min.replace(tzinfo=timezone.utc)), reverse=True):
        data = projects.get(proj, {})
        color = get_project_color(proj)
        content_parts = []

        # 1. Accomplishments from daily note (green checkmarks)
        accomplishments = accomplishments_by_project.get(proj, [])
        for acc in accomplishments[:4]:
            content_parts.append(f"<div style='color: #4ade80; font-size: 0.85em;'>✓ {esc(acc)}</div>")
        if len(accomplishments) > 4:
            content_parts.append(f"<div style='color: #4ade80; font-size: 0.85em;'>+{len(accomplishments)-4} more done</div>")

        # 2. Priority tasks
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

        # 3. memory notes (clickable to open in Obsidian)
        for note in data.get('memory_notes', [])[-2:]:
            obsidian_url = make_obsidian_url(note['title'], note.get('folder', ''))
            content_parts.append(f"<a href='{obsidian_url}' class='session-memory' target='_blank'>📝 {esc(note['title'])}</a>")

        # 4. Git activity
        git_project = data.get('git_project', '')
        if git_project:
            git_commits = get_project_git_activity(git_project)
            if git_commits:
                commits_display = ' | '.join([c[:40] for c in git_commits[:2]])
                content_parts.append(f"<div class='session-git'>📦 {esc(commits_display)}</div>")

        if not content_parts:
            continue

        # Build status line
        session_count = data.get('session_count', 0)
        status_parts = []
        if session_count:
            status_emoji, status_text = get_activity_status(data['last_modified'])
            status_parts.append(f"{status_text}")
            status_parts.append(f"{session_count} session{'s' if session_count > 1 else ''}")
        if project_tasks:
            status_parts.append(f"{len(project_tasks)} tasks")

        status_line = ' · '.join(status_parts) if status_parts else ''
        emoji = status_emoji if session_count else '📋'
        content_html = '\n'.join(content_parts)

        project_cards.append(f"""
        <div class='session-card' style='border-left-color: {color};'>
            <div class='session-header'>
                <span class='session-project' style='color: {color};'>{emoji} {proj}</span>
                <span class='session-status'>{status_line}</span>
            </div>
            {content_html}
        </div>
        """)

        if len(project_cards) >= 12:
            break

    # Render in two columns
    if project_cards:
        col1, col2 = st.columns(2)
        for i, card in enumerate(project_cards):
            with col1 if i % 2 == 0 else col2:
                st.markdown(card, unsafe_allow_html=True)
    else:
        st.info("No active projects")

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
