from typing import Type

from lib.gates.base import Gate


class GateRegistry:
    """Registry for all active gates."""

    _gates: dict[str, Gate] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, gate: Gate) -> None:
        """Register a gate instance."""
        cls._gates[gate.name] = gate

    @classmethod
    def get_gate(cls, name: str) -> Gate | None:
        """Get a gate by name."""
        return cls._gates.get(name)

    @classmethod
    def get_all_gates(cls) -> list[Gate]:
        """Get all registered gates."""
        return list(cls._gates.values())

    @classmethod
    def initialize(cls) -> None:
        """Initialize all gates (import and register them)."""
        if cls._initialized:
            return

        # Import all gate modules to trigger registration
        # This is where we'll add imports as we create the gate classes
        # from lib.gates.hydration import HydrationGate
        # cls.register(HydrationGate())
        # ...

        # For now, we'll leave it empty and populate it as we implement gates
        # We can also use a dynamic import if needed, but explicit is better.
        pass
