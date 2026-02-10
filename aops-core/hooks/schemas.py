from typing import Any, Literal

from pydantic import BaseModel, Field

# --- Input Schemas (Context) ---


class HookContext(BaseModel):
    """
    Normalized input context for all hooks.
    """

    # Core Identity
    session_id: str = Field(..., description="The unique session identifier.")
    hook_event: str = Field(
        ..., description="The normalized event name (e.g., SessionStart, PreToolUse)."
    )
    agent_id: str | None = Field(None, description="The unique ID for the specific agent instance.")
    slug: str | None = Field(None, description="The human-readable slug for the session/agent.")
    is_sidechain: bool | None = Field(
        None, description="Whether this is a subagent (sidechain) session."
    )

    # Event Data
    tool_name: str | None = None
    tool_input: dict[str, Any] | list[Any] = Field(default_factory=dict)
    tool_output: dict[str, Any] | list[Any] = Field(default_factory=dict)

    transcript_path: str | None = None
    cwd: str | None = None

    subagent_type: str | None = None

    # Raw Input (for fallback/passthrough)
    raw_input: dict[str, Any] = Field(default_factory=dict)


# --- Claude Code Hook Schemas ---


class ClaudeHookSpecificOutput(BaseModel):
    """
    Nested output structure for Claude Code hooks (used in most events).
    """

    hookEventName: str = Field(..., description="The name of the event that triggered the hook.")
    permissionDecision: Literal["allow", "deny", "ask"] | None = Field(
        None,
        description="The decision for the hook (allow/deny/ask). Primarily for PreToolUse.",
    )
    additionalContext: str | None = Field(
        None,
        description="Additional context to be provided to the agent. Supported in PreToolUse, PostToolUse, UserPromptSubmit, SessionStart.",
    )
    updatedInput: str | None = Field(
        None, description="Updated input for the command. Supported in PreToolUse."
    )


class ClaudeStopHookOutput(BaseModel):
    """
    Output structure specifically for the Claude 'Stop' event.
    Unlike other events, 'Stop' uses top-level fields instead of hookSpecificOutput.
    """

    decision: Literal["approve", "block"] | None = Field(
        None, description="Decision for the Stop event (approve/block)."
    )
    reason: str | None = Field(None, description="Reason for the decision (visible to the agent).")
    stopReason: str | None = Field(None, description="Reason for the stop (visible to the user).")
    systemMessage: str | None = Field(None, description="A message to be displayed to the user.")


class ClaudeGeneralHookOutput(BaseModel):
    """
    Output structure for standard Claude Code hooks (PreToolUse, etc.).
    """

    systemMessage: str | None = Field(None, description="A message to be displayed to the user.")
    hookSpecificOutput: ClaudeHookSpecificOutput | None = Field(
        None, description="Event-specific output data."
    )


# Union type for any Claude Hook Output
ClaudeHookOutput = ClaudeGeneralHookOutput | ClaudeStopHookOutput


# --- Gemini CLI Hook Schemas ---


class GeminiHookSpecificOutput(BaseModel):
    """
    Nested output structure for Gemini CLI hooks.
    Used for context injection and tool configuration.

    Per Gemini CLI docs (2026):
    - additionalContext: Injected into agent prompt (BeforeAgent, AfterTool)
    - toolConfig: Override tool selection behavior (BeforeToolSelection)
    """

    hookEventName: str | None = Field(None, description="The event type triggering the hook.")
    additionalContext: str | None = Field(
        None, description="Context injected into the agent's prompt."
    )
    toolConfig: dict[str, Any] | None = Field(
        None, description="Tool selection configuration (mode, allowedFunctionNames)."
    )
    clearContext: bool | None = Field(
        None, description="If True, clears LLM memory (AfterAgent only)."
    )


class GeminiHookOutput(BaseModel):
    """
    Output structure for Gemini CLI hooks.

    Per Gemini CLI docs (2026):
    - decision: "allow", "deny", or "block" for blocking operations
    - reason: Explanation for denial (NOT for context injection)
    - hookSpecificOutput: Contains additionalContext for prompt injection
    - Exit code 2 is "emergency brake" - stderr shown to agent
    """

    systemMessage: str | None = Field(None, description="Message to be displayed to the user.")
    decision: Literal["allow", "deny", "block"] | None = Field(
        None, description="Permission decision. 'deny'/'block' prevents the operation."
    )
    reason: str | None = Field(
        None, description="Reason for denial decision. NOT for context injection."
    )
    hookSpecificOutput: GeminiHookSpecificOutput | None = Field(
        None, description="Event-specific output including additionalContext."
    )
    suppressOutput: bool | None = Field(None, description="If True, suppresses output display.")
    continue_: bool | None = Field(
        None, alias="continue", description="If False, halts processing."
    )
    stopReason: str | None = Field(None, description="Reason for stopping (visible to user).")
    updatedInput: str | None = Field(
        None, description="Modified input string. Used for command interception."
    )
    # Metadata for internal tracking/debugging
    metadata: dict[str, Any] = Field(default_factory=dict, description="Internal metadata.")


# --- Canonical Internal Schema ---


class CanonicalHookOutput(BaseModel):
    """
    Internal normalized format used by the router to merge multiple hooks.
    All hooks (python scripts) should output this format.
    """

    system_message: str | None = None
    verdict: Literal["allow", "deny", "ask", "warn"] | None = "allow"
    context_injection: str | None = None
    updated_input: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
