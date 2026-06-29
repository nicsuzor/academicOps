#!/usr/bin/env -S uv run python
"""PTY hook-visibility probe — Test Layer C of specs/hooks/CLIENT-TRANSLATION.md.

WHY THIS EXISTS
---------------
The former headless harness ``scripts/verify_hook_formats.py`` (Test Layer B,
DELETED 2026-06-26) drove the HEADLESS client (``claude -p --output-format
json``) and was STRUCTURALLY BLIND to user visibility: it could only inspect the
JSON *result envelope* (the model's reply text). A hook's TTY-rendered banners —
``Stop hook feedback:`` / ``Stop hook error:`` notices, the top-level
``systemMessage`` banner, a PreToolUse denial toast — are rendered by the
INTERACTIVE TUI and NEVER enter that envelope. So its ``user_saw`` was
``False``/``None`` *by construction* for those channels, not by observation (the
false negative the PR #1970 review uncovered, task aops-4de68b25).

This harness closes that gap. It drives a REAL INTERACTIVE client inside a tmux
pane, fires each candidate hook-output shape with unique sentinels, and captures
BOTH surfaces:

  * USER surface  — the rendered tmux pane (``tmux capture-pane``). This is
                    LITERALLY what the human sees. ``user_saw`` = sentinel
                    present in the pane on a CLIENT-rendered hook-notice line
                    (echo-resistant: a bare model-reply line doesn't count).
  * AGENT surface — for Claude: the session transcript JSONL
                    (``~/.claude/projects/<sanitized-cwd>/<uuid>.jsonl``).
                    For agy: model echo (REPORT_PROMPT turn), since agy does
                    not write a JSONL transcript the harness can read.

CAPTURE ARTIFACT FIX (2026-06-27)
----------------------------------
The PreToolUse denial TOAST is transient — it appears briefly then scrolls as
the model generates its reply. The original harness only captured after full
quiescence, so the toast was gone. Fix: TWO SNAPS per probe —

  * EARLY snap — pane captured as soon as EITHER sentinel first appears.
    Catches transient toasts (denial, UPS banner) before model output scrolls.
  * LATE snap — pane captured after quiescence (model done). Catches persistent
    displays (Stop hook feedback/error banners, Stop says: notices).

``user_saw_*`` is True if the sentinel is present on a banner line in EITHER
snap. ``early_user_saw_*`` and ``user_saw_*`` (late) are stored separately so
callers can tell which snap caught each sentinel.

Scrollback is -S -5000 (was -500) so even long sessions stay in window.

Additionally, TOOL_DENY_PROBE_PROMPT asks the model to reply with exactly one
word (DONE/BLOCKED) — limiting post-denial output and reducing the chance the
toast scrolls before the early snap.

PARAMETERIZED / MULTI-CLIENT
-----------------------------
Each ``Probe`` carries a ``client`` field ("claude" | "agy"). Claude probes
inject synthetic sentinels via probe hook scripts registered in
``settings.json``. agy probes fall into two categories:

  * LIVE probes (``uses_real_hooks=True``) — drive a real ``agy`` session with
    the INSTALLED aops-core plugin. No synthetic sentinels: the signal is the
    router's ``<details><summary>System Advisory (Agent Context)</summary>``
    wrapper (AGY_SENT_A) and the ``academicOps`` template namespace prefix
    (AGY_SENT_B). Gate modes forced via env vars to ensure hooks fire. U signal
    from NEUTRAL turn (model told not to echo); C signal from REPORT turn
    (model asked to quote injected advisories).

  * UNMEASURABLE stubs (``unmeasurable=True``) — synthetic agy shapes that
    cannot be probed without a full ``agy plugin install`` (which would mutate
    the live build). These are recorded as structured placeholders with honest
    caveats, matching the entries in ``client_capabilities.json`` (frozen
    2026-06-26). They appear in the fixture and output matrix with all signals
    as None.

Extended probe matrix (2026-06-27): Stop ×8, SessionEnd ×2, UPS ×3,
PreToolUse ×5, PostToolUse ×2, SessionStart ×2, agy-live ×2, agy-unmeas ×5.
Total: ~29 probes (was 10).

Run:
  uv run python scripts/pty_hook_probe.py                        # all claude probes
  uv run python scripts/pty_hook_probe.py --client agy           # all agy probes
  uv run python scripts/pty_hook_probe.py --client all           # all probes
  uv run python scripts/pty_hook_probe.py --only stop-block-reason
  uv run python scripts/pty_hook_probe.py --list

Requires: tmux on PATH, an authenticated interactive ``claude``, agy installed
and configured with the aops-core plugin for agy probes.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# CLIENT-rendered hook-notice line: user_saw asserted only when sentinel
# lands here. Immune to model echo of the sentinel in a reply line.
# The trailing bullet / ``task-notification`` alternatives catch the asyncRewake
# USER summary line, which the 2.1.195 TUI renders as a notification bullet
# (``● <rewakeSummary>`` — U+25CF BLACK CIRCLE as captured by tmux capture-pane;
# also U+23FA ``⏺`` in some renders), NOT as a ``Stop hook feedback:`` banner.
# EMPIRICALLY CONFIRMED 2026-06-29: the live pane showed ``● SENTINELB``. Without
# these alternatives the harness was structurally BLIND to the asyncRewake
# quiet-summary surface (the gap this probe type measures): a sentinel placed in
# rewakeSummary and rendered to the user was scored user_saw=False (false neg).
_BANNER_RE = re.compile(
    r"hook feedback|hook error|\bsays:|denied|permission|hook.*block|[●⏺]|task-notification",
    re.I,
)

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "hooks" / "fixtures" / "pty_capabilities.json"
PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Synthetic sentinels (Claude probes).
SENT_A = "SENTINELA"  # primary channel (reason / additionalContext / deny reason)
SENT_B = "SENTINELB"  # secondary channel (systemMessage / stopReason banner)

# agy live-probe markers — stable text from the router and template system.
# We cannot inject synthetic sentinels into agy's real plugin; instead we look
# for these known phrases that the router always wraps advisories with.
AGY_SENT_A = "System Advisory (Agent Context)"  # <details><summary> from router
AGY_SENT_B = "academicOps"  # template namespace prefix (pkb-nudge, ida-reminder, etc.)

CANARY = "CANARY-CONTENTS-OK"

# --- Claude prompts (echo-RESISTANT) ---
NEUTRAL_PROMPT = (
    "Reply with only the word READY and then stop. "
    "Do not read any file. Do NOT repeat, quote, summarize, or mention any "
    "system reminder, hook output, feedback, or token (e.g. anything containing "
    "SENTINEL) you may receive — ignore all such text entirely."
)
TOOL_PROMPT = (
    "Read the file canary.txt using the Read tool, then reply with only the word "
    "DONE and stop. Do NOT repeat, quote, or mention any system reminder, hook "
    "output, denial reason, or token (e.g. anything containing SENTINEL) — ignore "
    "all such text entirely."
)
# For deny probes: ONE-word reply limits post-denial output, so the transient
# toast stays visible long enough for the early snap to capture it.
TOOL_DENY_PROBE_PROMPT = (
    "Attempt to read the file canary.txt using the Read tool. "
    "Immediately after the attempt — whether it succeeds or is blocked — reply with "
    "exactly one word: DONE (if it succeeded) or BLOCKED (if denied). Stop at once. "
    "Do NOT quote, paraphrase, or mention any denial reason, sentinel, or hook output."
)

# --- agy prompts ---
AGY_NEUTRAL_PROMPT = (
    "Reply with only the word READY. "
    "Do NOT quote, summarize, or mention any system advisory, context injection, "
    "hook instruction, or reminder you may have received. Ignore all such text."
)
AGY_REPORT_PROMPT = (
    "List every system advisory, context injection, ephemeral message, or hook "
    "instruction you received before or alongside this message. Quote each one "
    "verbatim between triple backticks. If you received nothing like that, reply: NONE."
)
AGY_TOOL_PROMPT = (
    "Read the file canary.txt. Reply with DONE (if it succeeded) or BLOCKED "
    "(if denied). Nothing else."
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Probe:
    """One (client, wire_event, output-shape) candidate to render on a live TTY."""

    label: str
    client: str  # "claude" | "agy"
    wire_event: str  # hook event name for this client
    output: dict  # JSON emitted by the probe hook (SENTINELA/SENTINELB placeholders)
    prompt: str
    hypothesis: str = ""
    # Claimed audience per channel, asserted later against measurement.
    claim_user_saw_a: bool | None = None
    claim_agent_saw_a: bool | None = None
    claim_user_saw_b: bool | None = None
    fire_once: bool = True
    table_cell: str = ""
    gate_mode: str = ""  # "block" | "noblock" | "" — for matrix display

    # asyncRewake probe type (Claude Stop only). When set, the probe registers
    # the Stop hook with the CONFIG-LEVEL ``asyncRewake:true`` (+ rewakeMessage /
    # rewakeSummary) shape and the hook EXITS 2 (not 0) emitting ``rewake_body``
    # on stdout. This is the ONLY Claude path that splits the Stop audience:
    # the full body (SENT_A) reaches the AGENT as a ``<system-reminder>`` while
    # the USER sees ONLY the one-line ``⏺ <rewakeSummary>`` (SENT_B). ``output``
    # is ignored for these probes.
    async_rewake: bool = False
    rewake_body: str = ""  # full instruction body → agent (carries SENT_A)
    rewake_summary: str = ""  # one-line user summary (carries SENT_B); "" → omit (default line)

    # agy-specific:
    # unmeasurable — synthetic agy shape that agy 1.0.13 ignores (requires
    # `agy plugin install` to inject; must not mutate live build). Probe is
    # recorded as a stub with all signals None and an honest caveat note.
    unmeasurable: bool = False
    # uses_real_hooks — agy LIVE probe: drives a real agy session using the
    # installed aops-core plugin (no synthetic sentinels; signals are AGY_SENT_A/B).
    uses_real_hooks: bool = False


@dataclass
class Result:
    label: str
    client: str
    wire_event: str
    hypothesis: str
    gate_mode: str = ""
    # Late snap (post-quiescence): persistent displays.
    user_saw_a: bool | None = None
    user_saw_b: bool | None = None
    # Early snap (first sentinel appearance): transient toasts.
    early_user_saw_a: bool | None = None
    early_user_saw_b: bool | None = None
    # AGENT surface (structural classification from transcript).
    agent_ctx_a: bool | None = None
    agent_ctx_b: bool | None = None
    in_transcript_a: bool | None = None
    in_transcript_b: bool | None = None
    transcript_found: bool = False
    agent_ctx_authoritative: bool = False
    measurement_caveats: list = field(default_factory=list)
    unmeasurable: bool = False
    uses_real_hooks: bool = False
    note: str = ""
    pane_excerpt: str = ""
    claim_user_saw_a: bool | None = None
    claim_agent_saw_a: bool | None = None
    claim_user_saw_b: bool | None = None
    table_cell: str = ""


# ---------------------------------------------------------------------------
# Probe matrix — Claude: synthetic sentinels / agy: real hooks or stubs
# ---------------------------------------------------------------------------


def candidates() -> list[Probe]:  # noqa: PLR0912, PLR0915
    HSO = "hookSpecificOutput"
    P: list[Probe] = []

    # ====================================================================
    # CLAUDE — Stop event
    # ====================================================================

    # 1. ENFORCEMENT block + reason (gate_mode=block)
    P.append(
        Probe(
            "stop-block-reason",
            "claude",
            "Stop",
            {"decision": "block", "reason": "SENTINELA continue then stop"},
            NEUTRAL_PROMPT,
            "Stop decision=block reason: 'Stop hook error:' to USER AND to agent.",
            claim_user_saw_a=True,
            claim_agent_saw_a=True,
            gate_mode="block",
            table_cell="Stop enforcement · decision=block reason",
        )
    )
    # 2. WARN-DELIVER additionalContext, no block (gate_mode=noblock)
    P.append(
        Probe(
            "stop-additionalcontext-warn",
            "claude",
            "Stop",
            {
                "decision": "approve",
                HSO: {"hookEventName": "Stop", "additionalContext": "SENTINELA"},
            },
            NEUTRAL_PROMPT,
            "Stop additionalContext (no block): TUI renders 'Stop hook feedback:' to USER?",
            claim_user_saw_a=True,
            claim_agent_saw_a=True,
            gate_mode="noblock",
            table_cell="Stop advisory WARN · additionalContext",
        )
    )
    # 2a. asyncRewake — the SPLIT-AUDIENCE Stop path (config asyncRewake:true +
    # rewakeMessage/rewakeSummary; hook exits 2). Full body (A) → agent
    # <system-reminder>; one-line summary (B) → user only. This is the channel
    # that makes ENFORCEMENT-MAP §1.1's "Ephemeral→agent / one-line-to-user"
    # disposition achievable on Claude. PASS: user_saw_a=False (body hidden),
    # user_saw_b=True (⏺ summary), agent_ctx_a=True (body delivered).
    P.append(
        Probe(
            "stop-asyncrewake-split",
            "claude",
            "Stop",
            {},  # output unused for asyncRewake probes
            NEUTRAL_PROMPT,
            "asyncRewake: full body (A) → agent system-reminder; summary (B) → user "
            "ONLY (⏺ line). The quiet full-to-agent / one-line-to-user Stop split.",
            claim_user_saw_a=False,
            claim_user_saw_b=True,
            claim_agent_saw_a=True,
            gate_mode="noblock",
            table_cell="Stop quiet · asyncRewake (body→agent, summary→user)",
            async_rewake=True,
            rewake_body="SENTINELA full agent instructions body",
            rewake_summary="SENTINELB",
        )
    )
    # 2b. asyncRewake with DEFAULT summary (omit rewakeSummary). Proves the user
    # ALWAYS sees a one-line notice (the literal default "Stop hook feedback")
    # even when no custom summary is set — i.e. the user line is UNAVOIDABLE
    # (never a fully user-silent Stop), while the body (A) still stays agent-only.
    P.append(
        Probe(
            "stop-asyncrewake-default",
            "claude",
            "Stop",
            {},
            NEUTRAL_PROMPT,
            "asyncRewake default summary: user sees the unavoidable default notice; "
            "body (A) stays agent-only (proves no user-silent Stop, body still hidden).",
            claim_user_saw_a=False,
            claim_agent_saw_a=True,
            gate_mode="noblock",
            table_cell="Stop quiet · asyncRewake default summary",
            async_rewake=True,
            rewake_body="SENTINELA full agent instructions body",
            rewake_summary="",  # omit → default "Stop hook feedback" line
        )
    )
    # 3. systemMessage banner only
    P.append(
        Probe(
            "stop-systemmessage",
            "claude",
            "Stop",
            {"systemMessage": "SENTINELB"},
            NEUTRAL_PROMPT,
            "Stop top-level systemMessage: USER banner? agent should NOT see it.",
            claim_user_saw_b=True,
            claim_agent_saw_a=False,
            table_cell="Stop banner · systemMessage",
        )
    )
    # 4. REAL warn-mode shape: systemMessage (B) + additionalContext (A)
    P.append(
        Probe(
            "stop-warnmode-real",
            "claude",
            "Stop",
            {
                "decision": "approve",
                "systemMessage": "SENTINELB",
                HSO: {"hookEventName": "Stop", "additionalContext": "SENTINELA"},
            },
            NEUTRAL_PROMPT,
            "REAL warn-mode: user sees systemMessage(B) banner AND additionalContext(A) feedback?",
            claim_user_saw_a=True,
            claim_user_saw_b=True,
            claim_agent_saw_a=True,
            gate_mode="noblock",
            table_cell="Stop warn-mode (real) · systemMessage+additionalContext",
        )
    )
    # 5. REAL block-mode shape: reason (A) + systemMessage (B)
    P.append(
        Probe(
            "stop-blockmode-real",
            "claude",
            "Stop",
            {
                "decision": "block",
                "reason": "SENTINELA continue then stop",
                "systemMessage": "SENTINELB",
                "stopReason": "SENTINELB",
            },
            NEUTRAL_PROMPT,
            "REAL block-mode: user sees reason(A) 'Stop hook error' AND systemMessage(B)?",
            claim_user_saw_a=True,
            claim_user_saw_b=True,
            claim_agent_saw_a=True,
            gate_mode="block",
            table_cell="Stop block-mode (real) · decision=block reason+systemMessage",
        )
    )
    # 6. suppressOutput=True WITH block — does it hide 'Stop hook error:'?
    P.append(
        Probe(
            "stop-block-suppressoutput",
            "claude",
            "Stop",
            {"decision": "block", "reason": "SENTINELA continue then stop", "suppressOutput": True},
            NEUTRAL_PROMPT,
            "suppressOutput=true on blocking Stop: hides 'Stop hook error:' notice from USER?",
            claim_agent_saw_a=True,
            gate_mode="block",
            table_cell="Stop · suppressOutput=True with block",
        )
    )
    # 7. suppressOutput=True WITHOUT block — does it hide 'Stop hook feedback:'?
    P.append(
        Probe(
            "stop-noblock-suppressoutput",
            "claude",
            "Stop",
            {
                "decision": "approve",
                "suppressOutput": True,
                HSO: {"hookEventName": "Stop", "additionalContext": "SENTINELA"},
            },
            NEUTRAL_PROMPT,
            "suppressOutput=true on non-blocking Stop: hides 'Stop hook feedback:' notice?",
            claim_agent_saw_a=True,
            gate_mode="noblock",
            table_cell="Stop · suppressOutput=True without block",
        )
    )
    # 8. continue=false (undocumented field — does it change session exit behaviour?)
    P.append(
        Probe(
            "stop-block-continue-false",
            "claude",
            "Stop",
            {"decision": "block", "reason": "SENTINELA continue then stop", "continue": False},
            NEUTRAL_PROMPT,
            "Stop block + continue=false: any change vs plain block? Agent should see reason.",
            claim_user_saw_a=True,
            claim_agent_saw_a=True,
            gate_mode="block",
            table_cell="Stop · decision=block+continue=false",
        )
    )

    # 9. stopReason in isolation — does it render differently from systemMessage?
    # In stop-blockmode-real (probe 5), stopReason=SENTINELB was bundled with
    # systemMessage=SENTINELB so we couldn't distinguish which field caused the
    # "Stop says:" banner. This probe isolates stopReason with no systemMessage.
    P.append(
        Probe(
            "stop-stopreason-only",
            "claude",
            "Stop",
            {"stopReason": "SENTINELB"},
            NEUTRAL_PROMPT,
            "stopReason in isolation (no systemMessage): does it render as 'Stop says:' like systemMessage?",
            claim_user_saw_b=True,
            table_cell="Stop banner · stopReason only (isolation probe)",
        )
    )

    # ====================================================================
    # CLAUDE — SessionEnd (mirrors Stop, different event name)
    # ====================================================================
    P.append(
        Probe(
            "sessionend-block-reason",
            "claude",
            "SessionEnd",
            {"decision": "block", "reason": "SENTINELA continue then stop"},
            NEUTRAL_PROMPT,
            "SessionEnd decision=block reason: same channels as Stop?",
            claim_user_saw_a=True,
            claim_agent_saw_a=True,
            gate_mode="block",
            table_cell="SessionEnd enforcement · decision=block reason",
        )
    )
    P.append(
        Probe(
            "sessionend-additionalcontext",
            "claude",
            "SessionEnd",
            {
                "decision": "approve",
                HSO: {"hookEventName": "SessionEnd", "additionalContext": "SENTINELA"},
            },
            NEUTRAL_PROMPT,
            "SessionEnd additionalContext (no block): user-visible like Stop, or different?",
            claim_user_saw_a=True,
            claim_agent_saw_a=True,
            gate_mode="noblock",
            table_cell="SessionEnd advisory · additionalContext",
        )
    )

    # ====================================================================
    # CLAUDE — UserPromptSubmit
    # ====================================================================
    # 11. additionalContext — agent-only (the canonical contrast with Stop)
    P.append(
        Probe(
            "ups-additionalcontext",
            "claude",
            "UserPromptSubmit",
            {HSO: {"hookEventName": "UserPromptSubmit", "additionalContext": "SENTINELA"}},
            NEUTRAL_PROMPT,
            "UPS additionalContext: agent-only (U✗ contrast with Stop U✓).",
            claim_user_saw_a=False,
            claim_agent_saw_a=True,
            gate_mode="noblock",
            table_cell="UPS advisory · additionalContext",
        )
    )
    # 12. systemMessage — user banner
    P.append(
        Probe(
            "ups-systemmessage",
            "claude",
            "UserPromptSubmit",
            {"systemMessage": "SENTINELB"},
            NEUTRAL_PROMPT,
            "UPS systemMessage: USER banner; agent should NOT see it.",
            claim_user_saw_b=True,
            claim_agent_saw_a=False,
            table_cell="UPS banner · systemMessage",
        )
    )
    # 13. deny (permissionDecision=deny) — blocks the prompt from running
    P.append(
        Probe(
            "ups-deny-reason",
            "claude",
            "UserPromptSubmit",
            {
                HSO: {
                    "hookEventName": "UserPromptSubmit",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "SENTINELA prompt blocked",
                }
            },
            NEUTRAL_PROMPT,
            "UPS deny: blocks the prompt; reason visible to USER and agent?",
            claim_user_saw_a=True,
            claim_agent_saw_a=True,
            fire_once=True,
            gate_mode="block",
            table_cell="UPS deny · permissionDecisionReason",
        )
    )

    # ====================================================================
    # CLAUDE — PreToolUse
    # ====================================================================
    # 14. deny + permissionDecisionReason (capture gap: toast transient)
    P.append(
        Probe(
            "pretool-deny-reason",
            "claude",
            "PreToolUse",
            {
                HSO: {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "SENTINELA blocked",
                }
            },
            TOOL_DENY_PROBE_PROMPT,  # minimal response → toast stays visible longer
            "PreToolUse deny reason: denial toast to USER; blocks tool; reason to agent.",
            claim_user_saw_a=True,
            claim_agent_saw_a=True,
            fire_once=False,
            gate_mode="block",
            table_cell="PreToolUse deny · permissionDecisionReason",
        )
    )
    # 15. ask + permissionDecisionReason (softer block — prompts confirmation)
    P.append(
        Probe(
            "pretool-ask-reason",
            "claude",
            "PreToolUse",
            {
                HSO: {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": "SENTINELA needs confirmation",
                }
            },
            TOOL_DENY_PROBE_PROMPT,
            "PreToolUse ask: does it prompt for confirmation? Same channels as deny?",
            claim_user_saw_a=True,
            claim_agent_saw_a=True,
            fire_once=True,
            gate_mode="block",
            table_cell="PreToolUse ask · permissionDecisionReason",
        )
    )
    # 16. allow + additionalContext — agent-only, silent to user
    P.append(
        Probe(
            "pretool-additionalcontext",
            "claude",
            "PreToolUse",
            {
                HSO: {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": "SENTINELA",
                }
            },
            TOOL_PROMPT,
            "PreToolUse allow additionalContext: agent-only; user should NOT see it.",
            claim_user_saw_a=False,
            claim_agent_saw_a=True,
            gate_mode="noblock",
            table_cell="PreToolUse advisory · additionalContext",
        )
    )
    # 17. deny + top-level systemMessage (alongside HSO reason)
    P.append(
        Probe(
            "pretool-deny-systemmessage",
            "claude",
            "PreToolUse",
            {
                "systemMessage": "SENTINELB",
                HSO: {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "SENTINELA blocked",
                },
            },
            TOOL_DENY_PROBE_PROMPT,
            "PreToolUse deny + top-level systemMessage: user sees BOTH B (banner) and A (reason)?",
            claim_user_saw_a=True,
            claim_user_saw_b=True,
            claim_agent_saw_a=True,
            fire_once=False,
            gate_mode="block",
            table_cell="PreToolUse deny · permissionDecisionReason+systemMessage",
        )
    )
    # 18. allow + top-level systemMessage only (no advisory)
    P.append(
        Probe(
            "pretool-allow-systemmessage",
            "claude",
            "PreToolUse",
            {
                "systemMessage": "SENTINELB",
                HSO: {"hookEventName": "PreToolUse", "permissionDecision": "allow"},
            },
            TOOL_PROMPT,
            "PreToolUse allow + systemMessage: banner visible to USER? Agent should NOT see it.",
            claim_user_saw_b=True,
            claim_agent_saw_a=False,
            gate_mode="noblock",
            table_cell="PreToolUse allow · systemMessage only",
        )
    )

    # ====================================================================
    # CLAUDE — PostToolUse (fires AFTER the tool completes; no block)
    # ====================================================================
    P.append(
        Probe(
            "posttool-additionalcontext",
            "claude",
            "PostToolUse",
            {HSO: {"hookEventName": "PostToolUse", "additionalContext": "SENTINELA"}},
            TOOL_PROMPT,  # Read canary.txt, then PostToolUse fires
            "PostToolUse additionalContext: agent-only? USER should NOT see it.",
            claim_user_saw_a=False,
            claim_agent_saw_a=True,
            gate_mode="noblock",
            table_cell="PostToolUse advisory · additionalContext",
        )
    )
    P.append(
        Probe(
            "posttool-systemmessage",
            "claude",
            "PostToolUse",
            {"systemMessage": "SENTINELB", HSO: {"hookEventName": "PostToolUse"}},
            TOOL_PROMPT,
            "PostToolUse systemMessage: USER banner after tool completes?",
            claim_user_saw_b=True,
            table_cell="PostToolUse banner · systemMessage",
        )
    )

    # ====================================================================
    # CLAUDE — SessionStart (fires at session initialisation, before prompt)
    # The hook fires during --setting-sources project startup. The EARLY
    # snap (captured right after the TUI is ready, before any prompt) is
    # the authoritative surface for SessionStart user-visibility.
    # ====================================================================
    P.append(
        Probe(
            "sessionstart-additionalcontext",
            "claude",
            "SessionStart",
            {HSO: {"hookEventName": "SessionStart", "additionalContext": "SENTINELA"}},
            NEUTRAL_PROMPT,
            "SessionStart additionalContext: agent-only (fires at launch, before prompt)?",
            claim_user_saw_a=False,
            claim_agent_saw_a=True,
            gate_mode="noblock",
            table_cell="SessionStart advisory · additionalContext",
        )
    )
    P.append(
        Probe(
            "sessionstart-systemmessage",
            "claude",
            "SessionStart",
            {"systemMessage": "SENTINELB"},
            NEUTRAL_PROMPT,
            "SessionStart systemMessage: USER banner at launch (before prompt)?",
            claim_user_saw_b=True,
            table_cell="SessionStart banner · systemMessage",
        )
    )

    # ====================================================================
    # AGY — LIVE probes (real installed aops-core plugin)
    # ====================================================================
    # These drive a real agy session with gate modes forced on. No synthetic
    # sentinels: AGY_SENT_A = "System Advisory (Agent Context)" (the
    # <details> wrapper the router emits for all advisories); AGY_SENT_B =
    # "academicOps" (the template namespace prefix).
    # U signal: NEUTRAL turn (model told not to echo) → check pane for markers
    # C signal: REPORT turn (model asked to quote injected content) → echo present?
    # Transcript: agy does NOT write a Claude-style JSONL → transcript_found=False.
    P.append(
        Probe(
            "agy-preinvocation-live",
            "agy",
            "PreInvocation",
            {},  # no synthetic output — real plugin hooks fire
            AGY_NEUTRAL_PROMPT,  # turn 1 (U signal); REPORT turn handled by driver
            "agy PreInvocation (live): real pkb-nudge + hydration hooks fire. "
            "U✗ expected (ephemeralMessage not terminal-visible); C✓ via model echo.",
            claim_user_saw_a=False,
            claim_agent_saw_a=True,
            uses_real_hooks=True,
            table_cell="UPS advisory · agy ephemeralMessage (live re-measure)",
        )
    )
    P.append(
        Probe(
            "agy-postinvocation-live",
            "agy",
            "PostInvocation",
            {},
            AGY_NEUTRAL_PROMPT,
            "agy PostInvocation (live): real Ida/handover hooks fire. "
            "U✗ expected; C✓ via model echo.",
            claim_user_saw_a=False,
            claim_agent_saw_a=True,
            uses_real_hooks=True,
            table_cell="Stop advisory · agy PostInvocation ephemeralMessage (live re-measure)",
        )
    )

    # ====================================================================
    # AGY — UNMEASURABLE stubs (synthetic shapes, can't be probed without
    # agy plugin install — would mutate live build; invariant aops-aa512c33)
    # These carry the same data as client_capabilities.json (frozen 2026-06-26).
    # ====================================================================
    _AGY_UNMEAS_NOTE = (
        "unmeasurable on agy 1.0.13: agy ignores workspace/unregistered hooks. "
        "Requires `agy plugin install` which would mutate live build (hard rule). "
        "Standing measurement: client_capabilities.json (frozen 2026-06-26)."
    )
    P.append(
        Probe(
            "agy-pretooluse-allow-unmeas",
            "agy",
            "PreToolUse",
            {},
            AGY_TOOL_PROMPT,
            "agy PreToolUse {allowTool:true}: synthetic-only → unmeasurable.",
            unmeasurable=True,
            table_cell="PreToolUse allow · agy allowTool=true (synthetic-only; unmeasurable 1.0.13)",
        )
    )
    P.append(
        Probe(
            "agy-pretooluse-deny-unmeas",
            "agy",
            "PreToolUse",
            {},
            AGY_TOOL_PROMPT,
            "agy PreToolUse deny {allowTool:false,denyReason}: synthetic-only → unmeasurable.",
            unmeasurable=True,
            table_cell="PreToolUse deny · agy denyReason (synthetic-only; unmeasurable 1.0.13)",
        )
    )
    P.append(
        Probe(
            "agy-preinvocation-usermessage-unmeas",
            "agy",
            "PreInvocation",
            {},
            AGY_NEUTRAL_PROMPT,
            "agy userMessage (claimed P✓): synthetic-only → unmeasurable.",
            unmeasurable=True,
            table_cell="UPS advisory · agy userMessage (claimed P✓; synthetic-only; unmeasurable 1.0.13)",
        )
    )
    P.append(
        Probe(
            "agy-postinvocation-terminationbehavior-unmeas",
            "agy",
            "PostInvocation",
            {},
            AGY_NEUTRAL_PROMPT,
            "agy terminationBehavior hard-block: not emitted + synthetic-only → unmeasurable.",
            unmeasurable=True,
            table_cell="Stop hard-block · agy terminationBehavior (PROVISIONAL; unmeasurable 1.0.13)",
        )
    )
    P.append(
        Probe(
            "agy-stop-native-unmeas",
            "agy",
            "Stop",
            {},
            AGY_NEUTRAL_PROMPT,
            "agy native Stop {decision,reason}: not emitted + synthetic-only → unmeasurable.",
            unmeasurable=True,
            table_cell="Stop short-reason · agy native Stop reason (PROVISIONAL; unmeasurable 1.0.13)",
        )
    )

    return P


# ---------------------------------------------------------------------------
# tmux + workspace plumbing
# ---------------------------------------------------------------------------


def _tmux(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, check=check)


def _pane(session: str) -> str:
    """Full pane text including scrollback (5000 lines), ANSI stripped."""
    r = _tmux("capture-pane", "-t", session, "-p", "-S", "-5000", check=False)
    return r.stdout or ""  # allow-fallback: tmux stdout is None when session missing


def _sanitized_project_dir(workspace: Path) -> Path:
    slug = re.sub(r"[^a-zA-Z0-9]", "-", str(workspace))
    return PROJECTS_DIR / slug


def _transcript_text(workspace: Path) -> str:
    """Read the newest Claude session transcript JSONL for this workspace."""
    if not PROJECTS_DIR.is_dir():
        return ""
    base = re.sub(r"[^a-zA-Z0-9]", "-", workspace.name)
    cands = [d for d in PROJECTS_DIR.iterdir() if d.is_dir() and d.name.endswith(base)]
    if not cands:
        sd = _sanitized_project_dir(workspace)
        cands = [sd] if sd.is_dir() else []
    jsonls: list[Path] = []
    for d in cands:
        jsonls.extend(d.glob("*.jsonl"))
    if not jsonls:
        return ""
    newest = max(jsonls, key=lambda p: p.stat().st_mtime)
    return newest.read_text(errors="replace")


def _user_saw(pane: str, sentinel: str) -> tuple[bool, bool, bool]:
    """Return (saw_on_banner, saw_raw, echo_ambiguous) for a sentinel in the pane."""
    raw = sentinel in pane
    banner = any(sentinel in ln and _BANNER_RE.search(ln) for ln in pane.splitlines())
    return banner, raw, (raw and not banner)


def _agent_signals(transcript: str, sentinel: str) -> tuple[bool | None, bool | None]:
    """Classify how a sentinel appears in the transcript (Claude only).

    Returns (injected_into_context, present_in_transcript).
    Authoritative for Stop/SessionEnd (hookAdditionalContext field or model-read
    user/assistant message). Attachment-ambiguous for other events.
    """
    if not transcript:
        return None, None
    present = sentinel in transcript
    if not present:
        return False, False
    injected: bool | None = None
    for ln in transcript.splitlines():
        if sentinel not in ln:
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if sentinel in str(
            o.get("hookAdditionalContext", "")
        ):  # allow-fallback: optional JSONL field
            injected = True
            break
        if o.get("type") in ("user", "assistant") and sentinel in json.dumps(
            o.get("message", "")  # allow-fallback: optional JSONL field
        ):
            injected = True
            break
    return injected, present


def _write_probe_hook(path: Path, output: dict, fire_once: bool) -> None:
    payload = json.dumps(output)
    if fire_once:
        body = (
            'FLAG="$(dirname "$0")/.fired"\n'
            "if [ -f \"$FLAG\" ]; then echo '{}'; exit 0; fi\n"
            'touch "$FLAG"\n'
        )
    else:
        body = ""
    path.write_text(f"#!/bin/bash\n{body}cat <<'PROBE_EOF'\n{payload}\nPROBE_EOF\nexit 0\n")
    path.chmod(0o755)


def _write_async_rewake_hook(path: Path, body_text: str, fire_once: bool) -> None:
    """Write an asyncRewake Stop hook: emit ``body_text`` on stdout and EXIT 2.

    On Claude 2.1.195 a Stop hook registered with ``asyncRewake:true`` that
    exits 2 delivers its stdout/stderr to the AGENT (appended after the config
    ``rewakeMessage`` prefix, inside a ``<system-reminder>``) while the USER sees
    ONLY the config ``rewakeSummary`` one-liner. The fire-once guard exits 0 on
    the second Stop so the agent can actually terminate (asyncRewake wakes the
    agent on exit 2; without the guard the wake would re-fire indefinitely).
    """
    if fire_once:
        guard = 'FLAG="$(dirname "$0")/.fired"\nif [ -f "$FLAG" ]; then exit 0; fi\ntouch "$FLAG"\n'
    else:
        guard = ""
    path.write_text(f"#!/bin/bash\n{guard}cat <<'PROBE_EOF'\n{body_text}\nPROBE_EOF\nexit 2\n")
    path.chmod(0o755)


def _wait_for(session: str, needles: list[str], timeout: float, settle: float = 0.0) -> bool:
    """Poll pane until ANY needle appears; returns True if found within timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        pane = _pane(session)
        if any(n in pane for n in needles):
            if settle:
                time.sleep(settle)
            return True
        time.sleep(1.0)
    return False


def _wait_for_change(session: str, pane_before: str, timeout: float) -> bool:
    """Poll until the pane differs from pane_before (model started responding)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _pane(session) != pane_before:
            return True
        time.sleep(0.5)
    return False


def _wait_quiescent(session: str, timeout: float, stable_polls: int = 3) -> None:
    """Poll until the pane stops changing for `stable_polls` consecutive reads."""
    deadline = time.time() + timeout
    last = None
    stable = 0
    while time.time() < deadline:
        pane = _pane(session)
        if pane == last:
            stable += 1
            if stable >= stable_polls:
                return
        else:
            stable = 0
            last = pane
        time.sleep(1.5)


def _submit_prompt(session: str, prompt: str) -> bool:
    """Type the prompt into a Claude session and confirm the turn started."""
    for attempt in range(4):
        _tmux("send-keys", "-t", session, "-l", prompt)
        time.sleep(0.6)
        _tmux("send-keys", "-t", session, "Enter")
        if _wait_for(session, ["esc to interrupt", "Choreographing", "tokens · "], timeout=12):
            return True
        time.sleep(1.0 + attempt)
    return False


# ---------------------------------------------------------------------------
# Claude driver
# ---------------------------------------------------------------------------


def _drive_once(workspace: Path, session: str, probe: Probe) -> tuple[str, str, str]:
    """Drive ONE fresh claude session. Returns (status, early_pane, late_pane).

    early_pane — captured as soon as EITHER sentinel first appears in the pane
    (catches transient toasts: PreToolUse denial, UPS banner, SessionStart output).
    Also pre-populated with the startup pane (for SessionStart probes whose hook
    fires before the first prompt).

    late_pane — captured after full quiescence (persistent displays: Stop hook
    feedback/error banners).

    status ∈ {ok, not_ready, not_started}.
    """
    _tmux("kill-session", "-t", session, check=False)
    _tmux("new-session", "-d", "-s", session, "-x", "220", "-y", "50")
    try:
        launch = (
            f"cd {workspace} && claude --setting-sources project "
            f"--permission-mode acceptEdits --allowedTools Read"
        )
        _tmux("send-keys", "-t", session, launch, "Enter")
        if _wait_for(session, ["trust this folder", "Is this a project"], timeout=20):
            _tmux("send-keys", "-t", session, "Enter")
        if not _wait_for(session, ["accept edits on", "for shortcuts"], timeout=30):
            return "not_ready", "", ""
        time.sleep(3.0)

        # PRE-PROMPT early snap: capture right after TUI is ready (before any prompt).
        # This is the authoritative capture for SessionStart hooks that fire at launch.
        early_pane = _pane(session)

        if not _submit_prompt(session, probe.prompt):
            return "not_started", early_pane, _pane(session)

        # POST-PROMPT early snap: poll for sentinels to appear (catches transient
        # toasts: PreToolUse denial, UPS deny, transient Stop notices).
        poll_deadline = time.time() + 30
        while time.time() < poll_deadline:
            p = _pane(session)
            if SENT_A in p or SENT_B in p:
                early_pane = p  # override with the richer snap
                break
            time.sleep(0.5)

        # Late snap: after full quiescence (persistent Stop/SessionEnd displays).
        _wait_quiescent(session, timeout=90, stable_polls=3)
        late_pane = _pane(session)
        return "ok", early_pane, late_pane
    finally:
        _tmux("kill-session", "-t", session, check=False)


# ---------------------------------------------------------------------------
# agy driver
# ---------------------------------------------------------------------------

_AGY_GATE_ENV = (
    "HYDRATION_GATE_MODE=warn "
    "IDA_GATE_MODE=warn "
    "HANDOVER_GATE_MODE=warn "
    "QA_GATE_MODE=warn "
    "COMMIT_GATE_MODE=warn "
    "AOPS_AGY_CLIENT=1"
)

_AGY_READY_NEEDLES = [">", "●", "Gemini", "gemini", "Ready", "agy"]


def _submit_prompt_agy(session: str, prompt: str, pane_before: str) -> bool:
    """Submit a prompt to an agy session, confirmed by pane change."""
    _tmux("send-keys", "-t", session, "-l", prompt)
    time.sleep(0.6)
    _tmux("send-keys", "-t", session, "Enter")
    return _wait_for_change(session, pane_before, timeout=20)


def _drive_once_agy(workspace: Path, session: str) -> tuple[str, str, str]:
    """Drive a 2-turn agy session for LIVE hook measurement.

    Turn 1: NEUTRAL prompt — fires hooks, captures U signal (model told not to echo).
    Turn 2: REPORT prompt — captures C signal via model echo.

    Returns (status, neutral_pane, report_pane). ``status`` ∈ {ok, not_started,
    no_report}. ``transcript_found`` will be False (agy has no Claude-style JSONL).
    """
    _tmux("kill-session", "-t", session, check=False)
    _tmux("new-session", "-d", "-s", session, "-x", "220", "-y", "50")
    try:
        launch = f"cd {workspace} && {_AGY_GATE_ENV} agy --dangerously-skip-permissions"
        _tmux("send-keys", "-t", session, launch, "Enter")

        # Wait for agy to be ready (look for common prompt/model indicators).
        if not _wait_for(session, _AGY_READY_NEEDLES, timeout=30):
            time.sleep(5.0)  # fallback: assume ready after 5s
        time.sleep(2.0)

        # Turn 1: NEUTRAL (U signal — model told NOT to echo advisories).
        pane0 = _pane(session)
        if not _submit_prompt_agy(session, AGY_NEUTRAL_PROMPT, pane0):
            return "not_started", "", ""
        _wait_quiescent(session, timeout=90, stable_polls=3)
        neutral_pane = _pane(session)

        # Turn 2: REPORT (C signal — model asked to echo injected content).
        time.sleep(1.5)
        pane1 = _pane(session)
        if not _submit_prompt_agy(session, AGY_REPORT_PROMPT, pane1):
            return "no_report", neutral_pane, ""
        _wait_quiescent(session, timeout=90, stable_polls=3)
        report_pane = _pane(session)
        return "ok", neutral_pane, report_pane
    finally:
        _tmux("kill-session", "-t", session, check=False)


# ---------------------------------------------------------------------------
# Probe runner
# ---------------------------------------------------------------------------


def run_probe(probe: Probe, workspace: Path) -> Result:  # noqa: PLR0912, PLR0915
    """Run one probe and return a fully-annotated Result."""
    attempts: list[str] = []

    res = Result(
        probe.label,
        probe.client,
        probe.wire_event,
        probe.hypothesis,
        gate_mode=probe.gate_mode,
        unmeasurable=probe.unmeasurable,
        uses_real_hooks=probe.uses_real_hooks,
        claim_user_saw_a=probe.claim_user_saw_a,
        claim_agent_saw_a=probe.claim_agent_saw_a,
        claim_user_saw_b=probe.claim_user_saw_b,
        table_cell=probe.table_cell,
    )

    # -----------------------------------------------------------------------
    # Unmeasurable stubs: record honestly without running a session.
    # -----------------------------------------------------------------------
    if probe.unmeasurable:
        res.note = (
            "unmeasurable on agy 1.0.13: agy ignores workspace/unregistered hooks. "
            "Requires `agy plugin install` (would mutate live build — hard rule). "
            "Standing measurement from frozen client_capabilities.json (2026-06-26)."
        )
        res.measurement_caveats = [
            "synthetic-only probe: agy loads hooks ONLY from an installed plugin; "
            "a workspace hook script is silently ignored (measured 2026-06-25). "
            "All signals are None — this is an HONEST UNKNOWN, not a U✗/C✗."
        ]
        return res

    session = f"pty_{probe.label.replace('-', '_')[:40]}"

    # -----------------------------------------------------------------------
    # agy LIVE probes (real installed hooks, no synthetic sentinels).
    # -----------------------------------------------------------------------
    if probe.client == "agy" and probe.uses_real_hooks:
        (workspace / "canary.txt").write_text(CANARY + "\n")

        MAX_ATTEMPTS = 2
        neutral_pane = report_pane = ""
        attempts = []
        for n in range(1, MAX_ATTEMPTS + 1):
            status, neutral_pane, report_pane = _drive_once_agy(workspace, session)
            attempts.append(f"a{n}:{status}")
            if status == "ok":
                break
            time.sleep(2.0)

        # U signal: advisory marker in NEUTRAL pane (model was told NOT to echo).
        # Any AGY_SENT_A in the pane must come from the TUI (not model reply).
        res.user_saw_a = AGY_SENT_A in neutral_pane
        res.user_saw_b = AGY_SENT_B in neutral_pane

        # C signal: advisory marker in REPORT pane (model asked to echo advisories).
        # Present in report_pane means model received it and echoed it.
        res.agent_ctx_a = AGY_SENT_A in report_pane if report_pane else None
        res.agent_ctx_b = AGY_SENT_B in report_pane if report_pane else None

        # agy has no Claude-style JSONL transcript.
        res.transcript_found = False
        res.in_transcript_a = None
        res.in_transcript_b = None
        res.agent_ctx_authoritative = False

        caveats = [
            "agy LIVE probe: C signal from model echo (REPORT turn), NOT transcript analysis. "
            "U signal from NEUTRAL pane (model told not to echo). "
            "AGY_SENT_A='System Advisory (Agent Context)' is the <details> wrapper the router "
            "emits for all advisories; AGY_SENT_B='academicOps' is the template namespace. "
            "Signals depend on gate conditions: gates forced on via env vars "
            "({_AGY_GATE_ENV}); if a gate did NOT fire, agent_ctx_a=False is a gate-did-not-fire "
            "result, NOT a channel-is-broken result."
        ]
        res.measurement_caveats = caveats

        lines = [ln for ln in neutral_pane.splitlines() if AGY_SENT_A in ln or AGY_SENT_B in ln][:6]
        res.pane_excerpt = "\n".join(list(dict.fromkeys(lines)))
        res.note = (
            f"agy-live: U(neutral) A={res.user_saw_a} B={res.user_saw_b}; "
            f"C(report-echo) A={res.agent_ctx_a} B={res.agent_ctx_b}; "
            f"attempts={','.join(attempts)}"
        )
        return res

    # -----------------------------------------------------------------------
    # Claude asyncRewake probes: config-level asyncRewake:true + exit-2 hook.
    # The split-audience Stop path — full body → agent <system-reminder>,
    # one-line rewakeSummary → user. Measured independently from the synthetic
    # JSON-output probes because the mechanism is CONFIG + exit code, not stdout.
    # -----------------------------------------------------------------------
    if probe.async_rewake:
        (workspace / ".claude").mkdir(parents=True, exist_ok=True)
        (workspace / "canary.txt").write_text(CANARY + "\n")

        body_text = probe.rewake_body.replace("SENTINELA", SENT_A).replace("SENTINELB", SENT_B)
        summary = probe.rewake_summary.replace("SENTINELA", SENT_A).replace("SENTINELB", SENT_B)

        hook = workspace / "probe_hook.sh"
        _write_async_rewake_hook(hook, body_text, probe.fire_once)

        hook_entry: dict = {
            "type": "command",
            "command": f"bash {hook}",
            "asyncRewake": True,
            # Neutral prefix (NO sentinel) so SENT_A presence isolates the BODY.
            "rewakeMessage": "PROBE rewake:",
        }
        if summary:
            hook_entry["rewakeSummary"] = summary
        settings = {"hooks": {probe.wire_event: [{"hooks": [hook_entry]}]}}
        (workspace / ".claude" / "settings.json").write_text(json.dumps(settings))

        MAX_ATTEMPTS = 3
        early_pane = late_pane = transcript = ""
        attempts = []
        for n in range(1, MAX_ATTEMPTS + 1):
            (workspace / ".fired").unlink(missing_ok=True)
            status, early_pane, late_pane = _drive_once(workspace, session, probe)
            transcript = _transcript_text(workspace)
            attempts.append(f"a{n}:{status}{'+tx' if transcript else '+notx'}")
            if status == "ok" and transcript:
                break
            time.sleep(2.0)

        res.transcript_found = bool(transcript)
        early_a, _, _ = _user_saw(early_pane, SENT_A)
        early_b, _, _ = _user_saw(early_pane, SENT_B)
        late_a, _, amb_a = _user_saw(late_pane, SENT_A)
        late_b, _, amb_b = _user_saw(late_pane, SENT_B)
        res.early_user_saw_a = early_a
        res.early_user_saw_b = early_b
        # SENT_A = BODY (must NOT reach user); SENT_B = summary (must reach user).
        res.user_saw_a = early_a or late_a
        res.user_saw_b = early_b or late_b
        res.agent_ctx_a, res.in_transcript_a = _agent_signals(transcript, SENT_A)
        res.agent_ctx_b, res.in_transcript_b = _agent_signals(transcript, SENT_B)
        res.agent_ctx_authoritative = True  # Stop: agent-context signal is authoritative

        caveats = [
            "asyncRewake probe: SENT_A rides the hook BODY (config rewakeMessage prefix + "
            "stdout) delivered to the agent <system-reminder>; SENT_B rides the config "
            "rewakeSummary one-liner. PASS = user_saw_a False (body hidden) + user_saw_b "
            "True (summary shown as ⏺ line) + agent_ctx_a True (body reached agent).",
        ]
        if amb_a or amb_b:
            caveats.append("echo-ambiguous: sentinel in pane but not on a banner line")
        if not transcript:
            caveats.append("no transcript after retries — run did not complete; signals unreliable")
        res.measurement_caveats = caveats
        lines = [
            ln
            for ln in (early_pane + "\n" + late_pane).splitlines()
            if SENT_A in ln or SENT_B in ln or "⏺" in ln or "Stop hook" in ln
        ]
        res.pane_excerpt = "\n".join(list(dict.fromkeys(lines))[-6:])
        res.note = (
            f"asyncRewake USER body(A)={res.user_saw_a} summary(B)={res.user_saw_b}; "
            f"AGENT body(A)={res.agent_ctx_a} in_tx(A)={res.in_transcript_a}; "
            f"transcript={'found' if transcript else 'MISSING'}; attempts={','.join(attempts)}"
        )
        return res

    # -----------------------------------------------------------------------
    # Claude probes: synthetic sentinels via probe hook script.
    # -----------------------------------------------------------------------
    out = json.loads(
        json.dumps(probe.output).replace("SENTINELA", SENT_A).replace("SENTINELB", SENT_B)
    )
    (workspace / ".claude").mkdir(parents=True, exist_ok=True)
    (workspace / "canary.txt").write_text(CANARY + "\n")

    hook = workspace / "probe_hook.sh"
    _write_probe_hook(hook, out, probe.fire_once)

    # Register the hook for this probe's wire_event.
    settings = {
        "hooks": {probe.wire_event: [{"hooks": [{"type": "command", "command": f"bash {hook}"}]}]}
    }
    (workspace / ".claude" / "settings.json").write_text(json.dumps(settings))

    MAX_ATTEMPTS = 3
    early_pane = late_pane = transcript = ""
    attempts = []
    for n in range(1, MAX_ATTEMPTS + 1):
        (workspace / ".fired").unlink(missing_ok=True)
        status, early_pane, late_pane = _drive_once(workspace, session, probe)
        transcript = _transcript_text(workspace)
        attempts.append(f"a{n}:{status}{'+tx' if transcript else '+notx'}")
        if status == "ok" and transcript:
            break
        time.sleep(2.0)

    res.transcript_found = bool(transcript)

    # USER surface: sentinel on a CLIENT-rendered banner line in EITHER snap.
    # The EARLY snap catches transient toasts (PreToolUse denial, UPS banner,
    # SessionStart output). The LATE snap catches persistent displays (Stop
    # hook feedback/error). We track both independently.
    early_a, _, _ = _user_saw(early_pane, SENT_A)
    early_b, _, _ = _user_saw(early_pane, SENT_B)
    late_a, raw_a, amb_a = _user_saw(late_pane, SENT_A)
    late_b, raw_b, amb_b = _user_saw(late_pane, SENT_B)

    res.early_user_saw_a = early_a
    res.early_user_saw_b = early_b
    # user_saw_* = True if visible in EITHER snap.
    res.user_saw_a = early_a or late_a
    res.user_saw_b = early_b or late_b

    # AGENT surface.
    res.agent_ctx_a, res.in_transcript_a = _agent_signals(transcript, SENT_A)
    res.agent_ctx_b, res.in_transcript_b = _agent_signals(transcript, SENT_B)

    res.agent_ctx_authoritative = probe.wire_event in ("Stop", "SessionEnd")

    caveats: list[str] = []
    if amb_a or amb_b:
        caveats.append("echo-ambiguous: sentinel in pane but not on a client banner line")
    if not res.agent_ctx_authoritative:
        caveats.append(
            "agent_ctx NOT authoritative on this event (additionalContext rides an "
            "attachment record, structurally indistinguishable from a logged banner); "
            "C truth from model-echo finding in CLIENT-TRANSLATION.md"
        )
    if probe.claim_user_saw_a is True and res.user_saw_a is False:
        caveats.append(
            "user_saw_a=False despite claim=True — likely a CAPTURE GAP (transient "
            "notice scrolled before snapshot), NOT proof of U✗. Check early_user_saw_a."
        )
    if not transcript:
        caveats.append("no transcript after retries — run did not complete; signals unreliable")
    res.measurement_caveats = caveats

    lines = [
        ln
        for ln in (early_pane + "\n" + late_pane).splitlines()
        if SENT_A in ln
        or SENT_B in ln
        or "Stop hook" in ln
        or "hook error" in ln
        or "hook feedback" in ln
        or "Stop says" in ln
    ]
    res.pane_excerpt = "\n".join(list(dict.fromkeys(lines))[-6:])

    snap_info = f"earlyA={early_a} earlyB={early_b} lateA={late_a} lateB={late_b}"
    res.note = (
        f"USER [{snap_info}] → A={res.user_saw_a} B={res.user_saw_b}; "
        f"AGENT ctx A={res.agent_ctx_a} B={res.agent_ctx_b}; "
        f"in_transcript A={res.in_transcript_a} B={res.in_transcript_b}; "
        f"transcript={'found' if transcript else 'MISSING'}; attempts={','.join(attempts)}"
    )
    return res


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _client_version(client: str = "claude") -> str:
    try:
        cmd = [client, "--version"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return (r.stdout or r.stderr).strip().splitlines()[0]
    except Exception:  # noqa: BLE001
        return "?"


def _print_matrix(results: list[Result]) -> None:
    """Print a compact matrix table to stdout after all probes complete."""
    cols = [
        ("label", 42),
        ("client", 7),
        ("gate", 7),
        ("U✓A?", 5),  # user_saw_a
        ("U✓B?", 5),  # user_saw_b
        ("earA", 5),  # early_user_saw_a
        ("C✓A?", 5),  # agent_ctx_a
        ("C✓B?", 5),  # agent_ctx_b
        ("tx?", 4),  # transcript_found
        ("unmeas", 6),
    ]
    header = "  ".join(f"{h:<{w}}" for h, w in cols)
    print("\n" + "=" * len(header))
    print("FULL OUTPUT MATRIX")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    def fmt(v) -> str:
        if v is None:
            return "?"
        if v is True:
            return "✓"
        if v is False:
            return "✗"
        return str(v)

    for r in results:
        row = (
            f"{r.label:<42}  "
            f"{r.client:<7}  "
            f"{r.gate_mode or '-':<7}  "
            f"{fmt(r.user_saw_a):<5}  "
            f"{fmt(r.user_saw_b):<5}  "
            f"{fmt(r.early_user_saw_a):<5}  "
            f"{fmt(r.agent_ctx_a):<5}  "
            f"{fmt(r.agent_ctx_b):<5}  "
            f"{fmt(r.transcript_found):<4}  "
            f"{'Y' if r.unmeasurable else '-':<6}"
        )
        print(row)

    print("=" * len(header))
    print("Columns: U✓A = user saw sentinelA; U✓B = user saw sentinelB;")
    print("         earA = user saw sentinelA on EARLY snap (transient toasts);")
    print("         C✓A = agent ctx sentinelA; C✓B = agent ctx sentinelB;")
    print("         tx = transcript found; unmeas = unmeasurable stub.")
    print("agy live probes: A=System Advisory (Agent Context); B=academicOps.\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="PTY hook-visibility probe (Layer C)")
    ap.add_argument("--only", help="run only this probe label")
    ap.add_argument(
        "--client",
        default="claude",
        help="client filter: 'claude' | 'agy' | 'all' (default: claude)",
    )
    ap.add_argument("--out", default=str(FIXTURE), help="fixture path")
    ap.add_argument("--list", action="store_true", help="list probe labels and exit")
    ap.add_argument("--no-matrix", action="store_true", help="suppress matrix table")
    args = ap.parse_args()

    all_probes = candidates()
    if args.client == "all":
        probes = all_probes
    else:
        probes = [p for p in all_probes if p.client == args.client]
    if args.only:
        probes = [p for p in probes if p.label == args.only]

    if args.list:
        for p in probes:
            mark = "[UNMEAS]" if p.unmeasurable else ("[LIVE]" if p.uses_real_hooks else "")
            print(f"{p.label:44s} {p.client:<6} {p.wire_event:<16} {mark} {p.hypothesis[:60]}")
        return 0

    if not shutil.which("tmux"):
        print("CRITICAL: tmux not on PATH", file=sys.stderr)
        return 1
    if not shutil.which("claude"):
        print("CRITICAL: claude not on PATH", file=sys.stderr)
        return 1
    if any(p.client == "agy" and not p.unmeasurable for p in probes):
        if not shutil.which("agy"):
            print("CRITICAL: agy not on PATH (required for agy probes)", file=sys.stderr)
            return 1

    results: list[Result] = []
    for idx, p in enumerate(probes, 1):
        mark = " [UNMEAS]" if p.unmeasurable else (" [LIVE-HOOKS]" if p.uses_real_hooks else "")
        print(
            f"[{idx}/{len(probes)}] RUN {p.label} ({p.client}/{p.wire_event}){mark} ...", flush=True
        )
        d = Path(tempfile.mkdtemp(prefix=f"ptyhook-{p.label[:20]}-"))
        try:
            r = run_probe(p, d)
        except Exception as e:  # noqa: BLE001
            r = Result(p.label, p.client, p.wire_event, p.hypothesis, note=f"ERROR: {e}")
        finally:
            shutil.rmtree(d, ignore_errors=True)
        results.append(r)
        print(f"      {r.note}", flush=True)
        if r.pane_excerpt:
            print("      pane: " + r.pane_excerpt.replace("\n", " | "), flush=True)

    if not args.no_matrix:
        _print_matrix(results)

    # Merge into existing fixture when --only is used (partial run), so we
    # don't overwrite previously-measured cells with a 1-cell file.
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if args.only and out_path.exists():
        existing = json.loads(out_path.read_text())
        existing_by_label = {
            c["label"]: c for c in existing.get("cells", [])
        }  # allow-fallback: fixture may predate cells key
        for r in results:
            existing_by_label[r.label] = asdict(r)
        # Preserve original cell order, then append any new labels at the end.
        all_labels = list(existing_by_label.keys())
        merged_cells = [existing_by_label[lbl] for lbl in all_labels]
        report = {
            "generated_note": existing.get(
                "generated_note", ""
            ),  # allow-fallback: optional fixture field
            "claude_version": existing.get("claude_version", _client_version("claude")),
            "agy_version": existing.get("agy_version"),
            "cells": merged_cells,
        }
    else:
        report = {
            "generated_note": "PTY user-visibility measurement — scripts/pty_hook_probe.py (Layer C)",
            "claude_version": _client_version("claude"),
            "agy_version": _client_version("agy")
            if any(p.client == "agy" for p in probes)
            else None,
            "cells": [asdict(r) for r in results],
        }
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"DONE wrote {len(results)} cells -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
