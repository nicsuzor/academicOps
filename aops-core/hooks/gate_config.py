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
    "ENFORCER_GATE_MODE",
    "HANDOVER_GATE_MODE",
    "QA_GATE_MODE",
    "IDA_GATE_MODE",
    "HYDRATION_GATE_MODE",
    "SENTINEL_GATE_MODE",
    "RBG_REVIEW_GATE_MODE",
    "ENFORCER_TOOL_CALL_THRESHOLD",
    "RBG_REVIEW_DEGRADE_THRESHOLD",
    # Polecat-vs-interactive posture axis
    "is_polecat_surface",
    # Slash-command + enforcer-channel hygiene
    "SLASH_COMMAND_PROMPT_PATTERNS",
    "ENFORCER_CHANNEL_SENTINEL",
    "is_enforcer_channel",
]

if TYPE_CHECKING:
    # Declared here so type checkers see precise types for PEP 562 lazy attrs.
    # At runtime these names come from __getattr__ below.
    ENFORCER_GATE_MODE: str
    HANDOVER_GATE_MODE: str
    QA_GATE_MODE: str
    IDA_GATE_MODE: str
    HYDRATION_GATE_MODE: str
    SENTINEL_GATE_MODE: str
    RBG_REVIEW_GATE_MODE: str
    ENFORCER_TOOL_CALL_THRESHOLD: int
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
# bare file paths (e.g. "/home/nic/.../session-enforcer.md"), which must still
# re-arm the gate. Matching `^/` would silently disarm the honesty/handover/qa
# gates on any path-only prompt. The `<command-name>` tag and the Gemini `# /`
# form are unambiguous; a bare path is not.
SLASH_COMMAND_PROMPT_PATTERNS: list[str] = [
    r"<command-name>\s*/[a-zA-Z0-9_-]+\s*</command-name>",  # Claude Code slash command (skill invocation)
    r"^\s*#\s*/(?:end[-_]session|dump|remember|planner)\b",  # Gemini CLI slash-command injection (e.g. "# /dump …")
]

# =============================================================================
# POLECAT-vs-INTERACTIVE POSTURE AXIS
# =============================================================================
# The single structural signal that separates the two registers the framework
# runs in: autonomous polecat (drive-to-done) vs interactive (hold between
# steps). It is NOT a session_type classifier and NOT a launch-time
# autonomous/interactive mode switch (both explicitly rejected — spec
# mem-438429c5 §6). The polecat dispatcher (polecat/cli.py) marks every
# polecat/crew container with AOPS_POLECAT_CONTAINER=1 (aops-b368109a) and
# stages the per-surface gate posture as *_GATE_MODE env vars resolved from
# polecat.yaml. The bare interactive host (junior/ida) carries neither, and so
# is — by definition — NOT a polecat surface. The POSTURE gates (handover, ida)
# resolve their block/warn/deny mode off this axis.


def is_polecat_surface() -> bool:
    """True iff this session runs on an autonomous polecat (or crew) surface.

    The sole structural discriminator for the polecat-vs-interactive posture
    axis. The dispatcher sets AOPS_POLECAT_CONTAINER=1 inside every polecat /
    crew container; a bare interactive host session never has it. Posture
    resolution keys on this to decide whether an unconfigured posture gate
    fails loudly (polecat — misconfig) or resolves to the interactive posture
    (non-polecat).
    """
    return os.environ.get("AOPS_POLECAT_CONTAINER") == "1"


# =============================================================================
# GATE MODES
# =============================================================================
# Gate enforcement modes are read directly from environment variables. The
# polecat launcher (polecat/cli.py) resolves the per-mode posture from
# polecat.yaml on the host and stages the values into the container as env
# vars. Hooks never read polecat.yaml; they only read these env vars.
#
# When no env var is set (e.g. host orchestrator chat, fresh-install dev
# machine), defaults below apply: warn for human-facing gates, off for
# hydration. These match the previous BUILTIN_GATES posture.

_GATE_MODE_DEFAULTS = {
    # Handover defaults to block: a session that did real work (write tool or
    # task claim) must hand over before Stop. Read-only sessions are exempt via
    # session_did_work=False in custom_conditions (the policy returns no verdict).
    "HANDOVER_GATE_MODE": "block",
    "QA_GATE_MODE": "warn",
    "ENFORCER_GATE_MODE": "warn",
    "HYDRATION_GATE_MODE": "off",
    "IDA_GATE_MODE": "warn",
    # Sentinel defaults to block — this is a safety gate protecting user
    # environment files from destructive ops, not just an advisory.
    "SENTINEL_GATE_MODE": "block",
    # RBG-review defaults to block: the per-turn axiom review must RUN before
    # Stop can pass (Nic's directive — guaranteed coverage). This is a real
    # DENY, not advisory; the escape-hatch (RBG_REVIEW_DEGRADE_THRESHOLD)
    # protects against a structurally-broken rbg dispatch trapping the session.
    "RBG_REVIEW_GATE_MODE": "block",
}
_ENFORCER_THRESHOLD_DEFAULT = 50
# Consecutive Stop-DENYs from the rbg-review gate in one turn before it degrades
# to WARN-and-allow (loud, not silent). Matches the 5-block router-level safety
# override; the escape-hatch is failure-degradation only, never a normal bypass.
_RBG_REVIEW_DEGRADE_THRESHOLD_DEFAULT = 5


def __getattr__(name: str):  # PEP 562 module-level lazy attrs
    if name in _GATE_MODE_DEFAULTS:
        return os.environ.get(name, _GATE_MODE_DEFAULTS[name])
    if name == "ENFORCER_TOOL_CALL_THRESHOLD":
        raw = os.environ.get("ENFORCER_TOOL_CALL_THRESHOLD")
        if raw is None:
            return _ENFORCER_THRESHOLD_DEFAULT
        try:
            return int(raw)
        except ValueError:
            return _ENFORCER_THRESHOLD_DEFAULT
    if name == "RBG_REVIEW_DEGRADE_THRESHOLD":
        raw = os.environ.get("RBG_REVIEW_DEGRADE_THRESHOLD")
        if raw is None:
            return _RBG_REVIEW_DEGRADE_THRESHOLD_DEFAULT
        try:
            return int(raw)
        except ValueError:
            return _RBG_REVIEW_DEGRADE_THRESHOLD_DEFAULT
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# =============================================================================
# WS7 item 4 — enforcer channel sentinel (#1315)
# =============================================================================
# The enforcer gate injects an instruction telling the main agent to invoke rbg
# with a session-log path. In the field this read as a prompt injection — an
# instruction arriving mid-stream that says "now go invoke this agent" looks
# exactly like smuggled content, so the agent correctly-but-wrongly ignored a
# real gate (#1315, thread 1). The fix is a stable first-party marker on the
# enforcer's own channel: text carrying this sentinel is framework-issued, not
# untrusted input. The marker is the trust boundary — identical text WITHOUT it
# is still treated as untrusted.
ENFORCER_CHANNEL_SENTINEL = "<!-- aops:enforcer-channel -->"


def is_enforcer_channel(text: str | None) -> bool:
    """Return True if text carries the first-party enforcer-channel sentinel.

    The injection defence uses this to distinguish a real enforcer-gate
    instruction (first-party, trusted) from a look-alike smuggled instruction
    (untrusted). Only text the framework wrapped with the sentinel passes.
    """
    return bool(text) and ENFORCER_CHANNEL_SENTINEL in text
