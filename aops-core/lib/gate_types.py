from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


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


class GateCondition(BaseModel):
    """Condition for a trigger or policy."""

    # Matchers (all optional, combined with AND logic)
    hook_event: str | None = None
    tool_name_pattern: str | None = None  # Regex
    tool_input_pattern: str | None = None  # Regex on stringified tool input dict
    subagent_type_pattern: str | None = None  # Regex on subagent type
    excluded_tool_categories: list[str] | None = None  # Skip if tool is in these categories

    # State checks
    current_status: GateStatus | None = None  # Applies only if gate is in this status
    min_ops_since_open: int | None = None
    min_ops_since_close: int | None = None
    min_turns_since_open: int | None = None
    min_turns_since_close: int | None = None

    # Custom logic key (resolved in engine)
    custom_check: str | None = None


class GateTransition(BaseModel):
    """Action to take when a trigger fires."""

    target_status: GateStatus | None = None  # If None, keep current status

    # Templates for feedback
    system_message_template: str | None = None
    context_injection_template: str | None = None

    # Side effects
    reset_ops_counter: bool = False
    set_metrics: dict[str, Any] = Field(default_factory=dict)
    increment_metrics: list[str] = Field(default_factory=list)

    # Execute complex logic (e.g. generate file)
    custom_action: str | None = None


class GateTrigger(BaseModel):
    """Event-driven rule to update gate state."""

    condition: GateCondition
    transition: GateTransition


class GatePolicy(BaseModel):
    """Rule for blocking/warning based on state."""

    condition: GateCondition
    verdict: str = "allow"  # allow, warn, deny

    # Message to show if policy triggers (blocking/warning)
    message_template: str
    context_template: str | None = None

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

    # Message template. Supports {remaining}, {threshold}, {gate_name}, {temp_path}
    message_template: str = (
        "Approaching {gate_name} threshold. You have {remaining} operations remaining."
    )

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

    # Transitions (Stateless -> State Update)
    triggers: list[GateTrigger] = Field(default_factory=list)

    # Policies (Stateful -> Verdict)
    policies: list[GatePolicy] = Field(default_factory=list)

    # Optional countdown warning before threshold
    countdown: CountdownConfig | None = None
