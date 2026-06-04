from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GateVerdict(Enum):
    """Verdict of a gate check."""

    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    ASK = "ask"  # Not fully implemented in router yet, but reserved


@dataclass
class GateResult:
    """Provider-agnostic result of a gate check."""

    verdict: GateVerdict
    system_message: str | None = None
    context_injection: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def allow(
        cls,
        system_message: str | None = None,
        context_injection: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "GateResult":
        """Factory method for ALLOW verdict."""
        return cls(
            verdict=GateVerdict.ALLOW,
            system_message=system_message,
            context_injection=context_injection,
            metadata=metadata or {},
        )

    @classmethod
    def deny(
        cls,
        system_message: str | None = None,
        context_injection: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "GateResult":
        """Factory method for DENY verdict."""
        return cls(
            verdict=GateVerdict.DENY,
            system_message=system_message,
            context_injection=context_injection,
            metadata=metadata or {},
        )

    @classmethod
    def warn(
        cls,
        system_message: str | None = None,
        context_injection: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "GateResult":
        """Factory method for WARN verdict."""
        return cls(
            verdict=GateVerdict.WARN,
            system_message=system_message,
            context_injection=context_injection,
            metadata=metadata or {},
        )

    def to_json(self) -> dict[str, Any]:
        """Serialize to canonical JSON format."""
        return {
            "verdict": self.verdict.value,
            "system_message": self.system_message,
            "context_injection": self.context_injection,
            "metadata": self.metadata,
        }
