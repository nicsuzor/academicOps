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
    """Turns of full-detail transcript context to include in an exit-reflection
    audit file.

    Historically sized to the (now-retired) RBG PreToolUse cadence threshold
    + 2 overlap turns, so the periodic in-session check and the end-of-session
    audit shared one windowed builder without a full-session re-send
    (aops-5bc65f76). The periodic cadence gate is gone (aops_4c2949d9,
    turn-based rbg retirement), but the sizing rationale — a bounded window,
    not the whole transcript — still applies to the exit_reflection gate's
    audit file, so the constant survives decoupled from any gate/env var.
    """
    return 52


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

    Both the RBG (PreToolUse cadence) and the rbg-review (Stop) dispatch
    now share ONE windowed context builder — ``build_audit_session_context``
    capped to the last n+2 turns (n = RBG cadence; aops-5bc65f76). The
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

        if gate == "exit_reflection" and entries:
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
        # a truncated read is detectable. The rbg-lens auditor requires this
        # via `tail -3` (aops-e4e90f31, #1976) — carried over to the
        # consolidated exit_reflection audit file (aops_4c2949d9).
        if content and gate == "exit_reflection":
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
    if name == "prepare_exit_reflection_full":
        # Build the exit_reflection audit file (session transcript + bound-task
        # directive) so the exit_reflection.policy_context template
        # ({temp_path}) has a real file to point the FULL-tier checklist at:
        # RBG-lens self-audit, durable capture, commit/push/PR, /learn,
        # /remember, prose handover. Fires on Stop while the exit_reflection
        # gate is CLOSED and the session is in full scope (task-bound, did
        # work this turn). On failure, return None so the gate engine falls
        # back to the policy's default verdict rather than bypassing the gate
        # (aops_4c2949d9 — replaces prepare_compliance_report/prepare_qa_review/
        # prepare_rbg_review, all retired).
        try:
            temp_path = create_audit_file(
                ctx.session_id,
                "exit_reflection",
                ctx,
                bound_task_id=session_state.main_agent.current_task,
            )
            state.metrics["temp_path"] = str(temp_path)
            return GateResult.allow(
                system_message=f"Exit-reflection record ready: {temp_path}",
            )
        except Exception as e:
            logger.warning("Failed to create exit-reflection audit file: %s", e)
            return None  # allow-fallback: None -> engine falls back to the policy's default DENY (gate still blocks; never bypasses)

    if name == "set_turn_did_work":
        # Mark the CURRENT TURN as having done real work (write tool or task
        # claim). The exit_reflection gate's FULL-tier scope check
        # (turn_did_work) uses this to decide whether the full checklist is
        # owed this turn (aops-16a15a05). Read-only turns never trigger this
        # action and get the lightweight tier instead.
        session_state.turn_did_work = True
        return None

    if name == "bind_task_from_tool_input":
        # Extract the task id from an update_task/claim_task PostToolUse call
        # and record it on session_state.main_agent.current_task, then mark
        # the turn as having done work (a claim IS work). Nothing in the
        # codebase populated main_agent.current_task before this action
        # existed — has_bound_task/is_exit_reflection_full_scope read it, but
        # it was always None in production, so the FULL-tier scope check
        # would never trigger for a genuinely task-bound session (found while
        # verifying aops_4c2949d9's fresh-session AC empirically). PKB MCP
        # tools (update_task, claim_task) both take the task id as `id`.
        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else None
        task_id = tool_input.get("id") if tool_input else None
        if task_id:
            session_state.main_agent.current_task = str(task_id)
        session_state.turn_did_work = True
        return None

    if name == "reset_turn_did_work":
        # Fired on the UserPromptSubmit re-arm trigger (start of a new turn):
        # turn_did_work must start False each turn so a no-op turn is exempt
        # from the full checklist even if an earlier turn in the same session
        # wrote something (aops_d18b2d4b — was never reset, so one write
        # latched the full ceremony onto every later turn for the rest of the
        # session).
        session_state.turn_did_work = False
        return None

    return None
