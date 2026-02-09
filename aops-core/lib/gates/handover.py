import re
import sys
from typing import Any

from hooks.schemas import HookContext
from lib.gate_model import GateResult, GateVerdict
from lib.gates.base import Gate
from lib.session_state import SessionState
from lib import session_state as session_state_lib


class HandoverGate(Gate):
    """
    Handover Gate: Requires session handover (reflection & cleanup) before stop.
    """

    @property
    def name(self) -> str:
        return "handover"

    def check(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PreToolUse: Handover gate doesn't block tools."""
        return None

    def on_tool_use(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PostToolUse: Track handover state."""
        tool_name = context.tool_name or ""
        tool_input = context.tool_input or {}

        system_messages = []

        # Check for handover skill
        if self._is_handover_invocation(tool_name, tool_input):
            session_state_lib.set_handover_skill_invoked(context.session_id)
            system_messages.append(
                "🤝 [Gate] Handover tool recorded. Stop gate will open once repo is clean and reflection message printed."
            )
        # Check for destructive tool -> reset gate
        elif self._is_actually_destructive(tool_name, tool_input):
            was_open = session_state_lib.is_handover_skill_invoked(context.session_id)
            session_state_lib.clear_handover_skill_invoked(context.session_id)
            if was_open:
                system_messages.append(
                    "⚠️ [Gate] Destructive tool used. Handover required before stop."
                )

        if system_messages:
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message="\n".join(system_messages)
            )

        return None

    def on_user_prompt(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """UserPromptSubmit: Reset gate on new prompt."""
        session_state_lib.clear_handover_skill_invoked(context.session_id)
        return None

    def on_after_agent(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """AfterAgent: Check for Framework Reflection."""
        response_text = context.raw_input.get("prompt_response", "")

        if "## Framework Reflection" in response_text:
            # Validate fields
            required_fields = [
                r"\*\*Prompts\*\*:",
                r"\*\*Guidance received\*\*:",
                r"\*\*Followed\*\*:",
                r"\*\*Outcome\*\*:",
                r"\*\*Accomplishments\*\*:",
                r"\*\*Friction points\*\*:",
                r"\*\*Proposed changes\*\*:",
                r"\*\*Next step\*\*:",
            ]

            missing_fields = []
            for field_pattern in required_fields:
                if not re.search(field_pattern, response_text, re.IGNORECASE):
                    field_name = field_pattern.replace(r"\*\*", "").replace(":", "")
                    missing_fields.append(field_name)

            if missing_fields:
                return GateResult(
                    verdict=GateVerdict.ALLOW,
                    system_message=f"⚠️ [Gate] Framework Reflection found but missing required fields: {', '.join(missing_fields)}. Handover gate remains closed.",
                    context_injection=(
                        "<system-reminder>\n"
                        "Your Framework Reflection is missing required fields.\n"
                        f"Missing: {', '.join(missing_fields)}\n"
                        "</system-reminder>"
                    ),
                    metadata={
                        "source": "handover_gate",
                        "missing_fields": missing_fields,
                    },
                )

            # Valid reflection
            session_state_lib.set_handover_skill_invoked(context.session_id)
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message="🧠 [Gate] Framework Reflection validated. Handover gate open.",
            )

        return None

    def on_stop(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """Stop: Require handover if work at risk."""
        # Only enforce handover if there's work at risk (uncommitted changes or active task)
        # Otherwise, allow stop - don't block normal conversation turns
        if not session_state_lib.is_handover_skill_invoked(context.session_id):
            # Check if there's work at risk
            has_uncommitted = self._check_git_dirty()
            current_task = session_state_lib.get_current_task(context.session_id)

            if has_uncommitted or current_task:
                 return GateResult(
                    verdict=GateVerdict.DENY,
                    context_injection="⛔ **BLOCKED**: Uncommitted changes or active task detected.\n\nInvoke `/handover` to clean up and document your work before stopping.",
                    metadata={"source": "stop_gate_handover_check"},
                 )

        return None

    def _is_handover_invocation(self, tool_name: str, tool_input: dict[str, Any]) -> bool:
        """Check if tool call is invoking handover."""
        if tool_name in ("handover", "aops-core:handover"):
            return True

        if tool_name in ("Task", "Skill", "activate_skill", "delegate_to_agent"):
            subagent = (
                tool_input.get("subagent_type", "")
                or tool_input.get("skill", "")
                or tool_input.get("name", "")
                or tool_input.get("agent_name", "")
            )
            if subagent and "handover" in subagent.lower():
                return True

        return False

    def _is_actually_destructive(self, tool_name: str, tool_input: dict[str, Any]) -> bool:
        """Check if this tool call is actually destructive (modifies state)."""
        # Non-Bash mutating tools are always destructive
        if tool_name in (
            "Edit",
            "Write",
            "NotebookEdit",
            "write_to_file",
            "write_file",
            "replace_file_content",
            "replace",
            "multi_replace_file_content",
        ):
            return True

        # Bash commands: check if actually destructive
        if tool_name in ("Bash", "run_shell_command", "run_command"):
            command = tool_input.get("command") or tool_input.get("CommandLine")
            if command is None:
                return True  # Fail-closed: no command = assume destructive
            return self._is_destructive_bash(str(command))

        # All other tools are not destructive
        return False

    def _is_destructive_bash(self, command: str) -> bool:
        """Check if a bash command is destructive."""
        # Normalize command for pattern matching
        cmd = command.strip().lower()

        # Read-only command patterns (safe)
        readonly_patterns = [
            "git status", "git diff", "git log", "git show", "git branch",
            "git remote", "git fetch",
            "ls ", "ls\n", "ls$", "cat ", "head ", "tail ",
            "grep ", "rg ", "find ", "which ", "type ",
            "echo ", "pwd", "env", "printenv",
            "uname", "whoami", "date", "uptime",
        ]

        for pattern in readonly_patterns:
            if pattern.endswith("$"):
                if cmd == pattern[:-1]:
                    return False
            elif cmd.startswith(pattern) or f" {pattern}" in cmd:
                return False

        # Destructive command patterns
        destructive_patterns = [
            "git commit", "git push", "git merge", "git rebase", "git reset",
            "git checkout", "git restore", "git clean", "git stash",
            "rm ", "rm\n", "rmdir", "mv ", "cp ", "mkdir",
            "touch ", "chmod ", "chown ",
            "> ", ">>", "tee ", "sed -i",
            "npm install", "npm run", "yarn ", "pip install", "uv pip", "uv sync", "uv run",
        ]

        for pattern in destructive_patterns:
            if cmd.startswith(pattern) or f" {pattern}" in cmd or f"&& {pattern}" in cmd:
                return True

        # Default: assume destructive (fail-closed)
        return True

    def _check_git_dirty(self) -> bool:
        """Check if git working directory has uncommitted changes."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Any output means there are changes
            return bool(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            # If git fails, assume no changes (fail-open for this check)
            return False
