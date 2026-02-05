from typing import Optional, Literal, Union, Dict, Any
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
    agent_id: Optional[str] = Field(None, description="The unique ID for the specific agent instance.")
    slug: Optional[str] = Field(None, description="The human-readable slug for the session/agent.")
    is_sidechain: Optional[bool] = Field(None, description="Whether this is a subagent (sidechain) session.")

    # Event Data
    tool_name: Optional[str] = None
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    transcript_path: Optional[str] = None
    cwd: Optional[str] = None

    # Raw Input (for fallback/passthrough)
    raw_input: Dict[str, Any] = Field(default_factory=dict)


# --- Claude Code Hook Schemas ---


class ClaudeHookSpecificOutput(BaseModel):
    """
    Nested output structure for Claude Code hooks (used in most events).
    """

    hookEventName: str = Field(
        ..., description="The name of the event that triggered the hook."
    )
    permissionDecision: Optional[Literal["allow", "deny", "ask"]] = Field(
        None,
        description="The decision for the hook (allow/deny/ask). Primarily for PreToolUse.",
    )
    additionalContext: Optional[str] = Field(
        None,
        description="Additional context to be provided to the agent. Supported in PreToolUse, PostToolUse, UserPromptSubmit, SessionStart.",
    )
    updatedInput: Optional[str] = Field(
        None, description="Updated input for the command. Supported in PreToolUse."
    )


class ClaudeStopHookOutput(BaseModel):
    """
    Output structure specifically for the Claude 'Stop' event.
    Unlike other events, 'Stop' uses top-level fields instead of hookSpecificOutput.
    """

    decision: Optional[Literal["approve", "block"]] = Field(
        None, description="Decision for the Stop event (approve/block)."
    )
    reason: Optional[str] = Field(
        None, description="Reason for the decision (visible to the agent)."
    )
    stopReason: Optional[str] = Field(
        None, description="Reason for the stop (visible to the user)."
    )
    systemMessage: Optional[str] = Field(
        None, description="A message to be displayed to the user."
    )


class ClaudeGeneralHookOutput(BaseModel):
    """
    Output structure for standard Claude Code hooks (PreToolUse, etc.).
    """

    systemMessage: Optional[str] = Field(
        None, description="A message to be displayed to the user."
    )
    hookSpecificOutput: Optional[ClaudeHookSpecificOutput] = Field(
        None, description="Event-specific output data."
    )


# Union type for any Claude Hook Output
ClaudeHookOutput = Union[ClaudeGeneralHookOutput, ClaudeStopHookOutput]


# --- Gemini CLI Hook Schemas ---


class GeminiHookSpecificOutput(BaseModel):
    """
    Nested output structure for Gemini CLI hooks.
    Used for context injection and tool configuration.

    Per Gemini CLI docs (2026):
    - additionalContext: Injected into agent prompt (BeforeAgent, AfterTool)
    - toolConfig: Override tool selection behavior (BeforeToolSelection)
    """

    hookEventName: Optional[str] = Field(
        None, description="The event type triggering the hook."
    )
    additionalContext: Optional[str] = Field(
        None, description="Context injected into the agent's prompt."
    )
    toolConfig: Optional[Dict[str, Any]] = Field(
        None, description="Tool selection configuration (mode, allowedFunctionNames)."
    )
    clearContext: Optional[bool] = Field(
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

    systemMessage: Optional[str] = Field(
        None, description="Message to be displayed to the user."
    )
    decision: Optional[Literal["allow", "deny", "block"]] = Field(
        None, description="Permission decision. 'deny'/'block' prevents the operation."
    )
    reason: Optional[str] = Field(
        None, description="Reason for denial decision. NOT for context injection."
    )
    hookSpecificOutput: Optional[GeminiHookSpecificOutput] = Field(
        None, description="Event-specific output including additionalContext."
    )
    suppressOutput: Optional[bool] = Field(
        None, description="If True, suppresses output display."
    )
    continue_: Optional[bool] = Field(
        None, alias="continue", description="If False, halts processing."
    )
    stopReason: Optional[str] = Field(
        None, description="Reason for stopping (visible to user)."
    )
    updatedInput: Optional[str] = Field(
        None, description="Modified input string. Used for command interception."
    )
    # Metadata for internal tracking/debugging
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Internal metadata."
    )


# --- Canonical Internal Schema ---


class CanonicalHookOutput(BaseModel):
    """
    Internal normalized format used by the router to merge multiple hooks.
    All hooks (python scripts) should output this format.
    """

    system_message: Optional[str] = None
    verdict: Optional[Literal["allow", "deny", "ask", "warn"]] = "allow"
    context_injection: Optional[str] = None
    updated_input: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
