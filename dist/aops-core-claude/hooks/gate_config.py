"""
Gate Configuration: gate-mode env-var resolution and slash-command detection.

Tool categorization (TOOL_CATEGORIES, get_tool_category, is_never_block,
COMPLIANCE_SUBAGENT_TYPES, SPAWN_TOOLS, extract_subagent_type) lives in
`lib/tool_categories.py` — it is consumed by gate-engine code in `lib/gates/*`
and must not live in the `hooks/` layer. Import those names directly from
`lib.tool_categories`; this module no longer re-exports them.
"""

import os
from typing import TYPE_CHECKING

__all__ = [
    # Gate modes (PEP 562 lazy attrs)
    "EXIT_REFLECTION_GATE_MODE",
    "IDA_GATE_MODE",
    "HYDRATION_GATE_MODE",
    "EXIT_REFLECTION_DEGRADE_THRESHOLD",
    "GATE_MODE_VARS",
    # Slash-command hygiene
    "SLASH_COMMAND_PROMPT_PATTERNS",
]

if TYPE_CHECKING:
    # Declared here so type checkers see precise types for PEP 562 lazy attrs.
    # At runtime these names come from __getattr__ below.
    EXIT_REFLECTION_GATE_MODE: str
    IDA_GATE_MODE: str
    HYDRATION_GATE_MODE: str
    EXIT_REFLECTION_DEGRADE_THRESHOLD: int


# =============================================================================
# SLASH-COMMAND PROMPT DETECTION
# =============================================================================
# A UserPromptSubmit whose prompt carries one of these markers is a
# slash-command turn — i.e. a skill invocation (`/end-session`, `/dump`,
# `/remember`, `/planner`, ...). Such a turn owns its own finishing format, so
# the per-turn session-end gates (qa, handover, ida) must NOT re-arm (close) on
# it. Re-arming would fire the gate a second time on the Stop that follows the
# skill — e.g. a redundant ida honesty reflection right after /end-session has
# already produced its own reflection blocks.
#
# These patterns are used ONLY as `prompt_exclude_patterns` on the gates'
# UserPromptSubmit -> CLOSED re-arm triggers. They SUPPRESS the close; they
# never open a gate. A gate keeps whatever status it already held.
#
# Surface formats (verified against real transcripts / existing triggers):
#   Claude Code: the prompt carries `<command-name>/foo</command-name>`
#                (with sibling <command-message>/<command-args> tags; tag order
#                varies, so we match the tag anywhere, not anchored).
#   Gemini CLI:  the slash command is injected as `# /foo — ...`.
#
# A BARE leading slash is deliberately NOT matched: real user prompts can be
# bare file paths (e.g. "/home/nic/.../session-rbg.md"), which must still
# re-arm the gate. Matching `^/` would silently disarm the honesty/handover/qa
# gates on any path-only prompt. The `<command-name>` tag and the Gemini `# /`
# form are unambiguous; a bare path is not.
SLASH_COMMAND_PROMPT_PATTERNS: list[str] = [
    r"<command-name>\s*/[a-zA-Z0-9_-]+\s*</command-name>",  # Claude Code slash command (skill invocation)
    r"^\s*#\s*/(?:end[-_]session|dump|remember|planner|continue)\b",  # Gemini CLI slash-command injection (e.g. "# /dump …")
]

# =============================================================================
# GATE MODES
# =============================================================================
# Gate enforcement modes are read directly from environment variables — the
# ONLY lever for per-surface gate posture. There is no code-level session-type
# or polecat-vs-interactive branching anywhere in the gate engine (removed —
# see aops-core/lib/gates/{engine,definitions}.py history): every gate has one
# uniform initial_status and one uniform set of triggers for every session.
# Whatever differs across surfaces (polecat run vs polecat crew vs an ad hoc
# interactive CLI session) differs SOLELY because something set a different
# *_GATE_MODE value for that surface — never because the gate code inspected
# session_type. The polecat launcher (polecat/cli.py) resolves the per-mode
# posture from polecat.yaml on the host and stages the values into the
# container as env vars; a bare interactive CLI session (no polecat.yaml) can
# still override these via its own `.claude/settings.json` env block or shell
# profile. Hooks never read polecat.yaml directly; they only read these vars.
#
# When no env var is set at all (fresh-install dev machine, no polecat.yaml,
# no settings.json override), the defaults below apply.
#
# IDA_GATE_MODE default is "warn", not "off" (aops_5ea32596 / note_296e5520
# §3 — the face-scoped ida honesty gate). This bare-fallback path is reached
# ONLY by sessions with no polecat launcher at all (see GATES.md's `ida` gate
# section): every polecat run/crew session always gets an explicit
# IDA_GATE_MODE injected by lib/polecat_config.py's for_mode() resolution
# (session_defaults.gates.ida, currently "off" — see
# polecat/defaults/polecat.yaml.example), so this fallback never fires for a
# headless/dispatched worker. What it DOES cover is the bare interactive CLI
# — a researcher running Claude/Gemini directly against the ida agent with no
# container — which is exactly the head/face surface the gate exists to
# protect (specs/interactive-experience/head-role-charter.md). Defaulting
# that path to "warn" is what makes the gate fire on the head surface and
# stay structurally absent everywhere else, without any code-level
# session-type branching (still forbidden — see the module docstring above).
_GATE_MODES = {
    "HYDRATION_GATE_MODE": "off",
    "EXIT_REFLECTION_GATE_MODE": "off",
    "IDA_GATE_MODE": "warn",
}

# Canonical list of gate-mode env-var names — the single source of truth for
# every consumer that needs to enumerate them (SessionStart summary/anchoring,
# router.py's test/ad-hoc fallback). Do not hardcode a second copy of this
# list elsewhere; import this instead.
GATE_MODE_VARS: list[str] = list(_GATE_MODES)


# Consecutive Stop-DENYs from the exit_reflection gate's full (task-bound)
# tier in one turn before it degrades to WARN-and-allow (loud, not silent).
# Matches the 5-block router-level safety override; the escape-hatch is
# failure-degradation only, never a normal bypass. An honest-failure
# release_task call (status=blocked/review/partial/cancelled) is also a legal,
# immediate exit — see the exit_reflection gate's release_task trigger in
# lib/gates/definitions.py — so this threshold is a backstop, not the primary
# escape valve (aops_4c2949d9).
_EXIT_REFLECTION_DEGRADE_THRESHOLD_DEFAULT = 5


def __getattr__(name: str):  # PEP 562 module-level lazy attrs
    if name in _GATE_MODES:
        val = os.environ.get(name)
        if val is None:
            import sys

            print(
                f"WARNING: Gate mode '{name}' not set in environment, falling back to default '{_GATE_MODES[name]}'",
                file=sys.stderr,
            )
            return _GATE_MODES[name]
        return val
    if name == "EXIT_REFLECTION_DEGRADE_THRESHOLD":
        raw = os.environ.get("EXIT_REFLECTION_DEGRADE_THRESHOLD")
        if raw is None:
            _warn_threshold_fallback(name, raw, _EXIT_REFLECTION_DEGRADE_THRESHOLD_DEFAULT)
            return _EXIT_REFLECTION_DEGRADE_THRESHOLD_DEFAULT
        try:
            return int(raw)
        except ValueError:
            _warn_threshold_fallback(name, raw, _EXIT_REFLECTION_DEGRADE_THRESHOLD_DEFAULT)
            return _EXIT_REFLECTION_DEGRADE_THRESHOLD_DEFAULT
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _warn_threshold_fallback(name: str, raw: str | None, default: int) -> None:
    """Loudly warn on a threshold env-var fallback (aops_47d0a754).

    Threshold env vars (e.g. EXIT_REFLECTION_DEGRADE_THRESHOLD) used to fall
    back to a hardcoded default silently — unlike every *_GATE_MODE var,
    which prints a WARNING to stderr on fallback (see the `name in
    _GATE_MODES` branch above). A silently-defaulted threshold degrades
    enforcement calibration invisibly: if the env var is dropped by a
    misconfigured launcher, the gate quietly enforces an arbitrary value
    instead of the one the operator intended. Match the gate-mode pattern
    exactly rather than introduce a second warning convention.
    """
    import sys

    if raw is None:
        reason = "not set in environment"
    else:
        reason = f"set to unparseable value {raw!r}"
    print(
        f"WARNING: Threshold '{name}' {reason}, falling back to default '{default}'",
        file=sys.stderr,
    )
