"""Cognitive Load Dashboard - Session cards + single focus task."""
from __future__ import annotations

import streamlit as st
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sys
import requests
from urllib.parse import quote

# Add aOps root to path for imports
aops_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(aops_root))

from skills.tasks.task_loader import load_focus_tasks
from lib.session_reader import find_sessions
from lib.session_analyzer import SessionAnalyzer, extract_todowrite_from_session


def load_task_index() -> dict | None:
    """Load task index from index.json if available."""
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        return None

    index_path = Path(aca_data) / "tasks" / "index.json"
    if not index_path.exists():
        return None

    try:
        with open(index_path) as f:
            return json.load(f)
    except Exception:
        return None


def load_synthesis() -> dict | None:
    """Load LLM synthesis from synthesis.json.

    Returns:
        Parsed synthesis dict with added '_age_minutes' field, or None if file doesn't exist.
    """
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        return None

    synthesis_path = Path(aca_data) / "dashboard" / "synthesis.json"
    if not synthesis_path.exists():
        return None

    try:
        mtime = synthesis_path.stat().st_mtime
        age_minutes = (datetime.now().timestamp() - mtime) / 60

        with open(synthesis_path) as f:
            data = json.load(f)
            data["_age_minutes"] = age_minutes
            return data
    except Exception:
        return None


def get_waiting_tasks(task_index: dict | None) -> list[dict]:
    """Get tasks with waiting status from index."""
    if not task_index:
        return []

    return [t for t in task_index.get("tasks", []) if t.get("status") == "waiting"]


def get_priority_tasks() -> list[dict]:
    """Get P0/P1 actionable tasks from task index.

    Loads task index from $ACA_DATA/tasks/index.json and filters to
    priority 0 or 1 tasks with non-terminal status (excludes archived,
    done, completed). This includes inbox, pending, active, waiting, etc.

    Returns:
        List of task dicts with keys: title, priority, project, status.
        Returns empty list if task index cannot be loaded.
    """
    task_index = load_task_index()
    if not task_index:
        return []

    tasks = task_index.get("tasks", [])
    result = []

    for t in tasks:
        priority = t.get("priority")
        status = t.get("status")

        # Filter to P0/P1 and non-terminal status
        if priority is None or priority > 1:
            continue
        if status in ("archived", "done", "completed"):
            continue

        result.append(
            {
                "title": t.get("title", ""),
                "priority": priority,
                "project": t.get("project", ""),
                "status": status,
            }
        )

    return result


def get_next_actions(task_index: dict | None) -> list[dict]:
    """Get P0/P1 tasks with incomplete subtasks - the concrete next actions."""
    if not task_index:
        return []

    tasks = task_index.get("tasks", [])

    # Filter to P0/P1 with incomplete work
    actionable = []
    for t in tasks:
        priority = t.get("priority")
        if priority is None or priority > 1:
            continue
        if t.get("status") in ("archived", "done"):
            continue

        # Has incomplete subtasks = has next action
        done = t.get("subtasks_done", 0)
        total = t.get("subtasks_total", 0)
        if total > 0 and done < total:
            actionable.append(t)
        elif total == 0:
            # No subtasks = task itself is the action
            actionable.append(t)

    # Sort by priority, then by completion %
    actionable.sort(
        key=lambda t: (
            t.get("priority", 999),
            t.get("subtasks_done", 0) / max(t.get("subtasks_total", 1), 1),
        )
    )

    return actionable[:5]  # Top 5


# Project color scheme (matching Peacock)
PROJECT_COLORS = {
    "aops": "#00ff88",  # Green
    "writing": "#bb86fc",  # Purple
    "buttermilk": "#f5deb3",  # Butter yellow
}
DEFAULT_COLOR = "#ffb000"  # Amber for unknown projects


def get_primary_focus() -> dict:
    """Get the primary focus task for prominent dashboard display.

    Checks in order:
    1. Daily log primary task
    2. synthesis.json next_action (if fresh)
    3. First P0 task from task index

    Returns:
        Dict with keys:
            - task_title: The primary task title (str)
            - source: One of 'daily_log', 'synthesis', 'task_index', 'none'
    """
    from lib.session_analyzer import SessionAnalyzer

    # Try daily log first
    analyzer = SessionAnalyzer()
    daily_log = analyzer.parse_daily_log()
    if daily_log is not None and daily_log["primary_title"] is not None:
        return {
            "task_title": daily_log["primary_title"],
            "source": "daily_log",
        }

    # Fall back to synthesis.json
    synthesis = load_synthesis()
    if synthesis is not None:
        next_action = synthesis.get("next_action")
        if next_action is not None:
            task = next_action.get("task")
            if task is not None and task != "":
                return {
                    "task_title": task,
                    "source": "synthesis",
                }

    # Fallback to first P0 task
    priority_tasks = get_priority_tasks()
    p0_tasks = [t for t in priority_tasks if t["priority"] == 0]
    if p0_tasks:
        return {"task_title": p0_tasks[0]["title"], "source": "task_index"}

    # No primary focus found
    return {
        "task_title": "",
        "source": "none",
    }


def get_session_display_info(
    session_info: "SessionInfo",
    analyzer: SessionAnalyzer | None = None,
) -> dict:
    """Extract displayable session identity from SessionInfo.

    Enables users to distinguish between multiple terminal sessions (AC-U1).

    Args:
        session_info: SessionInfo object from lib/session_reader.py
        analyzer: Optional SessionAnalyzer to extract activity context

    Returns:
        Dict with keys:
            - session_id_short: First 7 characters of session UUID
            - project: Project name from the session
            - last_activity: Timestamp of last session activity (datetime)
            - activity: Description of session activity (truncated to 50 chars)

    Raises:
        ValueError: If session_info is None or session_id is None
    """
    if session_info is None:
        raise ValueError("session_info cannot be None")
    if session_info.session_id is None:
        raise ValueError("session_info.session_id cannot be None")

    # Extract activity from session if analyzer provided
    activity = ""
    if analyzer is not None:
        try:
            state = analyzer.extract_dashboard_state(session_info.path)
            # Use first_prompt as activity description, truncate to 50 chars
            prompt = state.get("first_prompt", "") or state.get("last_prompt", "")
            if prompt:
                activity = prompt[:50]
                if len(prompt) > 50:
                    activity += "..."
        except Exception:
            activity = ""

    return {
        "session_id_short": session_info.session_id[:7],
        "project": session_info.project,
        "last_activity": session_info.last_modified,
        "activity": activity,
    }


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
    if project_path.startswith("-"):
        path = "/" + project_path[1:].replace("-", "/")
    else:
        path = project_path

    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-3", "--since=24 hours ago"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")[:2]  # Max 2 commits
    except Exception:
        pass
    return []


def get_todays_accomplishments() -> list[dict]:
    """Get unified list of today's accomplishments from all sources.

    Aggregates accomplishments from:
    - Daily log completed tasks (source='daily_log')
    - Daily log outcomes (source='outcome')
    - Git commits from known project repos (source='git')

    Returns:
        List of dicts, each with:
            - description: What was accomplished (str)
            - source: One of 'daily_log', 'outcome', 'git' (str)
            - project: Project name for grouping (str)
            - timestamp: When it happened (datetime or None)
    """
    accomplishments: list[dict] = []

    # Get daily log data
    analyzer = SessionAnalyzer()
    daily_log = analyzer.parse_daily_log()

    if daily_log is not None:
        # Add completed tasks from daily log
        for item in daily_log.get("completed", []):
            if item:  # Skip empty strings
                accomplishments.append(
                    {
                        "description": item,
                        "source": "daily_log",
                        "project": "general",
                        "timestamp": None,
                    }
                )

        # Add outcomes from daily log
        for item in daily_log.get("outcomes", []):
            if item:  # Skip empty strings
                accomplishments.append(
                    {
                        "description": item,
                        "source": "outcome",
                        "project": "general",
                        "timestamp": None,
                    }
                )

    # Add git commits from known project directories
    project_paths = [
        ("-Users-suzor-writing-academicOps", "academicOps"),
        ("-Users-suzor-writing", "writing"),
        ("-Users-suzor-src-buttermilk", "buttermilk"),
    ]

    for path_key, project_name in project_paths:
        git_commits = get_project_git_activity(path_key)
        for commit in git_commits:
            if commit:  # Skip empty strings
                accomplishments.append(
                    {
                        "description": commit,
                        "source": "git",
                        "project": project_name,
                        "timestamp": None,
                    }
                )

    return accomplishments


def get_dashboard_layout() -> dict:
    """Get structured dashboard data organized by the three core questions.

    Aggregates data from multiple sources into a layout suitable for
    dashboard rendering:
    - What to do: Primary focus and priority tasks
    - What doing: Currently active sessions (max 10, last 24 hours)
    - What done: Today's accomplishments

    Returns:
        Dict with three keys:
            - what_to_do: dict with 'primary_focus' and 'priority_tasks'
            - what_doing: dict with 'active_sessions' (list of session display dicts)
            - what_done: dict with 'accomplishments'
    """
    # Gather data from existing functions
    primary_focus = get_primary_focus()
    priority_tasks = get_priority_tasks()
    accomplishments = get_todays_accomplishments()

    # Get active sessions (last 24 hours, max 10)
    sessions = find_sessions()
    active_sessions: list[dict] = []
    now = datetime.now(timezone.utc)
    analyzer = SessionAnalyzer()

    for session in sessions:
        age = now - session.last_modified
        # Only include sessions from last 24 hours
        if age.total_seconds() > 86400:
            continue
        # Skip temp directories
        if "-tmp" in session.project or "-var-folders" in session.project:
            continue

        session_display = get_session_display_info(session, analyzer)
        active_sessions.append(session_display)

        # Limit to 10 sessions to avoid overwhelm
        if len(active_sessions) >= 10:
            break

    return {
        "what_to_do": {
            "primary_focus": primary_focus,
            "priority_tasks": priority_tasks,
        },
        "what_doing": {
            "active_sessions": active_sessions,
        },
        "what_done": {
            "accomplishments": accomplishments,
        },
    }


def get_session_state(session_info, analyzer: SessionAnalyzer) -> dict:
    """Extract current state from a session for display."""
    try:
        state = analyzer.extract_dashboard_state(session_info.path)
        # Return last 3 memory notes max (matching old behavior)
        if state.get("memory_notes"):
            state["memory_notes"] = state["memory_notes"][-3:]
        return state
    except Exception:
        return {
            "first_prompt": "Unable to parse session",
            "first_prompt_full": "Unable to parse session",
            "last_prompt": "Unable to parse session",
            "todos": None,
            "memory_notes": [],
        }


def get_activity_status(last_modified: datetime) -> tuple[str, str]:
    """Return (status_emoji, status_text) based on session age."""
    now = datetime.now(timezone.utc)
    age = now - last_modified
    minutes = age.total_seconds() / 60
    hours = age.total_seconds() / 3600
    days = hours / 24

    if minutes < 5:
        return "🟢", "Active"
    elif hours < 2:
        return "🟡", f"{int(minutes)}m ago"
    elif days < 1:
        return "⚪", f"{int(hours)}h ago"
    else:
        return "⚪", f"{int(days)}d ago"


def fetch_cross_machine_prompts() -> list[dict]:
    """Fetch recent prompts from Cloudflare R2 endpoint."""
    api_key = os.environ.get("PROMPT_LOG_API_KEY")
    if not api_key:
        return []

    try:
        response = requests.get(
            "https://prompt-logs.nicsuzor.workers.dev/read",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5,
        )
        if response.status_code != 200:
            return []

        prompts = response.json()

        # Parse JSON content from each prompt
        parsed = []
        for p in prompts:
            try:
                content = p.get("content", "")
                if content.startswith("{"):
                    data = json.loads(content)
                    data["raw_timestamp"] = p.get("timestamp", "")
                    parsed.append(data)
                else:
                    # Plain text prompt (legacy)
                    parsed.append(
                        {
                            "prompt": content,
                            "hostname": "unknown",
                            "project": "unknown",
                            "raw_timestamp": p.get("timestamp", ""),
                        }
                    )
            except json.JSONDecodeError:
                pass

        # Sort by timestamp descending (most recent first)
        parsed.sort(key=lambda x: x.get("raw_timestamp", ""), reverse=True)
        return parsed[:20]  # Last 20 prompts
    except Exception:
        return []


def group_prompts_by_machine(prompts: list[dict]) -> dict[str, list[dict]]:
    """Group prompts by hostname."""
    grouped: dict[str, list[dict]] = {}
    for p in prompts:
        hostname = p.get("hostname", "unknown")
        if hostname not in grouped:
            grouped[hostname] = []
        grouped[hostname].append(p)
    return grouped


# Cache for session activity (60s TTL)
_session_activity_cache: dict = {"data": None, "timestamp": 0}


def fetch_session_activity(hours: int = 2) -> list[dict]:
    """Fetch active sessions with prompts from R2 and TodoWrite from local JSONL.

    Combines cross-machine prompt data from R2 with local session TodoWrite state.
    For local sessions, includes the current in_progress task.

    Args:
        hours: How far back to look for activity (default 2 hours)

    Returns:
        List of session activity dicts with keys:
            - session_id: Full session UUID
            - session_short: First 7 chars for display
            - hostname: Machine name
            - project: Project/repo name
            - last_prompt: Most recent user prompt (truncated)
            - timestamp: ISO timestamp of last activity
            - time_ago: Human-readable time since activity
            - todowrite: TodoWriteState or None for local sessions
    """
    import time
    from datetime import timedelta

    # Check cache (60s TTL)
    now = time.time()
    if (
        _session_activity_cache["data"]
        and (now - _session_activity_cache["timestamp"]) < 60
    ):
        return _session_activity_cache["data"]

    # Fetch R2 prompts
    r2_prompts = fetch_cross_machine_prompts()

    # Build session map from R2 data (most recent prompt per session)
    sessions: dict[str, dict] = {}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    for p in r2_prompts:
        session_id = p.get("session_id", "")
        if not session_id:
            continue

        # Parse timestamp and filter by cutoff
        try:
            ts_str = p.get("timestamp") or p.get("raw_timestamp", "")
            if ts_str:
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                ts = datetime.fromisoformat(ts_str)
                if ts < cutoff:
                    continue
        except (ValueError, TypeError):
            continue

        # Keep most recent per session
        if session_id not in sessions:
            sessions[session_id] = {
                "session_id": session_id,
                "session_short": session_id[:7],
                "hostname": p.get("hostname", "unknown"),
                "project": p.get("project", "unknown"),
                "last_prompt": p.get("prompt", "")[:100],
                "timestamp": ts_str,
                "time_ago": _format_time_ago(ts),
                "todowrite": None,
            }

    # Try to find local JSONL for each session and extract TodoWrite
    claude_projects = Path.home() / ".claude" / "projects"
    if claude_projects.exists():
        for session_id, session_data in sessions.items():
            # Search for session file
            for project_dir in claude_projects.iterdir():
                if not project_dir.is_dir():
                    continue
                session_file = project_dir / f"{session_id}.jsonl"
                if session_file.exists():
                    todowrite = extract_todowrite_from_session(session_file)
                    session_data["todowrite"] = todowrite
                    break

    # Sort by timestamp descending
    result = sorted(
        sessions.values(), key=lambda x: x.get("timestamp", ""), reverse=True
    )

    # Update cache
    _session_activity_cache["data"] = result
    _session_activity_cache["timestamp"] = now

    return result


def _format_time_ago(dt: datetime) -> str:
    """Format datetime as human-readable time ago string."""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    else:
        days = int(seconds / 86400)
        return f"{days}d ago"


def group_sessions_by_project(sessions: list[dict]) -> dict[str, list[dict]]:
    """Group session activity by project for display."""
    grouped: dict[str, list[dict]] = {}
    for s in sessions:
        project = s.get("project", "unknown")
        if project not in grouped:
            grouped[project] = []
        grouped[project].append(s)
    return grouped


# Page config
st.set_page_config(page_title="Cognitive Load Dashboard", layout="wide")

# Custom CSS
st.markdown(
    """
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

    /* Cross-machine activity panel */
    .cross-machine-panel {
        background: linear-gradient(135deg, #1a1a2d 0%, #0a0a1a 100%);
        border: 1px solid #6366f1;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 16px;
    }

    .cross-machine-title {
        color: #a5b4fc;
        font-size: 0.95em;
        font-weight: bold;
        margin-bottom: 10px;
    }

    .machine-group {
        margin-bottom: 12px;
        padding-left: 8px;
        border-left: 2px solid #4f46e5;
    }

    .machine-name {
        color: #818cf8;
        font-size: 0.85em;
        font-weight: bold;
        margin-bottom: 4px;
    }

    .machine-prompt {
        color: #94a3b8;
        font-size: 0.8em;
        padding: 2px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .machine-prompt-project {
        color: #6366f1;
        font-size: 0.75em;
    }

    /* Active Sessions panel */
    .active-sessions-panel {
        background: linear-gradient(135deg, #1a1a2d 0%, #0a0a1a 100%);
        border: 1px solid #6366f1;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 16px;
    }

    .active-sessions-title {
        color: #a5b4fc;
        font-size: 0.95em;
        font-weight: bold;
        margin-bottom: 10px;
    }

    .session-card {
        margin-bottom: 12px;
        padding: 8px 12px;
        background: rgba(99, 102, 241, 0.1);
        border-left: 3px solid #4f46e5;
        border-radius: 0 4px 4px 0;
    }

    .session-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
    }

    .session-id {
        font-family: monospace;
        color: #818cf8;
        font-size: 0.8em;
        background: rgba(99, 102, 241, 0.2);
        padding: 2px 6px;
        border-radius: 3px;
    }

    .session-meta {
        color: #64748b;
        font-size: 0.75em;
    }

    .session-prompt {
        color: #94a3b8;
        font-size: 0.85em;
        padding: 4px 0;
        font-style: italic;
    }

    .session-todo {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 4px 0;
    }

    .session-todo-active {
        color: #22c55e;
        font-size: 0.85em;
    }

    .session-todo-pending {
        color: #64748b;
        font-size: 0.8em;
    }

    /* What Now panel - synthesized status */
    .what-now-panel {
        background: linear-gradient(135deg, #1a1a2d 0%, #0d0d1a 100%);
        border: 2px solid #8b5cf6;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
    }

    .what-now-title {
        color: #a78bfa;
        font-size: 1.1em;
        font-weight: bold;
        margin-bottom: 12px;
    }

    .what-now-section {
        margin-bottom: 12px;
    }

    .what-now-section-title {
        color: #7c3aed;
        font-size: 0.85em;
        font-weight: bold;
        margin-bottom: 4px;
    }

    .what-now-item {
        color: #c4b5fd;
        font-size: 0.9em;
        padding: 4px 0 4px 16px;
        border-left: 2px solid #6d28d9;
        margin: 2px 0;
    }

    .what-now-item.action {
        color: #a78bfa;
        border-left-color: #8b5cf6;
    }

    .what-now-item.waiting {
        color: #fbbf24;
        border-left-color: #d97706;
    }

    .what-now-progress {
        font-size: 0.75em;
        color: #6d28d9;
        margin-left: 8px;
    }

    /* LLM Synthesis panels */
    .synthesis-panel {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        border: 2px solid #6366f1;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }

    .synthesis-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }

    .synthesis-title {
        color: #a5b4fc;
        font-size: 1.2em;
        font-weight: bold;
    }

    .synthesis-age {
        color: #64748b;
        font-size: 0.75em;
    }

    .synthesis-next {
        background: linear-gradient(135deg, #312e81 0%, #1e1b4b 100%);
        border-left: 4px solid #818cf8;
        padding: 12px 16px;
        margin-bottom: 12px;
        border-radius: 0 8px 8px 0;
    }

    .synthesis-next-label {
        color: #818cf8;
        font-size: 0.8em;
        font-weight: bold;
        margin-bottom: 4px;
    }

    .synthesis-next-task {
        color: #e0e7ff;
        font-size: 1.1em;
        font-weight: 600;
    }

    .synthesis-next-reason {
        color: #94a3b8;
        font-size: 0.85em;
        margin-top: 6px;
        font-style: italic;
    }

    .synthesis-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }

    .synthesis-card {
        background: rgba(30, 27, 75, 0.5);
        border-radius: 8px;
        padding: 12px;
    }

    .synthesis-card-title {
        font-size: 0.75em;
        font-weight: bold;
        margin-bottom: 6px;
    }

    .synthesis-card-content {
        font-size: 0.85em;
    }

    .synthesis-card.done .synthesis-card-title { color: #4ade80; }
    .synthesis-card.done .synthesis-card-content { color: #86efac; }

    .synthesis-card.alignment .synthesis-card-title { color: #fbbf24; }
    .synthesis-card.alignment .synthesis-card-content { color: #fde68a; }
    .synthesis-card.alignment.on_track .synthesis-card-title { color: #4ade80; }
    .synthesis-card.alignment.on_track .synthesis-card-content { color: #86efac; }
    .synthesis-card.alignment.blocked .synthesis-card-title { color: #f87171; }
    .synthesis-card.alignment.blocked .synthesis-card-content { color: #fca5a5; }

    .synthesis-card.context .synthesis-card-title { color: #60a5fa; }
    .synthesis-card.context .synthesis-card-content { color: #93c5fd; }

    .synthesis-card.waiting .synthesis-card-title { color: #f87171; }
    .synthesis-card.waiting .synthesis-card-content { color: #fca5a5; }

    .synthesis-card.insights .synthesis-card-title { color: #38bdf8; }
    .synthesis-card.insights .synthesis-card-content { color: #7dd3fc; }

    .insights-panel {
        background: linear-gradient(135deg, #0c1929 0%, #0f172a 100%);
        border: 1px solid #0ea5e9;
        border-radius: 8px;
        padding: 12px 16px;
        margin-top: 12px;
    }

    .insights-title {
        color: #38bdf8;
        font-size: 0.9em;
        font-weight: bold;
        margin-bottom: 8px;
    }

    .insights-stat {
        display: inline-block;
        background: rgba(14, 165, 233, 0.15);
        padding: 4px 10px;
        border-radius: 4px;
        margin: 2px 4px 2px 0;
        font-size: 0.8em;
    }

    .insights-stat-label {
        color: #7dd3fc;
    }

    .insights-stat-value {
        color: #f0f9ff;
        font-weight: bold;
    }

    .insights-gap {
        color: #fbbf24;
        font-size: 0.8em;
        padding: 2px 0;
        padding-left: 12px;
    }

    .insights-gap::before {
        content: "⚠ ";
        color: #f59e0b;
    }

    .synthesis-suggestion {
        background: rgba(99, 102, 241, 0.2);
        border-radius: 6px;
        padding: 10px 12px;
        margin-top: 12px;
        color: #a5b4fc;
        font-size: 0.85em;
    }

    .synthesis-suggestion::before {
        content: "💡 ";
    }

    /* Project cards - integrated with synthesis panel */
    .project-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-top: 16px;
    }

    .project-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        border: 1px solid #4f46e5;
        border-radius: 8px;
        padding: 12px 14px;
    }

    .project-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        padding-bottom: 6px;
        border-bottom: 1px solid rgba(99, 102, 241, 0.3);
    }

    .project-card-name {
        font-size: 0.95em;
        font-weight: bold;
    }

    .project-card-meta {
        color: #64748b;
        font-size: 0.75em;
    }

    .project-task {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 4px 0;
        font-size: 0.85em;
        color: #e0e7ff;
    }

    .project-task-priority {
        background: #4f46e5;
        color: #fff;
        padding: 1px 5px;
        border-radius: 3px;
        font-size: 0.75em;
        font-weight: bold;
        flex-shrink: 0;
    }

    .project-task-priority.p0 { background: #ef4444; }
    .project-task-priority.p1 { background: #f97316; }
    .project-task-priority.p2 { background: #6366f1; }

    .project-done {
        color: #4ade80;
        font-size: 0.8em;
        padding: 2px 0;
    }

    .project-done::before {
        content: "✓ ";
    }

    /* Narrative section - day's story */
    .synthesis-narrative {
        background: rgba(139, 92, 246, 0.15);
        border-left: 3px solid #a78bfa;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 16px;
    }

    .synthesis-narrative-title {
        color: #c4b5fd;
        font-weight: 600;
        font-size: 0.9em;
        margin-bottom: 8px;
        letter-spacing: 0.5px;
    }

    .synthesis-narrative-list {
        margin: 0;
        padding-left: 20px;
        color: #e9d5ff;
        font-size: 0.9em;
        line-height: 1.6;
    }

    .synthesis-narrative-list li {
        margin-bottom: 4px;
    }

</style>
""",
    unsafe_allow_html=True,
)


# Helper to escape HTML
def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def clean_activity_text(raw_text: str) -> str:
    """Clean raw session prompt for display.

    Strips markdown formatting to produce a clean summary suitable for dashboard.

    Args:
        raw_text: Raw prompt text potentially containing markdown headers and formatting.

    Returns:
        Cleaned text, max 60 characters, with "..." suffix if truncated.
    """
    if not raw_text:
        return "Working..."

    # Remove markdown headers (lines starting with #)
    lines = [line for line in raw_text.split("\n") if not line.strip().startswith("#")]

    # Join remaining lines and remove markdown formatting
    text = " ".join(lines)
    text = text.replace("**", "").replace("*", "").strip()

    # Collapse multiple spaces
    while "  " in text:
        text = text.replace("  ", " ")

    # Take first 60 chars
    if len(text) > 60:
        text = text[:57] + "..."

    return text if text else "Working..."


# ============================================================================
# UNIFIED FOCUS DASHBOARD - Single glanceable view
# ============================================================================

# Initialize analyzer for daily log
analyzer = SessionAnalyzer()

# Load task index and synthesis
task_index = load_task_index()
synthesis = load_synthesis()

# === LLM SYNTHESIS PANEL (if available) ===
if synthesis:
    # Calculate age and staleness
    age_minutes = synthesis.get("_age_minutes", 0)
    age_str = f"{int(age_minutes)}m ago"
    is_stale = age_minutes > 60

    # Stale indicator styling
    stale_class = "stale" if is_stale else ""
    stale_badge = " <span style='background: #f59e0b; color: #000; padding: 2px 6px; border-radius: 3px; font-size: 0.7em; margin-left: 8px;'>STALE - re-run /session-insights</span>" if is_stale else ""

    synth_html = "<div class='synthesis-panel'>"
    synth_html += f"<div class='synthesis-header'><div class='synthesis-title'>🧠 FOCUS SYNTHESIS{stale_badge}</div><div class='synthesis-age'>{age_str}</div></div>"

    # Narrative section - tell the day's story
    narrative = synthesis.get("narrative", [])
    if narrative:
        synth_html += "<div class='synthesis-narrative'>"
        synth_html += "<div class='synthesis-narrative-title'>📖 TODAY'S STORY</div>"
        synth_html += "<ul class='synthesis-narrative-list'>"
        for bullet in narrative:
            synth_html += f"<li>{esc(bullet)}</li>"
        synth_html += "</ul></div>"

    # Grid of status cards
    synth_html += "<div class='synthesis-grid'>"

    # Done card
    accomplishments = synthesis.get("accomplishments", {})
    if accomplishments.get("summary"):
        synth_html += "<div class='synthesis-card done'>"
        synth_html += f"<div class='synthesis-card-title'>✅ DONE ({accomplishments.get('count', 0)})</div>"
        synth_html += f"<div class='synthesis-card-content'>{esc(accomplishments.get('summary', ''))}</div>"
        synth_html += "</div>"

    # Alignment card
    alignment = synthesis.get("alignment", {})
    if alignment.get("note"):
        status = alignment.get("status", "drifted")
        status_class = f"alignment {status}"
        status_icon = (
            "✅" if status == "on_track" else "⚠️" if status == "drifted" else "🚫"
        )
        synth_html += f"<div class='synthesis-card {status_class}'>"
        synth_html += f"<div class='synthesis-card-title'>{status_icon} ALIGNMENT</div>"
        synth_html += f"<div class='synthesis-card-content'>{esc(alignment.get('note', ''))}</div>"
        synth_html += "</div>"

    # Context card
    context = synthesis.get("context", {})
    if context.get("recent_threads"):
        threads = ", ".join(context.get("recent_threads", [])[:2])
        synth_html += "<div class='synthesis-card context'>"
        synth_html += "<div class='synthesis-card-title'>📍 CONTEXT</div>"
        synth_html += f"<div class='synthesis-card-content'>{esc(threads)}</div>"
        synth_html += "</div>"

    # Waiting card
    waiting_on = synthesis.get("waiting_on", [])
    if waiting_on:
        first_blocker = waiting_on[0]
        synth_html += "<div class='synthesis-card waiting'>"
        synth_html += (
            f"<div class='synthesis-card-title'>⏳ BLOCKED ({len(waiting_on)})</div>"
        )
        synth_html += f"<div class='synthesis-card-content'>{esc(first_blocker.get('task', ''))}</div>"
        synth_html += "</div>"

    synth_html += "</div>"  # End grid

    # Session Insights panel (skill compliance, context gaps)
    skill_insights = synthesis.get("skill_insights", {})
    if skill_insights:
        synth_html += "<div class='insights-panel'>"
        synth_html += "<div class='insights-title'>🔍 SESSION INSIGHTS</div>"

        # Stats row
        compliance = skill_insights.get("compliance_rate")
        if compliance is not None:
            pct = int(compliance * 100)
            color = "#4ade80" if pct >= 70 else "#fbbf24" if pct >= 40 else "#f87171"
            synth_html += f"<span class='insights-stat'><span class='insights-stat-label'>Skill Compliance:</span> <span class='insights-stat-value' style='color: {color};'>{pct}%</span></span>"

        corrections = skill_insights.get("corrections_count", 0)
        if corrections > 0:
            synth_html += f"<span class='insights-stat'><span class='insights-stat-label'>Corrections:</span> <span class='insights-stat-value'>{corrections}</span></span>"

        failures = skill_insights.get("failures_count", 0)
        if failures > 0:
            synth_html += f"<span class='insights-stat'><span class='insights-stat-label'>Failures:</span> <span class='insights-stat-value' style='color: #f87171;'>{failures}</span></span>"

        successes = skill_insights.get("successes_count", 0)
        if successes > 0:
            synth_html += f"<span class='insights-stat'><span class='insights-stat-label'>Successes:</span> <span class='insights-stat-value' style='color: #4ade80;'>{successes}</span></span>"

        # Context gaps
        context_gaps = skill_insights.get("top_context_gaps", [])
        if context_gaps:
            synth_html += "<div style='margin-top: 8px;'>"
            for gap in context_gaps[:3]:
                synth_html += f"<div class='insights-gap'>{esc(gap)}</div>"
            synth_html += "</div>"

        synth_html += "</div>"

    # Suggestion
    suggestion = synthesis.get("suggestion")
    if suggestion:
        synth_html += f"<div class='synthesis-suggestion'>{esc(suggestion)}</div>"

    synth_html += "</div>"  # End panel
    st.markdown(synth_html, unsafe_allow_html=True)

# Check for blockers from daily log
daily_log = analyzer.parse_daily_log()
has_blockers = daily_log and daily_log.get("blockers")

# === PROJECTS (integrated into dashboard) ===

try:
    sessions = find_sessions()
    # analyzer already initialized above for daily log

    # Load daily note accomplishments
    daily_note = analyzer.read_daily_note()
    accomplishments_by_project: dict[str, list] = {}
    if daily_note and daily_note.get("sessions"):
        for session in daily_note["sessions"]:
            proj = session.get("project", "Unknown")
            if proj not in accomplishments_by_project:
                accomplishments_by_project[proj] = []
            accomplishments_by_project[proj].extend(session.get("accomplishments", []))

    # Load priority tasks
    focus_tasks = load_focus_tasks(count=20)
    tasks_by_project: dict[str, list] = {}
    for task in focus_tasks:
        proj = task.project or "unassigned"
        if proj not in tasks_by_project:
            tasks_by_project[proj] = []
        tasks_by_project[proj].append(task)

    # Group sessions by project
    projects: dict[str, dict] = {}
    for session in sessions:
        age = datetime.now(timezone.utc) - session.last_modified
        if age.total_seconds() > 86400 * 7:
            continue
        if "-tmp" in session.project or "-var-folders" in session.project:
            continue

        proj = session.project_display
        state = get_session_state(session, analyzer)

        if proj not in projects:
            projects[proj] = {
                "last_modified": session.last_modified,
                "memory_notes": [],
                "git_project": session.project,
                "session_count": 0,
            }

        projects[proj]["session_count"] += 1
        if session.last_modified > projects[proj]["last_modified"]:
            projects[proj]["last_modified"] = session.last_modified

        # Aggregate memory notes
        existing_titles = {n["title"] for n in projects[proj]["memory_notes"]}
        for note in state.get("memory_notes", []):
            if note["title"] not in existing_titles:
                projects[proj]["memory_notes"].append(note)
                existing_titles.add(note["title"])

    # Ensure all projects with tasks or accomplishments are included
    all_projects = (
        set(projects.keys())
        | set(tasks_by_project.keys())
        | set(accomplishments_by_project.keys())
    )

    # Build project cards with synthesis-matching style
    project_cards = []
    for proj in sorted(
        all_projects,
        key=lambda p: (
            # Sort by: has tasks first, then by last modified
            -len(tasks_by_project.get(p, [])),
            projects.get(p, {}).get(
                "last_modified", datetime.min.replace(tzinfo=timezone.utc)
            ),
        ),
        reverse=True,
    ):
        data = projects.get(proj, {})
        color = get_project_color(proj)
        project_tasks = tasks_by_project.get(proj, [])
        accomplishments = accomplishments_by_project.get(proj, [])

        # Skip projects with no tasks and no accomplishments
        if not project_tasks and not accomplishments:
            continue

        # Build card content - tasks first (what to do), then accomplishments (what done)
        content_parts = []

        # Priority tasks - the core focus
        for task in project_tasks[:4]:
            priority = task.priority if task.priority is not None else 9
            priority_class = f"p{priority}" if priority <= 2 else ""
            priority_text = f"P{priority}" if priority <= 2 else ""
            progress = ""
            if task.subtasks:
                done = sum(1 for s in task.subtasks if s.completed)
                progress = f" <span style='color: #64748b;'>({done}/{len(task.subtasks)})</span>"
            content_parts.append(
                f"<div class='project-task'><span class='project-task-priority {priority_class}'>{priority_text}</span>{esc(task.title)}{progress}</div>"
            )
        if len(project_tasks) > 4:
            content_parts.append(
                f"<div style='color: #64748b; font-size: 0.8em;'>+{len(project_tasks)-4} more tasks</div>"
            )

        # Accomplishments - compact at bottom
        if accomplishments:
            for acc in accomplishments[:2]:
                content_parts.append(f"<div class='project-done'>{esc(acc[:60])}</div>")
            if len(accomplishments) > 2:
                content_parts.append(
                    f"<div class='project-done'>+{len(accomplishments)-2} more</div>"
                )

        # Build status line
        session_count = data.get("session_count", 0)
        status_parts = []
        if session_count:
            status_emoji, status_text = get_activity_status(data["last_modified"])
            status_parts.append(status_text)
        if project_tasks:
            status_parts.append(f"{len(project_tasks)} tasks")
        if accomplishments:
            status_parts.append(f"{len(accomplishments)} done")

        status_line = " · ".join(status_parts) if status_parts else ""
        content_html = "\n".join(content_parts)

        project_cards.append(
            f"""<div class='project-card' style='border-color: {color};'>
            <div class='project-card-header'>
                <span class='project-card-name' style='color: {color};'>{proj}</span>
                <span class='project-card-meta'>{status_line}</span>
            </div>
            {content_html}
        </div>"""
        )

        if len(project_cards) >= 8:
            break

    # Render as grid (integrated with synthesis panel styling)
    if project_cards:
        grid_html = "<div class='project-grid'>" + "\n".join(project_cards) + "</div>"
        st.markdown(grid_html, unsafe_allow_html=True)
    else:
        st.info("No active projects with tasks")

except Exception as e:
    st.error(f"Error loading projects: {e}")

# Timestamp
st.markdown(
    f"<div class='timestamp'>Updated: {datetime.now().strftime('%H:%M:%S')}</div>",
    unsafe_allow_html=True,
)

# Auto-refresh every 5 minutes
import time

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

current_time = time.time()
if current_time - st.session_state.last_refresh >= 300:
    st.session_state.last_refresh = current_time
    st.rerun()
