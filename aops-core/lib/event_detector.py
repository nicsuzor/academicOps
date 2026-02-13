"""Centralized event detection module.

Consolidates logic for detecting state changes (task binding, unbinding, etc.)
from hook events (Tool Use, User Propmt, etc.).
"""

import json
from enum import Enum
from typing import Any


class StateChange(Enum):
    BIND_TASK = "bind_task"
    UNBIND_TASK = "unbind_task"
    PLAN_MODE = "plan_mode"
    # Future: HYDRATE_SKIP, etc.


class RuleType(Enum):
    TOOL_CALL = "tool_call"
    # Future: PROMPT_CONTENT = "prompt_content"


class EventDetector:
    def __init__(self):
        self.rules = self._get_default_rules()

    def _get_default_rules(self) -> list[dict[str, Any]]:
        """Define default detection rules."""
        return [
            # --- Plan Mode ---
            {
                "change": StateChange.PLAN_MODE,
                "type": RuleType.TOOL_CALL,
                "tools": ["EnterPlanMode"],
            },
            # --- Task Binding (Claim via update_task) ---
            # Support both Claude (mcp__plugin_*) and Gemini (aops-core/tools:*) naming conventions
            {
                "change": StateChange.BIND_TASK,
                "type": RuleType.TOOL_CALL,
                "tools": [
                    "mcp__plugin_aops-core_task_manager__update_task",
                    "mcp__plugin_aops-tools_task_manager__update_task",
                    "aops-core:task_manager:update_task",
                    "aops-tools:task_manager:update_task",
                    "task_manager__update_task",
                    "update_task",
                ],
                "input_pattern": {"status": "in_progress"},
            },
            # --- Task Binding (Claim via claim_next_task) ---
            # claim_next_task implicitly sets status to in_progress, no input_pattern needed
            {
                "change": StateChange.BIND_TASK,
                "type": RuleType.TOOL_CALL,
                "tools": [
                    "mcp__plugin_aops-core_task_manager__claim_next_task",
                    "mcp__plugin_aops-tools_task_manager__claim_next_task",
                    "aops-core:task_manager:claim_next_task",
                    "aops-tools:task_manager:claim_next_task",
                    "task_manager__claim_next_task",
                    "claim_next_task",
                ],
                "result_check": "success",
            },
            # --- Task Unbinding (Completion) ---
            {
                "change": StateChange.UNBIND_TASK,
                "type": RuleType.TOOL_CALL,
                "tools": [
                    "mcp__plugin_aops-core_task_manager__complete_task",
                    "mcp__plugin_aops-tools_task_manager__complete_task",
                    "aops-core:task_manager:complete_task",
                    "aops-tools:task_manager:complete_task",
                    "task_manager__complete_task",
                    "complete_task",
                    "mcp__plugin_aops-core_task_manager__complete_tasks",
                    "mcp__plugin_aops-tools_task_manager__complete_tasks",
                    "aops-core:task_manager:complete_tasks",
                    "aops-tools:task_manager:complete_tasks",
                    "task_manager__complete_tasks",
                    "complete_tasks",
                ],
                "result_check": "success",
            },
            {
                "change": StateChange.UNBIND_TASK,
                "type": RuleType.TOOL_CALL,
                "tools": [
                    "mcp__plugin_aops-core_task_manager__update_task",
                    "mcp__plugin_aops-tools_task_manager__update_task",
                    "aops-core:task_manager:update_task",
                    "aops-tools:task_manager:update_task",
                    "task_manager__update_task",
                    "update_task",
                ],
                "input_pattern": {"status": "done"},
            },
            {
                "change": StateChange.UNBIND_TASK,
                "type": RuleType.TOOL_CALL,
                "tools": [
                    "mcp__plugin_aops-core_task_manager__update_task",
                    "mcp__plugin_aops-tools_task_manager__update_task",
                    "aops-core:task_manager:update_task",
                    "aops-tools:task_manager:update_task",
                    "task_manager__update_task",
                    "update_task",
                ],
                "input_pattern": {"status": "cancelled"},
            },
        ]

    def _match_pattern(self, data: dict[str, Any], pattern: dict[str, Any]) -> bool:
        """Check if pattern dict is a subset of data dict."""
        for key, value in pattern.items():
            if key not in data:
                return False
            if data[key] != value:
                return False
        return True

    def _check_result_success(self, tool_result: dict[str, Any]) -> bool:
        """Check if tool result indicates success."""
        # Handle Gemini format (JSON in returnDisplay)
        if "returnDisplay" in tool_result:
            try:
                content = tool_result["returnDisplay"]
                if isinstance(content, str):
                    data = json.loads(content)
                    return data.get("success", False) or data.get("success_count", 0) > 0
            except (json.JSONDecodeError, TypeError):
                pass

        # Handle Standard/Claude format
        return tool_result.get("success", False) or tool_result.get("success_count", 0) > 0

    def detect_tool_changes(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_result: dict[str, Any] | None = None,
    ) -> list[StateChange]:
        """Detect state changes from a tool call."""
        detected = []

        for rule in self.rules:
            if rule["type"] != RuleType.TOOL_CALL:
                continue

            # 1. Check Tool Name
            if tool_name not in rule["tools"]:
                continue

            # 2. Check Input Pattern (if defined)
            if "input_pattern" in rule:
                if not self._match_pattern(tool_input, rule["input_pattern"]):
                    continue

            # 3. Check Result (if defined)
            if "result_check" in rule:
                if not tool_result:
                    continue  # Result required but not provided

                if rule["result_check"] == "success":
                    if not self._check_result_success(tool_result):
                        continue

            detected.append(rule["change"])

        return detected


# Singleton or factory usage
_detector = EventDetector()


def detect_tool_state_changes(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_result: dict[str, Any] | None = None,
) -> list[StateChange]:
    """Public API for tool change detection."""
    return _detector.detect_tool_changes(tool_name, tool_input, tool_result)
