#!/usr/bin/env python3
"""Shared fixtures and constants for polecat e2e tests."""

# Known-stable fallback parent under the aops project: an active "Framework
# maintenance and tooling improvements" epic with mixed scratch children.
# Can be overridden via POLECAT_E2E_PARENT.
_DEFAULT_AOPS_SCRATCH_PARENT = "task-0d77545a"
