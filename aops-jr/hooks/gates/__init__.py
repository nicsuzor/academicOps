"""Function-per-gate hook system.

A gate is a plain Python function ``(Event, state) -> Verdict | None``. The
``GATES`` list in ``registry.py`` is the registry — no discovery magic, no
registry class. See ``specs/enforcement/hook-gate-system.md`` for the design.
"""
