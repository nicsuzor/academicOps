"""Shared conftest for hooks tests.

Sets gate mode env vars at module level so they are available during
test collection, before any test module imports gate_config.py.
"""

import os

# gate_config.py reads these at module level with os.environ[] (no default).
# They must be set before any test module that imports hooks.router or
# hooks.gate_config is collected by pytest.
os.environ.setdefault("HANDOVER_GATE_MODE", "warn")
os.environ.setdefault("QA_GATE_MODE", "block")
os.environ.setdefault("CUSTODIET_GATE_MODE", "block")
os.environ.setdefault("HYDRATION_GATE_MODE", "warn")
