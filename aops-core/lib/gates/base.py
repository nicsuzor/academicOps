from abc import ABC, abstractmethod

from hooks.schemas import HookContext
from lib.gate_model import GateResult
from lib.session_state import SessionState


class Gate(ABC):
    """Abstract base class for all gates."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the gate (e.g., 'hydration', 'task')."""
        pass

    def check(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """
        PreToolUse: Check if the gate allows the tool usage.

        Returns:
            GateResult if the gate has a verdict (ALLOW/DENY/WARN).
            None if the gate is not applicable or has no opinion.
        """
        return None

    def on_tool_use(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """
        PostToolUse: Update gate state based on tool usage.

        Returns:
            GateResult with system_message if state changed.
            None otherwise.
        """
        return None

    def on_session_start(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """
        SessionStart: Initialize gate state.

        Returns:
            GateResult with system_message if initialization occurred.
            None otherwise.
        """
        return None

    def on_user_prompt(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """
        UserPromptSubmit: Handle new user prompt (e.g., reset gate).

        Returns:
            GateResult with system_message if state changed.
            None otherwise.
        """
        return None

    def on_after_agent(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """
        AfterAgent: Handle agent response (e.g., detect completion).

        Returns:
            GateResult with system_message if state changed.
            None otherwise.
        """
        return None

    def on_stop(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """
        Stop: Check if the session can be stopped.

        Returns:
            GateResult with DENY verdict if stop is blocked.
            None otherwise.
        """
        return None
