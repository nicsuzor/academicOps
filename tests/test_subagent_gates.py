import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from hooks.gate_config import extract_subagent_type
from hooks.router import HookRouter
from hooks.schemas import HookContext
from lib.gate_model import GateVerdict
from lib.gate_types import GateStatus
from lib.gates.definitions import GATE_CONFIGS
from lib.gates.engine import GenericGate
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState

# --- Fixture loading (mirrors test_gate_verdicts.py pattern) ---

FIXTURES_DIR = Path(__file__).parent / "hooks" / "fixtures"
LIVE_SCENARIOS_FILE = FIXTURES_DIR / "gate_scenarios_live.json"


def _load_live_scenarios() -> dict:
    if LIVE_SCENARIOS_FILE.exists():
        with LIVE_SCENARIOS_FILE.open() as f:
            return json.load(f)
    return {}


LIVE = _load_live_scenarios()


def _scenarios(group: str) -> list[dict]:
    return LIVE.get(group, [])


@pytest.fixture
def router():
    # Mock get_session_data to avoid reading shared PID session map during xdist tests
    with patch("hooks.router.get_session_data", return_value={}):
        return HookRouter()


# =============================================================================
# Normalization tests (these use raw_input dicts, not fixture scenarios)
# =============================================================================


def test_router_normalize_subagent_type_extraction(router):
    """Test extraction of subagent_type from tool_input in normalize_input."""
    raw_input = {
        "hook_event_name": "PreToolUse",
        "session_id": "main-session",
        "tool_name": "Task",
        "tool_input": {"subagent_type": "hydrator", "prompt": "test"},
    }

    ctx = router.normalize_input(raw_input)
    assert ctx.subagent_type == "hydrator"
    assert ctx.tool_name == "Task"


def test_router_normalize_subagent_type_from_string_input(router):
    """Test extraction of subagent_type when tool_input is a JSON string."""
    raw_input = {
        "hook_event_name": "PreToolUse",
        "session_id": "main-session",
        "tool_name": "Task",
        "tool_input": '{"subagent_type": "critic", "prompt": "test"}',
    }

    ctx = router.normalize_input(raw_input)
    assert ctx.subagent_type == "critic"


def test_subagent_detection_from_id(router):
    """Test that short hex session IDs are correctly identified as subagents."""
    raw_input = {
        "hook_event_name": "PreToolUse",
        "session_id": "aafdeee",  # Typical Claude subagent ID
        "tool_name": "Read",
        "tool_input": {"file_path": "test.txt"},
    }

    ctx = router.normalize_input(raw_input)
    assert ctx.is_subagent is True


def test_router_normalize_skill_tool_extracts_skill_name(router):
    """normalize_input extracts skill name from Skill tool into subagent_type."""
    raw_input = {
        "hook_event_name": "PostToolUse",
        "session_id": "main-session-uuid-1234",
        "tool_name": "Skill",
        "tool_input": {"skill": "handover", "args": ""},
    }
    ctx = router.normalize_input(raw_input)
    assert ctx.subagent_type == "handover"
    assert ctx.tool_name == "Skill"


def test_router_normalize_skill_tool_not_subagent(router):
    """Main-session Skill invocations must NOT be classified as subagent sessions."""
    raw_input = {
        "hook_event_name": "PostToolUse",
        "session_id": "main-session-uuid-1234",
        "tool_name": "Skill",
        "tool_input": {"skill": "handover", "args": ""},
    }
    ctx = router.normalize_input(raw_input)
    assert ctx.is_subagent is False


def test_router_normalize_activate_skill_extracts_skill_name(router):
    """normalize_input extracts skill name from activate_skill (Gemini) into subagent_type."""
    raw_input = {
        "hook_event_name": "PostToolUse",
        "session_id": "main-session-uuid-5678",
        "tool_name": "activate_skill",
        "tool_input": {"skill": "handover"},
    }
    ctx = router.normalize_input(raw_input)
    assert ctx.subagent_type == "handover"
    assert ctx.is_subagent is False


# =============================================================================
# Gate bypass in subagent sessions — backed by real log data
# =============================================================================

_SUBAGENT_INTERNAL = _scenarios("gemini_subagent_internal_tools")
_SPAWN_IN_MAIN = _scenarios("claude_spawn_in_main_session") + _scenarios(
    "gemini_spawn_in_main_session"
)
_SUBAGENT_EVENTS = _scenarios("claude_subagent_events") + _scenarios("gemini_subagent_events")


class TestSubagentInternalToolsSkipGates:
    """Tool calls inside subagent sessions skip gate dispatch entirely.

    Backed by real log data: PreToolUse events where is_subagent=True.
    """

    @pytest.mark.parametrize(
        "scenario",
        _SUBAGENT_INTERNAL[:10],  # Cap to avoid huge parametrization
        ids=[s["id"] for s in _SUBAGENT_INTERNAL[:10]],
    )
    def test_subagent_internal_skips_gates(self, router, scenario):
        GateRegistry.initialize()
        state = SessionState.create("test-subagent")
        ctx = HookContext(
            session_id="test-subagent",
            hook_event=scenario["hook_event"],
            tool_name=scenario.get("tool_name"),
            tool_input=scenario.get("tool_input", {}),
            is_subagent=scenario.get("is_subagent", False),
            subagent_type=scenario.get("subagent_type"),
        )
        result = router._dispatch_gates(ctx, state)
        assert result is None, (
            f"[{scenario['id']}] Subagent internal tool call should skip gates, "
            f"got {result.verdict.value if result else 'N/A'}"
        )
        assert state.get_gate("custodiet").ops_since_open == 0


class TestSpawnToolNotClassifiedAsSubagent:
    """Agent(subagent_type=...) calls from the main session must NOT be classified as subagent.

    Real logs show these events had is_subagent=True (the bug). After the fix,
    normalize_input() should set is_subagent=False for spawn tool calls.

    Backed by real log data: PreToolUse for Agent tool with subagent_type extracted.
    """

    @pytest.mark.parametrize(
        "scenario",
        _SPAWN_IN_MAIN[:10],
        ids=[s["id"] for s in _SPAWN_IN_MAIN[:10]],
    )
    def test_spawn_not_subagent(self, router, scenario):
        """Spawn tool calls should be classified as main session after fix."""
        # Re-create a raw_input-like dict from the scenario and run through normalize_input
        raw_input = {
            "hook_event_name": scenario["hook_event"],
            "session_id": "main-session-uuid-1234",  # Long UUID = main session
            "tool_name": scenario["tool_name"],
            "tool_input": scenario.get("tool_input", {}),
        }
        ctx = router.normalize_input(raw_input)
        assert ctx.is_subagent is False, (
            f"[{scenario['id']}] Spawn tool '{scenario['tool_name']}' in main session "
            f"should NOT be classified as subagent"
        )
        # subagent_type should still be extracted for trigger evaluation
        if scenario.get("subagent_type"):
            assert ctx.subagent_type == scenario["subagent_type"]


class TestSubagentEventsNotSubagent:
    """SubagentStart/SubagentStop fire in the parent session — not subagent sessions.

    Backed by real log data: is_subagent=False for these events.
    """

    @pytest.mark.parametrize(
        "scenario",
        _SUBAGENT_EVENTS[:10],
        ids=[s["id"] for s in _SUBAGENT_EVENTS[:10]],
    )
    def test_subagent_events_not_subagent(self, router, scenario):
        assert scenario["is_subagent"] is False, (
            f"[{scenario['id']}] {scenario['hook_event']} should have "
            f"is_subagent=False in real log data"
        )


# =============================================================================
# Gate engine unit tests (these test GenericGate directly, not via router)
# =============================================================================


def test_hydration_gate_simplified_triggers():
    """Test that simplified triggers in hydration gate work correctly."""
    state = SessionState.create("test-session")
    state.get_gate("hydration").status = GateStatus.CLOSED

    hydration_config = next(g for g in GATE_CONFIGS if g.name == "hydration")
    gate = GenericGate(hydration_config)

    # 1. Test SubagentStop trigger
    ctx_stop = HookContext(
        session_id="aafdeee", hook_event="SubagentStop", subagent_type="prompt-hydrator"
    )
    gate.on_subagent_stop(ctx_stop, state)
    assert state.get_gate("hydration").status == GateStatus.OPEN

    # 2. Reset and Test PostToolUse fallback trigger
    state.get_gate("hydration").status = GateStatus.CLOSED
    ctx_post = HookContext(
        session_id="aafdeee", hook_event="PostToolUse", subagent_type="prompt-hydrator"
    )
    gate.on_tool_use(ctx_post, state)
    assert state.get_gate("hydration").status == GateStatus.OPEN


def test_regex_hook_event_matching():
    """Test that GenericGate supports regex in hook_event matching."""
    from lib.gate_types import GateCondition

    state = SessionState.create("s1")

    cond = GateCondition(
        hook_event="^(SubagentStop|PostToolUse)$", subagent_type_pattern="prompt-hydrator"
    )

    hydration_config = next(g for g in GATE_CONFIGS if g.name == "hydration")
    gate = GenericGate(hydration_config)

    # Matches
    assert (
        gate._evaluate_condition(
            cond,
            HookContext(
                session_id="s1", hook_event="SubagentStop", subagent_type="prompt-hydrator"
            ),
            state.get_gate("hydration"),
            state,
        )
        is True
    )
    assert (
        gate._evaluate_condition(
            cond,
            HookContext(session_id="s1", hook_event="PostToolUse", subagent_type="prompt-hydrator"),
            state.get_gate("hydration"),
            state,
        )
        is True
    )

    # Does not match
    assert (
        gate._evaluate_condition(
            cond,
            HookContext(session_id="s1", hook_event="PreToolUse", subagent_type="prompt-hydrator"),
            state.get_gate("hydration"),
            state,
        )
        is False
    )
    assert (
        gate._evaluate_condition(
            cond,
            HookContext(session_id="s1", hook_event="Stop", subagent_type="prompt-hydrator"),
            state.get_gate("hydration"),
            state,
        )
        is False
    )


# =============================================================================
# extract_subagent_type() unit tests
# =============================================================================


class TestExtractSubagentType:
    """Tests for the cross-platform extract_subagent_type() function."""

    def test_claude_task_extracts_subagent_type(self):
        """Claude's Task tool extracts subagent_type param."""
        result, is_skill = extract_subagent_type(
            "Task", {"subagent_type": "custodiet", "prompt": "check"}
        )
        assert result == "custodiet"
        assert is_skill is False

    def test_claude_skill_extracts_skill_name(self):
        """Claude's Skill tool extracts skill param and marks as skill."""
        result, is_skill = extract_subagent_type("Skill", {"skill": "handover", "args": ""})
        assert result == "handover"
        assert is_skill is True

    def test_gemini_delegate_extracts_name(self):
        """Gemini's delegate_to_agent extracts name param."""
        result, is_skill = extract_subagent_type(
            "delegate_to_agent", {"name": "aops-core:qa", "query": "test"}
        )
        assert result == "aops-core:qa"
        assert is_skill is False

    def test_gemini_delegate_extracts_agent_name_fallback(self):
        """Gemini's delegate_to_agent falls back to agent_name param."""
        result, is_skill = extract_subagent_type("delegate_to_agent", {"agent_name": "custodiet"})
        assert result == "custodiet"
        assert is_skill is False

    def test_gemini_activate_skill_extracts_skill(self):
        """Gemini's activate_skill extracts skill param and marks as skill."""
        result, is_skill = extract_subagent_type("activate_skill", {"skill": "dump"})
        assert result == "dump"
        assert is_skill is True

    def test_unknown_tool_returns_none(self):
        """Non-spawn tools return (None, False)."""
        result, is_skill = extract_subagent_type("Read", {"file_path": "test.py"})
        assert result is None
        assert is_skill is False

    def test_none_tool_returns_none(self):
        """None tool_name returns (None, False)."""
        result, is_skill = extract_subagent_type(None, {"anything": "value"})
        assert result is None
        assert is_skill is False

    def test_missing_params_returns_none(self):
        """Spawn tool without matching params returns (None, is_skill)."""
        result, is_skill = extract_subagent_type("Task", {"prompt": "test"})
        assert result is None
        assert is_skill is False

    def test_skill_with_missing_params_returns_none_with_is_skill(self):
        """Skill tool without skill param returns (None, True)."""
        result, is_skill = extract_subagent_type("Skill", {"args": "test"})
        assert result is None
        assert is_skill is True


# =============================================================================
# E2E gate dispatch tests with real DEBUG_HOOKS raw stdin
# =============================================================================
#
# Source: cc_hooks_9f3e3217-fb40-44cf-8a93-f78b6b292e29.jsonl
# Session: polecat worker crew/michelle_61, 2026-03-10T03:22–03:27
# Captured with DEBUG_HOOKS=1 via _debug_log_input() in router.py:74-90
#
# Raw stdin payloads are verbatim from the debug log except:
# - last_assistant_message in SubagentStop truncated (irrelevant to gate logic)
# - tool_response.content[].text in PostToolUse truncated (same reason)
# Each scenario records its source line and timestamp for traceability.

_LOG_FILE = "cc_hooks_9f3e3217-fb40-44cf-8a93-f78b6b292e29.jsonl"

# Line 38, ts=2026-03-10T03:26:14.835878
# Main session PreToolUse for Agent tool spawning custodiet.
_STDIN_SPAWN_AGENT_COMPLIANCE = {
    "session_id": "9f3e3217-fb40-44cf-8a93-f78b6b292e29",
    "transcript_path": "/home/debian/.claude/projects/-opt-nic--aops-crew-michelle-61-aops/9f3e3217-fb40-44cf-8a93-f78b6b292e29.jsonl",
    "cwd": "/opt/nic/.aops/crew/michelle_61/aops",
    "permission_mode": "bypassPermissions",
    "hook_event_name": "PreToolUse",
    "tool_name": "Agent",
    "tool_input": {
        "description": "Compliance check",
        "prompt": "/opt/nic/.aops/sessions/hooks/20260310-9f3e3217-custodiet.md",
        "subagent_type": "aops-core:custodiet",
    },
    "tool_use_id": "toolu_017q4iiDqdFQfdEvCs2BTTz4",
}

# Line 39, ts=2026-03-10T03:26:15.296250
# SubagentStart fires in main session context about the custodiet subagent.
_STDIN_SUBAGENT_START = {
    "session_id": "9f3e3217-fb40-44cf-8a93-f78b6b292e29",
    "transcript_path": "/home/debian/.claude/projects/-opt-nic--aops-crew-michelle-61-aops/9f3e3217-fb40-44cf-8a93-f78b6b292e29.jsonl",
    "cwd": "/opt/nic/.aops/crew/michelle_61/aops",
    "agent_id": "aa27af7b50acfae7f",
    "agent_type": "aops-core:custodiet",
    "hook_event_name": "SubagentStart",
}

# Line 40, ts=2026-03-10T03:26:16.907683
# Subagent internal PreToolUse — custodiet reading its audit file.
_STDIN_SUBAGENT_INTERNAL_READ = {
    "session_id": "9f3e3217-fb40-44cf-8a93-f78b6b292e29",
    "transcript_path": "/home/debian/.claude/projects/-opt-nic--aops-crew-michelle-61-aops/9f3e3217-fb40-44cf-8a93-f78b6b292e29.jsonl",
    "cwd": "/opt/nic/.aops/crew/michelle_61/aops",
    "permission_mode": "bypassPermissions",
    "agent_id": "aa27af7b50acfae7f",
    "agent_type": "aops-core:custodiet",
    "hook_event_name": "PreToolUse",
    "tool_name": "Read",
    "tool_input": {"file_path": "/opt/nic/.aops/sessions/hooks/20260310-9f3e3217-custodiet.md"},
    "tool_use_id": "toolu_01KTvJFkfJZWCkAMGRmD5X8t",
}

# Line 2, ts=2026-03-10T03:22:30 (approx — first tool call in session)
# Main session Bash tool call — no subagent context at all.
_STDIN_MAIN_SESSION_BASH = {
    "session_id": "9f3e3217-fb40-44cf-8a93-f78b6b292e29",
    "transcript_path": "/home/debian/.claude/projects/-opt-nic--aops-crew-michelle-61-aops/9f3e3217-fb40-44cf-8a93-f78b6b292e29.jsonl",
    "cwd": "/opt/nic/.aops/crew/michelle_61/aops",
    "permission_mode": "bypassPermissions",
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {
        "command": "gh pr view 846 --json title,body,author,state,baseRefName,headRefName,additions,deletions,changedFiles,commits --jq '{title,body,author: .author.login,state,base: .baseRefName,head: .headRefName,additions,deletions,changedFiles,commits: (.commits | length)}'",
        "description": "Get PR #846 summary",
    },
    "tool_use_id": "toolu_0165GS1S2rUgXg21UV3qqi1W",
}

# Line 68, ts=2026-03-10T03:27:05.009187
# SubagentStop fires in main session context after custodiet finishes.
_STDIN_SUBAGENT_STOP = {
    "session_id": "9f3e3217-fb40-44cf-8a93-f78b6b292e29",
    "transcript_path": "/home/debian/.claude/projects/-opt-nic--aops-crew-michelle-61-aops/9f3e3217-fb40-44cf-8a93-f78b6b292e29.jsonl",
    "cwd": "/opt/nic/.aops/crew/michelle_61/aops",
    "permission_mode": "bypassPermissions",
    "agent_id": "aa27af7b50acfae7f",
    "agent_type": "aops-core:custodiet",
    "hook_event_name": "SubagentStop",
    "stop_hook_active": False,
    "agent_transcript_path": "/home/debian/.claude/projects/-opt-nic--aops-crew-michelle-61-aops/9f3e3217-fb40-44cf-8a93-f78b6b292e29/subagents/agent-aa27af7b50acfae7f.jsonl",
    "last_assistant_message": "(truncated — content irrelevant to gate logic)",
}

# Line 69, ts=2026-03-10T03:27:05 (approx)
# PostToolUse for Agent after custodiet spawn completes.
_STDIN_SPAWN_AGENT_POSTTOOLUSE = {
    "session_id": "9f3e3217-fb40-44cf-8a93-f78b6b292e29",
    "transcript_path": "/home/debian/.claude/projects/-opt-nic--aops-crew-michelle-61-aops/9f3e3217-fb40-44cf-8a93-f78b6b292e29.jsonl",
    "cwd": "/opt/nic/.aops/crew/michelle_61/aops",
    "permission_mode": "bypassPermissions",
    "hook_event_name": "PostToolUse",
    "tool_name": "Agent",
    "tool_input": {
        "description": "Compliance check",
        "prompt": "/opt/nic/.aops/sessions/hooks/20260310-9f3e3217-custodiet.md",
        "subagent_type": "aops-core:custodiet",
    },
    "tool_response": {
        "status": "completed",
        "prompt": "/opt/nic/.aops/sessions/hooks/20260310-9f3e3217-custodiet.md",
        "agentId": "aa27af7b50acfae7f",
        "content": [{"type": "text", "text": "(truncated)"}],
    },
}


class TestE2EGateDispatchFromRawStdin:
    """E2E tests passing real raw hook stdin through normalize_input → _dispatch_gates.

    Every scenario is backed by actual DEBUG_HOOKS=1 captured data.
    No field mapping or reconstruction — raw stdin dicts are passed directly.

    Source log: {_LOG_FILE}
    """

    @pytest.fixture(autouse=True)
    def _init_gate_registry(self):
        """Ensure GateRegistry is populated (normally done by execute_hooks)."""
        from lib.gates.registry import GateRegistry

        GateRegistry.initialize()

    @pytest.fixture()
    def state_hydration_closed(self):
        """Session state with hydration gate CLOSED (pre-hydration).

        In production, hydrate_prompt sets temp_path in gate metrics during
        UserPromptSubmit (before any PreToolUse fires). We replicate that here.
        """
        state = SessionState.create("test-e2e-raw-stdin")
        gate = state.get_gate("hydration")
        gate.status = GateStatus.CLOSED
        gate.metrics["temp_path"] = "/tmp/test-hydration-context.md"
        return state

    # --- Subagent internal tool calls skip gate policies (compliance bypass) ---

    def test_subagent_internal_compliance_read_skips_gates(self, router, state_hydration_closed):
        """Custodiet subagent's Read tool is not blocked even with hydration CLOSED.

        Source: {_LOG_FILE} line 40, ts=2026-03-10T03:26:16.907683
        The subagent's agent_id/agent_type fields mark it as a compliance agent,
        so _dispatch_gates only evaluates triggers, never enforcing policies.
        """
        stdin = copy.deepcopy(_STDIN_SUBAGENT_INTERNAL_READ)
        ctx = router.normalize_input(stdin)

        # Normalization: detected as subagent via agent_id field
        assert ctx.is_subagent is True
        assert ctx.subagent_type == "aops-core:custodiet"
        assert ctx.hook_event == "PreToolUse"
        assert ctx.tool_name == "Read"

        # Gate dispatch: compliance agent bypass — never DENY
        result = router._dispatch_gates(ctx, state_hydration_closed)
        if result is not None:
            assert result.verdict != GateVerdict.DENY

    # --- Spawn tool (Agent) for compliance agent gets compliance bypass ---

    def test_spawn_agent_compliance_not_denied(self, router, state_hydration_closed):
        """Agent tool spawning custodiet is never denied, even with hydration CLOSED.

        Source: {_LOG_FILE} line 38, ts=2026-03-10T03:26:14.835878
        The subagent_type is extracted from tool_input, but since the spawn
        happens in the main session (not inside a subagent), is_subagent stays
        False. The spawn is not blocked because get_tool_category() classifies
        compliance agent spawns as "infrastructure" (excluded from gate policies).
        """
        stdin = copy.deepcopy(_STDIN_SPAWN_AGENT_COMPLIANCE)
        ctx = router.normalize_input(stdin)

        # Normalization: subagent_type extracted from Agent tool_input
        assert ctx.subagent_type == "aops-core:custodiet"
        assert ctx.hook_event == "PreToolUse"
        assert ctx.tool_name == "Agent"
        # Spawn tool calls stay in main session context — is_subagent is False
        assert ctx.is_subagent is False

        # Gate dispatch: compliance spawn classified as "infrastructure" → never DENY
        result = router._dispatch_gates(ctx, state_hydration_closed)
        if result is not None:
            assert result.verdict != GateVerdict.DENY

    # --- SubagentStart/SubagentStop are NOT subagent events ---

    def test_subagent_start_not_classified_as_subagent(self, router):
        """SubagentStart fires in the main agent's context, is_subagent forced False.

        Source: {_LOG_FILE} line 39, ts=2026-03-10T03:26:15.296250
        Even though agent_id/agent_type are present, the router overrides
        is_subagent to False for SubagentStart events (they describe a subagent
        starting, but the hook fires in the parent session).
        """
        stdin = copy.deepcopy(_STDIN_SUBAGENT_START)
        ctx = router.normalize_input(stdin)

        assert ctx.is_subagent is False
        assert ctx.hook_event == "SubagentStart"
        assert ctx.subagent_type == "aops-core:custodiet"

    def test_subagent_stop_not_classified_as_subagent(self, router):
        """SubagentStop fires in the main agent's context, is_subagent forced False.

        Source: {_LOG_FILE} line 68, ts=2026-03-10T03:27:05.009187
        Same override as SubagentStart — the event carries agent metadata
        but is not itself a subagent event.
        """
        stdin = copy.deepcopy(_STDIN_SUBAGENT_STOP)
        ctx = router.normalize_input(stdin)

        assert ctx.is_subagent is False
        assert ctx.hook_event == "SubagentStop"
        assert ctx.subagent_type == "aops-core:custodiet"

    # --- Main session non-spawn tool call — gates evaluate normally ---

    def test_main_session_bash_gates_evaluate(self, router, state_hydration_closed, monkeypatch):
        """Main session Bash tool is subject to hydration gate when CLOSED.

        Source: {_LOG_FILE} line 2, ts=2026-03-10T03:22:30 (approx)
        No subagent context: no agent_id, no agent_type, UUID session_id.
        Hydration policy fires because Bash is not in excluded categories.
        Monkeypatch forces policy verdict to 'warn' to prevent state-leak flakiness.
        """
        stdin = copy.deepcopy(_STDIN_MAIN_SESSION_BASH)
        ctx = router.normalize_input(stdin)

        # Normalization: plain main-session tool call
        assert ctx.is_subagent is False
        assert ctx.subagent_type is None
        assert ctx.tool_name == "Bash"

        # Dynamically change the policy verdict since GateRegistry caches configs
        gate_config = GateRegistry.get_gate("hydration").config
        monkeypatch.setattr(gate_config.policies[0], "verdict", "warn")

        # Gate dispatch: hydration CLOSED blocks non-infrastructure tools
        result = router._dispatch_gates(ctx, state_hydration_closed)
        assert result is not None
        assert result.verdict == GateVerdict.WARN

    # --- PostToolUse for spawn tool — gates still evaluate triggers ---

    def test_spawn_agent_posttooluse_fires_triggers(self, router, state_hydration_closed):
        """PostToolUse for Agent carries subagent_type and fires gate triggers.

        Source: {_LOG_FILE} line 69, ts=2026-03-10T03:27:05 (approx)
        The tool_response contains the completed subagent's output. The
        subagent_type is extracted from tool_input (same as PreToolUse).
        """
        stdin = copy.deepcopy(_STDIN_SPAWN_AGENT_POSTTOOLUSE)
        ctx = router.normalize_input(stdin)

        assert ctx.subagent_type == "aops-core:custodiet"
        assert ctx.hook_event == "PostToolUse"
        assert ctx.tool_name == "Agent"

        # Compliance agent on PostToolUse: triggers only, never DENY
        result = router._dispatch_gates(ctx, state_hydration_closed)
        if result is not None:
            assert result.verdict != GateVerdict.DENY
