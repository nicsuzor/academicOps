"""
Gate Configuration: gate-mode resolution and slash-command detection.

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
    "RBG_GATE_MODE",
    "HANDOVER_GATE_MODE",
    "QA_GATE_MODE",
    "IDA_GATE_MODE",
    "HYDRATION_GATE_MODE",
    "RBG_REVIEW_GATE_MODE",
    "RBG_TOOL_CALL_THRESHOLD",
    "RBG_REVIEW_DEGRADE_THRESHOLD",
    "GATE_MODE_VARS",
    # Slash-command hygiene
    "SLASH_COMMAND_PROMPT_PATTERNS",
]

if TYPE_CHECKING:
    # Declared here so type checkers see precise types for PEP 562 lazy attrs.
    # At runtime these names come from __getattr__ below.
    RBG_GATE_MODE: str
    HANDOVER_GATE_MODE: str
    QA_GATE_MODE: str
    IDA_GATE_MODE: str
    HYDRATION_GATE_MODE: str
    RBG_REVIEW_GATE_MODE: str
    RBG_TOOL_CALL_THRESHOLD: int
    RBG_REVIEW_DEGRADE_THRESHOLD: int


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
# GATE MODES — DEFAULTS-NONE, universal (note_296e5520 §4).
# =============================================================================
# Gate enforcement modes have exactly two resolution steps, in order, and NO
# third (fallback/default) step:
#
#   1. The env var (`*_GATE_MODE`, `RBG_TOOL_CALL_THRESHOLD`) — set by a
#      polecat/crew launcher (`polecat/cli.py`) that already resolved
#      `polecat.yaml` on the host, OR by `session_env_setup.py`'s SessionStart
#      hook, which resolves the SAME way this module does (step 2) and
#      persists the result so inner-loop hooks (stripped shell env) can reuse
#      it via `session_state.gate_modes`.
#   2. `polecat.yaml`'s `face` section (this module resolves it directly via
#      `lib.polecat_config.load_polecat_config`) — the fallback path for any
#      caller that reaches this module WITHOUT having gone through a launcher
#      or SessionStart (ad hoc test harnesses, bare CLI invocations of a hook
#      script, etc). This is NOT a "built-in default" — it is a genuine read
#      of the single posture source, and it hard-fails exactly like step 1's
#      absence does if polecat.yaml cannot be located or fails validation.
#
# There is no code-level session-type or polecat-vs-interactive branching
# anywhere in the gate engine (removed — see aops-core/lib/gates/{engine,
# definitions}.py history): every gate has one uniform initial_status and one
# uniform set of triggers for every session. Whatever differs across surfaces
# (polecat run vs polecat crew vs an ad hoc interactive CLI session) differs
# SOLELY because a different `*_GATE_MODE` value was resolved for that
# surface via steps 1/2 above — never because the gate code inspected
# session_type.
#
# When NEITHER step resolves a value (no env var AND polecat.yaml is missing/
# unlocatable/malformed), this HARD-FAILS. There is no third step. A session
# that cannot resolve its posture does not run with a guessed one.

GATE_MODE_VARS: list[str] = [
    "QA_GATE_MODE",
    "RBG_GATE_MODE",
    "HYDRATION_GATE_MODE",
    "RBG_REVIEW_GATE_MODE",
    "HANDOVER_GATE_MODE",
    "IDA_GATE_MODE",
]
_GATE_MODE_VAR_SET = frozenset(GATE_MODE_VARS)

# RBG_REVIEW_DEGRADE_THRESHOLD is deliberately EXEMPT from DEFAULTS-NONE: it
# is not a polecat.yaml-sourced posture value (no `gates.rbg_review_degrade_
# threshold` key exists in the schema, and no launcher ever stages this env
# var). It is an internal failure-degradation constant — the escape hatch that
# downgrades a stuck rbg-review DENY loop to WARN-and-allow after N consecutive
# blocks — with an optional env-var override used only for test tuning. There
# is nothing in polecat.yaml for a missing value to be "missing from" here, so
# the hard-fail requirement (which targets config-loading, not this kind of
# engineering constant) does not apply.
_RBG_REVIEW_DEGRADE_THRESHOLD_DEFAULT = 5


def _face_session_defaults():
    """Resolve `polecat.yaml`'s `face` section — the single fallback step
    (step 2 above) when a gate-mode env var is not already set. Memoised per
    process/import so repeated attribute access doesn't re-parse the YAML.

    Propagates whatever `lib.polecat_config.load_polecat_config` raises
    (missing/unlocatable/malformed polecat.yaml, missing required key in ANY
    surface section) — there is no further fallback beneath this.
    """
    global _face_config_cache
    if _face_config_cache is None:
        from lib.polecat_config import load_polecat_config

        _face_config_cache = load_polecat_config().face
    return _face_config_cache


_face_config_cache = None


def __getattr__(name: str):  # PEP 562 module-level lazy attrs
    if name in _GATE_MODE_VAR_SET:
        val = os.environ.get(name)
        if val is not None:
            return val
        gate_key = name[: -len("_GATE_MODE")].lower()
        return getattr(_face_session_defaults().gates, gate_key)
    if name == "RBG_TOOL_CALL_THRESHOLD":
        raw = os.environ.get("RBG_TOOL_CALL_THRESHOLD")
        if raw is not None:
            try:
                return int(raw)
            except ValueError as exc:
                raise RuntimeError(
                    f"gate_config: RBG_TOOL_CALL_THRESHOLD={raw!r} is not an integer "
                    "(sourced from polecat.yaml gates.rbg_threshold)."
                ) from exc
        return _face_session_defaults().gates.rbg_threshold
    if name == "RBG_REVIEW_DEGRADE_THRESHOLD":
        raw = os.environ.get("RBG_REVIEW_DEGRADE_THRESHOLD")
        if raw is None:
            return _RBG_REVIEW_DEGRADE_THRESHOLD_DEFAULT
        try:
            return int(raw)
        except ValueError:
            return _RBG_REVIEW_DEGRADE_THRESHOLD_DEFAULT
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
