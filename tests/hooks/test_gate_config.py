#!/usr/bin/env python3
"""Tests for gate_config consistency and separation of concerns.

Ensures:
- No tool appears in multiple categories (prevents ambiguous matching)
- Agent/skill names are NOT in tool categories (they're subagent_type values)
- All spawn tools are in always_available (so they bypass gates)
- COMPLIANCE_SUBAGENT_TYPES and SPAWN_TOOLS are internally consistent
"""

import sys
from pathlib import Path

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.gate_config import (
    COMPLIANCE_SUBAGENT_TYPES,
    SPAWN_TOOLS,
    TOOL_CATEGORIES,
    extract_subagent_type,
    get_tool_category,
)


class TestToolCategoryConsistency:
    """Verify no tool appears in multiple categories."""

    def test_no_overlap_between_categories(self):
        """Each tool should appear in exactly one category."""
        seen: dict[str, str] = {}
        for category, tools in TOOL_CATEGORIES.items():
            for tool in tools:
                assert tool not in seen, (
                    f"Tool '{tool}' appears in both '{seen[tool]}' and '{category}'. "
                    f"Each tool must be in exactly one category."
                )
                seen[tool] = category


class TestAgentNameSeparation:
    """Agent names must NOT be in TOOL_CATEGORIES."""

    def test_compliance_types_not_in_tool_categories(self):
        """COMPLIANCE_SUBAGENT_TYPES entries should NOT be in any tool category."""
        all_tools = set()
        for tools in TOOL_CATEGORIES.values():
            all_tools |= tools

        for agent_name in COMPLIANCE_SUBAGENT_TYPES:
            assert agent_name not in all_tools, (
                f"Compliance agent '{agent_name}' found in TOOL_CATEGORIES. "
                f"Agent names are subagent_type values, not tool names."
            )


class TestSpawnToolsInAlwaysAvailable:
    """All spawn tool names must be in always_available."""

    def test_all_spawn_tools_bypass_gates(self):
        """Every tool in SPAWN_TOOLS should be in always_available."""
        always_available = TOOL_CATEGORIES["always_available"]
        for tool_name in SPAWN_TOOLS:
            assert tool_name in always_available, (
                f"Spawn tool '{tool_name}' not in always_available. "
                f"Spawn tools must bypass all gates so agents can be invoked."
            )

    def test_get_tool_category_for_spawn_tools(self):
        """get_tool_category should return always_available for all spawn tools."""
        for tool_name in SPAWN_TOOLS:
            assert get_tool_category(tool_name) == "always_available", (
                f"get_tool_category('{tool_name}') didn't return 'always_available'"
            )


class TestExtractSubagentType:
    """Test extract_subagent_type covers all platforms in SPAWN_TOOLS."""

    def test_every_spawn_tool_extracts_with_first_param(self):
        """For each spawn tool, extraction works with the first parameter name."""
        for tool_name, (param_names, expected_is_skill) in SPAWN_TOOLS.items():
            first_param = param_names[0]
            tool_input = {first_param: "test-agent"}
            result, is_skill = extract_subagent_type(tool_name, tool_input)
            assert result == "test-agent", (
                f"extract_subagent_type('{tool_name}', {{{first_param}: 'test-agent'}}) "
                f"returned {result!r}, expected 'test-agent'"
            )
            assert is_skill == expected_is_skill, (
                f"is_skill for '{tool_name}' was {is_skill}, expected {expected_is_skill}"
            )

    def test_empty_tool_input_returns_none(self):
        """Empty tool_input should return None for all spawn tools."""
        for tool_name in SPAWN_TOOLS:
            result, _ = extract_subagent_type(tool_name, {})
            assert result is None


class TestComplianceSubagentTypes:
    """Verify COMPLIANCE_SUBAGENT_TYPES has expected members."""

    def test_hydrator_variants(self):
        assert "hydrator" in COMPLIANCE_SUBAGENT_TYPES
        assert "prompt-hydrator" in COMPLIANCE_SUBAGENT_TYPES
        assert "aops-core:prompt-hydrator" in COMPLIANCE_SUBAGENT_TYPES

    def test_custodiet_variants(self):
        assert "custodiet" in COMPLIANCE_SUBAGENT_TYPES
        assert "aops-core:custodiet" in COMPLIANCE_SUBAGENT_TYPES

    def test_audit_variants(self):
        assert "audit" in COMPLIANCE_SUBAGENT_TYPES
        assert "aops-core:audit" in COMPLIANCE_SUBAGENT_TYPES

    def test_butler_variants(self):
        assert "butler" in COMPLIANCE_SUBAGENT_TYPES
        assert "aops-core:butler" in COMPLIANCE_SUBAGENT_TYPES
