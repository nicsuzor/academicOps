from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from lib.gate_model import GateVerdict


class GateStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class GateState(BaseModel):
    """
    Standardized state for all gates.
    Tracks core metrics (time, turns, ops) since last state change.
    """

    status: GateStatus = GateStatus.OPEN

    # Timestamps (seconds since epoch)
    last_open_ts: float = 0.0
    last_close_ts: float = 0.0

    # Turn counts (relative to session start)
    last_open_turn: int = 0
    last_close_turn: int = 0

    # Operation counts (e.g., tool calls)
    ops_since_open: int = 0
    ops_since_close: int = 0

    # Arbitrary metrics specific to this gate (e.g., custom counters)
    metrics: dict[str, Any] = Field(default_factory=dict)

    # Block reason if currently blocked explicitly
    blocked: bool = False
    block_reason: str | None = None

    # Sticky latch: when True, transitions targeting a different status are
    # suppressed until an event in sticky_until_events fires.
    sticky: bool = False
    sticky_until_events: list[str] = Field(default_factory=list)


class GateCondition(BaseModel):
    """Condition for a trigger or policy."""

    # Matchers (all optional, combined with AND logic)
    hook_event: str | None = None
    tool_name_pattern: str | None = None  # Regex
    tool_input_pattern: str | None = None  # Regex on stringified tool input dict
    subagent_type_pattern: str | None = None  # Regex on subagent type
    prompt_pattern: str | None = None  # Regex on raw_input.prompt
    excluded_tool_categories: list[str] | None = None  # Skip if tool is in these categories

    # State checks
    current_status: GateStatus | None = None  # Applies only if gate is in this status
    min_ops_since_open: int | None = None
    min_ops_since_close: int | None = None
    min_turns_since_open: int | None = None
    min_turns_since_close: int | None = None

    # Declarative subagent/prompt filters (avoids custom_check for simple cases)
    exclude_if_subagent: bool = False  # Skip if ctx.is_subagent is True
    prompt_exclude_patterns: list[str] = Field(
        default_factory=list
    )  # Regex list: skip if any matches the prompt (stripped)

    # Session type filter: condition only matches if session_type is in this list.
    # None means no filter (matches all session types).
    session_type_filter: list[str] | None = None

    # Custom logic key (resolved in engine)
    custom_check: str | None = None


class GateTransition(BaseModel):
    """Action to take when a trigger fires."""

    target_status: GateStatus | None = None  # If None, keep current status

    # Templates for feedback — prefer _key fields (resolved via TemplateRegistry)
    # over inline _template strings. Keys take priority when both are set.
    system_message_template: str | None = None
    system_message_key: str | None = None
    context_template: str | None = None
    context_key: str | None = None

    # Side effects
    reset_ops_counter: bool = False
    set_metrics: dict[str, Any] = Field(default_factory=dict)
    increment_metrics: list[str] = Field(default_factory=list)

    # Execute complex logic (e.g. generate file)
    custom_action: str | None = None

    # Sticky latch: after this transition fires, suppress any subsequent
    # transition that targets a different status until one of these hook
    # events fires and clears the latch.
    sticky_until: list[str] | None = None


class GateTrigger(BaseModel):
    """Event-driven rule to update gate state."""

    condition: GateCondition
    transition: GateTransition


from typing import cast


def normalize_verdict(v: Any) -> GateVerdict:
    if isinstance(v, str):
        v_lower = v.lower()
        if v_lower == "block":
            return GateVerdict.DENY
        if v_lower == "off":
            return GateVerdict.ALLOW
        try:
            return GateVerdict(v_lower)
        except ValueError:
            pass
    return cast(GateVerdict, v)


class GatePolicy(BaseModel):
    """Rule for blocking/warning based on state."""

    condition: GateCondition
    verdict: GateVerdict = GateVerdict.ALLOW

    @field_validator("verdict", mode="before")
    @classmethod
    def _normalize_verdict(cls, v: Any) -> Any:
        return normalize_verdict(v)

    # Message to show if policy triggers — prefer _key fields (resolved via
    # TemplateRegistry) over inline _template strings. Keys take priority.
    message_template: str = ""
    message_key: str | None = None
    context_template: str | None = None
    context_key: str | None = None

    # Execute complex logic (e.g. generate file)
    custom_action: str | None = None


class CountdownConfig(BaseModel):
    """Configuration for countdown warnings before a gate blocks.

    Provides advance notice to agents before they hit a gate threshold,
    allowing them to proactively run compliance checks.
    """

    # Number of ops before threshold to start showing countdown
    # e.g., if threshold=15 and start_before=5, countdown shows at ops 10-14
    start_before: int = 5

    # Message template — prefer message_key (resolved via TemplateRegistry)
    # over inline message_template. Key takes priority when both are set.
    message_template: str = (
        "Approaching {gate_name} threshold. You have {remaining} operations remaining."
    )
    message_key: str | None = None

    # Which metric to count against (default: ops_since_open)
    metric: str = "ops_since_open"

    # Threshold value for countdown
    threshold: int


class GateConfig(BaseModel):
    """Declarative configuration for a gate."""

    name: str
    description: str

    # Initial state
    initial_status: GateStatus = GateStatus.OPEN
    # Session-type-specific initial status overrides (e.g. polecat → CLOSED)
    initial_status_by_session_type: dict[str, GateStatus] = Field(default_factory=dict)

    # Transitions (Stateless -> State Update)
    triggers: list[GateTrigger] = Field(default_factory=list)

    # Policies (Stateful -> Verdict)
    policies: list[GatePolicy] = Field(default_factory=list)

    # Optional countdown warning before threshold
    countdown: CountdownConfig | None = None

    # Stop-DENY escape-hatch (per-gate override of the engine default).
    # After this many CONSECUTIVE Stop DENYs from this gate in one turn, the
    # engine degrades DENY -> WARN-and-allow so a structurally-broken forcing
    # function cannot permanently trap the session (the infinite-Stop-loop
    # prior incident). None -> use the engine default (_STOP_DENY_DOWNGRADE_
    # THRESHOLD). Set higher for hard gates that must really run (e.g.
    # rbg-review uses 5 to match the router-level 5-block safety override).
    stop_deny_downgrade_threshold: int | None = None
    # Template key for a LOUD, user-visible message emitted on the Stop where
    # the gate degrades (the escape-hatch fire). Rendered with {threshold}.
    # None -> degrade silently (legacy behaviour for advisory gates).
    stop_deny_degraded_message_key: str | None = None
