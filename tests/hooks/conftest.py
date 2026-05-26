"""Shared conftest for hooks tests — fixtures only.

Helpers, constants, and non-fixture functions live in gate_helpers.py.
"""

import pytest

from tests.hooks.gate_helpers import (
    HookRouter,
    reinit_gates_with_defaults,
    set_gate_modes,
)


@pytest.fixture(autouse=True)
def _deterministic_gate_modes(monkeypatch):
    """Ensure gate modes use known defaults regardless of host env."""
    set_gate_modes(
        monkeypatch,
        handover="warn",
        qa="block",
        enforcer="block",
        hydration="off",
    )
    reinit_gates_with_defaults()


@pytest.fixture
def router(monkeypatch):
    """Create a HookRouter with mocked session data."""
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()
