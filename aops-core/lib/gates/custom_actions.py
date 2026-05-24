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
    active_skill = None
    skill_scope = None
    if transcript_path:
        if gate == "enforcer":
            from lib.session_reader import (
                SessionProcessor,
                _extract_recent_skill,
                build_audit_session_context,
                load_skill_scope,
            )

            # Parse transcript once, reuse for both context building and skill extraction
            entries = None
            try:
                processor = SessionProcessor()
                _, entries, _ = processor.parse_session_file(
                    Path(transcript_path), load_agents=False, load_hooks=False
                )
            except Exception:
                logger.warning("Failed to parse transcript for enforcer audit", exc_info=True)

            try:
                session_context = build_audit_session_context(transcript_path, entries=entries)
            except Exception:
                logger.warning(
                    "Failed to build audit session context for transcript_path=%s",
                    transcript_path,
                    exc_info=True,
                )

            if entries:
                try:
                    active_skill = _extract_recent_skill(entries)
                    if active_skill:
                        # Strip namespace prefix (e.g. "aops-core:learn" -> "learn")
                        skill_short = active_skill.split(":")[-1]
                        skill_scope = load_skill_scope(skill_short)
                except Exception:
                    logger.warning("Failed to extract skill scope", exc_info=True)
        else:
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
                "active_skill": active_skill or "none",
                "skill_scope": skill_scope or "",
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
    gate_path = get_gate_file_path(gate, session_id, transcript_path=ctx.transcript_path)
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
    if name == "prepare_compliance_report":
        # Memoized audit file: avoid re-parsing the full transcript when it
        # hasn't grown since the last compliance check.  Stores the transcript
        # byte size at last parse in state.metrics["transcript_parse_pos"].
        # If the audit file already exists at the same transcript size, reuse
        # it instead of rebuilding. (#331 O(n²) token cost)
        transcript_path_str = ctx.transcript_path or ctx.raw_input.get("transcript_path")
        existing_temp = state.metrics.get("temp_path")
        stored_pos = state.metrics.get("transcript_parse_pos", -1)
        reuse = False
        if transcript_path_str and existing_temp:
            transcript_file = Path(transcript_path_str)
            if transcript_file.exists() and Path(existing_temp).exists():
                current_size = transcript_file.stat().st_size
                if current_size == stored_pos:
                    reuse = True
                    temp_path = Path(existing_temp)

        if not reuse:
            temp_path = create_audit_file(ctx.session_id, "enforcer", ctx)
            state.metrics["temp_path"] = str(temp_path)
            if transcript_path_str:
                tf = Path(transcript_path_str)
                state.metrics["transcript_parse_pos"] = tf.stat().st_size if tf.exists() else -1

        registry = TemplateRegistry.instance()
        instruction = registry.render("enforcer.instruction", {"temp_path": str(temp_path)})

        return GateResult.allow(
            system_message=f"Compliance report ready: {temp_path}",
            context_injection=instruction,
        )

    if name == "prepare_qa_review":
        # Build the qa-context audit file from the session transcript so the
        # qa.policy_context template ({temp_path}) has a real file to point at.
        # Fires on Stop while qa gate is CLOSED; no memoization since the gate
        # only evaluates this once per Stop attempt.
        # On failure, return None so the gate engine falls back to the policy's
        # default verdict (block in QA_GATE_MODE) rather than bypassing the gate.
        try:
            temp_path = create_audit_file(ctx.session_id, "qa", ctx)
            state.metrics["temp_path"] = str(temp_path)
            return GateResult.allow(
                system_message=f"QA review file ready: {temp_path}",
            )
        except Exception as e:
            logger.warning("Failed to create QA audit file: %s", e)
            return None

    if name == "update_todo_in_progress":
        # Track whether the agent currently has an in-progress todo item.
        # Called via PostToolUse trigger on TodoWrite. (#319 mid-work false BLOCK)
        todos = ctx.tool_input.get("todos", []) if isinstance(ctx.tool_input, dict) else []
        has_in_progress = any(
            isinstance(t, dict) and t.get("status") == "in_progress" for t in todos
        )
        state.metrics["has_in_progress_todo"] = has_in_progress
        return None

    if name == "set_handover_invoked":
        session_state.state["handover_skill_invoked"] = True
        return None

    if name == "reset_handover_invoked":
        session_state.state["handover_skill_invoked"] = False
        return None

    if name == "set_qa_verified":
        session_state.state["qa_verified"] = True
        return None

    if name == "reset_qa_verified":
        session_state.state["qa_verified"] = False
        return None

    return None
