"""Test Skill Activation Bypass for Hydration."""

from unittest.mock import patch
from hooks.gate_registry import (
    check_hydration_gate,
    check_skill_activation_listener,
    GateVerdict,
)
from hooks.schemas import HookContext


@patch("hooks.gate_registry.session_state")
@patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
def test_substantive_skill_clears_hydration(mock_get_temp_dir, mock_session_state):
    """Verify substantive skill activation bypasses hydration check and clears pending."""
    mock_session_state.is_hydration_pending.return_value = True
    mock_get_temp_dir.return_value = "/tmp/hydrator"

    # 1. Activation Check (PreToolUse)
    # Ensure activate_skill (any name) is allowed even if hydration pending
    ctx_pre = HookContext(
        session_id="s1",
        hook_event="PreToolUse",
        raw_input={"tool_name": "activate_skill", "tool_input": {"name": "daily"}},
        tool_name="activate_skill",
        tool_input={"name": "daily"},
    )
    result_pre = check_hydration_gate(ctx_pre)
    assert result_pre is None  # Allowed

    # 2. State Cleared (PostToolUse) for substantive skill
    # Ensure hydration pending is cleared after activation of non-infrastructure skill
    ctx_post = HookContext(
        session_id="s1",
        hook_event="PostToolUse",
        raw_input={"tool_name": "activate_skill", "tool_input": {"name": "daily"}},
        tool_name="activate_skill",
        tool_input={"name": "daily"},
    )

    result_post = check_skill_activation_listener(ctx_post)

    # Verify Allow result and state clearing call for substantive skill
    assert result_post is not None
    assert result_post.verdict == GateVerdict.ALLOW
    assert result_post.metadata.get("source") == "skill_activation_bypass"
    mock_session_state.clear_hydration_pending.assert_called_with("s1")


@patch("hooks.gate_registry.session_state")
def test_infrastructure_skill_does_not_clear_hydration(mock_session_state):
    """Verify infrastructure skills like /bump do NOT clear hydration pending."""
    # Test with Gemini's activate_skill tool
    ctx_bump = HookContext(
        session_id="s2",
        hook_event="PostToolUse",
        raw_input={"tool_name": "activate_skill", "tool_input": {"name": "bump"}},
        tool_name="activate_skill",
        tool_input={"name": "bump"},
    )

    result = check_skill_activation_listener(ctx_bump)

    # Should still return ALLOW (skill ran successfully)
    assert result is not None
    assert result.verdict == GateVerdict.ALLOW
    # But should NOT clear hydration pending
    assert result.metadata.get("source") == "skill_activation_infrastructure"
    mock_session_state.clear_hydration_pending.assert_not_called()


@patch("hooks.gate_registry.session_state")
def test_infrastructure_skill_with_prefix_does_not_clear_hydration(mock_session_state):
    """Verify infrastructure skills with aops-core: prefix do NOT clear hydration."""
    ctx_bump = HookContext(
        session_id="s3",
        hook_event="PostToolUse",
        raw_input={
            "tool_name": "activate_skill",
            "tool_input": {"name": "aops-core:bump"},
        },
        tool_name="activate_skill",
        tool_input={"name": "aops-core:bump"},
    )

    result = check_skill_activation_listener(ctx_bump)

    assert result is not None
    assert result.verdict == GateVerdict.ALLOW
    assert result.metadata.get("source") == "skill_activation_infrastructure"
    mock_session_state.clear_hydration_pending.assert_not_called()


@patch("hooks.gate_registry.session_state")
def test_claude_skill_tool_clears_hydration_for_substantive_skill(mock_session_state):
    """Verify Claude Code's Skill tool clears hydration for substantive skills."""
    ctx = HookContext(
        session_id="s4",
        hook_event="PostToolUse",
        raw_input={"tool_name": "Skill", "tool_input": {"skill": "analyst"}},
        tool_name="Skill",
        tool_input={"skill": "analyst"},
    )

    result = check_skill_activation_listener(ctx)

    assert result is not None
    assert result.verdict == GateVerdict.ALLOW
    assert result.metadata.get("source") == "skill_activation_bypass"
    mock_session_state.clear_hydration_pending.assert_called_with("s4")


@patch("hooks.gate_registry.session_state")
def test_claude_skill_tool_does_not_clear_for_infrastructure(mock_session_state):
    """Verify Claude Code's Skill tool does NOT clear hydration for infrastructure skills."""
    ctx = HookContext(
        session_id="s5",
        hook_event="PostToolUse",
        raw_input={"tool_name": "Skill", "tool_input": {"skill": "aops-core:diag"}},
        tool_name="Skill",
        tool_input={"skill": "aops-core:diag"},
    )

    result = check_skill_activation_listener(ctx)

    assert result is not None
    assert result.verdict == GateVerdict.ALLOW
    assert result.metadata.get("source") == "skill_activation_infrastructure"
    mock_session_state.clear_hydration_pending.assert_not_called()


@patch("hooks.gate_registry.session_state")
def test_multiple_infrastructure_skills(mock_session_state):
    """Verify multiple infrastructure skills are correctly identified."""
    infrastructure_samples = [
        "bump",
        "diag",
        "log",
        "q",
        "aops-core:dump",
        "aops-core:email",
    ]

    for skill_name in infrastructure_samples:
        mock_session_state.reset_mock()
        ctx = HookContext(
            session_id="s6",
            hook_event="PostToolUse",
            raw_input={"tool_name": "Skill", "tool_input": {"skill": skill_name}},
            tool_name="Skill",
            tool_input={"skill": skill_name},
        )

        result = check_skill_activation_listener(ctx)

        assert result is not None, f"Failed for {skill_name}"
        assert result.verdict == GateVerdict.ALLOW, f"Failed for {skill_name}"
        assert result.metadata.get("source") == "skill_activation_infrastructure", (
            f"Failed for {skill_name}"
        )
        mock_session_state.clear_hydration_pending.assert_not_called()


@patch("hooks.gate_registry.session_state")
def test_non_skill_tool_ignored(mock_session_state):
    """Verify non-skill tools are ignored by the listener."""
    ctx = HookContext(
        session_id="s7",
        hook_event="PostToolUse",
        raw_input={"tool_name": "Read", "tool_input": {"file_path": "/tmp/test.txt"}},
        tool_name="Read",
        tool_input={"file_path": "/tmp/test.txt"},
    )

    result = check_skill_activation_listener(ctx)

    assert result is None
    mock_session_state.clear_hydration_pending.assert_not_called()


@patch("hooks.gate_registry.session_state")
def test_empty_skill_name_does_not_clear_hydration(mock_session_state):
    """Verify empty/missing skill name does NOT clear hydration (fail-safe)."""
    # Test with empty skill name
    ctx_empty = HookContext(
        session_id="s8",
        hook_event="PostToolUse",
        raw_input={"tool_name": "Skill", "tool_input": {"skill": ""}},
        tool_name="Skill",
        tool_input={"skill": ""},
    )

    result = check_skill_activation_listener(ctx_empty)

    assert result is not None
    assert result.verdict == GateVerdict.ALLOW
    assert result.metadata.get("source") == "skill_activation_unknown"
    mock_session_state.clear_hydration_pending.assert_not_called()


@patch("hooks.gate_registry.session_state")
def test_missing_skill_name_does_not_clear_hydration(mock_session_state):
    """Verify missing skill name key does NOT clear hydration (fail-safe)."""
    # Test with no skill/name key at all
    ctx_missing = HookContext(
        session_id="s9",
        hook_event="PostToolUse",
        raw_input={"tool_name": "Skill", "tool_input": {}},
        tool_name="Skill",
        tool_input={},
    )

    result = check_skill_activation_listener(ctx_missing)

    assert result is not None
    assert result.verdict == GateVerdict.ALLOW
    assert result.metadata.get("source") == "skill_activation_unknown"
    mock_session_state.clear_hydration_pending.assert_not_called()
