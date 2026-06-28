"""HookContext — normalized hook-event context used across gates and routing.

Lives in `lib/` rather than `hooks/` because gate-engine code (`lib/gates/*`)
needs to consume it, and `lib/` is the lower layer. The hook-platform-specific
output schemas (ClaudeHookSpecificOutput, GeminiHookOutput, etc.) stay in
`hooks/schemas.py` — only the cross-cutting *input* context moved here.

`hooks/schemas.py` re-exports `HookContext` for backward compatibility.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HookContext(BaseModel):
    """
    Normalized input context for all hooks.

    Precomputed values (session_short_hash, is_subagent) are computed once
    during normalize_input() to avoid redundant calculations across gates.
    """

    model_config = ConfigDict()

    # Core Identity
    session_id: str = Field(..., description="The unique session identifier.")
    trace_id: str | None = Field(
        default=None, description="The unique ID for the specific hook invocation (tracing)."
    )
    hook_event: str = Field(
        ..., description="The normalized event name (e.g., SessionStart, PreToolUse)."
    )
    agent_id: str | None = None
    slug: str | None = None
    client_type: str | None = None  # "claude" or "gemini" (set from --client flag)

    # Metadata (aops-d9ba7159)
    machine: str | None = None
    provider: str | None = None
    crew: str | None = None
    repo: str | None = None
    task_id: str | None = None

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
