import logging
from pathlib import Path

from hooks.schemas import HookContext

logger = logging.getLogger(__name__)

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
        from lib.session_reader import build_rich_session_context

        try:
            session_context = build_rich_session_context(transcript_path)
        except Exception:
            logger.warning(
                "Failed to build rich session context for transcript_path=%s",
                transcript_path,
                exc_info=True,
            )

    logger.info(
        "create_audit_file: gate=%s transcript_path=%s session_context_len=%d",
        gate,
        transcript_path,
        len(session_context),
    )

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

    NOTE: prepare_compliance_report was removed — custodiet gate replaced by
    CC auto mode classifier. QA and other gate actions remain.
    """
    return None
