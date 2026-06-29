"""Client translation SSoT — Table 1 of specs/hooks/CLIENT-TRANSLATION.md.

The SINGLE source of truth for how the Universal Hook Router maps between the
internal canonical hook model and each client's wire dialect (Claude Code,
Gemini CLI, Antigravity CLI / "agy"). Both the RUNTIME router
(``aops-core/hooks/router.py``) and the BUILD (``scripts/build.py``) import from
here, replacing the three previously-divergent copies of the event map
(``router.GEMINI_EVENT_MAP``, ``build.CLAUDE_TO_GEMINI_EVENTS`` + ``AGY_EVENT_MAP``,
``scripts/transforms/hooks.py``) and the scattered channel-routing prose in the
three ``output_for_*`` formatters.

DESIGN CONSTRAINT: this module is **stdlib-only** (no pydantic, no project
imports) so ``scripts/build.py`` can import it without pulling in the hook
runtime's dependency tree.

Two concerns live here:

1. EVENT-NAME MAPPING (both directions):
   - ``to_internal_event(client, wire)`` — inbound, used by ``normalize_input``.
   - ``to_wire_events(client, internal)`` — outbound, used by the build to emit
     ``hooks.json`` (a list, because one internal event can fan out to several
     wire events, e.g. Gemini ``Stop`` → ``[SessionEnd, AfterAgent]``).
   plus per-wire-event registration shape and cold-start timeout floors.

2. CHANNEL CAPABILITY (``channel_spec(client, internal)``): for each
   (client, event), WHICH delivery channels exist — can it block? can it deliver
   ``context_injection`` to the AGENT without forcing a block? is there a
   USER-only message channel? The per-client renderers read this to decide
   routing; the cross-client test matrix asserts the renderer honoured it; the
   gate layer reads ``agent_context_without_block`` to decide whether a WARN that
   carries advisory must be upgraded to a block purely to deliver it.

   The wire FIELD names (``allowTool`` vs ``decision``, ``additionalContext`` vs
   ``injectSteps``) are structural and live in the renderers — the table carries
   POLICY (what is supported), not byte layout.

PROVISIONAL cells are contested/empirically-pending. USER-visibility cells are
resolved by the PTY harness (``scripts/pty_hook_probe.py`` →
``tests/hooks/fixtures/pty_capabilities.json``, Test Layer C — drives a real
interactive ``claude`` in tmux). The headless ``scripts/verify_hook_formats.py``
was removed 2026-06-26 (it was structurally blind to TTY user-visibility). Cells
are flagged ``provisional=True`` with a note so a wrong guess is never silently
load-bearing.
"""

from __future__ import annotations

from dataclasses import dataclass

CLIENTS = ("claude", "gemini", "agy")


# --- Canonical internal event names -----------------------------------------
class Event:
    SESSION_START = "SessionStart"
    PRE_TOOL = "PreToolUse"
    POST_TOOL = "PostToolUse"
    USER_PROMPT = "UserPromptSubmit"
    STOP = "Stop"
    SESSION_END = "SessionEnd"
    SUBAGENT_START = "SubagentStart"
    SUBAGENT_STOP = "SubagentStop"
    PRE_COMPACT = "PreCompact"
    NOTIFICATION = "Notification"


# =============================================================================
# EVENT-NAME MAPPING
# =============================================================================
# INBOUND: wire event name (as the client invokes the hook) -> internal canonical
# name. Used by HookRouter.normalize_input. Claude is identity (its native names
# ARE the canonical names). Identity-mapped wire names that equal an internal name
# need no entry; the resolver falls back to identity.
_INBOUND: dict[str, dict[str, str]] = {
    "claude": {},  # identity — Claude's wire names are the canonical names.
    "gemini": {
        "SessionStart": Event.SESSION_START,
        "BeforeTool": Event.PRE_TOOL,
        "AfterTool": Event.POST_TOOL,
        "BeforeAgent": Event.USER_PROMPT,
        "AfterAgent": Event.STOP,
        "SessionEnd": Event.SESSION_END,
        "Notification": Event.NOTIFICATION,
        "PreCompress": Event.PRE_COMPACT,
        "SubagentStart": Event.SUBAGENT_START,
        "SubagentStop": Event.SUBAGENT_STOP,
    },
    "agy": {
        "PreToolUse": Event.PRE_TOOL,
        "PostToolUse": Event.POST_TOOL,
        "PreInvocation": Event.USER_PROMPT,  # agy: fires before each model invocation
        "PostInvocation": Event.STOP,  # agy: fires after tool calls finish
        "Stop": Event.STOP,  # agy native session-end (see P4 correction)
    },
}

# OUTBOUND: internal canonical name -> list of wire event names to REGISTER in the
# generated hooks.json. A list because one internal event can fan out (Gemini
# Stop -> SessionEnd AND AfterAgent). Events absent from a client's map are NOT
# shipped to that client (e.g. agy drops SessionStart/SubagentStart/etc).
_OUTBOUND: dict[str, dict[str, list[str]]] = {
    "claude": {  # identity for every event Claude supports natively
        e: [e]
        for e in (
            Event.SESSION_START,
            Event.PRE_TOOL,
            Event.POST_TOOL,
            Event.USER_PROMPT,
            Event.STOP,
            Event.SESSION_END,
            Event.SUBAGENT_START,
            Event.SUBAGENT_STOP,
            Event.PRE_COMPACT,
            Event.NOTIFICATION,
        )
    },
    "gemini": {
        Event.PRE_TOOL: ["BeforeTool"],
        Event.POST_TOOL: ["AfterTool"],
        Event.USER_PROMPT: ["BeforeAgent"],
        Event.STOP: ["SessionEnd", "AfterAgent"],  # fan-out (see CLIENT-TRANSLATION.md)
        Event.SESSION_START: ["SessionStart"],
        Event.SESSION_END: ["SessionEnd"],
        Event.SUBAGENT_START: ["BeforeTool"],
        Event.SUBAGENT_STOP: ["AfterTool"],
        Event.PRE_COMPACT: ["BeforeAgent"],
        Event.NOTIFICATION: ["BeforeAgent"],
    },
    "agy": {
        # CURRENT behavior: internal Stop -> PostInvocation. The P4 correction
        # (harness-gated) adds native ``Stop`` so handover can hard-block; until
        # the harness confirms terminationBehavior/decision delivery this stays
        # PostInvocation so P1-P3 are byte-identical. See AGY_STOP_PROVISIONAL.
        Event.USER_PROMPT: ["PreInvocation"],
        Event.STOP: ["PostInvocation"],
        Event.PRE_TOOL: ["PreToolUse"],
        Event.POST_TOOL: ["PostToolUse"],
    },
}

# Wire events each client's harness actually accepts in hooks.json (the build
# drops anything that maps to a wire event not in this set).
VALID_WIRE_EVENTS: dict[str, frozenset[str]] = {
    "claude": frozenset(_OUTBOUND["claude"]),  # Claude accepts all native names
    "gemini": frozenset(
        {"SessionStart", "BeforeAgent", "AfterAgent", "BeforeTool", "AfterTool", "SessionEnd"}
    ),
    "agy": frozenset({"PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop"}),
}

# Registration shape per (client, wire_event):
#   "wrapper" — matcher + hooks[] list (tool events)
#   "flat"    — bare handler list directly under the event key
#   "claude"  — Claude's native settings.json hook entry shape
_CONFIG_SHAPE: dict[str, dict[str, str]] = {
    "agy": {
        "PreToolUse": "wrapper",
        "PostToolUse": "wrapper",
        "PreInvocation": "flat",
        "PostInvocation": "flat",
        "Stop": "flat",
    },
    # gemini uses the wrapper shape for every event; claude uses its own.
}

# Cold-start timeout floors (ms) per (client, wire_event). Only RAISES a source
# timeout, never lowers it. agy PreToolUse 15000 guards the cold venv build that
# otherwise surfaces as a spurious "Tool call denied" (invariant #10).
_TIMEOUT_FLOOR_MS: dict[str, dict[str, int]] = {
    "agy": {"PreToolUse": 15000},
}


# =============================================================================
# CHANNEL CAPABILITY TABLE
# =============================================================================
@dataclass(frozen=True)
class ChannelSpec:
    """What delivery channels (client, internal_event) supports.

    POLICY, not byte layout. The per-client renderer maps these to wire fields.
    """

    can_block: bool
    # Can context_injection reach the AGENT on a NON-blocking result? If False and
    # the gate has advisory to deliver, the gate/renderer must block to deliver it
    # (the "block-to-inject" path) — that is the ONLY place that decision lives.
    agent_context_without_block: bool
    # Is there a USER-facing (not agent) message channel for system_message?
    user_message: bool
    notes: str = ""
    provisional: bool = False


# Key: (client, internal_event). Confirmed from live docs + the conformance
# harness (2026-06-25). PROVISIONAL=contested, pending harness measurement.
_CHANNELS: dict[tuple[str, str], ChannelSpec] = {
    # ---- Claude Code (2.1.191) ----
    ("claude", Event.PRE_TOOL): ChannelSpec(True, True, True),
    ("claude", Event.USER_PROMPT): ChannelSpec(True, True, True),
    ("claude", Event.POST_TOOL): ChannelSpec(False, True, True),
    ("claude", Event.SESSION_START): ChannelSpec(False, True, True),
    # Stop additionalContext-without-block CONFIRMED on 2.1.191, re-confirmed
    # 2.1.195 (mem-4ab6cc0b; task aops-c0363bf8, PTY-probed): delivery works
    # without blocking. The legacy "Stop rejects hookSpecificOutput" (2.1.158)
    # is STALE. user_message=True: the delivered field ALSO renders to the user
    # as "Stop hook feedback:" — there is NO agent-only Stop channel. NB:
    # delivery != enforcement — a non-blocking nudge can be ignored, so
    # block-mode gates (handover) still need can_block.
    ("claude", Event.STOP): ChannelSpec(True, True, True, notes="2.1.195 mem-4ab6cc0b"),
    ("claude", Event.SESSION_END): ChannelSpec(True, True, True, notes="same as Stop"),
    # ---- Gemini CLI ----
    ("gemini", Event.PRE_TOOL): ChannelSpec(True, True, True),
    ("gemini", Event.USER_PROMPT): ChannelSpec(True, True, True),
    ("gemini", Event.POST_TOOL): ChannelSpec(True, True, True),
    ("gemini", Event.SESSION_START): ChannelSpec(False, True, True),
    # AfterAgent delivers feedback to the agent via reason->retry (a block), not a
    # free additionalContext. agent_context_without_block PROVISIONAL.
    ("gemini", Event.STOP): ChannelSpec(
        True, False, True, notes="AfterAgent: reason=retry prompt", provisional=True
    ),
    ("gemini", Event.SESSION_END): ChannelSpec(False, True, True),
    # ---- Antigravity CLI (agy) ----
    # PreToolUse has only decision/reason (+allowTool/denyReason) — no inject
    # channel, so advisory cannot ride an allow; reason carries the deny reason.
    ("agy", Event.PRE_TOOL): ChannelSpec(True, False, True),
    ("agy", Event.POST_TOOL): ChannelSpec(False, False, False, notes="{} only"),
    # PreInvocation injectSteps delivery LIVE-PROVEN by model echo (invariant #14,
    # 2026-06-25 agy 1.0.12): ephemeralMessage reaches the model (C✓) but does NOT
    # leak to the user terminal (U✗) and does NOT persist across --conversation
    # (P✗). user_message=True here means a user banner is structurally possible,
    # NOT that the EMITTED ephemeralMessage is user-visible — it is not.
    # Recorded in tests/hooks/fixtures/client_capabilities.json (frozen 2026-06-26;
    # the agy live-measurement harness was deleted, value stands as recorded).
    ("agy", Event.USER_PROMPT): ChannelSpec(
        False, True, True, notes="injectSteps; ephemeralMessage U✗ C✓ P✗ live-proven"
    ),
    # PostInvocation: injectSteps deliver advisory (ephemeralMessage U✗ C✓ P✗
    # LIVE-PROVEN, same as PreInvocation); terminationBehavior hard-block PROVISIONAL
    # — not emitted and unmeasurable on agy 1.0.12 (ignores synthetic probe hooks).
    ("agy", Event.STOP): ChannelSpec(
        True,
        True,
        True,
        notes="injectSteps U✗ C✓ P✗ live-proven; terminationBehavior unmeasurable",
        provisional=True,
    ),
}

# The P4 agy hard-stop correction: register native ``Stop`` and emit
# ``{"decision":"continue","reason":...}``. Held until the harness confirms the
# enum + reason delivery; see CLIENT-TRANSLATION.md §P4.
AGY_STOP_PROVISIONAL = True


# =============================================================================
# Accessors
# =============================================================================
def to_internal_event(client: str, wire_event: str) -> str:
    """Map a client's wire event name to the internal canonical name.

    Falls back to identity (the wire name already equals an internal name, e.g.
    Claude, or an unmapped passthrough event).
    """
    return _INBOUND.get(client, {}).get(
        wire_event, wire_event
    )  # allow-fallback: identity is the designed default for unmapped/passthrough events


def to_wire_events(client: str, internal_event: str) -> list[str]:
    """Map an internal event to the wire event name(s) to register for a client.

    Returns [] if the client does not support the event (build drops it).
    """
    return list(
        _OUTBOUND.get(client, {}).get(internal_event, [])
    )  # allow-fallback: empty = event not shipped to this client (build drops it), the designed semantics


def valid_wire_event(client: str, wire_event: str) -> bool:
    return wire_event in VALID_WIRE_EVENTS.get(client, frozenset())


def config_shape(client: str, wire_event: str) -> str:
    """Registration shape for a (client, wire_event): 'wrapper' | 'flat' | 'claude'."""
    if client == "claude":
        return "claude"
    if client == "gemini":
        return "wrapper"
    return _CONFIG_SHAPE.get(client, {}).get(
        wire_event, "wrapper"
    )  # allow-fallback: wrapper is the default registration shape for tool-style events


def timeout_floor_ms(client: str, wire_event: str) -> int | None:
    return _TIMEOUT_FLOOR_MS.get(client, {}).get(
        wire_event
    )  # allow-fallback: None = no floor for this (client, event), the designed default


def channel_spec(client: str, internal_event: str) -> ChannelSpec | None:
    """Channel capability for (client, internal_event), or None if unmapped."""
    return _CHANNELS.get((client, internal_event))
