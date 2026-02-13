import os
from pathlib import Path

from hooks.schemas import HookContext

from lib import hook_utils
from lib.gate_model import GateResult
from lib.gate_types import GateState
from lib.session_paths import get_gate_file_path
from lib.session_state import SessionState
from lib.template_registry import TemplateRegistry


def create_audit_file(session_id: str, gate: str, ctx: HookContext) -> Path:
    """Create rich audit file for gate using TemplateRegistry.

    Fails fast if audit file cannot be created — callers depend on the
    returned path being valid and present in gate metrics.

    Raises:
        RuntimeError: If template rendering or file write fails.
    """
    transcript_path = ctx.transcript_path or ctx.raw_input.get("transcript_path")
    session_context = ""
    if transcript_path:
        if gate in ("critic", "custodiet"):
            from lib.session_reader import build_critic_session_context

            try:
                session_context = build_critic_session_context(transcript_path)
            except Exception:
                pass  # Degrade context, not the file creation
        else:
            from lib.session_reader import build_rich_session_context

            try:
                session_context = build_rich_session_context(transcript_path)
            except Exception:
                pass  # Degrade context, not the file creation

    axioms, heuristics, skills = hook_utils.load_framework_content()
    custodiet_mode = os.environ.get("CUSTODIET_MODE", "block").lower()

    registry = TemplateRegistry.instance()

    # Try rich context template first, then simple audit template.
    # If BOTH fail, raise — don't silently return None.
    render_errors: list[str] = []
    content = None

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
    except (KeyError, ValueError, FileNotFoundError) as e:
        render_errors.append(f"{gate}.context: {e}")
        try:
            content = registry.render(
                f"{gate}.audit",
                {
                    "session_id": session_id,
                    "gate_name": gate,
                    "tool_name": ctx.tool_name or "unknown",
                },
            )
        except (KeyError, ValueError, FileNotFoundError) as e2:
            render_errors.append(f"{gate}.audit: {e2}")

    if content is None:
        raise RuntimeError(
            f"create_audit_file failed: all templates failed for gate '{gate}': "
            + "; ".join(render_errors)
        )

    # Write to predictable gate file path — fail fast on disk errors
    input_data = ctx.raw_input or {}
    if "session_id" not in input_data:
        input_data = {**input_data, "session_id": session_id}
    gate_path = get_gate_file_path(gate, session_id, input_data)
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(content, encoding="utf-8")
    return gate_path


def execute_custom_action(
    name: str, ctx: HookContext, state: GateState, session_state: SessionState
) -> GateResult | None:
    """Execute a named custom action.

    Custom actions that produce temp files MUST set state.metrics["temp_path"]
    before returning. Policy templates depend on this metric being present.
    """
    if name == "hydrate_prompt":
        from lib.hydration import build_hydration_instruction

        prompt = ctx.raw_input.get("prompt")
        if not prompt:
            prompt = ctx.raw_input.get("message") or ctx.raw_input.get("intent")

        if not prompt:
            raise RuntimeError(
                "hydrate_prompt: no prompt found in raw_input "
                f"(keys: {list(ctx.raw_input.keys())})"
            )

        transcript_path = ctx.transcript_path or ctx.raw_input.get("transcript_path")

        instruction = build_hydration_instruction(
            ctx.session_id, prompt, transcript_path, state=session_state
        )

        temp_path = session_state.get_gate("hydration").metrics.get("temp_path")
        if not temp_path:
            raise RuntimeError(
                "hydrate_prompt: build_hydration_instruction completed but "
                "temp_path not set in hydration gate metrics"
            )

        return GateResult.allow(
            system_message=f"Hydration ready: {temp_path}", context_injection=instruction
        )

    if name == "prepare_compliance_report":
        temp_path = create_audit_file(ctx.session_id, "custodiet", ctx)
        state.metrics["temp_path"] = str(temp_path)

        registry = TemplateRegistry.instance()
        instruction = registry.render(
            "custodiet.instruction", {"temp_path": str(temp_path)}
        )

        return GateResult.allow(
            system_message=f"Compliance report ready: {temp_path}",
            context_injection=instruction,
        )

    if name == "prepare_critic_review":
        temp_path = create_audit_file(ctx.session_id, "critic", ctx)
        state.metrics["temp_path"] = str(temp_path)
        return None

    if name == "prepare_qa_review":
        temp_path = create_audit_file(ctx.session_id, "qa", ctx)
        state.metrics["temp_path"] = str(temp_path)
        return None

    return None
