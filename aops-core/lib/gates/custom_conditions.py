import re

from lib.gate_types import GateState
from lib.hook_context import HookContext
from lib.session_state import SessionState
from lib.tool_categories import get_tool_category

# =============================================================================
# SENTINEL GATE — destructive-env-op detection
# =============================================================================
# Protected user-environment paths. Matches both tilde-expanded (~) and
# absolute home-dir forms (/home/user or /Users/user on macOS). Case-
# insensitive so macOS case-folded paths and adversarial mixed-case commands
# are caught.
_PROTECTED_PATH_RE = re.compile(
    r"(?:~|(?:/home|/Users)/[^/\s]+)"
    r"/\."
    r"(?:"
    r"gemini/extensions"  # ~/.gemini/extensions/
    r"|gemini/settings\.json"  # ~/.gemini/settings.json
    r"|claude/plugins"  # ~/.claude/plugins/
    r"|claude/[^/\s]+\.json"  # ~/.claude/*.json (e.g. settings.json)
    r"|config/gemini"  # ~/.config/gemini/
    r")",
    re.IGNORECASE,
)

# Destructive shell commands. Word-bounded so rm doesn't match inside rmdir
# and vice versa; case-insensitive to block RM, Rm, TRUNCATE, etc.
_DESTRUCTIVE_CMD_RE = re.compile(
    r"\b(?:rm|mv|rmdir|unlink|truncate)\b",
    re.IGNORECASE,
)

# Tool name sets for sentinel gate dispatch.
_SENTINEL_SHELL_TOOLS: frozenset[str] = frozenset(
    {"Bash", "run_shell_command", "shell", "execute_code"}
)
_SENTINEL_WRITE_FILE_TOOLS: frozenset[str] = frozenset({"Edit", "Write", "write_file", "replace"})


def check_custom_condition(
    name: str, ctx: HookContext, state: GateState, session_state: SessionState
) -> bool:
    """
    Evaluate a named custom condition.
    """
    if name == "is_destructive_env_op":
        # Sentinel gate: block destructive ops on protected user-env paths.
        # Shell tools: command must contain BOTH a destructive verb AND a
        # protected path reference (and-logic to reduce false positives).
        # Write-file tools: ANY write to a protected path is blocked —
        # no destructive-verb check needed because the write itself is the
        # destructive op (Edit/Write will overwrite or truncate the file).
        tool_name = ctx.tool_name or ""
        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else {}

        if tool_name in _SENTINEL_SHELL_TOOLS:
            command = tool_input.get("command", "")
            if not isinstance(command, str):
                return False
            return bool(_DESTRUCTIVE_CMD_RE.search(command) and _PROTECTED_PATH_RE.search(command))

        if tool_name in _SENTINEL_WRITE_FILE_TOOLS:
            # file_path is Claude Code field; path is Gemini write_file field
            file_path = tool_input.get("file_path") or tool_input.get("path") or ""
            if not isinstance(file_path, str):
                return False
            return bool(_PROTECTED_PATH_RE.search(file_path))

        return False

    if name == "is_write_tool":
        # Treat shell tools as read-only when the handover gate is sticky
        # (post-skill) or no task is bound — prevents gates from re-closing
        # on discovery/status commands (e.g. git status after /end-session).
        handover_state = session_state.gates.get("handover")
        if (handover_state and handover_state.sticky) or not session_state.main_agent.current_task:
            if ctx.tool_name in ("Bash", "run_shell_command", "shell", "execute_code"):
                return False

        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else None
        return ctx.tool_name is not None and get_tool_category(ctx.tool_name, tool_input) == "write"

    if name == "not_mid_edit":
        # Defer RBG block while agent has an in-progress todo item.
        # The RBG trigger on TodoWrite PostToolUse keeps this metric
        # up to date. False (condition not met) when mid-edit, deferring the
        # block until the agent has finished its current sub-task. (#319)
        return not state.metrics.get("has_in_progress_todo", False)

    if name == "is_ida_active":
        # IDA gate trigger: fires when IDA mode is warn or block (not off).
        # Used by the AskUserQuestion trigger which must never deny — the
        # trigger delivers advisory context injection only (GateResult.allow).
        # Posture resolves via gate_config (the polecat-vs-not posture axis),
        # the same mechanism the handover gate uses — NOT a bare os.environ read.
        from hooks.gate_config import IDA_GATE_MODE

        return IDA_GATE_MODE in ("warn", "block", "deny")

    if name == "is_ida_block_mode":
        # IDA gate policy: active only when IDA_GATE_MODE is blocking.
        # Separating block vs warn into distinct policies lets each choose
        # appropriate message channels (context_key vs message_key) so
        # warn mode doesn't inadvertently upgrade Stop to decision=block.
        from hooks.gate_config import IDA_GATE_MODE

        return IDA_GATE_MODE in ("block", "deny")

    if name == "is_ida_warn_mode":
        # IDA gate policy: active only when IDA_GATE_MODE is warn.
        # Warn mode delivers the advisory via system_message only (user-visible)
        # rather than context_injection, so output_for_claude does not upgrade
        # the WARN verdict to decision=block for the Stop hook.
        from hooks.gate_config import IDA_GATE_MODE

        return IDA_GATE_MODE == "warn"

    if name == "is_qa_block_mode":
        # QA gate policy: active only when QA_GATE_MODE is blocking.
        # Separating block vs warn into distinct policies lets each choose
        # appropriate message channels (context_key vs message_key) so
        # warn mode doesn't inadvertently upgrade Stop to decision=block.
        # Posture resolves via gate_config (the polecat-vs-not posture axis),
        # the same mechanism the other gates use — NOT a bare os.environ read.
        from hooks.gate_config import QA_GATE_MODE

        return QA_GATE_MODE in ("block", "deny")

    if name == "is_qa_warn_mode":
        # QA gate policy: active only when QA_GATE_MODE is warn.
        # Warn mode delivers the advisory via system_message only (user-visible)
        # rather than context_injection, so output_for_claude does not upgrade
        # the WARN verdict to decision=block for the Stop hook.
        from hooks.gate_config import QA_GATE_MODE

        return QA_GATE_MODE == "warn"

    if name == "is_rbg_review_block_mode":
        # RBG-review gate policy: active only when RBG_REVIEW_GATE_MODE is
        # blocking. Block mode delivers the dispatch instruction via the
        # context_injection channel (upgraded to decision=block on Stop), which
        # is what makes the agent actually run rbg. This is the directive's
        # required posture: a real DENY until rbg has run for the armed turn.
        from hooks.gate_config import RBG_REVIEW_GATE_MODE

        return RBG_REVIEW_GATE_MODE in ("block", "deny")

    if name == "is_rbg_review_warn_mode":
        # RBG-review gate policy: active only when RBG_REVIEW_GATE_MODE is warn.
        # Warn still injects the dispatch instruction (block-once per turn via
        # the warn+context_injection upgrade path), but does not hard-hold the
        # session. Provided for parity / staged rollout; default mode is block.
        from hooks.gate_config import RBG_REVIEW_GATE_MODE

        return RBG_REVIEW_GATE_MODE == "warn"

    if name == "is_handover_block_mode":
        # Handover gate policy: active only when HANDOVER_GATE_MODE is blocking
        # AND the session did real work (write tool or task claim).
        # Read-only sessions (session_did_work=False) are exempt — they need no
        # structured handover (aops-16a15a05).
        if not session_state.session_did_work:
            return False
        from hooks.gate_config import HANDOVER_GATE_MODE

        return HANDOVER_GATE_MODE in ("block", "deny")

    if name == "is_handover_warn_mode":
        # Handover gate policy: active only when HANDOVER_GATE_MODE is warn
        # AND the session did real work. Same read-only exemption as block mode.
        if not session_state.session_did_work:
            return False
        from hooks.gate_config import HANDOVER_GATE_MODE

        # D1 (uniform stop-gate behaviour): warn hard-blocks ONCE per turn like
        # every other warn gate — the single forced continuation IS the nudge,
        # so the former soft interactive rate-limiting (spec mem-438429c5
        # §5.4-5.5) is superseded and removed. Fire-once (the warn-mode Stop
        # trigger in definitions.py) is now the whole cadence.
        return HANDOVER_GATE_MODE == "warn"

    if name == "has_bound_task":
        return bool(session_state.main_agent.current_task)

    if name == "no_unevidenced_completion_claim":
        # Handover satisfier guard (epic aops-262def9f WI2a): the skill-open
        # triggers (/end-session, /dump, /continue, handover templates) may
        # only open the gate when no completion claim in the session ledger
        # lacks the evidence contract. /dump with NO claim in-session stays
        # evidence-free (emergency bail preserved); a claim made earlier
        # in-session cannot be laundered by a later /dump. The ledger is
        # written by the router at PostToolUse (works in is_subagent
        # sessions, where gate dispatch skips tool-call events).
        from lib.verification_evidence import has_unevidenced_completion_claim

        return not has_unevidenced_completion_claim(session_state)

    if name == "handover_unevidenced_claim":
        # Handover Stop policy (epic aops-262def9f WI2a): DENY the exit while
        # a completion claim without contract-conformant evidence stands.
        # Mode-aware like the sibling policies (off → inert); deliberately
        # does NOT require session_did_work — a completion claim is a claim
        # about work regardless of which tools this session used. Warn-mode
        # fire-once and the block-mode stop_deny_count escape hatch behave as
        # for every other stop gate (the policy keys on gate CLOSED, which
        # the ledger enforces by force-closing on an unevidenced claim).
        from hooks.gate_config import HANDOVER_GATE_MODE

        if HANDOVER_GATE_MODE not in ("warn", "block", "deny"):
            return False
        from lib.verification_evidence import has_unevidenced_completion_claim

        return has_unevidenced_completion_claim(session_state)

    if name == "verifier_verdict_present":
        # qa satisfier (epic aops-262def9f WI3b): the verifier subagent's OWN
        # result channel (last_assistant_message on SubagentStop / Agent
        # tool_response content on PostToolUse) must carry a parseable
        # PASS/FAIL/REVISE verdict. A name-match alone (a dispatched-but-empty
        # marsha/qa/verify run) no longer satisfies the gate, and producer
        # prose cannot reach these channels — that is the independence this
        # boundary can enforce. Records what it parsed in gate metrics for
        # observability (side effect on True, mirroring custom_action style).
        from lib.verification_evidence import parse_verifier_verdict, verifier_result_text

        verdict = parse_verifier_verdict(verifier_result_text(ctx))
        if verdict is None:
            return False
        state.metrics["last_verifier_verdict"] = verdict
        state.metrics["last_verifier_type"] = (
            ctx.subagent_type or ""
        )  # allow-fallback: observability metric only
        return True

    if name == "session_did_work":
        # True if the session has used a write tool or claimed a task.
        # Used directly in triggers/conditions that need this signal without
        # combining it with a gate-mode check (aops-16a15a05).
        return session_state.session_did_work

    return False
