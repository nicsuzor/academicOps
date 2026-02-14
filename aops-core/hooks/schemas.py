from functools import cached_property
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

# --- Input Schemas (Context) ---


class HookContext(BaseModel):
    """
    Normalized input context for all hooks.

    Precomputed values (session_short_hash, is_subagent) are computed once
    during normalize_input() to avoid redundant calculations across gates.
    """

    model_config = ConfigDict(
        # Allow cached_property to work with Pydantic
        ignored_types=(cached_property,),
    )

    # Core Identity
    session_id: str = Field(..., description="The unique session identifier.")
    trace_id: str | None = Field(
        None, description="The unique ID for the specific hook invocation (tracing)."
    )
    hook_event: str = Field(
        ..., description="The normalized event name (e.g., SessionStart, PreToolUse)."
    )
    agent_id: str | None = None
    slug: str | None = None

    # Precomputed values (computed once in router.normalize_input())
    session_short_hash: str = Field(
        default="", description="8-char hash of session_id (computed once at normalization)."
    )
    is_subagent: bool = Field(
        default=False,
        description="Whether this is a subagent session (computed once at normalization).",
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

    # Cached framework content (lazy loaded)
    _framework_content_cache: tuple[str, str, str] | None = None

    @cached_property
    def framework_content(self) -> tuple[str, str, str]:
        """Lazy-load framework content (axioms, heuristics, skills).

        Returns:
            tuple: (axioms_text, heuristics_text, skills_text)
        """
        from lib.hook_utils import load_framework_content

        return load_framework_content()


# --- Claude Code Hook Schemas ---


class ClaudeHookSpecificOutput(BaseModel):
    """
    Nested output structure for Claude Code hooks (used in most events).
    """

    hookEventName: str
    permissionDecision: Literal["allow", "deny", "ask"] | None = None
    additionalContext: str | None = None
    updatedInput: str | None = None


class ClaudeStopHookOutput(BaseModel):
    """
    Output structure specifically for the Claude 'Stop' event.
    Unlike other events, 'Stop' uses top-level fields instead of hookSpecificOutput.
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
    updatedInput: str | None = None
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
    updated_input: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
