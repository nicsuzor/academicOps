from hooks.schemas import HookContext
from lib.gate_model import GateResult
from lib.gate_types import GateState, GateStatus
from lib.session_state import SessionState

def execute_custom_action(name: str, ctx: HookContext, state: GateState, session_state: SessionState) -> GateResult | None:
    """
    Execute a named custom action.
    """
    if name == "hydrate_prompt":
        try:
            from hooks.user_prompt_submit import build_hydration_instruction
            # Gemini prompt is in ctx.raw_input["prompt"]
            prompt = ctx.raw_input.get("prompt")
            if not prompt:
                # Fallback for Claude if needed, but for now we focus on Gemini
                return None

            transcript_path = ctx.transcript_path or ctx.raw_input.get("transcript_path")
            
            # This writes the temp file AND updates the session_state in memory
            instruction = build_hydration_instruction(
                ctx.session_id, prompt, transcript_path, state=session_state
            )
            
            return GateResult.allow(
                system_message=instruction,
                context_injection=instruction
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return GateResult.allow(system_message=f"WARNING: Hydration failed: {e}")

    return None
