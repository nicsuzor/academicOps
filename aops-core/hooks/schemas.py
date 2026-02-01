from typing import Optional, Literal, Union, Dict, Any, List
from pydantic import BaseModel, Field

# --- Input Schemas (Context) ---

class HookContext(BaseModel):
    """
    Normalized input context for all hooks.
    """
    # Core Identity
    session_id: str = Field(..., description="The unique session identifier.")
    hook_event: str = Field(..., description="The normalized event name (e.g., SessionStart, PreToolUse).")

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
    hookEventName: str = Field(..., description="The name of the event that triggered the hook.")
    permissionDecision: Optional[Literal["allow", "deny", "ask"]] = Field(
        None, description="The decision for the hook (allow/deny/ask). Primarily for PreToolUse."
    )
    additionalContext: Optional[str] = Field(
        None, description="Additional context to be provided to the agent. Supported in PreToolUse, PostToolUse, UserPromptSubmit, SessionStart."
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

class GeminiHookOutput(BaseModel):
    """
    Output structure for Gemini CLI hooks.
    Gemini uses a flatter structure compared to Claude.
    """
    systemMessage: Optional[str] = Field(
        None, description="Message to be displayed to the user."
    )
    decision: Optional[Literal["allow", "deny"]] = Field(
        None, description="Permission decision (allow/deny). Required for blocking events."
    )
    reason: Optional[str] = Field(
        None, description="Reason for the decision or context. Used for explanations or agent instructions."
    )
    updatedInput: Optional[str] = Field(
        None, description="Modified input string. Used for command interception."
    )
    # Metadata for internal tracking/debugging
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Internal metadata.")


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
