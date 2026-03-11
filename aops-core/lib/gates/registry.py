from lib.gates.engine import GenericGate


class GateRegistry:
    """Registry for all active gates."""

    _gates: dict[str, GenericGate] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, gate: GenericGate) -> None:
        """Register a gate instance."""
        cls._gates[gate.name] = gate

    @classmethod
    def get_gate(cls, name: str) -> GenericGate | None:
        """Get a gate by name."""
        return cls._gates.get(name)

    @classmethod
    def get_all_gates(cls) -> list[GenericGate]:
        """Get all registered gates."""
        return list(cls._gates.values())

    @classmethod
    def initialize(cls) -> None:
        """Initialize all gates (import and register them)."""
        if cls._initialized:
            return

        from lib.gates.definitions import GATE_CONFIGS
        from lib.gates.engine import GenericGate

        for config in GATE_CONFIGS:
            cls.register(GenericGate(config))

        cls._initialized = True
