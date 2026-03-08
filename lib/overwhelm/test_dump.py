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

# Suppress stdout
import io

original_stdout = sys.stdout
sys.stdout = io.StringIO()

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

try:
    import dashboard
except Exception:
    sys.stdout = original_stdout
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
        }
        for a in dashboard.get_active_agents(max_age_hours=1)
    ],
    "left_off": dashboard.where_left_off,
    "synthesis": dashboard.synthesis or {},
    "daily_story": dashboard.daily_story or {},
}

print(json.dumps(data, default=str))
