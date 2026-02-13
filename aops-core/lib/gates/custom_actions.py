from pathlib import Path

from hooks.schemas import HookContext

from lib import hook_utils
from lib.gate_model import GateResult
from lib.gate_types import GateState
from lib.session_state import SessionState
from lib.template_registry import TemplateRegistry


def create_audit_file(session_id: str, gate: str, ctx: HookContext) -> Path | None:
    """Create rich audit file for gate using TemplateRegistry.

    Moved from lib/gate_utils.py to eliminate wrapper layer.
    """
    # Use gate name as category (e.g., 'custodiet', 'critic')
    category = gate

    # Try to load rich context if possible
    transcript_path = ctx.transcript_path or ctx.raw_input.get("transcript_path")
    session_context = ""
    if transcript_path:
        if gate in ("critic", "custodiet"):
            from lib.session_reader import build_critic_session_context

            try:
                session_context = build_critic_session_context(transcript_path)
            except Exception:
                pass
        else:
            from lib.session_reader import build_rich_session_context

            try:
                session_context = build_rich_session_context(transcript_path)
            except Exception:
                pass

    axioms, heuristics, skills = hook_utils.load_framework_content()

    import os

    custodiet_mode = os.environ.get("CUSTODIET_MODE", "block").lower()

    registry = TemplateRegistry.instance()

    # Fill template using unified logic
    try:
        content = registry.render(
            f"{gate}.context",
            {
                "session_id": session_id,
                "gate_name": gate,
                "tool_name": ctx.tool_name or "unknown",
                "session_context": session_context,
                "axioms_content": axioms,
                "heuristics_content": heuristics,
                "skills_content": skills,
                "custodiet_mode": custodiet_mode,
            },
        )
    except (KeyError, ValueError, FileNotFoundError):
        # Fallback to simple audit template if rich one fails
        try:
            content = registry.render(
                f"{gate}.audit",
                {
                    "session_id": session_id,
                    "gate_name": gate,
                    "tool_name": ctx.tool_name or "unknown",
                },
            )
        except (KeyError, ValueError, FileNotFoundError):
            return None

    # Write to temp
    try:
        temp_dir = hook_utils.get_hook_temp_dir(category, ctx.raw_input)
        return hook_utils.write_temp_file(
            content, temp_dir, f"audit_{gate}_", session_id=session_id
        )
    except Exception:
        return None


def execute_custom_action(
    name: str, ctx: HookContext, state: GateState, session_state: SessionState
) -> GateResult | None:
    """
    Execute a named custom action.
    """
    if name == "hydrate_prompt":
        try:
            from lib.hydration import build_hydration_instruction

            # Gemini prompt is in ctx.raw_input["prompt"]
            prompt = ctx.raw_input.get("prompt")
            if not prompt:
                # Fallback for Claude or other clients
                prompt = ctx.raw_input.get("message") or ctx.raw_input.get("intent")

            if not prompt:
                return None

            transcript_path = ctx.transcript_path or ctx.raw_input.get("transcript_path")

            # This writes the temp file AND updates the session_state in memory
            instruction = build_hydration_instruction(
                ctx.session_id, prompt, transcript_path, state=session_state
            )

            # User sees brief summary; agent gets full instruction
            temp_path = session_state.get_gate("hydration").metrics.get("temp_path", "temp file")
            return GateResult.allow(
                system_message=f"Hydration ready: {temp_path}", context_injection=instruction
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            return GateResult.allow(system_message=f"WARNING: Hydration failed: {e}")

    if name == "prepare_compliance_report":
        try:
            # Use 'custodiet' as the gate name for auditing
            temp_path = create_audit_file(ctx.session_id, "custodiet", ctx)
            if temp_path:
                state.metrics["temp_path"] = str(temp_path)

                # Render instruction template
                from lib.template_registry import TemplateRegistry

                registry = TemplateRegistry.instance()
                instruction = registry.render(
                    "custodiet.instruction", {"temp_path": str(temp_path)}
                )

                # User sees brief summary; agent gets full instruction
                return GateResult.allow(
                    system_message=f"Compliance report ready: {temp_path}",
                    context_injection=instruction,
                )
        except Exception as e:
            import traceback

            traceback.print_exc()
            return GateResult.allow(
                system_message=f"WARNING: Compliance report generation failed: {e}"
            )

    return None
