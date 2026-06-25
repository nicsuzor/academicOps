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
    - ``decision="block"`` + ``reason``: Claude is prevented from stopping and the
      ``reason`` text is fed to the agent as the reason it must continue. This is
      the only Stop-event channel that demonstrably reaches the *agent's* context
      on the next turn.
    - ``stopReason``, ``systemMessage``: user-visible only. The agent does NOT see
      these on its next turn. Do NOT route advisory/recovery text here — that
      inverts intent (the advisory leaks to the user as noise, the agent sees
      nothing). See aops-d10e7db6.

    ``hookSpecificOutput`` is NOT supported for Stop events. Claude Code's schema
    validator only accepts hookSpecificOutput for PreToolUse, UserPromptSubmit,
    PostToolUse, and PostToolBatch. Emitting it with hookEventName="Stop" causes
    the entire JSON payload to be rejected ("Hook JSON output validation failed —
    (root): Invalid input", a hook_non_blocking_error surfaced to the user as a
    generic "Stop hook error" notification), discarding both the decision and
    reason fields. Discovered via polecat self-test 2026-05-23; re-verified
    empirically on Claude Code 2.1.158, 2026-05-31 (repro: proof/anthropic-issue/).
    """

    decision: Literal["approve", "block"] | None = None
    reason: str | None = None
    stopReason: str | None = None
    systemMessage: str | None = None


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
