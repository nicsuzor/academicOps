import re
from typing import Any

from hooks.gate_config import get_tool_category
from hooks.schemas import HookContext
from lib import session_state as session_state_lib
from lib.gate_model import GateResult, GateVerdict
from lib.gates.base import Gate
from lib.session_state import SessionState
from lib.template_registry import TemplateRegistry


class HydrationGate(Gate):
    """
    Hydration Gate: Ensures the agent is hydrated with context before working.

    - Blocks tools until hydration is complete.
    - specific tools (Task/Skill to spawn hydrator) are allowed.
    - read-only access to hydrator files is allowed.
    """

    @property
    def name(self) -> str:
        return "hydration"

    def check(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PreToolUse: Block if hydration is pending."""
        tool_name = context.tool_name or ""
        tool_input = context.tool_input or {}

        # 1. Allow hydrator's own tool calls (recursive loop prevention)
        if session_state_lib.is_hydrator_active(context.session_id):
            return None

        # 2. Allow spawning hydrator
        if self._is_spawning_hydrator(tool_name, tool_input):
            # Open hydration gate immediately when hydrator is invoked
            # This allows the subagent to proceed with tool calls while hydrator runs
            # We set the flag here, but we also rely on on_tool_use to set hydrator_active
            session_state_lib.clear_hydration_pending(context.session_id)
            return None

        # 3. Allow reads from hydrator files (bootstrap)
        if self._is_hydrator_file_read(tool_name, tool_input):
            return None

        # 4. Always-available tools bypass all gates
        if get_tool_category(tool_name) == "always_available":
            return None

        # 5. Check if gate is open
        if not session_state_lib.is_hydration_pending(context.session_id):
            return None

        # Gate is closed (hydration pending) - Block
        return self._create_block_result(context)

    def on_tool_use(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PostToolUse: Track hydrator activity."""
        tool_name = context.tool_name or ""
        tool_input = context.tool_input or {}

        # Set hydrator active if spawning
        if self._is_spawning_hydrator(tool_name, tool_input):
            session_state_lib.set_hydrator_active(context.session_id)
            return None

        # Clear hydrator active if hydrator task completed
        # Note: We check if the tool *was* spawning hydrator, and now it finished.
        # But wait, PostToolUse happens after the tool execution.
        # If it was "Task", it means the subagent finished.
        if (
            tool_name in ("Task", "Skill", "delegate_to_agent", "activate_skill")
            or "hydrator" in tool_name.lower()
        ):
             if self._is_spawning_hydrator(tool_name, tool_input) or "hydrator" in tool_name.lower():
                session_state_lib.clear_hydrator_active(context.session_id)

        # Increment turns since hydration
        # Copied from gate_registry.py run_accountant
        SAFE_READ_TOOLS = {
            "Read", "Glob", "Grep", "WebFetch", "WebSearch",
            "read_file", "view_file", "list_dir", "find_by_name", "grep_search",
            "search_web", "read_url_content",
            "mcp__memory__retrieve_memory", "mcp_memory_retrieve_memory",
            "mcp__plugin_aops-core_memory__retrieve_memory",
        }

        if tool_name not in SAFE_READ_TOOLS:
             session_state_lib.update_hydration_metrics(context.session_id, turns_since_hydration=session_state.get("hydration", {}).get("turns_since_hydration", -1) + 1)

        return None

    def on_user_prompt(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """UserPromptSubmit: Require hydration for new prompts."""
        try:
            from hooks.user_prompt_submit import (
                build_hydration_instruction,
                should_skip_hydration,
                write_initial_hydrator_state,
            )
            from lib.session_state import clear_reflection_output, set_gates_bypassed
        except ImportError:
            return None

        prompt = context.raw_input.get("prompt", "")
        session_id = context.session_id
        transcript_path = context.raw_input.get("transcript_path")

        clear_reflection_output(session_id)

        if should_skip_hydration(prompt):
             write_initial_hydrator_state(session_id, prompt, hydration_pending=False)
             if prompt.strip().startswith("."):
                 set_gates_bypassed(session_id, True)
             return None

        # Require hydration
        try:
            instruction = build_hydration_instruction(session_id, prompt, transcript_path)
            # This implicitly sets hydration_pending=True via write_initial_hydrator_state inside build_hydration_instruction
            return GateResult(
                verdict=GateVerdict.ALLOW,
                context_injection=instruction,
                metadata={"source": "hydration_gate"},
            )
        except Exception as e:
             # Fail gracefully
             return GateResult(
                verdict=GateVerdict.ALLOW,
                context_injection=f"⛔ **HYDRATION ERROR**: {e}\n\nCannot proceed with hydration.",
                metadata={"source": "hydration_gate", "error": str(e)},
             )

    def on_after_agent(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """AfterAgent: Check for hydration completion."""
        response_text = context.raw_input.get("prompt_response", "")

        # Check for "HYDRATION RESULT"
        if re.search(
            r"(?:##\s*|\*\*)?(?:HYDRATION RESULT|Execution Plan|Execution Steps)",
            response_text,
            re.IGNORECASE,
        ):
            session_state_lib.clear_hydration_pending(context.session_id)
            session_state_lib.update_hydration_metrics(context.session_id, turns_since_hydration=0)

            # Workflow tracking
            workflow_match = re.search(
                r"\*\*Workflows?\*\*:\s*\[\[workflows/([^\]]+)\]\]", response_text
            )
            workflow_id = workflow_match.group(1) if workflow_match else None

            if workflow_id:
                state = session_state_lib.get_or_create_session_state(context.session_id)
                state["state"]["current_workflow"] = workflow_id
                session_state_lib.save_session_state(context.session_id, state)

            # Detect streamlined workflows
            is_streamlined = workflow_id in (
                "interactive-followup",
                "simple-question",
                "direct-skill",
            )

            if is_streamlined:
                 return GateResult(
                    verdict=GateVerdict.ALLOW,
                    system_message=f"[Gate] Hydration complete (workflow: {workflow_id}). Streamlined mode enabled.",
                    metadata={"source": "hydration_gate", "streamlined": True}
                )

            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message="💧 [Gate] Hydration plan detected. Gate satisfied.",
                context_injection=(
                    "<system-reminder>\n"
                    "Hydration plan detected. Next step: Invoke the critic to review this plan.\n"
                    "Use: `activate_skill(name='critic', prompt='Review this plan...')`\n"
                    "</system-reminder>"
                ),
                metadata={"source": "hydration_gate"}
            )

        return None

    def on_session_start(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """SessionStart: Initialize hydration state."""
        # Ensure hydration is pending at start
        session_state_lib.set_gate_status(context.session_id, self.name, "closed")
        return None

    # --- Helpers ---

    def _is_spawning_hydrator(self, tool_name: str, tool_input: dict[str, Any]) -> bool:
        """Check if tool call is spawning the hydrator."""
        if tool_name in ("prompt-hydrator", "aops-core:prompt-hydrator"):
            return True

        if tool_name in ("Task", "Skill", "activate_skill", "delegate_to_agent"):
            subagent = (
                tool_input.get("subagent_type", "")
                or tool_input.get("skill", "")
                or tool_input.get("name", "")
                or tool_input.get("agent_name", "")
            )
            if subagent and "hydrator" in subagent.lower():
                return True

        return False

    def _is_hydrator_file_read(self, tool_name: str, tool_input: dict[str, Any]) -> bool:
        """Check if this is a read of a hydrator file."""
        if tool_name not in ("Read", "read_file", "view_file"):
            return False

        file_path = tool_input.get("file_path") or tool_input.get("path")
        if not file_path:
            return False

        if "/hydrator/hydrate_" in str(file_path):
            return True

        return False

    def _create_block_result(self, context: HookContext) -> GateResult:
        """Create a block result for the gate."""
        import os
        from hooks.gate_config import GATE_MODE_DEFAULTS, GATE_MODE_ENV_VARS

        mode = os.environ.get(GATE_MODE_ENV_VARS.get(self.name, ""), GATE_MODE_DEFAULTS.get(self.name, "warn"))

        # We need to construct the message.
        # Using TemplateRegistry as in gates.py

        # Construct audit path for instruction
        audit_path = session_state_lib.get_hydration_temp_path(context.session_id)

        next_instruction = "Invoke prompt-hydrator agent."
        if audit_path:
             next_instruction = f"Invoke prompt-hydrator agent with context file: `{audit_path}`"

        try:
            msg = TemplateRegistry.instance().render(
                "tool.gate_message",
                {
                    "mode": mode,
                    "tool_name": context.tool_name,
                    "tool_category": get_tool_category(context.tool_name or ""),
                    "missing_gates": "hydration",
                    "gate_status": "- hydration: ✗",
                    "next_instruction": next_instruction,
                },
            )
        except Exception:
             # Fallback
             msg = f"⛔ **GATE BLOCKED**: Hydration required.\n\n{next_instruction}"

        if mode == "block":
            return GateResult.deny(system_message=msg, context_injection=msg)
        return GateResult.warn(system_message=msg, context_injection=msg)
