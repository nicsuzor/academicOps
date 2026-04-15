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
            # Support both Claude (mcp__pkb__*) and Gemini (pkb:*) naming conventions
            {
                "change": StateChange.BIND_TASK,
                "type": RuleType.TOOL_CALL,
                "tools": [
                    "mcp__pkb__update_task",
                    "pkb:update_task",
                    "pkb__update_task",
                    "update_task",
                ],
                "input_pattern": {"status": "in_progress"},
            },
            # --- Task Unbinding (Completion) ---
            {
                "change": StateChange.UNBIND_TASK,
                "type": RuleType.TOOL_CALL,
                "tools": [
                    "mcp__pkb__complete_task",
                    "pkb:complete_task",
                    "pkb__complete_task",
                    "complete_task",
                ],
                "result_check": "success",
            },
            {
                "change": StateChange.UNBIND_TASK,
                "type": RuleType.TOOL_CALL,
                "tools": [
                    "mcp__pkb__update_task",
                    "pkb:update_task",
                    "pkb__update_task",
                    "update_task",
                ],
                "input_pattern": {"status": "done"},
            },
            {
                "change": StateChange.UNBIND_TASK,
                "type": RuleType.TOOL_CALL,
                "tools": [
                    "mcp__pkb__update_task",
                    "pkb:update_task",
                    "pkb__update_task",
                    "update_task",
                ],
                "input_pattern": {"status": "cancelled"},
            },
        ]

    def _match_pattern(self, data: dict[str, Any], pattern: dict[str, Any]) -> bool:
        """Check if pattern dict is a subset of data dict.

        Supports both top-level parameters and nested 'updates' object (PKB friction).

        Constraint: Strategy 2 (nested updates) requires ALL pattern keys to be
        present in the 'updates' dict. Patterns that mix top-level fields (e.g. 'id')
        with nested fields (e.g. 'status') will not match via either strategy.
        Current rules use only single-key patterns, so this is not an issue today.
        If multi-key patterns are added that span both levels, this method must be
        extended (e.g. split pattern keys by scope).
        """
        # Strategy 1: Top-level match (e.g. status="in_progress")
        top_match = True
        for key, value in pattern.items():
            if key not in data or data[key] != value:
                top_match = False
                break
        if top_match:
            return True

        # Strategy 2: Nested 'updates' object (e.g. updates={"status": "in_progress"})
        # NOTE: All pattern keys must live in 'updates' — see constraint above.
        updates = data.get("updates")
        if isinstance(updates, dict):
            for key, value in pattern.items():
                if updates.get(key) != value:
                    return False
            return True

        return False

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
