"""Shared conftest for hooks tests.

Gate modes are resolved from $AOPS_POLECAT_CONFIG / $AOPS_SESSIONS/polecat.yaml
via lib/polecat_config.py — NOT from env vars. The root tests/conftest.py sets
AOPS_POLECAT_CONFIG to polecat/defaults/polecat.yaml.example at collection time
so all hooks tests have a valid config without per-test setup.

Tests that need specific gate modes write a temporary polecat.yaml and point
AOPS_POLECAT_CONFIG at it via monkeypatch (see test_gate_verdicts.py for the
canonical pattern).
"""
