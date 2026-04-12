#!/usr/bin/env python3
"""Gate replay tests using real hook log data and additional coverage.

These tests complement test_gate_verdicts.py by:
1. Replaying REAL hook events extracted from production sessions
2. Testing PostToolUse counter increments
3. Testing countdown warnings
4. Validating temp_path locations are readable by clients
5. Smoke-testing the full execute_hooks() path

The real events fixture (real_hook_events.json) was extracted from actual
Claude Code hook logs at ~/.claude/projects/<project>/*-hooks.jsonl.
Each event records the verdict that was actually produced in production.

Run with:
    uv run pytest tests/hooks/test_gate_replay.py -v
"""

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.gate_config import COMPLIANCE_SUBAGENT_TYPES, TOOL_CATEGORIES, get_tool_category
from hooks.router import HookRouter
from hooks.schemas import CanonicalHookOutput, HookContext
from lib.gate_model import GateVerdict
from lib.gate_types import GateStatus
from lib.gates.registry import GateRegistry
from lib.session_paths import get_gate_file_path
from lib.session_state import SessionState

# --- Fixture loading ---

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REAL_EVENTS_FILE = FIXTURES_DIR / "real_hook_events.json"


def _load_real_events() -> list[dict]:
    """Load real hook events from the fixture file."""
    with REAL_EVENTS_FILE.open() as f:
        return json.load(f)


REAL_EVENTS = _load_real_events()


# --- Helpers ---


def _reinit_gates_with_defaults():
    """Reload gate_config and definitions with current env vars, reinit registry."""
    if "gate_config" in sys.modules:
        importlib.reload(sys.modules["gate_config"])
    if "hooks.gate_config" in sys.modules:
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


@pytest.fixture(autouse=True)
def gate_mode(monkeypatch):
    """Set gate modes for all tests.

    Yields a SimpleNamespace with gate configuration info.
    """
    monkeypatch.setenv("CUSTODIET_GATE_MODE", "block")
    monkeypatch.setenv("QA_GATE_MODE", "block")
    monkeypatch.setenv("HANDOVER_GATE_MODE", "warn")
    monkeypatch.setenv("CUSTODIET_TOOL_CALL_THRESHOLD", "50")
    _reinit_gates_with_defaults()
    yield SimpleNamespace()
    _reinit_gates_with_defaults()


@pytest.fixture
def router(monkeypatch):
    """Create a HookRouter with mocked session data."""
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


def _make_context(event: dict) -> HookContext:
    """Create a HookContext from a real event dict."""
    return HookContext(
        session_id="test-replay",
        hook_event=event["hook_event"],
        tool_name=event.get("tool_name"),
        tool_input=event.get("tool_input", {}),
        is_subagent=event.get("is_subagent", False),
        subagent_type=event.get("subagent_type"),
    )


# ===========================================================================
# REAL HOOK LOG REPLAY: Verify invariants hold on production data
# ===========================================================================


class TestRealEventInvariants:
    """Replay real hook events and verify core invariants hold.

    These events were extracted from actual Claude Code sessions.
    The test verifies that the gate system's behavior on real data
    matches the architectural invariants, regardless of what the
    production router happened to produce at the time.
    """

    # Categorize real events by what they test
    PRETOOLUSE_EVENTS = [e for e in REAL_EVENTS if e["hook_event"] == "PreToolUse"]

    COMPLIANCE_SPAWN_EVENTS = [
        e for e in PRETOOLUSE_EVENTS if e.get("subagent_type") in COMPLIANCE_SUBAGENT_TYPES
    ]

    ALWAYS_AVAILABLE_EVENTS = [
        e for e in PRETOOLUSE_EVENTS if e.get("tool_name") in TOOL_CATEGORIES["infrastructure"]
    ]

    @pytest.mark.parametrize(
        "event",
        COMPLIANCE_SPAWN_EVENTS,
        ids=[
            f"seq{e['sequence_index']}_{e['tool_name']}_{e['subagent_type']}"
            for e in COMPLIANCE_SPAWN_EVENTS
        ],
    )
    def test_compliance_spawn_always_allowed(self, router, event):
        """Real compliance agent spawns must always be allowed."""
        state = SessionState.create("test-replay")
        # Hostile state: custodiet at threshold
        state.gates["custodiet"].ops_since_open = 100
        ctx = _make_context(event)

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict != GateVerdict.DENY, (
                f"CRITICAL: Real compliance spawn (seq {event['sequence_index']}) "
                f"tool={event['tool_name']} subagent_type={event['subagent_type']} "
                f"was DENIED. Compliance agents must NEVER be blocked."
            )

    @pytest.mark.parametrize(
        "event",
        ALWAYS_AVAILABLE_EVENTS,
        ids=[f"seq{e['sequence_index']}_{e['tool_name']}" for e in ALWAYS_AVAILABLE_EVENTS],
    )
    def test_always_available_tools_from_real_logs(self, router, event):
        """Real always-available tool calls must pass even with hostile state."""
        state = SessionState.create("test-replay")
        state.gates["custodiet"].ops_since_open = 100
        ctx = _make_context(event)

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict == GateVerdict.ALLOW, (
                f"Always-available tool '{event['tool_name']}' (seq {event['sequence_index']}) "
                f"should be ALLOW, got {result.verdict.value}"
            )


# ===========================================================================
# REAL HOOK LOG DISCOVERY: Find and replay from actual log files
# ===========================================================================


@pytest.mark.integration
class TestHookLogDiscovery:
    """Discover and parse actual hook log files from the filesystem.

    This test verifies that real hook log files exist, are parseable,
    and contain events that can be replayed through the gate system.
    Skipped in CI environments (slow marker).
    """

    @staticmethod
    def _find_hook_logs() -> list[Path]:
        """Find hook log files in known locations."""
        locations = [
            Path.home() / ".claude" / "projects",
        ]
        files = []
        for loc in locations:
            if loc.exists():
                files.extend(sorted(loc.rglob("*-hooks.jsonl")))
        return files

    @staticmethod
    def _parse_pretooluse_events(logfile: Path, limit: int = 50) -> list[dict]:
        """Parse PreToolUse events from a hook log file."""
        events = []
        with logfile.open() as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("hook_event") == "PreToolUse":
                        events.append(entry)
                        if len(events) >= limit:
                            break
                except json.JSONDecodeError:
                    continue
        return events

    _NO_HOOK_LOGS_MSG = "No hook log files found in ~/.claude/projects/ (expected in CI)"

    def test_hook_logs_exist_and_parseable(self):
        """Verify that hook log files exist and contain valid JSON."""
        hook_files = self._find_hook_logs()
        if not hook_files:
            pytest.skip(self._NO_HOOK_LOGS_MSG)

        # At least one file should parse successfully
        parsed_any = False
        for f in hook_files[:5]:
            events = self._parse_pretooluse_events(f, limit=5)
            if events:
                parsed_any = True
                # Verify event structure
                for event in events:
                    assert "hook_event" in event
                    assert "tool_name" in event or event.get("tool_name") is None
                    assert "output" in event
                    assert "verdict" in event["output"]
                break

        assert parsed_any, "Hook log files exist but none could be parsed"

    def test_replay_real_pretooluse_from_disk(self, router):
        """Replay PreToolUse events from actual disk logs through gate system.

        This is the core conformance test: take events that actually
        happened and verify the gate system handles them without crashing.
        The focus is on exercising the real code path, not asserting
        specific verdicts (which depend on gate state at the time).
        """
        hook_files = self._find_hook_logs()
        if not hook_files:
            pytest.skip(self._NO_HOOK_LOGS_MSG)

        # Find the richest file
        best_file = None
        best_count = 0
        for f in hook_files[:10]:
            events = self._parse_pretooluse_events(f, limit=100)
            if len(events) > best_count:
                best_count = len(events)
                best_file = f

        if best_file is None or best_count == 0:
            pytest.skip("No PreToolUse events found in hook logs")

        events = self._parse_pretooluse_events(best_file, limit=50)
        state = SessionState.create("test-disk-replay")

        replayed = 0
        errors = []
        for event in events:
            ctx = HookContext(
                session_id="test-disk-replay",
                hook_event="PreToolUse",
                tool_name=event.get("tool_name"),
                tool_input=event.get("tool_input", {}),
                is_subagent=event.get("is_subagent", False),
                subagent_type=event.get("subagent_type"),
            )
            try:
                router._dispatch_gates(ctx, state)
                replayed += 1
            except Exception as exc:
                errors.append(f"Event {replayed}: {exc}")

        assert replayed > 0, "No events were replayed"
        assert not errors, "Errors during replay:\n" + "\n".join(errors)

    def test_compliance_events_from_disk_never_denied(self, router):
        """Verify compliance agent events from real logs are never denied.

        Searches all available hook logs for compliance agent PreToolUse
        events and replays them under hostile gate state.
        """
        hook_files = self._find_hook_logs()
        if not hook_files:
            pytest.skip(self._NO_HOOK_LOGS_MSG)

        compliance_events = []
        for f in hook_files[:10]:
            with f.open() as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        if (
                            entry.get("hook_event") == "PreToolUse"
                            and entry.get("is_subagent")
                            and entry.get("subagent_type") in COMPLIANCE_SUBAGENT_TYPES
                        ):
                            compliance_events.append(entry)
                    except json.JSONDecodeError:
                        continue
            if len(compliance_events) >= 20:
                break

        if not compliance_events:
            pytest.skip("No compliance agent PreToolUse events found in logs")

        state = SessionState.create("test-compliance-disk")
        state.gates["custodiet"].ops_since_open = 100

        for event in compliance_events:
            ctx = HookContext(
                session_id="test-compliance-disk",
                hook_event="PreToolUse",
                tool_name=event.get("tool_name"),
                tool_input=event.get("tool_input", {}),
                is_subagent=True,
                subagent_type=event.get("subagent_type"),
            )
            result = router._dispatch_gates(ctx, state)
            if result is not None:
                assert result.verdict != GateVerdict.DENY, (
                    f"CRITICAL: Real compliance event "
                    f"(tool={event.get('tool_name')}, type={event.get('subagent_type')}) "
                    f"was DENIED under hostile state"
                )


# ===========================================================================
# PostToolUse: Ops counter increment
# ===========================================================================


class TestPostToolUseCounter:
    """Verify ops_since_open increments on PostToolUse for write tools."""

    def test_ops_counter_increments_on_write_tool(self, router):
        """PostToolUse for write tools must increment ops_since_open."""
        state = SessionState.create("test-counter")
        state.gates["custodiet"].status = GateStatus.OPEN
        state.gates["custodiet"].ops_since_open = 0

        initial_ops = state.gates["custodiet"].ops_since_open

        # Simulate PostToolUse for a write tool
        ctx = HookContext(
            session_id="test-counter",
            hook_event="PostToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/f.py", "old_string": "a", "new_string": "b"},
        )
        router._dispatch_gates(ctx, state)

        assert state.gates["custodiet"].ops_since_open == initial_ops + 1, (
            f"ops_since_open should increment from {initial_ops} to {initial_ops + 1}, "
            f"got {state.gates['custodiet'].ops_since_open}"
        )

    def test_ops_counter_increments_multiple_times(self, router):
        """Multiple PostToolUse events should increment the counter each time."""
        state = SessionState.create("test-counter-multi")
        state.gates["custodiet"].status = GateStatus.OPEN
        state.gates["custodiet"].ops_since_open = 0

        for i in range(5):
            ctx = HookContext(
                session_id="test-counter-multi",
                hook_event="PostToolUse",
                tool_name="Bash",
                tool_input={"command": f"echo {i}"},
            )
            router._dispatch_gates(ctx, state)

        assert state.gates["custodiet"].ops_since_open == 5, (
            f"ops_since_open should be 5 after 5 PostToolUse events, "
            f"got {state.gates['custodiet'].ops_since_open}"
        )

    def test_custodiet_counter_resets_after_compliance_check(self, router):
        """Counter should reset to 0 when custodiet SubagentStop fires."""
        state = SessionState.create("test-counter-reset")
        state.gates["custodiet"].status = GateStatus.OPEN
        state.gates["custodiet"].ops_since_open = 42

        # Simulate custodiet SubagentStop
        ctx = HookContext(
            session_id="test-counter-reset",
            hook_event="SubagentStop",
            tool_name=None,
            tool_input={},
            subagent_type="aops-core:custodiet",
        )
        router._dispatch_gates(ctx, state)

        assert state.gates["custodiet"].ops_since_open == 0, (
            f"ops_since_open should reset to 0 after custodiet check, "
            f"got {state.gates['custodiet'].ops_since_open}"
        )


# ===========================================================================
# Countdown Warning: Ops approaching threshold
# ===========================================================================


class TestCountdownWarning:
    """Verify countdown warning fires when ops approach custodiet threshold."""

    def test_countdown_warning_in_range(self, router):
        """Ops at 45 (within 43-49 range) should produce countdown message."""
        state = SessionState.create("test-countdown")
        state.gates["custodiet"].status = GateStatus.OPEN
        state.gates["custodiet"].ops_since_open = 45  # threshold=50, start_before=7

        ctx = HookContext(
            session_id="test-countdown",
            hook_event="PreToolUse",
            tool_name="Read",  # Read-only: bypasses custodiet policy, but countdown still shows
            tool_input={"file_path": "/f.py"},
        )
        result = router._dispatch_gates(ctx, state)

        # Countdown should produce a system message with remaining count
        assert result is not None, "Countdown warning should produce a result"
        assert result.system_message is not None, "Countdown should have a system message"
        assert "5" in result.system_message or "turns" in result.system_message.lower(), (
            f"Countdown message should mention remaining turns, got: {result.system_message}"
        )

    def test_no_countdown_below_range(self, router):
        """Ops at 10 (well below range) should not produce countdown."""
        state = SessionState.create("test-no-countdown")
        state.gates["custodiet"].status = GateStatus.OPEN
        state.gates["custodiet"].ops_since_open = 10

        ctx = HookContext(
            session_id="test-no-countdown",
            hook_event="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "/f.py"},
        )
        result = router._dispatch_gates(ctx, state)

        # Should be None (allow) with no messages
        if result is not None:
            assert result.verdict == GateVerdict.ALLOW

    def test_no_countdown_at_threshold(self, router):
        """Ops at 50 (at threshold) should produce policy block, not countdown."""
        state = SessionState.create("test-at-threshold")
        state.gates["custodiet"].status = GateStatus.OPEN
        state.gates["custodiet"].ops_since_open = 50

        ctx = HookContext(
            session_id="test-at-threshold",
            hook_event="PreToolUse",
            tool_name="Edit",  # Write tool: subject to custodiet policy
            tool_input={"file_path": "/f.py", "old_string": "a", "new_string": "b"},
        )
        result = router._dispatch_gates(ctx, state)

        assert result is not None
        assert result.verdict == GateVerdict.DENY, (
            f"At threshold, write tool should be DENIED, got {result.verdict.value}"
        )


# ===========================================================================
# Temp Path Validation
# ===========================================================================


class TestTempPathValidation:
    """Verify gate temp_path is in a readable, predictable location.

    Gate context files (custodiet.md, etc.) must be:
    1. Under a directory that exists (or can be created)
    2. In the Claude/Gemini project directory (readable by the client)
    3. Named with a predictable pattern for session isolation
    """

    def test_claude_gate_path_under_claude_projects(self, monkeypatch, tmp_path):
        """Claude gate files should be under ~/.claude/projects/."""
        # Mock home to tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/Users/test/src/myproject")
        # Clear any cached env vars
        monkeypatch.delenv("AOPS_GATE_FILE_CUSTODIET", raising=False)
        monkeypatch.delenv("GEMINI_SESSION_ID", raising=False)
        monkeypatch.delenv("AOPS_SESSION_STATE_DIR", raising=False)
        monkeypatch.delenv("AOPS_SESSIONS", raising=False)

        path = get_gate_file_path("custodiet", "test-session-abc123")

        # Path should be under ~/.claude/projects/
        assert str(path).startswith(str(Path.home() / ".claude" / "projects")), (
            f"Gate file path should be under ~/.claude/projects/, got: {path}"
        )

        # Path should end with the gate name
        assert path.name.endswith("-custodiet.md"), (
            f"Gate file should end with -custodiet.md, got: {path.name}"
        )

        # Path should contain session hash for isolation
        from lib.session_paths import get_session_short_hash

        expected_hash = get_session_short_hash("test-session-abc123")
        assert expected_hash in path.name, (
            f"Gate file path should contain session hash '{expected_hash}', got: {path.name}"
        )

    def test_gate_path_parent_exists_or_creatable(self, monkeypatch, tmp_path):
        """Gate file parent directory must exist or be creatable."""
        # Use AOPS_GATE_FILE env var override to test with temp path
        test_gate_file = tmp_path / "test-gate.md"
        monkeypatch.setenv("AOPS_GATE_FILE_CUSTODIET", str(test_gate_file))

        path = get_gate_file_path("custodiet", "test-session")

        assert path == test_gate_file
        assert path.parent.exists(), f"Gate file parent directory must exist: {path.parent}"

    def test_custodiet_context_injection_contains_temp_path(self, router):
        """When custodiet gate fires, context injection must contain temp_path."""
        state = SessionState.create("test-custodiet-path")
        state.gates["custodiet"].status = GateStatus.OPEN
        state.gates["custodiet"].ops_since_open = 55

        ctx = HookContext(
            session_id="test-custodiet-path",
            hook_event="PreToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/f.py", "old_string": "a", "new_string": "b"},
        )

        # The custodiet policy has custom_action="prepare_compliance_report"
        # which creates a file and sets temp_path. In tests, this will fail
        # because templates aren't available. We mock it.
        with patch(
            "lib.gates.custom_actions.create_audit_file",
            return_value=Path("/tmp/custodiet-test.md"),
        ):
            result = router._dispatch_gates(ctx, state)

        assert result is not None
        # temp_path should have been set by the custom action mock
        temp_path = state.gates["custodiet"].metrics.get("temp_path")
        assert temp_path is not None, "Custodiet policy should set temp_path in metrics"
        assert result.context_injection is not None, (
            "Custodiet gate should produce context injection"
        )
        assert temp_path in result.context_injection, (
            f"Context injection should contain temp_path '{temp_path}', "
            f"got: {result.context_injection[:200]}"
        )


# ===========================================================================
# Smoke test through execute_hooks() public API
# ===========================================================================


class TestExecuteHooksSmoke:
    """Smoke test the full execute_hooks() path for a few key scenarios.

    This tests the public API rather than _dispatch_gates, covering:
    - State loading/saving
    - Special handlers
    - Gate status icon formatting
    - Output canonical conversion
    """

    def test_pretooluse_through_full_pipeline(self, router, tmp_path, monkeypatch):
        """PreToolUse for a write tool through full pipeline.

        With a fresh state dir, no gates fire (custodiet ops=0).
        The expected verdict is 'allow'.
        """
        # Isolate state storage
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))
        monkeypatch.setenv("AOPS_HOOK_LOG_PATH", str(tmp_path / "hooks.jsonl"))

        ctx = HookContext(
            session_id="test-smoke-pipeline",
            hook_event="PreToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/f.py", "old_string": "a", "new_string": "b"},
        )

        result = router.execute_hooks(ctx)

        assert isinstance(result, CanonicalHookOutput)
        # Fresh state has custodiet ops=0 — no gates fire
        assert result.verdict == "allow", (
            f"Fresh state should produce 'allow' (custodiet ops=0), got '{result.verdict}'"
        )

    def test_infrastructure_through_full_pipeline(self, router, tmp_path, monkeypatch):
        """Infrastructure tool through full pipeline should always be allowed.

        Always_available (AskUserQuestion, etc.) and infrastructure (PKB ops) tools bypass all gates.
        """
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))
        monkeypatch.setenv("AOPS_HOOK_LOG_PATH", str(tmp_path / "hooks.jsonl"))

        ctx = HookContext(
            session_id="test-smoke-infra",
            hook_event="PreToolUse",
            tool_name="AskUserQuestion",
            tool_input={"prompt": "What should I do next?"},
        )

        result = router.execute_hooks(ctx)

        assert isinstance(result, CanonicalHookOutput)
        assert result.verdict == "allow", (
            f"Infrastructure tool should produce 'allow', got '{result.verdict}'"
        )


# ===========================================================================
# REAL TOOL NAME COVERAGE: Every tool name seen in production logs
# ===========================================================================

# Each tuple: (tool_name, expected_category, description)
# expected_category is what gate_config SHOULD return for this tool.
# "always_available" tools bypass ALL gates (meta/control tools: AskUserQuestion, etc.).
# "infrastructure" tools bypass ALL gates (PKB ops).
# "spawn" tools are subject to gate policies (Agent, Task, Skill, etc.).
# "read_only" tools bypass custodiet gate.
# "write" tools are subject to ALL gate policies.
#
# Sourced from 170 hook log files spanning 7 days of production usage.
# Includes Claude Code, Gemini CLI, and all MCP plugin name variants.

REAL_TOOL_NAMES: list[tuple[str, str, str]] = [
    # ===== Claude Code built-in tools =====
    ("Read", "read_only", "Claude: read file"),
    ("Bash", "write", "Claude: shell command"),
    ("Grep", "read_only", "Claude: content search"),
    ("Edit", "write", "Claude: edit file"),
    ("Glob", "read_only", "Claude: file search"),
    ("Write", "write", "Claude: write file"),
    ("NotebookEdit", "write", "Claude: notebook edit"),
    ("WebFetch", "read_only", "Claude: web fetch"),
    ("WebSearch", "read_only", "Claude: web search"),
    ("TaskOutput", "read_only", "Claude: task output"),
    ("TaskStop", "read_only", "Claude: stop task"),
    ("ToolSearch", "read_only", "Claude: tool search"),
    # Claude Code spawn tools (subject to gate policies)
    ("Agent", "spawn", "Claude: spawn subagent"),
    ("Task", "spawn", "Claude: spawn subagent (legacy)"),
    ("Skill", "spawn", "Claude: invoke skill"),
    ("TaskCreate", "spawn", "Claude: create task"),
    ("TaskUpdate", "spawn", "Claude: update task"),
    ("TaskGet", "spawn", "Claude: get task"),
    ("TaskList", "spawn", "Claude: list tasks"),
    # Claude Code always_available tools (meta/control tools, bypass all gates)
    ("AskUserQuestion", "always_available", "Claude: ask user"),
    ("TodoWrite", "always_available", "Claude: write todo"),
    ("EnterPlanMode", "always_available", "Claude: enter plan"),
    ("ExitPlanMode", "always_available", "Claude: exit plan"),
    # ===== Gemini CLI tools =====
    ("read_file", "read_only", "Gemini: read file"),
    ("run_shell_command", "write", "Gemini: shell command"),
    ("grep_search", "read_only", "Gemini: grep search"),
    ("replace", "write", "Gemini: replace in file"),
    ("write_file", "write", "Gemini: write file"),
    ("list_directory", "read_only", "Gemini: list dir"),
    ("glob", "read_only", "Gemini: glob search"),
    ("activate_skill", "spawn", "Gemini: invoke skill"),
    # Gemini bare PKB tool names (infrastructure: bypass all gates)
    ("get_task", "infrastructure", "Gemini: get task"),
    ("create_task", "infrastructure", "Gemini: create task"),
    ("update_task", "infrastructure", "Gemini: update task"),
    ("complete_task", "infrastructure", "Gemini: complete task"),
    ("list_tasks", "infrastructure", "Gemini: list tasks"),
    ("task_search", "infrastructure", "Gemini: task search"),
    # ===== PKB MCP: mcp__plugin_aops-core_pkb__* (Claude Code full plugin prefix) =====
    ("mcp__plugin_aops-core_pkb__update_task", "infrastructure", "CC plugin: update task"),
    ("mcp__plugin_aops-core_pkb__get_task", "infrastructure", "CC plugin: get task"),
    ("mcp__plugin_aops-core_pkb__create_task", "infrastructure", "CC plugin: create task"),
    ("mcp__plugin_aops-core_pkb__list_tasks", "infrastructure", "CC plugin: list tasks"),
    ("mcp__plugin_aops-core_pkb__complete_task", "infrastructure", "CC plugin: complete task"),
    ("mcp__plugin_aops-core_pkb__reindex", "infrastructure", "CC plugin: reindex"),
    ("mcp__plugin_aops-core_pkb__search", "infrastructure", "CC plugin: search"),
    ("mcp__plugin_aops-core_pkb__task_search", "infrastructure", "CC plugin: task search"),
    ("mcp__plugin_aops-core_pkb__pkb_orphans", "infrastructure", "CC plugin: orphans"),
    (
        "mcp__plugin_aops-core_pkb__get_task_children",
        "infrastructure",
        "CC plugin: task children",
    ),
    ("mcp__plugin_aops-core_pkb__decompose_task", "infrastructure", "CC plugin: decompose task"),
    ("mcp__plugin_aops-core_pkb__append", "infrastructure", "CC plugin: append"),
    ("mcp__plugin_aops-core_pkb__create_memory", "infrastructure", "CC plugin: create memory"),
    (
        "mcp__plugin_aops-core_pkb__retrieve_memory",
        "infrastructure",
        "CC plugin: retrieve memory",
    ),
    ("mcp__plugin_aops-core_pkb__create", "infrastructure", "CC plugin: create doc"),
    ("mcp__plugin_aops-core_pkb__delete", "infrastructure", "CC plugin: delete doc"),
    ("mcp__plugin_aops-core_pkb__delete_memory", "infrastructure", "CC plugin: delete memory"),
    ("mcp__plugin_aops-core_pkb__search_by_tag", "infrastructure", "CC plugin: search by tag"),
    # ===== PKB MCP: mcp__pkb__* (short form, in current gate_config) =====
    ("mcp__pkb__create_task", "infrastructure", "short: create task"),
    ("mcp__pkb__get_task", "infrastructure", "short: get task"),
    ("mcp__pkb__task_search", "infrastructure", "short: task search"),
    ("mcp__pkb__create", "infrastructure", "short: create doc"),
    ("mcp__pkb__append", "infrastructure", "short: append"),
    # ===== PKB MCP: mcp__pbk__* (typo variant seen in Gemini sessions) =====
    ("mcp__pbk__update_task", "infrastructure", "typo: update task"),
    ("mcp__pbk__get_task", "infrastructure", "typo: get task"),
    ("mcp__pbk__create_task", "infrastructure", "typo: create task"),
    ("mcp__pbk__complete_task", "infrastructure", "typo: complete task"),
    ("mcp__pbk__list_tasks", "infrastructure", "typo: list tasks"),
    ("mcp__pbk__pkb_context", "infrastructure", "typo: pkb context"),
    ("mcp__pbk__search", "infrastructure", "typo: search"),
    ("mcp__pbk__get_document", "infrastructure", "typo: get document"),
    ("mcp__pbk__list_documents", "infrastructure", "typo: list documents"),
    ("mcp__pbk__create", "infrastructure", "typo: create doc"),
    ("mcp__pbk__append", "infrastructure", "typo: append"),
    ("mcp__pbk__create_memory", "infrastructure", "typo: create memory"),
    ("mcp__pbk__reindex", "infrastructure", "typo: reindex"),
    ("mcp__pbk__pkb_orphans", "infrastructure", "typo: orphans"),
    ("mcp__pbk__get_network_metrics", "infrastructure", "typo: network metrics"),
    # ===== PKB MCP: versioned plugin prefix (seen once) =====
    ("mcp__plugin_0_2_25_pkb__list_tasks", "infrastructure", "versioned plugin: list tasks"),
    # ===== PKB MCP: pkb__* (bare prefix, Gemini variant) =====
    ("pkb__search", "infrastructure", "bare: search"),
    ("pkb_orphans", "infrastructure", "bare: orphans"),
    # ===== Memory MCP: mcp__plugin_aops-core_memory__* =====
    ("mcp__plugin_aops-core_memory__retrieve_memory", "infrastructure", "CC memory: retrieve"),
    ("mcp__plugin_aops-core_memory__store_memory", "infrastructure", "CC memory: store"),
    # ===== Context7 MCP =====
    ("mcp__context7__query-docs", "read_only", "context7: query docs"),
    ("mcp__context7__resolve-library-id", "read_only", "context7: resolve lib"),
    # ===== Zotero MCP =====
    ("mcp__zot__search", "read_only", "zotero: search"),
    ("mcp__zot__search_library_by_author", "read_only", "zotero: search by author"),
    ("mcp__zot__search_openalex_author", "read_only", "zotero: openalex author"),
    # ===== Outlook MCP: mcp__omcp__* =====
    ("mcp__omcp__messages_get", "read_only", "outlook: get message"),
    ("mcp__omcp__messages_list_recent", "read_only", "outlook: list recent"),
    ("mcp__omcp__messages_search", "read_only", "outlook: search"),
    ("mcp__omcp__messages_reply", "write", "outlook: reply"),
    ("mcp__omcp__messages_create_draft", "write", "outlook: create draft"),
    ("mcp__omcp__calendar_list_today", "read_only", "outlook: calendar today"),
    ("mcp__omcp__calendar_list_events", "read_only", "outlook: calendar events"),
    ("mcp__omcp__calendar_get_event", "read_only", "outlook: get event"),
    ("mcp__omcp__calendar_create_event", "write", "outlook: create event"),
    ("mcp__omcp__help", "read_only", "outlook: help"),
    # ===== Outlook MCP: mcp__outlook__* (alternate prefix) =====
    ("mcp__outlook__messages_get", "read_only", "outlook alt: get message"),
    ("mcp__outlook__messages_list_recent", "read_only", "outlook alt: list recent"),
    ("mcp__outlook__calendar_list_today", "read_only", "outlook alt: calendar today"),
    ("mcp__outlook__calendar_list_upcoming", "read_only", "outlook alt: calendar upcoming"),
    # ===== Playwright MCP =====
    ("mcp__playwright__browser_navigate", "write", "playwright: navigate"),
    ("mcp__playwright__browser_click", "write", "playwright: click"),
    ("mcp__playwright__browser_wait_for", "read_only", "playwright: wait"),
    ("mcp__playwright__browser_take_screenshot", "read_only", "playwright: screenshot"),
    ("mcp__playwright__browser_install", "write", "playwright: install"),
    # ===== Playwright bare names (Gemini) =====
    ("browser_navigate", "write", "Gemini playwright: navigate"),
    ("browser_click", "write", "Gemini playwright: click"),
    ("browser_wait_for", "read_only", "Gemini playwright: wait"),
    ("browser_take_screenshot", "read_only", "Gemini playwright: screenshot"),
    ("browser_evaluate", "write", "Gemini playwright: evaluate"),
    ("browser_console_messages", "read_only", "Gemini playwright: console"),
    ("browser_network_requests", "read_only", "Gemini playwright: network"),
    ("browser_run_code", "write", "Gemini playwright: run code"),
    # ===== Gemini bare tool names (miscellaneous PKB ops - infrastructure) =====
    ("create_memory", "infrastructure", "Gemini: create memory"),
    ("decompose_task", "infrastructure", "Gemini: decompose task"),
    ("append", "infrastructure", "Gemini: append"),
    ("search", "infrastructure", "Gemini: search"),
    ("get_task_children", "infrastructure", "Gemini: task children"),
    ("get_internal_docs", "read_only", "Gemini: internal docs"),
    ("shell", "write", "Gemini: shell"),
    ("cli_help", "read_only", "Gemini: cli help"),
    # ===== Agent/subagent type names that appeared as tool_name (bug/edge case) =====
    ("qa", "infrastructure", "subagent name as tool (qa)"),
]

# Build Agent/Skill spawn scenarios from real logs
# Each tuple: (tool_name, subagent_type, is_subagent, expected_category, description)
REAL_SPAWN_EVENTS: list[tuple[str, str, bool, str, str]] = [
    # Claude Code Agent spawns (is_subagent=False in main agent context)
    ("Agent", "Explore", False, "spawn", "CC Agent: Explore"),
    ("Agent", "aops-core:custodiet", False, "spawn", "CC Agent: custodiet"),
    ("Agent", "aops-core:hydrator", False, "spawn", "CC Agent: hydrator"),
    ("Agent", "aops-core:butler", False, "spawn", "CC Agent: butler"),
    ("Agent", "general-purpose", False, "spawn", "CC Agent: general-purpose"),
    # Claude Code legacy Task spawns (is_subagent=True from subagent context)
    ("Task", "general-purpose", True, "spawn", "CC Task: general-purpose"),
    ("Task", "aops-core:hydrator", True, "spawn", "CC Task: hydrator"),
    ("Task", "aops-core:custodiet", True, "spawn", "CC Task: custodiet"),
    ("Task", "Explore", True, "spawn", "CC Task: Explore"),
    ("Task", "claude-code-guide", True, "spawn", "CC Task: cc-guide"),
    ("Task", "aops-core:butler", True, "spawn", "CC Task: butler"),
    ("Task", "Plan", True, "spawn", "CC Task: Plan"),
    (
        "Task",
        "aops-core:custodiet-reviewer",
        True,
        "spawn",
        "CC Task: custodiet-reviewer",
    ),
    ("Task", "aops-core:hydrator-reviewer", True, "spawn", "CC Task: hydrator-reviewer"),
    ("Task", "aops-core:qa", True, "spawn", "CC Task: qa"),
    # Claude Code Skill invocations
    ("Skill", "aops-core:handover", False, "spawn", "CC Skill: handover"),
    ("Skill", "aops-core:daily", False, "spawn", "CC Skill: daily"),
    ("Skill", "aops-core:learn", False, "spawn", "CC Skill: learn"),
    ("Skill", "aops-core:strategy", False, "spawn", "CC Skill: strategy"),
    ("Skill", "aops-core:remember", False, "spawn", "CC Skill: remember"),
    ("Skill", "aops-core:garden", False, "spawn", "CC Skill: garden"),
    ("Skill", "aops-core:q", False, "spawn", "CC Skill: q"),
    ("Skill", "aops-core:framework", False, "spawn", "CC Skill: framework"),
    ("Skill", "framework", False, "spawn", "CC Skill: framework (bare)"),
    ("Skill", "remember", False, "spawn", "CC Skill: remember (bare)"),
    # Gemini CLI
    ("activate_skill", "aops-core:handover", False, "spawn", "Gemini: activate handover"),
]


class TestRealToolNameCategorization:
    """Verify gate_config categorizes every real production tool name correctly.

    These tool names were extracted from 170 hook log files spanning 7 days
    of production usage across Claude Code and Gemini CLI sessions.

    The gate system falls back to 'write' for unknown tool names (conservative),
    which means any uncategorized read-only or always-available tool will be
    incorrectly blocked under deny mode.
    """

    @pytest.mark.parametrize(
        "tool_name,expected_category,desc",
        REAL_TOOL_NAMES,
        ids=[f"{t[2]}:{t[0]}" for t in REAL_TOOL_NAMES],
    )
    def test_tool_category_matches_expected(self, tool_name, expected_category, desc):
        """Every real tool name must be categorized correctly by get_tool_category."""
        actual = get_tool_category(tool_name)
        assert actual == expected_category, (
            f"Tool '{tool_name}' ({desc}): expected category '{expected_category}', "
            f"got '{actual}'. This tool will be {'blocked' if expected_category != 'write' else 'correctly blocked'} "
            f"under deny mode if miscategorized."
        )

    @pytest.mark.parametrize(
        "tool_name,expected_category,desc",
        [t for t in REAL_TOOL_NAMES if t[1] == "infrastructure"],
        ids=[f"{t[2]}:{t[0]}" for t in REAL_TOOL_NAMES if t[1] == "infrastructure"],
    )
    def test_infrastructure_never_blocked(self, router, tool_name, expected_category, desc):
        """Infrastructure tools bypass all gates.

        PKB ops (mcp__pkb__*, create_task, etc.) are in the infrastructure category and bypass
        all gates. Meta/control tools (AskUserQuestion, TodoWrite, etc.) are in always_available.
        """
        state = SessionState.create("test-tool-categorization")

        ctx = HookContext(
            session_id="test-tool-categorization",
            hook_event="PreToolUse",
            tool_name=tool_name,
            tool_input={},
        )
        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict == GateVerdict.ALLOW, (
                f"infrastructure tool '{tool_name}' ({desc}) should be ALLOW, "
                f"got {result.verdict.value}. "
                f"get_tool_category() returned '{get_tool_category(tool_name)}'"
            )


class TestRealSpawnEventCategorization:
    """Verify Agent/Task/Skill spawn events are correctly categorized.

    These spawn combinations were extracted from real production logs.
    Spawn tools (Agent, Task, Skill) are now in the 'spawn' category and are
    subject to gate policies.
    """

    @pytest.mark.parametrize(
        "tool_name,subagent_type,is_subagent,expected_category,desc",
        REAL_SPAWN_EVENTS,
        ids=[f"{t[4]}" for t in REAL_SPAWN_EVENTS],
    )
    def test_spawn_tool_category(
        self, router, tool_name, subagent_type, is_subagent, expected_category, desc
    ):
        """Spawn tools are in 'spawn' category."""
        state = SessionState.create("test-spawn-categorization")
        # Hostile state: custodiet at threshold
        state.gates["custodiet"].ops_since_open = 100

        tool_input = (
            {"subagent_type": subagent_type, "prompt": "test"}
            if tool_name in ("Agent", "Task")
            else {"skill": subagent_type}
        )
        ctx = HookContext(
            session_id="test-spawn-categorization",
            hook_event="PreToolUse",
            tool_name=tool_name,
            tool_input=tool_input,
            is_subagent=is_subagent,
            subagent_type=subagent_type,
        )
        router._dispatch_gates(ctx, state)

        # Category must be "spawn" for all spawn tools
        actual_cat = get_tool_category(tool_name)
        assert actual_cat == expected_category, (
            f"Spawn tool '{tool_name}' ({desc}): expected category '{expected_category}', "
            f"got '{actual_cat}'"
        )
