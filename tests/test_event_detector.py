"""Tests for centralized event detection module."""

from lib.event_detector import StateChange, detect_tool_state_changes


class TestEventDetector:
    """Tests for EventDetector logic."""

    def test_plan_mode_detection(self):
        changes = detect_tool_state_changes("EnterPlanMode", {})
        assert StateChange.PLAN_MODE in changes

    def test_task_binding_update_task_in_progress(self):
        # Claiming a task
        changes = detect_tool_state_changes(
            "update_task", {"status": "in_progress", "id": "task-1"}
        )
        assert StateChange.BIND_TASK in changes
        assert StateChange.UNBIND_TASK not in changes

    def test_task_binding_update_task_active_ignored(self):
        # Setting to active (ready) is NOT claiming
        changes = detect_tool_state_changes("update_task", {"status": "active", "id": "task-1"})
        assert StateChange.BIND_TASK not in changes

    def test_task_unbinding_complete_task_success(self):
        # Regular completion
        changes = detect_tool_state_changes("complete_task", {"id": "task-1"}, {"success": True})
        assert StateChange.UNBIND_TASK in changes

    def test_task_unbinding_complete_task_failure(self):
        # Failed completion should not unbind
        changes = detect_tool_state_changes("complete_task", {"id": "task-1"}, {"success": False})
        assert StateChange.UNBIND_TASK not in changes

    def test_task_unbinding_update_task_done(self):
        # Marking done via update_task (bug fix case)
        changes = detect_tool_state_changes("update_task", {"status": "done", "id": "task-1"})
        assert StateChange.UNBIND_TASK in changes
        assert StateChange.BIND_TASK not in changes

    def test_task_unbinding_update_task_cancelled(self):
        # Marking cancelled via update_task
        changes = detect_tool_state_changes("update_task", {"status": "cancelled", "id": "task-1"})
        assert StateChange.UNBIND_TASK in changes

    def test_gemini_json_result_parsing(self):
        # Gemini-style JSON in returnDisplay
        result = {"returnDisplay": '{"success": true, "task": {"id": "1"}}'}
        changes = detect_tool_state_changes("complete_task", {"id": "1"}, result)
        assert StateChange.UNBIND_TASK in changes
