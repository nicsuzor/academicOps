"""Cognitive Load Dashboard - Live task and activity monitoring."""
from __future__ import annotations

import streamlit as st
from datetime import datetime
from skills.tasks.task_loader import load_focus_tasks

# Page config
st.set_page_config(page_title="Cognitive Load Dashboard", layout="wide")

# Header
st.title("🎯 Cognitive Load Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# Focus Panel
st.header("Focus Panel (Today's Priorities)")
try:
    focus_tasks = load_focus_tasks(count=5)
    if focus_tasks:
        for task in focus_tasks:
            # Priority badge color
            priority_color = {0: "🔴", 1: "🟡", 2: "🔵", 3: "⚪"}.get(task.priority or 3, "⚪")

            # Display task
            with st.container():
                st.markdown(f"### {priority_color} P{task.priority or '?'} - {task.title}")
                if task.project:
                    st.caption(f"📁 {task.project}")
                if task.classification:
                    st.caption(f"🏷️ {task.classification}")
                st.divider()
    else:
        st.info("No P0 or P1 tasks in focus")
except Exception as e:
    st.error(f"Error loading tasks: {e}")

# Activity Log (stub for Phase 2)
st.header("Activity Log")
st.info("Activity logging will be implemented in Phase 2")

# Task Summary
st.header("Task Summary")
# Simple counts for now - will enhance
st.info("Task summary metrics will be added shortly")

# Auto-refresh
import time
time.sleep(30)
st.rerun()
