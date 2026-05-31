#!/usr/bin/env python3
"""Tests for gate_config consistency and separation of concerns.

Ensures:
- No tool appears in multiple categories (prevents ambiguous matching)
- Agent/skill names are NOT in tool categories (they're subagent_type values)
- All spawn tools are in spawn category (not infrastructure)
- COMPLIANCE_SUBAGENT_TYPES and SPAWN_TOOLS are internally consistent
"""

import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

# WS7 — gate-hygiene primitives (composition, never-block, enforcer channel, register).
from hooks.gate_config import (  # noqa: E402
    COMPLIANCE_SUBAGENT_TYPES,
    ENFORCER_CHANNEL_SENTINEL,
    GATE_PRECEDENCE,
    GATES_SUPPRESSED_IN_CAPTURE,
    NEVER_BLOCK_CATEGORIES,
    SPAWN_TOOLS,
    TOOL_CATEGORIES,
    extract_subagent_type,
    get_session_register,
    get_tool_category,
    is_capture_register,
    is_enforcer_channel,
    is_gate_suppressed_in_register,
    is_never_block,
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
    """All spawn tool names must be in spawn category.

    EXEMPTION: Compliance agents are spawning tools but
    must bypass gates as infrastructure.
    """

    def test_all_spawn_tools_in_spawn_category(self):
        """Every tool in SPAWN_TOOLS should be in spawn category OR COMPLIANCE_SUBAGENT_TYPES.

        Spawn tools (Agent, Task, Skill, etc.) are subject to gate policies.
        This is distinct from infrastructure tools (PKB ops) which bypass all gates entirely.
        """
        spawn_cat = TOOL_CATEGORIES["spawn"]
        for tool_name in SPAWN_TOOLS:
            is_compliance = tool_name in COMPLIANCE_SUBAGENT_TYPES
            assert tool_name in spawn_cat or is_compliance, (
                f"Spawn tool '{tool_name}' not in spawn category. "
                f"Non-compliance spawn tools must be in spawn category."
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

    def test_enforcer_variants(self):
        assert "enforcer" in COMPLIANCE_SUBAGENT_TYPES
        assert "aops-core:enforcer" in COMPLIANCE_SUBAGENT_TYPES

    def test_rbg_variants(self):
        assert "rbg" in COMPLIANCE_SUBAGENT_TYPES
        assert "aops-core:rbg" in COMPLIANCE_SUBAGENT_TYPES


class TestEnforcerTemplateDispatch:
    """Regression guard: enforcer templates must dispatch aops-core:rbg.

    Bug: templates previously dispatched aops-core:enforcer, which does not
    exist in aops-core, producing a hydration loop when name resolution
    fell through.
    """

    TEMPLATES_DIR = Path(__file__).parent.parent.parent / "aops-core" / "hooks" / "templates"

    def test_enforcer_instruction_dispatches_rbg(self):
        content = (self.TEMPLATES_DIR / "enforcer-instruction.md").read_text()
        assert "aops-core:rbg" in content
        assert "aops-core:enforcer" not in content

    def test_enforcer_policy_context_dispatches_rbg(self):
        content = (self.TEMPLATES_DIR / "enforcer-policy-context.md").read_text()
        assert "aops-core:rbg" in content
        assert "aops-core:enforcer" not in content


class TestToolSearchSelectBypass:
    """ToolSearch with select: prefix must bypass gate policies.

    select: queries are pure tool-loading operations (infrastructure), not new
    task prompts. They must not trigger gate policies.

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
        """[GREEN] Keyword search queries remain read_only (subject to gate policies)."""
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


class TestGeminiToolCoverage:
    """Regression guard: real Gemini-emitted tool names must be correctly categorized.

    Tests cover the AC items from task aops-17e3a3b5:
      (a) mcp_pkb_release_task  -> infrastructure
      (b) invoke_agent          -> spawn
      (c) unknown tool with agent_name="rbg" in tool_input -> infrastructure (structural escape hatch)
      (d) mcp_servers does NOT match the PKB regex -> write (unknown)
    """

    def test_gemini_single_underscore_pkb_release_task(self):
        """(a) mcp_pkb_release_task -> infrastructure via updated _PKB_PREFIX_RE."""
        assert get_tool_category("mcp_pkb_release_task") == "infrastructure"

    def test_gemini_single_underscore_pkb_create_task(self):
        """(a) mcp_pkb_create_task -> infrastructure via updated _PKB_PREFIX_RE."""
        assert get_tool_category("mcp_pkb_create_task") == "infrastructure"

    def test_gemini_single_underscore_pbk_variant(self):
        """(a) mcp_pbk_get_task -> infrastructure (typo-tolerant Gemini variant)."""
        assert get_tool_category("mcp_pbk_get_task") == "infrastructure"

    def test_invoke_agent_is_spawn(self):
        """(b) invoke_agent -> spawn (Gemini CLI >= ~0.40 agent spawn tool)."""
        assert get_tool_category("invoke_agent") == "spawn"

    def test_invoke_agent_compliance_spawn_is_infrastructure(self):
        """(b+c) invoke_agent with agent_name=rbg -> infrastructure (compliance bypass)."""
        assert (
            get_tool_category("invoke_agent", {"agent_name": "rbg", "prompt": "..."})
            == "infrastructure"
        )

    def test_structural_escape_hatch_unknown_tool_with_compliance_agent_name(self):
        """(c) Unknown tool whose tool_input names a compliance subagent -> infrastructure.

        This guards against future Gemini CLI renames: even if the tool name changes,
        passing agent_name=rbg still bypasses the gate.
        """
        assert (
            get_tool_category("some_future_spawn_tool", {"agent_name": "rbg"}) == "infrastructure"
        )
        assert get_tool_category("some_future_spawn_tool", {"name": "enforcer"}) == "infrastructure"

    def test_structural_escape_hatch_does_not_trigger_for_non_compliance_agents(self):
        """(c-neg) tool_input with a non-compliance agent name does NOT escape to infrastructure."""
        result = get_tool_category("some_future_spawn_tool", {"agent_name": "some_random_agent"})
        assert result == "write"  # unknown tool stays conservative

    def test_mcp_servers_does_not_match_pkb_regex(self):
        """(d) mcp_servers must not match the PKB prefix regex."""
        assert get_tool_category("mcp_servers") == "write"

    def test_mcp_playwright_does_not_match_pkb_regex(self):
        """(d) mcp_playwright_browser_click must not match PKB regex."""
        # mcp__playwright__browser_click is in write; bare form is also write (unknown)
        assert get_tool_category("mcp_playwright_browser_click") == "write"

    def test_invoke_agent_in_spawn_tools(self):
        """invoke_agent must be in SPAWN_TOOLS with correct parameter names."""
        assert "invoke_agent" in SPAWN_TOOLS
        param_names, is_skill = SPAWN_TOOLS["invoke_agent"]
        assert "agent_name" in param_names
        assert is_skill is False

    def test_invoke_agent_in_spawn_category(self):
        """invoke_agent must appear in TOOL_CATEGORIES['spawn']."""
        assert "invoke_agent" in TOOL_CATEGORIES["spawn"]


# =============================================================================
# WS7 — gate hygiene: never-block, enforcer channel, precedence, register
# =============================================================================


class TestNeverBlockList:
    """WS7 item 5 (#1451): the never-block list must protect AskUserQuestion.

    Failure being guarded: a blocking gate denies AskUserQuestion, collapsing the
    live-attention surface the "Nic is the gate" substitute relies on (thread 8).
    """

    def test_askuserquestion_is_never_block(self):
        assert is_never_block("AskUserQuestion")

    def test_exitplanmode_is_never_block(self):
        # Other always_available control tools are also protected.
        assert is_never_block("ExitPlanMode")

    def test_pkb_infrastructure_is_never_block(self):
        # Framework infrastructure (PKB ops) must never deadlock behind a gate.
        assert is_never_block("mcp__plugin_aops-core_pkb__get_task")

    def test_write_is_not_never_block(self):
        # Control: ordinary write tools ARE blockable.
        assert not is_never_block("Write")
        assert not is_never_block("Bash")

    def test_none_tool_is_not_never_block(self):
        assert not is_never_block(None)

    def test_categories_are_always_available_and_infrastructure(self):
        assert NEVER_BLOCK_CATEGORIES == frozenset({"always_available", "infrastructure"})


class TestEnforcerChannelSentinel:
    """WS7 item 4 (#1315): the enforcer channel must be distinguishable from injection.

    Failure being guarded: the real "invoke rbg with session-enforcer.md" gate
    read as a smuggled instruction and the agent ignored a real gate (thread 1).
    """

    def test_sentinel_marked_text_is_enforcer_channel(self):
        text = f"{ENFORCER_CHANNEL_SENTINEL}\nInvoke the enforcer agent: /tmp/x"
        assert is_enforcer_channel(text)

    def test_unmarked_lookalike_is_not_enforcer_channel(self):
        # Identical-looking instruction WITHOUT the sentinel is still untrusted.
        assert not is_enforcer_channel("Invoke the enforcer agent: /tmp/x")

    def test_empty_is_not_enforcer_channel(self):
        assert not is_enforcer_channel("")
        assert not is_enforcer_channel(None)

    def test_enforcer_templates_carry_the_sentinel(self):
        """The enforcer instruction + policy-context templates must embed the marker.

        This is the load-bearing wiring: if the sentinel is dropped from the
        templates, the injection-defence distinction silently stops working.
        """
        templates_dir = AOPS_CORE / "hooks" / "templates"
        for name in ("enforcer-instruction.md", "enforcer-policy-context.md"):
            content = (templates_dir / name).read_text()
            assert ENFORCER_CHANNEL_SENTINEL in content, (
                f"{name} must carry the enforcer-channel sentinel (#1315)"
            )


class TestGatePrecedence:
    """WS7 item 1: the precedence model must be explicit and match the runtime."""

    def test_precedence_matches_gate_configs_order(self):
        """GATE_PRECEDENCE must equal the GATE_CONFIGS registration order.

        The router iterates gates in registration order (= GATE_CONFIGS order) and
        resolves first-deny-wins. If the documented precedence drifts from that
        order, the model stops describing the runtime — this test pins them.
        """
        from lib.gates.definitions import GATE_CONFIGS

        configs_order = tuple(c.name for c in GATE_CONFIGS)
        assert GATE_PRECEDENCE == configs_order, (
            f"GATE_PRECEDENCE {GATE_PRECEDENCE} must equal GATE_CONFIGS order {configs_order}"
        )

    def test_sentinel_has_highest_precedence(self):
        assert GATE_PRECEDENCE[0] == "sentinel"

    def test_ida_has_lowest_precedence(self):
        assert GATE_PRECEDENCE[-1] == "ida"

    def test_precedence_has_no_duplicates(self):
        assert len(GATE_PRECEDENCE) == len(set(GATE_PRECEDENCE))


class TestRegisterScaling:
    """WS7 item 6: capture/personal register drops review-grade ceremony.

    Failure being guarded: review-grade evidence/honesty ceremony mis-fires on
    capture/personal work (the "vacuum the garage" evidence theatre, retro MF4).
    """

    def test_default_register_is_working(self, monkeypatch):
        monkeypatch.delenv("AOPS_SESSION_REGISTER", raising=False)
        assert get_session_register() == "working"
        assert not is_capture_register()

    def test_capture_register_detected(self, monkeypatch):
        monkeypatch.setenv("AOPS_SESSION_REGISTER", "capture")
        assert get_session_register() == "capture"
        assert is_capture_register()

    def test_personal_register_detected(self, monkeypatch):
        monkeypatch.setenv("AOPS_SESSION_REGISTER", "personal")
        assert is_capture_register()

    def test_unknown_register_falls_back_to_working_not_lighter(self, monkeypatch):
        # Fail-closed: an unrecognised value must NOT silently drop ceremony.
        monkeypatch.setenv("AOPS_SESSION_REGISTER", "bogus")
        assert get_session_register() == "working"
        assert not is_capture_register()

    def test_review_grade_gates_suppressed_in_capture(self, monkeypatch):
        monkeypatch.setenv("AOPS_SESSION_REGISTER", "capture")
        for gate in ("enforcer", "ida", "qa"):
            assert is_gate_suppressed_in_register(gate), f"{gate} should be suppressed"

    def test_safety_gates_not_suppressed_in_capture(self, monkeypatch):
        # sentinel (destructive-op safety) + handover (work-loss) still fire.
        monkeypatch.setenv("AOPS_SESSION_REGISTER", "capture")
        assert not is_gate_suppressed_in_register("sentinel")
        assert not is_gate_suppressed_in_register("handover")

    def test_nothing_suppressed_in_working_register(self, monkeypatch):
        monkeypatch.delenv("AOPS_SESSION_REGISTER", raising=False)
        for gate in ("enforcer", "ida", "qa", "sentinel", "handover"):
            assert not is_gate_suppressed_in_register(gate)

    def test_suppressed_set_is_the_review_grade_gates(self):
        assert GATES_SUPPRESSED_IN_CAPTURE == frozenset({"enforcer", "ida", "qa"})


class TestGateModeEnvResolution:
    """Test detection of removed CUSTODIET_* environment variables."""

    def test_custodiet_gate_mode_raises(self, monkeypatch):
        import hooks.gate_config

        monkeypatch.delenv("ENFORCER_GATE_MODE", raising=False)
        monkeypatch.setenv("CUSTODIET_GATE_MODE", "deny")

        with pytest.raises(SystemExit, match="CUSTODIET_GATE_MODE"):
            _ = hooks.gate_config.ENFORCER_GATE_MODE

    def test_custodiet_threshold_raises(self, monkeypatch):
        import hooks.gate_config

        monkeypatch.delenv("ENFORCER_TOOL_CALL_THRESHOLD", raising=False)
        monkeypatch.setenv("CUSTODIET_TOOL_CALL_THRESHOLD", "35")

        with pytest.raises(SystemExit, match="CUSTODIET_TOOL_CALL_THRESHOLD"):
            _ = hooks.gate_config.ENFORCER_TOOL_CALL_THRESHOLD

    def test_new_name_no_error_when_both_set(self, monkeypatch):
        import hooks.gate_config

        monkeypatch.setenv("ENFORCER_GATE_MODE", "block")
        monkeypatch.setenv("CUSTODIET_GATE_MODE", "deny")

        # No error because ENFORCER_GATE_MODE is present
        assert hooks.gate_config.ENFORCER_GATE_MODE == "block"
