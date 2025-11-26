"""Cognitive Load Dashboard - Live task and activity monitoring."""
from __future__ import annotations

import streamlit as st
from datetime import datetime
from pathlib import Path
import json
import os
from skills.tasks.task_loader import load_focus_tasks


def load_recent_activity(limit: int = 50) -> list[dict]:
    """Load recent activity from activity.jsonl log.

    Args:
        limit: Maximum number of activity entries to return

    Returns:
        List of activity dicts, newest first. Empty list if file doesn't exist.
    """
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        return []

    activity_file = Path(aca_data) / "logs" / "activity.jsonl"
    if not activity_file.exists():
        return []

    activities = []
    with open(activity_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                activities.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

    # Return newest first (reverse order), limited
    return list(reversed(activities))[:limit]

# Page config
st.set_page_config(page_title="Cognitive Load Dashboard", layout="wide")

# Custom CSS - Solari flip-board airport display aesthetic
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    /* Global font - monospaced for flip-board feel */
    * {
        font-family: 'Courier New', Monaco, Consolas, monospace !important;
    }

    /* Dark theme with amber terminal colors */
    .stApp {
        background-color: #1a1a1a;
        color: #ffb000;
    }

    /* Header styling */
    h1, h2, h3 {
        color: #ffb000 !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    /* Task container - flip-board style */
    .task-container {
        background-color: #0a0a0a;
        border: 2px solid #ffb000;
        border-radius: 4px;
        padding: 16px;
        margin: 12px 0;
        box-shadow: 0 0 10px rgba(255, 176, 0, 0.3);
    }

    /* Priority badges with Font Awesome */
    .priority-badge {
        display: inline-block;
        padding: 4px 12px;
        margin-right: 8px;
        border: 1px solid #ffb000;
        border-radius: 3px;
        background-color: #2a2a2a;
        font-weight: bold;
    }

    /* Icon styling */
    .fa-icon {
        margin-right: 8px;
        color: #ffb000;
    }

    /* Metadata row */
    .task-meta {
        color: #888;
        font-size: 0.9em;
        margin-top: 8px;
    }

    /* Section frames */
    .section-frame {
        border: 1px solid #ffb000;
        padding: 20px;
        margin: 20px 0;
        border-radius: 4px;
        background-color: #0f0f0f;
    }

    /* Caption text */
    .caption-text {
        color: #666;
        font-size: 0.85em;
    }

    /* Divider */
    hr {
        border-color: #333 !important;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("# <i class='fa-solid fa-bullseye fa-icon'></i>Cognitive Load Dashboard", unsafe_allow_html=True)
st.markdown(f"<div class='caption-text'><i class='fa-solid fa-clock fa-icon'></i>Last updated: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

# Focus Panel
st.markdown("<div class='section-frame'>", unsafe_allow_html=True)
st.markdown("## <i class='fa-solid fa-list-check fa-icon'></i>Focus Panel (Today's Priorities)", unsafe_allow_html=True)
try:
    focus_tasks = load_focus_tasks(count=5)
    if focus_tasks:
        for task in focus_tasks:
            # Priority icon mapping (Font Awesome)
            priority_icons = {
                0: "fa-fire",              # P0: urgent
                1: "fa-circle-exclamation", # P1: high priority
                2: "fa-circle-info",        # P2: medium
                3: "fa-circle-minus"        # P3: low
            }
            priority_icon = priority_icons.get(task.priority or 3, "fa-circle-minus")

            # Build task HTML with flip-board styling
            task_html = f"""
            <div class='task-container'>
                <div>
                    <span class='priority-badge'>
                        <i class='fa-solid {priority_icon}'></i> P{task.priority or '?'}
                    </span>
                    <span style='font-size: 1.1em; font-weight: bold;'>{task.title}</span>
                </div>
            """

            # Metadata row
            meta_parts = []
            if task.project:
                meta_parts.append(f"<i class='fa-solid fa-folder fa-icon'></i>{task.project}")
            if task.classification:
                meta_parts.append(f"<i class='fa-solid fa-tag fa-icon'></i>{task.classification}")

            if meta_parts:
                task_html += f"<div class='task-meta'>{' | '.join(meta_parts)}</div>"

            task_html += "</div>"

            st.markdown(task_html, unsafe_allow_html=True)
    else:
        st.info("No P0 or P1 tasks in focus")
except Exception as e:
    st.error(f"Error loading tasks: {e}")
st.markdown("</div>", unsafe_allow_html=True)

# Activity Log
st.markdown("<div class='section-frame'>", unsafe_allow_html=True)
st.markdown("## <i class='fa-solid fa-clock fa-icon'></i>Activity Log", unsafe_allow_html=True)
try:
    activities = load_recent_activity(limit=20)
    if activities:
        for activity in activities:
            # Parse timestamp
            timestamp = activity.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M:%S")
                except (ValueError, AttributeError):
                    time_str = timestamp[:8] if len(timestamp) >= 8 else timestamp
            else:
                time_str = "??:??:??"

            session = activity.get("session", "unknown")
            action = activity.get("action", "unknown")

            # Build activity HTML with flip-board styling
            activity_html = f"""
            <div class='task-container'>
                <div>
                    <span class='priority-badge'>
                        <i class='fa-solid fa-clock'></i> {time_str}
                    </span>
                    <span style='font-size: 1.0em;'><i class='fa-solid fa-terminal fa-icon'></i>{session}</span>
                </div>
                <div class='task-meta'>{action}</div>
            </div>
            """
            st.markdown(activity_html, unsafe_allow_html=True)
    else:
        st.info("No activity logged yet")
except Exception as e:
    st.error(f"Error loading activity: {e}")
st.markdown("</div>", unsafe_allow_html=True)

# Task Summary
st.markdown("<div class='section-frame'>", unsafe_allow_html=True)
st.markdown("## <i class='fa-solid fa-chart-simple fa-icon'></i>Task Summary", unsafe_allow_html=True)
st.info("Task summary metrics will be added shortly")
st.markdown("</div>", unsafe_allow_html=True)

# Auto-refresh
import time
time.sleep(30)
st.rerun()
