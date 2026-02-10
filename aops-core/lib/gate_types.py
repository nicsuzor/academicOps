from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class GateStatus(str, Enum):
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
    metrics: Dict[str, Any] = Field(default_factory=dict)

    # Block reason if currently blocked explicitly
    blocked: bool = False
    block_reason: Optional[str] = None


class GateCondition(BaseModel):
    """Condition for a trigger or policy."""
    # Matchers (all optional, combined with AND logic)
    hook_event: Optional[str] = None
    tool_name_pattern: Optional[str] = None  # Regex
    tool_input_pattern: Optional[str] = None # Regex on JSON string of input? Or key-value match?
    subagent_type_pattern: Optional[str] = None # Regex on subagent type
    excluded_tool_categories: Optional[List[str]] = None  # Skip if tool is in these categories

    # State checks
    current_status: Optional[GateStatus] = None # Applies only if gate is in this status
    min_ops_since_open: Optional[int] = None
    min_ops_since_close: Optional[int] = None
    min_turns_since_open: Optional[int] = None
    min_turns_since_close: Optional[int] = None

    # Custom logic key (resolved in engine)
    custom_check: Optional[str] = None


class GateTransition(BaseModel):
    """Action to take when a trigger fires."""
    target_status: Optional[GateStatus] = None # If None, keep current status

    # Templates for feedback
    system_message_template: Optional[str] = None
    context_injection_template: Optional[str] = None

    # Side effects
    reset_ops_counter: bool = False
    set_metrics: Dict[str, Any] = Field(default_factory=dict)
    increment_metrics: List[str] = Field(default_factory=list)

    # Execute complex logic (e.g. generate file)
    custom_action: Optional[str] = None


class GateTrigger(BaseModel):
    """Event-driven rule to update gate state."""
    condition: GateCondition
    transition: GateTransition


class GatePolicy(BaseModel):
    """Rule for blocking/warning based on state."""
    condition: GateCondition
    verdict: str = "allow" # allow, warn, deny

    # Message to show if policy triggers (blocking/warning)
    message_template: str
    context_template: Optional[str] = None


class GateConfig(BaseModel):
    """Declarative configuration for a gate."""
    name: str
    description: str

    # Initial state
    initial_status: GateStatus = GateStatus.OPEN

    # Transitions (Stateless -> State Update)
    triggers: List[GateTrigger] = Field(default_factory=list)

    # Policies (Stateful -> Verdict)
    policies: List[GatePolicy] = Field(default_factory=list)
