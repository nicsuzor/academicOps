import re
from typing import Any

from hooks.gate_config import get_tool_category
from hooks.schemas import HookContext
from lib.gate_model import GateResult, GateVerdict
from lib.gates.base import Gate
from lib.session_state import SessionState
from lib.template_registry import TemplateRegistry


class HydrationGate(Gate):
    """
    Hydration Gate: Ensures the agent is hydrated with context before working.
    """

    @property
    def name(self) -> str:
        return "hydration"

    def check(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PreToolUse: Block if hydration is pending."""
        tool_name = context.tool_name or ""
        tool_input = context.tool_input or {}

        # 1. Global Bypass (Hydrator itself) - Handled in dispatcher but good to keep logic here too?
        # Dispatcher handles `is_hydrator_active`.

        # 2. Allow spawning hydrator
        if self._is_spawning_hydrator(tool_name, tool_input):
            # Open hydration gate immediately when hydrator is invoked
            session_state.open_gate(self.name)
            # Legacy flag for compat
            session_state.state["hydration_pending"] = False
            return None

        # 3. Allow reads from hydrator files
        if self._is_hydrator_file_read(tool_name, tool_input):
            return None

        # 4. Always-available tools
        if get_tool_category(tool_name) == "always_available":
            return None

        # 5. Check if gate is open
        if session_state.is_gate_open(self.name):
            return None

        return self._create_block_result(context, session_state)

    def on_tool_use(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PostToolUse: Track hydrator activity."""
        tool_name = context.tool_name or ""
        tool_input = context.tool_input or {}

        # Set hydrator active if spawning
        if self._is_spawning_hydrator(tool_name, tool_input):
            session_state.state["hydrator_active"] = True
            return None

        # Clear hydrator active if hydrator task completed (main task tool done)
        if (
            tool_name in ("Task", "Skill", "delegate_to_agent", "activate_skill")
            or "hydrator" in tool_name.lower()
        ):
             if self._is_spawning_hydrator(tool_name, tool_input) or "hydrator" in tool_name.lower():
                session_state.state["hydrator_active"] = False

        # Increment turns since hydration
        SAFE_READ_TOOLS = {
            "Read", "Glob", "Grep", "WebFetch", "WebSearch",
            "read_file", "view_file", "list_dir", "find_by_name", "grep_search",
            "search_web", "read_url_content",
            "mcp__memory__retrieve_memory", "mcp_memory_retrieve_memory",
            "mcp__plugin_aops-core_memory__retrieve_memory",
        }

        if tool_name not in SAFE_READ_TOOLS:
             session_state.hydration.turns_since_hydration += 1

        return None

    def on_subagent_stop(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """SubagentStop: Check if hydrator completed successfully."""
        subagent_type = context.subagent_type or ""

        if "hydrator" in subagent_type.lower():
            session_state.state["hydrator_active"] = False

            result_text = ""
            if isinstance(context.tool_output, dict):
                result_text = str(context.tool_output.get("output", ""))
            else:
                result_text = str(context.tool_output)

            if "## HYDRATION RESULT" in result_text or "HYDRATION RESULT" in result_text:
                session_state.open_gate(self.name)
                session_state.state["hydration_pending"] = False
                return GateResult.allow(system_message="✓ Hydration gate opened (subagent success)")
            else:
                return GateResult.allow(system_message="⚠️ Hydrator finished but result missing '## HYDRATION RESULT'. Gate remains closed.")

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

        # Legacy compat - using helper functions inside hooks?
        # `write_initial_hydrator_state` uses `set_hydration_pending`.
        # I should probably update `user_prompt_submit.py` too, or just manually set state here.
        # But `build_hydration_instruction` does IO (writes temp file).

        # We can reuse the logic:

        if should_skip_hydration(prompt):
             session_state.open_gate(self.name)
             if prompt.strip().startswith("."):
                 session_state.state["gates_bypassed"] = True
             return None

        # Require hydration
        try:
            # We call this to generate the file, but we manage state ourselves
            # Note: build_hydration_instruction calls set_hydration_temp_path legacy helper
            # We should probably update that hook or patch it.
            # For now, let it do its thing, but we update our object.
            instruction = build_hydration_instruction(session_id, prompt, transcript_path)

            # Set pending
            session_state.close_gate(self.name)
            session_state.state["hydration_pending"] = True

            return GateResult(
                verdict=GateVerdict.ALLOW,
                context_injection=instruction,
                metadata={"source": "hydration_gate"},
            )
        except Exception as e:
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
            session_state.open_gate(self.name)
            session_state.state["hydration_pending"] = False
            session_state.hydration.turns_since_hydration = 0

            # Workflow tracking
            workflow_match = re.search(
                r"\*\*Workflows?\*\*:\s*\[\[workflows/([^\]]+)\]\]", response_text
            )
            workflow_id = workflow_match.group(1) if workflow_match else None

            if workflow_id:
                session_state.state["current_workflow"] = workflow_id

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
        session_state.close_gate(self.name)
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

    def _create_block_result(self, context: HookContext, session_state: SessionState) -> GateResult:
        """Create a block result for the gate."""
        import os
        from hooks.gate_config import GATE_MODE_DEFAULTS, GATE_MODE_ENV_VARS

        mode = os.environ.get(GATE_MODE_ENV_VARS.get(self.name, ""), GATE_MODE_DEFAULTS.get(self.name, "warn"))

        audit_path = session_state.hydration.temp_path

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
