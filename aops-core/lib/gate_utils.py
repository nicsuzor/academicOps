from pathlib import Path

from hooks.schemas import HookContext

from lib import hook_utils
from lib.template_registry import TemplateRegistry


def create_audit_file(session_id: str, gate: str, ctx: HookContext) -> Path | None:
    """Create rich audit file for gate using TemplateRegistry."""
    # Align temp category with hydrator per user request
    category = "hydrator"

    # Try to load rich context if possible
    # Critic and custodiet get deep session context (full history, reasoning, diffs)
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

    # Import os here to avoid top-level import issues if not needed
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

    # Write to temp (using aligned category)
    try:
        temp_dir = hook_utils.get_hook_temp_dir(category, ctx.raw_input)
        return hook_utils.write_temp_file(content, temp_dir, f"audit_{gate}_")
    except Exception:
        return None
