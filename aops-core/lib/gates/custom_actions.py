import logging
from pathlib import Path

from lib.gate_model import GateResult
from lib.gate_types import GateState
from lib.hook_context import HookContext
from lib.session_paths import get_gate_file_path
from lib.session_state import SessionState
from lib.template_registry import TemplateRegistry

logger = logging.getLogger(__name__)


def _audit_window_turns() -> int:
    """The single context window = enforcer cadence (n) + 2 overlap turns.

    n is the enforcer ops-counter threshold that triggers the compliance gate
    (ENFORCER_TOOL_CALL_THRESHOLD). rbg fires every n tool-calls, so an n+2
    window overlaps the previous window by 2 turns and a clean sliding window
    covers every turn at full detail without a full-session re-send
    (aops-5bc65f76). Both the enforcer (PreToolUse) and rbg-review (Stop)
    dispatches share this one window.
    """
    from hooks.gate_config import ENFORCER_TOOL_CALL_THRESHOLD

    return ENFORCER_TOOL_CALL_THRESHOLD + 2


def _bound_task_directive(task_id: str | None) -> str:
    """Render the bound task's initial directive (title + body) for the rbg
    review payload, so rbg can verify the session stayed on-target and within
    authority (aops-5bc65f76).

    Best-effort: returns "" when no task is bound (un-armed session) or the PKB
    lookup is unavailable/fails — the audit then proceeds without the directive
    header rather than blocking.
    """
    if not task_id:
        return ""
    try:
        from polecat import pkb_bridge

        task = pkb_bridge.get_task(task_id)
    except Exception:
        logger.warning("Failed to load bound-task directive for %s", task_id, exc_info=True)
        return (
            ""  # allow-fallback: best-effort directive; PKB lookup failure must not block the audit
        )
    if not task:
        return ""
    title = (task.title or "").strip()  # allow-fallback: title optional; body may carry the brief
    body = (task.body or "").strip()  # allow-fallback: body optional free text
    if not title and not body:
        return ""
    parts = ["## Bound Task Directive (verify the session stayed on-target / within authority)", ""]
    if title:
        parts.append(f"**{task_id}** — {title}")
        parts.append("")
    if body:
        parts.append(body)
        parts.append("")
    return "\n".join(parts)


def create_audit_file(
    session_id: str,
    gate: str,
    ctx: HookContext,
    bound_task_id: str | None = None,
) -> Path:
    """Create rich audit file for gate using TemplateRegistry.

    Both the enforcer (PreToolUse cadence) and the rbg-review (Stop) dispatch
    now share ONE windowed context builder — ``build_audit_session_context``
    capped to the last n+2 turns (n = enforcer cadence; aops-5bc65f76). The
    rbg-review payload additionally prepends the bound task's initial directive
    (when ``bound_task_id`` is set) so rbg can verify the session stayed
    on-target and within authority.

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
        from lib.session_reader import (
            SessionProcessor,
            build_audit_session_context,
        )

        # Parse transcript once, reuse for both context building and skill extraction
        entries = None
        try:
            processor = SessionProcessor()
            _, entries, _ = processor.parse_session_file(
                Path(transcript_path), load_agents=False, load_hooks=False
            )
        except Exception:
            logger.warning("Failed to parse transcript for %s audit", gate, exc_info=True)

        # ONE windowed builder for both triggers: last n+2 turns at full detail.
        try:
            session_context = build_audit_session_context(
                transcript_path, entries=entries, max_turns=_audit_window_turns()
            )
        except Exception:
            logger.warning(
                "Failed to build windowed audit context for transcript_path=%s",
                transcript_path,
                exc_info=True,
            )

        if gate == "enforcer" and entries:
            from lib.session_reader import _extract_recent_skill, load_skill_scope

            try:
                active_skill = _extract_recent_skill(entries)
                if active_skill:
                    # Strip namespace prefix (e.g. "aops-core:learn" -> "learn")
                    skill_short = active_skill.split(":")[-1]
                    skill_scope = load_skill_scope(skill_short)
            except Exception:
                logger.warning("Failed to extract skill scope", exc_info=True)

    # Always prepend the bound task's directive to the rbg review payload so the
    # reviewer can check on-target / within-authority. Omitted gracefully when
    # no task is bound (un-armed session). (aops-5bc65f76)
    directive = _bound_task_directive(bound_task_id)
    if directive:
        session_context = f"{directive}\n{session_context}" if session_context else directive

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
                "active_skill": active_skill
                or "none",  # allow-fallback: no active skill is a valid state
                "skill_scope": skill_scope
                or "",  # allow-fallback: empty scope when no skill / scope file absent
            },
        )

        # Coverage sentinel: must be the last line of the rendered file so that
        # a truncated read is detectable. The rbg auditor requires this via
        # `tail -3` (aops-e4e90f31, #1976).
        if content and gate == "enforcer":
            import re

            # Extract turn count from session_context if possible, fallback to ?
            turns = re.findall(r"#### Turn (\d+)", session_context)
            turn_num = turns[-1] if turns else "?"

            # Use rstrip to ensure no trailing newlines from the template
            # push the sentinel out of the `tail -3` window
            content = content.rstrip() + f"\n\n<!-- audit-complete: {turn_num} turns -->\n"

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

    # Write to predictable gate file path — fail fast on disk errors. Thread
    # client_type (alongside transcript_path) so the file honours the session's
    # harness routing and never silently falls back to the Claude project dir.
    gate_path = get_gate_file_path(
        gate, session_id, transcript_path=ctx.transcript_path, client_type=ctx.client_type
    )
    gate_path.parent.mkdir(parents=True, exist_ok=True)

    # Scrub known secrets before writing to the gate/narrative file (aops-efc4592f)
    from lib.secret_redaction import redact_secrets

    content_redacted = redact_secrets(content)

    gate_path.write_text(content_redacted, encoding="utf-8")
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
            temp_path = create_audit_file(
                ctx.session_id,
                "enforcer",
                ctx,
                bound_task_id=session_state.main_agent.current_task,
            )
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
            temp_path = create_audit_file(
                ctx.session_id,
                "qa",
                ctx,
                bound_task_id=session_state.main_agent.current_task,
            )
            state.metrics["temp_path"] = str(temp_path)
            return GateResult.allow(
                system_message=f"QA review file ready: {temp_path}",
            )
        except Exception as e:
            logger.warning("Failed to create QA audit file: %s", e)
            return None

    if name == "prepare_rbg_review":
        # Build the rbg-review audit file from the session transcript so the
        # rbg_review.policy_context template ({temp_path}) has a real file to
        # point the agent's rbg dispatch at. Fires on Stop while the gate is
        # CLOSED (armed and rbg has not run this turn). Mirrors prepare_qa_review.
        # On failure, return None so the gate engine falls back to the policy's
        # default verdict (block) rather than bypassing the gate.
        try:
            temp_path = create_audit_file(ctx.session_id, "rbg_review", ctx)
            state.metrics["temp_path"] = str(temp_path)
            return GateResult.allow(
                system_message=f"RBG review file ready: {temp_path}",
            )
        except Exception as e:
            logger.warning("Failed to create rbg-review audit file: %s", e)
            return None  # allow-fallback: None -> engine falls back to the policy's default DENY (gate still blocks; never bypasses)

    if name == "update_todo_in_progress":
        # Track whether the agent currently has an in-progress todo item.
        # Called via PostToolUse trigger on TodoWrite. (#319 mid-work false BLOCK)
        todos = ctx.tool_input.get("todos", []) if isinstance(ctx.tool_input, dict) else []
        has_in_progress = any(
            isinstance(t, dict) and t.get("status") == "in_progress" for t in todos
        )
        state.metrics["has_in_progress_todo"] = has_in_progress
        return None

    if name == "set_session_did_work":
        # Mark the session as having done real work (write tool or task claim).
        # The handover gate policies check session_did_work to decide whether
        # a full handover is required (aops-16a15a05). Read-only sessions
        # never trigger this action and bypass the handover gate.
        session_state.session_did_work = True
        return None

    return None
