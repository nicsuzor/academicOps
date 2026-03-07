import json
import os
import sys
import traceback
from unittest.mock import MagicMock


class MockColumns:
    def __call__(self, arg, *args, **kwargs):
        if isinstance(arg, int):
            return [MagicMock() for _ in range(arg)]
        elif isinstance(arg, list):
            return [MagicMock() for _ in range(len(arg))]
        return [MagicMock(), MagicMock()]


class MockTabs:
    def __call__(self, arg, *args, **kwargs):
        return [MagicMock() for _ in range(len(arg))]


st_mock = MagicMock()
st_mock.columns = MockColumns()
st_mock.tabs = MockTabs()
sys.modules["streamlit"] = st_mock

os.environ.setdefault("ACA_DATA", os.path.expanduser("~/writing/data"))
os.environ.setdefault("AOPS_SESSIONS", os.path.expanduser("~/.aops/sessions"))

import io

original_stdout = sys.stdout
sys.stdout = io.StringIO()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../..", "lib", "overwhelm"))

try:
    import dashboard
except Exception as e:
    sys.stdout = original_stdout
    sys.stderr.write(f"Error importing dashboard: {e}\n")
    traceback.print_exc()
    sys.exit(1)

sys.stdout = original_stdout

data = {
    "active_agents": [
        {
            "session_id": a.session_id,
            "project": a.project,
            "started_at": a.started_at,
            "task_id": a.task_id,
            "description": (
                a.context.current_status
                if a.context and a.context.current_status
                else (a.context.initial_prompt if a.context else "")
            ),
        }
        for a in dashboard.get_active_agents(max_age_hours=1)
        if a.context
        and a.context.has_meaningful_context()
        and (
            a.project != "unknown"
            or (a.context.initial_prompt and len(a.context.initial_prompt) > 20)
        )
    ],
    "left_off": dashboard.where_left_off,
    "synthesis": dashboard.synthesis or {},
    "daily_story": dashboard.daily_story or {},
    "project_projects": [p for p in dashboard.sorted_projects]
    if hasattr(dashboard, "sorted_projects")
    else [],
    "project_data": {
        "tasks": dashboard.tasks_by_project,
        "accomplishments": dashboard.accomplishments_by_project,
        "sessions": dashboard.sessions_by_project,
        "meta": dashboard.projects,
    }
    if hasattr(dashboard, "tasks_by_project")
    else {},
    # Wait, we need the "needs you" tasks too
    "needs_you": dashboard._blocked_waiting if hasattr(dashboard, "_blocked_waiting") else [],
    "path": {
        "abandoned_work": [vars(a) for a in dashboard.path.abandoned_work]
        if hasattr(dashboard, "path") and dashboard.path
        else [],
        "threads": [
            {
                "project": t.project,
                "session_id": t.session_id,
                "git_branch": getattr(t, "git_branch", None),
                "hydrated_intent": getattr(t, "hydrated_intent", None),
                "initial_goal": getattr(t, "initial_goal", None),
                "events": [
                    {
                        "timestamp": e.timestamp,
                        "event_type": str(e.event_type),
                        "task_id": e.task_id,
                        "narrative": e.render_narrative(),
                    }
                    for e in t.events
                ],
            }
            for t in dashboard.path.threads
        ]
        if hasattr(dashboard, "path") and dashboard.path
        else [],
    },
}

print(json.dumps(data, default=str))
