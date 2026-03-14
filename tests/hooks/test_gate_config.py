#!/usr/bin/env python3
"""Tests for gate_config consistency and separation of concerns.

Ensures:
- No tool appears in multiple categories (prevents ambiguous matching)
- Agent/skill names are NOT in tool categories (they're subagent_type values)
- All spawn tools are in spawn category (subject to hydration gate, not infrastructure)
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
    """Agent names must NOT be in TOOL_CATEGORIES.

    EXEMPTION: Gemini bare agent tools (where tool_name == agent_name).
    """

    def test_compliance_types_not_in_tool_categories(self):
        """COMPLIANCE_SUBAGENT_TYPES entries should NOT be in any tool category UNLESS they are spawning tools.

        This separation prevents accidentally blocking a tool because it happens
        to share a name with an agent. For Gemini, we intentionally use the same name.
        """
        all_tools = set()
        for tools in TOOL_CATEGORIES.values():
            all_tools |= tools

        for agent_name in COMPLIANCE_SUBAGENT_TYPES:
            if agent_name in SPAWN_TOOLS:
                # Gemini pattern: name is both tool and agent. Allowed.
                continue

            assert agent_name not in all_tools, (
                f"Compliance agent '{agent_name}' found in TOOL_CATEGORIES. "
                f"Agent names are subagent_type values, not tool names."
            )


class TestSpawnToolsInSpawnCategory:
    """All spawn tool names must be in spawn category (subject to hydration gate).

    EXEMPTION: Compliance agents (e.g. hydrator) are spawning tools but
    must bypass gates as infrastructure.
    """

    def test_all_spawn_tools_in_spawn_category(self):
        """Every tool in SPAWN_TOOLS should be in spawn category OR COMPLIANCE_SUBAGENT_TYPES.

        Spawn tools (Agent, Task, Skill, etc.) are subject to the hydration gate —
        they cannot dispatch subagents until hydration is complete. This is distinct
        from infrastructure tools (PKB ops) which bypass all gates entirely.
        """
        spawn_cat = TOOL_CATEGORIES["spawn"]
        for tool_name in SPAWN_TOOLS:
            is_compliance = tool_name in COMPLIANCE_SUBAGENT_TYPES
            assert tool_name in spawn_cat or is_compliance, (
                f"Spawn tool '{tool_name}' not in spawn category. "
                f"Non-compliance spawn tools must be subject to hydration gate."
            )

    def test_get_tool_category_for_spawn_tools(self):
        """get_tool_category returns spawn for regular spawn tools, infrastructure for compliance."""
        for tool_name in SPAWN_TOOLS:
            is_compliance = tool_name in COMPLIANCE_SUBAGENT_TYPES
            expected = "infrastructure" if is_compliance else "spawn"
            assert get_tool_category(tool_name) == expected, (
                f"get_tool_category('{tool_name}') didn't return '{expected}'"
            )


class TestExtractSubagentType:
    """Test extract_subagent_type covers all platforms in SPAWN_TOOLS."""

    def test_every_spawn_tool_extracts_with_first_param(self):
        """For each spawn tool with params, extraction works with the first parameter name."""
        for tool_name, (param_names, expected_is_skill) in SPAWN_TOOLS.items():
            if not param_names:
                # Strategy 1 (bare agent) tools have no parameters
                continue
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

    def test_empty_tool_input_returns_none_unless_compliance(self):
        """Empty tool_input should return None for regular spawn tools, or self for compliance."""
        for tool_name in SPAWN_TOOLS:
            result, _ = extract_subagent_type(tool_name, {})
            if tool_name in COMPLIANCE_SUBAGENT_TYPES:
                assert result == tool_name
            else:
                assert result is None


class TestComplianceSubagentTypes:
    """Verify COMPLIANCE_SUBAGENT_TYPES has expected members."""

    def test_hydrator_variants(self):
        assert "hydrator" in COMPLIANCE_SUBAGENT_TYPES
        assert "hydrator" in COMPLIANCE_SUBAGENT_TYPES
        assert "aops-core:hydrator" in COMPLIANCE_SUBAGENT_TYPES

    def test_custodiet_variants(self):
        assert "custodiet" in COMPLIANCE_SUBAGENT_TYPES
        assert "aops-core:custodiet" in COMPLIANCE_SUBAGENT_TYPES

    def test_audit_variants(self):
        assert "audit" in COMPLIANCE_SUBAGENT_TYPES
        assert "aops-core:audit" in COMPLIANCE_SUBAGENT_TYPES


class TestToolSearchSelectBypass:
    """ToolSearch with select: prefix must bypass the hydration gate.

    select: queries are pure tool-loading operations (infrastructure), not new
    task prompts. They must not trigger the hydration gate.

    Test taxonomy:
    - [RED]   Tests that fail because the behavior does not yet exist.
    - [GREEN] Regression guards for existing/unchanged behavior. These pass
              now and must continue to pass after implementation.
    """

    # ------------------------------------------------------------------
    # [RED] New behavior: select: prefix elevates ToolSearch to infrastructure
    # ------------------------------------------------------------------

    def test_select_single_tool_is_infrastructure(self):
        """[RED] select:X query must return 'infrastructure', not 'read_only'."""
        assert get_tool_category("ToolSearch", {"query": "select:Read"}) == "infrastructure"

    def test_select_multiple_tools_is_infrastructure(self):
        """[RED] Comma-separated select: query must still return 'infrastructure'."""
        assert (
            get_tool_category("ToolSearch", {"query": "select:Read,Edit,Bash"}) == "infrastructure"
        )

    # ------------------------------------------------------------------
    # [GREEN] Existing behavior: non-select queries stay read_only.
    # These pass now (behavior already correct) and must not regress.
    # ------------------------------------------------------------------

    def test_keyword_query_stays_read_only(self):
        """[GREEN] Keyword search queries remain read_only (subject to hydration)."""
        assert get_tool_category("ToolSearch", {"query": "slack message"}) == "read_only"

    def test_empty_query_stays_read_only(self):
        """[GREEN] Empty query string is not a select: call — stays read_only."""
        assert get_tool_category("ToolSearch", {"query": ""}) == "read_only"

    def test_no_tool_input_stays_read_only(self):
        """[GREEN] Backward compat: no tool_input arg returns read_only unchanged."""
        assert get_tool_category("ToolSearch") == "read_only"

    def test_empty_tool_input_stays_read_only(self):
        """[GREEN] Empty dict (no query key) — not a select: call, stays read_only."""
        assert get_tool_category("ToolSearch", {}) == "read_only"

    def test_other_tools_unaffected_by_tool_input(self):
        """[GREEN] tool_input must not affect categorization for non-ToolSearch tools."""
        assert get_tool_category("Read", {"query": "select:anything"}) == "read_only"
        assert get_tool_category("Glob", {"query": "select:anything"}) == "read_only"
        assert get_tool_category("Bash", {"query": "select:anything"}) == "write"
