from typing import Any, Literal, TypeAlias

# HookContext lives in lib/hook_context.py (so gate-engine code in lib/gates/*
# can consume it without importing upward from hooks/). Import it directly from
# there — this module no longer re-exports it.
from pydantic import BaseModel, Field

__all__ = [
    "ClaudeHookSpecificOutput",
    "ClaudeStopHookOutput",
    "ClaudeGeneralHookOutput",
    "ClaudeHookOutput",
    "GeminiHookSpecificOutput",
    "GeminiHookOutput",
    "CanonicalHookOutput",
]


# --- Claude Code Hook Schemas ---


class ClaudeHookSpecificOutput(BaseModel):
    """
    Nested output structure for Claude Code hooks (used in most events).
    """

    hookEventName: str
    permissionDecision: Literal["allow", "deny", "ask"] | None = None
    permissionDecisionReason: str | None = None
    additionalContext: str | None = None


class ClaudeStopHookOutput(BaseModel):
    """
    Output structure specifically for the Claude 'Stop' event.

    Channel routing (per Claude Code hooks API):
    - ``hookSpecificOutput.additionalContext``: delivers advisory to the *agent's*
      context on the next turn WITHOUT blocking the stop. Live-verified accepted +
      delivered (model echo) + continues on Claude Code 2.1.191, 2026-06-25
      (mem-4ab6cc0b; harness probe ``claude-stop-additionalcontext-noblock``).
      This RETIRES the legacy WARN→block-to-deliver upgrade for warn-mode gates —
      a warn that only needs to DELIVER no longer has to spuriously block.
      CAVEAT (DOCUMENTED + human-verified 2026-06-26): additionalContext on Stop
      is NOT agent-only on the user's screen. The official Claude Code hooks docs
      (code.claude.com/docs/en/hooks.md, "Stop") state additionalContext is
      "shown as 'Stop hook feedback' in transcript" — i.e. user-visible BY
      DESIGN, not a quirk. Confirmed live on the interactive TUI. CRITICAL: the
      ``systemMessage``/``stopReason`` assignment in output_for_claude() is
      UNCONDITIONAL (outside the verdict branch), so the short user line is
      emitted in BOTH block and warn modes. The user therefore ALWAYS sees TWO
      things on a gate Stop: the short ``systemMessage`` ("Stop says: …") AND the
      full long context — via ``reason`` ("Stop hook blocking error") in block
      mode, or via ``additionalContext`` ("Stop hook feedback") in warn mode.
      block and warn are EQUALLY noisy for the user (human-verified BOTH modes
      2026-06-26); the mode changes only the transcript LABEL and whether the
      agent is hard-blocked — it does NOT reduce user-visible noise. The
      "agent-only / user-not-shown" claim came from a headless harness that
      cannot observe TTY rendering (it only sees the ``claude -p`` JSON result
      envelope). PTY-PROVEN 2026-06-26: ``scripts/pty_hook_probe.py`` drives a
      real interactive ``claude`` in tmux and captured ``Stop hook feedback:``
      rendered to the user for warn-mode additionalContext (fixture
      ``tests/hooks/fixtures/pty_capabilities.json``, cell
      ``stop-additionalcontext-warn`` → user_saw=True). Reducing
      Stop noise is a TEMPLATE-LENGTH / CADENCE / suppressOutput problem, NOT a
      channel-routing or gate-mode one.
    - ``decision="block"`` + ``reason``: Claude is prevented from stopping and the
      ``reason`` text is fed to the agent. This is the ENFORCEMENT path — kept for
      deny/block-mode gates (handover) that must HALT the agent. Delivery alone
      (additionalContext) can be disregarded by the model (mem-4ab6cc0b); a
      block-mode gate needs the block, not just delivery.
    - ``stopReason``, ``systemMessage``: user-visible only. The agent does NOT see
      these on its next turn. Do NOT route advisory/recovery text here — that
      inverts intent (the advisory leaks to the user as noise, the agent sees
      nothing). See aops-d10e7db6.

    HISTORY: the legacy "Stop rejects hookSpecificOutput" belief (verified Claude
    Code 2.1.158, 2026-05-31; proof/anthropic-issue/) is STALE at 2.1.191 — 33
    patch releases later the validator accepts ``hookSpecificOutput`` on Stop and
    delivers ``additionalContext`` to the agent. The live-conformance harness
    (Test Layer B) guards this so an upstream regression flips the cell red.
    """

    decision: Literal["approve", "block"] | None = None
    reason: str | None = None
    stopReason: str | None = None
    systemMessage: str | None = None
    hookSpecificOutput: ClaudeHookSpecificOutput | None = None


class ClaudeGeneralHookOutput(BaseModel):
    """
    Output structure for standard Claude Code hooks (PreToolUse, etc.).
    """

    systemMessage: str | None = None
    hookSpecificOutput: ClaudeHookSpecificOutput | None = None


# Union type for any Claude Hook Output
ClaudeHookOutput: TypeAlias = ClaudeGeneralHookOutput | ClaudeStopHookOutput


# --- Gemini CLI Hook Schemas ---


class GeminiHookSpecificOutput(BaseModel):
    """
    Nested output structure for Gemini CLI hooks.
    Used for context injection and tool configuration.

    Per Gemini CLI docs (2026):
    - additionalContext: Injected into agent prompt (BeforeAgent, AfterTool)
    - toolConfig: Override tool selection behavior (BeforeToolSelection)
    """

    hookEventName: str | None = None
    additionalContext: str | None = None
    toolConfig: dict[str, Any] | None = None
    clearContext: bool | None = None


class GeminiHookOutput(BaseModel):
    """
    Output structure for Gemini CLI hooks.

    Per Gemini CLI docs (2026):
    - decision: "allow", "deny", or "block" for blocking operations
    - reason: Explanation for denial (NOT for context injection)
    - hookSpecificOutput: Contains additionalContext for prompt injection
    - Exit code 2 is "emergency brake" - stderr shown to agent
    """

    systemMessage: str | None = None
    decision: Literal["allow", "deny", "block"] | None = None
    reason: str | None = None
    hookSpecificOutput: GeminiHookSpecificOutput | None = None
    suppressOutput: bool | None = None
    continue_: bool | None = Field(default=None, alias="continue")
    stopReason: str | None = None
    # Metadata for internal tracking/debugging
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Canonical Internal Schema ---


class CanonicalHookOutput(BaseModel):
    """
    Internal normalized format used by the router to merge multiple hooks.
    All hooks (python scripts) should output this format.
    """

    system_message: str | None = None
    verdict: Literal["allow", "deny", "ask", "warn"] | None = "allow"
    context_injection: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
