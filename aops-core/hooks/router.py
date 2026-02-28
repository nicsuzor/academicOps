#!/usr/bin/env python3
"""
Universal Hook Router.

Handles hook events from both Claude Code and Gemini CLI.
Consolidates multiple hooks per event into a single invocation.
Manages session persistence for Gemini.

Architecture:
- Loads Pydantic SessionState object at start.
- Passes SessionState to all gates via gate_registry.
- Saves SessionState at end.
- GateResult objects used internally, converted to JSON only at final output.
"""

import json
import os
import sys
import tempfile
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

# --- Path Setup ---
HOOK_DIR = Path(__file__).parent  # aops-core/hooks
AOPS_CORE_DIR = HOOK_DIR.parent  # aops-core

# Add aops-core to path for imports
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

try:
    from lib.gate_model import GateResult, GateVerdict
    from lib.gates.registry import GateRegistry
    from lib.hook_utils import is_subagent_session
    from lib.session_paths import get_pid_session_map_path, get_session_short_hash
    from lib.session_state import SessionState

    # Use relative import if possible, or direct import if run as script
    try:
        from hooks.schemas import (
            CanonicalHookOutput,
            ClaudeGeneralHookOutput,
            ClaudeHookSpecificOutput,
            ClaudeStopHookOutput,
            GeminiHookOutput,
            GeminiHookSpecificOutput,
            HookContext,
        )
    except ImportError:
        from schemas import (
            CanonicalHookOutput,
            ClaudeGeneralHookOutput,
            ClaudeHookSpecificOutput,
            ClaudeStopHookOutput,
            GeminiHookOutput,
            GeminiHookSpecificOutput,
            HookContext,
        )

    from hooks.unified_logger import log_event_to_session, log_hook_event
except ImportError as e:
    # Fail fast if schemas missing
    print(f"CRITICAL: Failed to import: {e}", file=sys.stderr)
    sys.exit(1)


# --- Configuration ---

DEBUG_LOG_DIR = Path("/tmp")


def _debug_log_path(session_id: str | None) -> Path:
    """Return per-session debug log path."""
    slug = session_id if session_id else "unknown"
    return DEBUG_LOG_DIR / f"cc_hooks_{slug}.jsonl"


def _debug_log_input(raw_input: dict[str, Any], args: Any) -> None:
    """Append raw hook input to debug JSONL file if DEBUG_HOOKS=1."""
    if not os.environ.get("DEBUG_HOOKS"):
        return
    try:
        session_id = raw_input.get("session_id") or os.environ.get("CLAUDE_SESSION_ID")
        entry = {
            "ts": datetime.now().isoformat(),
            "session_id": session_id,
            "client": getattr(args, "client", None),
            "event": getattr(args, "event", None),
            "input": raw_input,
        }
        with _debug_log_path(session_id).open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"DEBUG_LOG error: {e}", file=sys.stderr)


# Event mapping: Gemini -> Claude (internal normalization)
GEMINI_EVENT_MAP = {
    "SessionStart": "SessionStart",
    "BeforeTool": "PreToolUse",
    "AfterTool": "PostToolUse",
    "BeforeAgent": "UserPromptSubmit",  # Mapped to UPS for unified handling
    "AfterAgent": "Stop",  # This is the event after the agent returns their final response for a turn.
    "SessionEnd": "SessionEnd",
    "Notification": "Notification",
    "PreCompress": "PreCompact",
    "SubagentStart": "SubagentStart",  # Explicit mapping if Gemini sends it
    "SubagentStop": "SubagentStop",  # Explicit mapping if Gemini sends it
}

# --- Gate Status Display ---
GATE_ICONS = {
    "hydration": ("🫗", "."),
    "custodiet": ("🛡", "."),
    "handover": ("📤", "."),
}


def format_gate_status_icons(state: SessionState) -> str:
    """Format current gate statuses as a compact icon line.

    Uses the loaded SessionState object.
    """
    # Collect blocking (closed) gates
    blocking_gates = []

    # Iterate known gates
    for gate_name in GATE_ICONS.keys():
        gate_state = state.gates.get(gate_name)
        if not gate_state or gate_state.status == "closed":
            blocking_gates.append(gate_name)
        elif gate_state.blocked:  # Explicit block
            blocking_gates.append(gate_name)

    # Format output
    blocking_set = sorted(blocking_gates)
    open_gates = sorted(set(GATE_ICONS.keys()) - set(blocking_gates))
    blocking_icons = " ".join([GATE_ICONS[g][0] for g in blocking_set])
    open_icons = " ".join([GATE_ICONS[g][1] for g in open_gates])

    return f"[{blocking_icons}  ✓ {open_icons}]"


# --- Session Management ---


def get_session_data() -> dict[str, Any]:
    """Read session metadata."""
    try:
        session_file = get_pid_session_map_path()
        if session_file.exists():
            return json.loads(session_file.read_text().strip())
    except (OSError, json.JSONDecodeError) as e:
        print(f"WARNING: Failed to read session data: {e}", file=sys.stderr)
    return {}


def persist_session_data(data: dict[str, Any]) -> None:
    """Write session metadata atomically."""
    try:
        session_file = get_pid_session_map_path()
        existing = get_session_data()
        existing.update(data)

        # Atomic write
        fd, temp_path = tempfile.mkstemp(dir=str(session_file.parent), text=True)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(existing, f)
            Path(temp_path).rename(session_file)
        except Exception as e:
            Path(temp_path).unlink(missing_ok=True)
            print(f"CRITICAL: Failed to persist session data: {e}", file=sys.stderr)
            raise
    except OSError as e:
        print(f"WARNING: OSError in persist_session_data: {e}", file=sys.stderr)


# --- Router Logic ---


class HookRouter:
    def __init__(self):
        self.session_data = get_session_data()
        self._execution_timestamps = deque(maxlen=20)  # Store last 20 timestamps

    @staticmethod
    def _normalize_json_field(value: Any) -> Any:
        """Normalize a field that may be a JSON string to its parsed form."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def normalize_input(
        self, raw_input: dict[str, Any], gemini_event: str | None = None
    ) -> HookContext:
        """Create a normalized HookContext from raw input."""

        # 1. Determine Event Name
        if gemini_event:
            hook_event = GEMINI_EVENT_MAP.get(gemini_event, gemini_event)
        else:
            raw_event = raw_input.get("hook_event_name") or ""
            hook_event = GEMINI_EVENT_MAP.get(raw_event, raw_event)

        # 2. Determine Session ID
        session_id = raw_input.get("session_id")
        if not session_id:
            session_id = self.session_data.get("session_id") or os.environ.get("CLAUDE_SESSION_ID")

        if not session_id and hook_event == "SessionStart":
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            short_uuid = str(uuid.uuid4())[:8]
            session_id = f"gemini-{timestamp}-{short_uuid}"

        if not session_id:
            session_id = f"unknown-{str(uuid.uuid4())[:8]}"

        # 3. Determine Agent ID and Subagent Type
        # Check both payload and persisted session data (for subagent tool calls)
        agent_id = (
            raw_input.get("agent_id")
            or raw_input.get("agentId")
            or self.session_data.get("agent_id")
        )
        subagent_type = (
            raw_input.get("subagent_type")
            or raw_input.get("agent_type")
            or self.session_data.get("subagent_type")
        )

        # Prefer explicit env var if set
        if not subagent_type:
            subagent_type = os.environ.get("CLAUDE_SUBAGENT_TYPE")

        # 4. Transcript Path / Temp Root
        transcript_path = raw_input.get("transcript_path")

        # Request Tracing (aops-32068a2e)
        trace_id = raw_input.get("trace_id") or str(uuid.uuid4())

        # 5. Tool Data
        tool_name = raw_input.get("tool_name")
        tool_input = self._normalize_json_field(raw_input.get("tool_input", {}))
        if not isinstance(tool_input, dict):
            tool_input = {}

        # Normalize tool_result and toolResult in raw_input (for PostToolUse/SubagentStop)
        tool_output = {}
        raw_tool_output = (
            raw_input.get("tool_result")
            or raw_input.get("toolResult")
            or raw_input.get("tool_response")
            or raw_input.get("subagent_result")
        )
        if raw_tool_output:
            tool_output = self._normalize_json_field(raw_tool_output)

        # 6. Extract subagent_type from spawning tools
        # Uses the SPAWN_TOOLS table in gate_config for cross-platform detection
        # (Claude Task/Skill, Gemini delegate_to_agent/activate_skill, extensible
        # to Codex/Copilot). _subagent_type_from_skill prevents Skill invocations
        # from being misclassified as subagent sessions.
        from hooks.gate_config import extract_subagent_type as _extract_subagent_type

        _subagent_type_from_skill = False
        if not subagent_type and isinstance(tool_input, dict):
            extracted, is_skill = _extract_subagent_type(tool_name, tool_input)
            if extracted:
                subagent_type = extracted
                _subagent_type_from_skill = is_skill

        # 7. Detect Subagent Session
        # Call is_subagent_session BEFORE popping fields from raw_input
        is_subagent = is_subagent_session(raw_input)

        # If we have subagent info from PID map or spawning tool, treat as subagent.
        # Skill/activate_skill tool calls are NOT subagent invocations — they run
        # in the main agent's session — so skip the is_subagent override for those.
        if (
            not is_subagent
            and not _subagent_type_from_skill
            and (
                subagent_type
                or agent_id
                or raw_input.get("is_sidechain")
                or raw_input.get("isSidechain")
            )
        ):
            is_subagent = True

        # SubagentStart/SubagentStop fire in the MAIN agent's context ABOUT a
        # subagent. They carry agent_id/agent_type metadata which causes false
        # positives above. Override: these are never subagent events.
        if hook_event in ("SubagentStart", "SubagentStop"):
            is_subagent = False

        # 8. Persist session data on session start only (not subagent start, as multiple
        # subagents may run simultaneously and would clobber each other's entries)
        if hook_event == "SessionStart":
            persist_session_data(
                {"session_id": session_id, "agent_id": agent_id, "subagent_type": subagent_type}
            )

        # 9. Precompute values
        short_hash = get_session_short_hash(session_id)

        # 10. Build Context and POP processed fields from raw_input
        # We pop now so the remainder in ctx.raw_input is "extra" data
        processed_fields = [
            "hook_event_name",
            "session_id",
            "transcript_path",
            "trace_id",
            "tool_name",
            "tool_input",
            "tool_result",
            "toolResult",
            "tool_response",
            "subagent_result",
            "agent_id",
            "agentId",
            "slug",
            "cwd",
            "is_sidechain",
            "isSidechain",
            "subagent_type",
            "agent_type",
        ]
        slug = raw_input.get("slug")
        cwd = raw_input.get("cwd")

        for field in processed_fields:
            raw_input.pop(field, None)

        return HookContext(
            session_id=session_id,
            trace_id=trace_id,
            hook_event=hook_event,
            agent_id=agent_id,
            slug=slug,
            is_subagent=is_subagent,
            subagent_type=subagent_type,
            # Precomputed values
            session_short_hash=short_hash,
            # Event Data
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            transcript_path=transcript_path,
            cwd=cwd,
            raw_input=raw_input,
        )

    def execute_hooks(self, ctx: HookContext) -> CanonicalHookOutput:
        """Run all configured gates for the event and merge results.

        Dispatches directly to GateRegistry and GenericGate methods,
        eliminating the wrapper layers in gates.py and gate_registry.py.
        """
        merged_result = CanonicalHookOutput()

        # Load Session State ONCE
        try:
            state = SessionState.load(ctx.session_id)
        except Exception as e:
            print(f"WARNING: Failed to load session state: {e}", file=sys.stderr)
            state = SessionState.create(ctx.session_id)

        # Initialize gate registry
        GateRegistry.initialize()

        # Run special handlers first (unified_logger, ntfy, etc.) then gates
        self._run_special_handlers(ctx, state, merged_result)

        # Dispatch to GenericGate methods based on event type
        # We now dispatch for ALL sessions, including subagents, to ensure
        # that gate triggers (state transitions) always run.
        result = self._dispatch_gates(ctx, state)
        if result:
            hook_output = self._gate_result_to_canonical(result)
            self._merge_result(merged_result, hook_output)

        # Append gate status icons to system message
        try:
            gate_status = format_gate_status_icons(state)
            if merged_result.system_message:
                merged_result.system_message = f"{merged_result.system_message} {gate_status}"
            else:
                merged_result.system_message = gate_status
        except Exception as e:
            print(f"WARNING: Gate status icons failed: {e}", file=sys.stderr)

        # Safety: auto-approve if Stop blocked >= 4 times within 2 minutes (aops-c67313ef)
        if ctx.hook_event in ("Stop", "SessionEnd") and merged_result.verdict == "deny":
            try:
                now = datetime.now().timestamp()
                block_timestamps: list[float] = state.state.get("stop_block_timestamps", [])
                # Purge entries older than 2 minutes
                block_timestamps = [ts for ts in block_timestamps if now - ts < 120.0]
                block_timestamps.append(now)
                state.state["stop_block_timestamps"] = block_timestamps
                if len(block_timestamps) >= 5:
                    merged_result.verdict = "allow"
                    warn = (
                        "⚠️ SAFETY OVERRIDE: Stop hook blocked 5+ times in 2 minutes."
                        " Auto-approving to prevent stall."
                    )
                    merged_result.system_message = (
                        f"{merged_result.system_message}\n{warn}"
                        if merged_result.system_message
                        else warn
                    )
                    state.state["stop_block_timestamps"] = []
            except Exception as e:
                print(f"WARNING: Stop block safety check failed: {e}", file=sys.stderr)

        # Save Session State ONCE
        try:
            state.save()
        except Exception as e:
            print(f"CRITICAL: Failed to save session state: {e}", file=sys.stderr)

        # Log hook event with output AFTER all gates complete
        try:
            log_hook_event(ctx, output=merged_result)
        except Exception as e:
            print(f"WARNING: Failed to log hook event: {e}", file=sys.stderr)

        return merged_result

    def _run_special_handlers(
        self, ctx: HookContext, state: SessionState, merged_result: CanonicalHookOutput
    ) -> None:
        """Run special handlers (logging, notifications) that aren't gates."""
        # Unified logger
        try:
            log_event_to_session(ctx.session_id, ctx.hook_event, ctx.raw_input, state)
        except Exception as e:
            print(f"WARNING: unified_logger error: {e}", file=sys.stderr)

        # ntfy push notifications
        if ctx.hook_event in ("SessionStart", "Stop", "PostToolUse"):
            self._run_ntfy_notifier(ctx, state)

        # Session env setup on start
        if ctx.hook_event == "SessionStart":
            try:
                from hooks.session_env_setup import run_session_env_setup

                init_result = run_session_env_setup(ctx, state)
                if init_result:
                    hook_output = self._gate_result_to_canonical(init_result)
                    self._merge_result(merged_result, hook_output)
                    if init_result.verdict == GateVerdict.DENY:
                        return  # Fail-fast on initialization failure
            except Exception as e:
                print(f"WARNING: session_env_setup error: {e}", file=sys.stderr)

        # Auto-commit ACA_DATA after state-modifying operations
        if ctx.hook_event == "PostToolUse":
            self._run_aca_data_autocommit(ctx)

        # Generate transcript on stop
        if ctx.hook_event == "Stop":
            transcript_path = ctx.raw_input.get("transcript_path")
            if transcript_path:
                self._run_generate_transcript(transcript_path)

    def _run_ntfy_notifier(self, ctx: HookContext, state: SessionState) -> None:
        """Run ntfy push notification handler."""
        try:
            from lib.paths import get_ntfy_config

            config = get_ntfy_config()
            if not config:
                return

            from hooks.ntfy_notifier import (
                notify_session_start,
                notify_session_stop,
                notify_subagent_stop,
                notify_task_bound,
                notify_task_completed,
            )

            if ctx.hook_event == "SessionStart":
                notify_session_start(config, ctx.session_id)
            elif ctx.hook_event == "Stop":
                current_task = state.main_agent.current_task
                notify_session_stop(config, ctx.session_id, current_task)
            elif ctx.hook_event == "PostToolUse":
                TASK_BINDING_TOOLS = {
                    "mcp__pkb__update_task",
                    "mcp__pkb__complete_task",
                    "mcp__pkb__complete_tasks",
                    "update_task",
                    "complete_task",
                    "complete_tasks",
                }
                if ctx.tool_name in TASK_BINDING_TOOLS:
                    tool_input = ctx.tool_input
                    if (
                        isinstance(tool_input, dict)
                        and "status" in tool_input
                        and "id" in tool_input
                    ):
                        status = tool_input["status"]
                        task_id = tool_input["id"]
                        if status == "in_progress":
                            notify_task_bound(config, ctx.session_id, task_id)
                        elif status == "done":
                            notify_task_completed(config, ctx.session_id, task_id)

                if ctx.tool_name in ("Task", "delegate_to_agent"):
                    agent_type = "unknown"
                    tool_input = ctx.tool_input
                    if isinstance(tool_input, dict):
                        # Support both Claude (subagent_type) and Gemini (name) parameters
                        agent_type = (
                            tool_input.get("subagent_type")
                            or tool_input.get("agent_name")
                            or tool_input.get("name", "unknown")
                        )
                    verdict = None
                    if tool_result := ctx.tool_output:
                        if isinstance(tool_result, dict) and "verdict" in tool_result:
                            verdict = tool_result["verdict"]
                    notify_subagent_stop(config, ctx.session_id, agent_type, verdict)
        except Exception as e:
            print(f"WARNING: ntfy_notifier error: {e}", file=sys.stderr)

    def _run_generate_transcript(self, transcript_path: str) -> None:
        """Run transcript generation on stop."""
        try:
            import subprocess
            from pathlib import Path

            root_dir = Path(__file__).parent.parent
            script_path = root_dir / "scripts" / "transcript.py"

            if script_path.exists():
                subprocess.run(
                    [sys.executable, str(script_path), transcript_path],
                    check=False,
                    capture_output=True,
                    text=True,
                )
        except Exception as e:
            print(f"WARNING: generate_transcript error: {e}", file=sys.stderr)

    def _run_aca_data_autocommit(self, ctx: HookContext) -> None:
        """Auto-commit ACA_DATA changes after state-modifying tool calls.

        Checks if the tool call modified the data repo, and if so,
        commits and pushes with a descriptive message. Never blocks
        the agent on failure.
        """
        try:
            from hooks.autocommit_state import (
                commit_and_push_repo,
                generate_commit_message,
                get_modified_repos,
                has_repo_changes,
            )

            tool_name = ctx.tool_name or ""
            tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else {}

            modified = get_modified_repos(tool_name, tool_input)
            if "data" not in modified:
                return

            aca_data = os.environ.get("ACA_DATA")
            if not aca_data:
                return

            from pathlib import Path

            repo_path = Path(aca_data)
            if not repo_path.exists() or not (repo_path / ".git").exists():
                return

            if not has_repo_changes(repo_path):
                return

            msg = generate_commit_message(tool_name, tool_input)
            success, result_msg = commit_and_push_repo(repo_path, commit_message=msg)
            if not success:
                print(f"WARNING: ACA_DATA autocommit: {result_msg}", file=sys.stderr)

        except Exception as e:
            # Never block the agent on autocommit failure
            print(f"WARNING: ACA_DATA autocommit error: {e}", file=sys.stderr)

    def _dispatch_gates(self, ctx: HookContext, state: SessionState) -> GateResult | None:
        """Dispatch to GenericGate methods based on event type.

        Maps hook events to GenericGate methods:
        - PreToolUse -> gate.check()
        - PostToolUse -> gate.on_tool_use()
        - UserPromptSubmit -> gate.on_user_prompt()
        - SessionStart -> gate.on_session_start()
        - Stop -> gate.on_stop()
        - AfterAgent -> gate.on_after_agent()
        - SubagentStart -> gate.on_subagent_start()
        - SubagentStop -> gate.on_subagent_stop()
        """
        from hooks.gate_config import COMPLIANCE_SUBAGENT_TYPES

        is_compliance_agent = ctx.is_subagent and (
            state.state.get("hydrator_active") or ctx.subagent_type in COMPLIANCE_SUBAGENT_TYPES
        )

        messages = []
        context_injections = []
        final_verdict = GateVerdict.ALLOW

        for gate in GateRegistry.get_all_gates():
            try:
                # If compliance agent, only evaluate triggers for PreToolUse and Stop
                # (other events only run triggers anyway)
                if is_compliance_agent and ctx.hook_event in ("PreToolUse", "PostToolUse", "Stop"):
                    result = gate.evaluate_triggers(ctx, state)
                else:
                    result = self._call_gate_method(gate, ctx, state)

                if result:
                    if result.system_message:
                        messages.append(result.system_message)
                    if result.context_injection:
                        context_injections.append(result.context_injection)

                    # Verdict precedence: DENY > WARN > ALLOW
                    # Compliance agents ALWAYS return ALLOW verdict because they bypass policies
                    if not is_compliance_agent:
                        if result.verdict == GateVerdict.DENY:
                            final_verdict = GateVerdict.DENY
                            break  # First deny wins
                        elif (
                            result.verdict == GateVerdict.WARN and final_verdict != GateVerdict.DENY
                        ):
                            final_verdict = GateVerdict.WARN

            except Exception as e:
                import traceback

                print(f"Gate '{gate.name}' failed: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

        if messages or context_injections or final_verdict != GateVerdict.ALLOW:
            return GateResult(
                verdict=final_verdict,
                system_message="\n".join(messages) if messages else None,
                context_injection="\n\n".join(context_injections) if context_injections else None,
            )
        return None

    def _call_gate_method(self, gate, ctx: HookContext, state: SessionState) -> GateResult | None:
        """Call the appropriate gate method based on hook event."""
        event = ctx.hook_event
        if event == "PreToolUse":
            return gate.check(ctx, state)
        elif event == "PostToolUse":
            return gate.on_tool_use(ctx, state)
        elif event == "UserPromptSubmit":
            return gate.on_user_prompt(ctx, state)
        elif event == "SessionStart":
            return gate.on_session_start(ctx, state)
        elif event == "Stop":
            return gate.on_stop(ctx, state)
        elif event == "AfterAgent":
            return gate.on_after_agent(ctx, state)
        elif event == "SubagentStart":
            return gate.on_subagent_start(ctx, state)
        elif event == "SubagentStop":
            return gate.on_subagent_stop(ctx, state)
        return None

    def _gate_result_to_canonical(self, result: GateResult) -> CanonicalHookOutput:
        """Convert GateResult to CanonicalHookOutput."""
        return CanonicalHookOutput(
            verdict=result.verdict.value,
            system_message=result.system_message,
            context_injection=result.context_injection,
            metadata=result.metadata,
        )

    def _merge_result(self, target: CanonicalHookOutput, source: CanonicalHookOutput):
        """Merge source into target (in-place)."""
        if source.verdict == "deny":
            target.verdict = "deny"
        elif source.verdict == "ask" and target.verdict != "deny":
            target.verdict = "ask"
        elif source.verdict == "warn" and target.verdict == "allow":
            target.verdict = "warn"

        if source.system_message:
            target.system_message = (
                f"{target.system_message}\n{source.system_message}"
                if target.system_message
                else source.system_message
            )

        if source.context_injection:
            target.context_injection = (
                f"{target.context_injection}\n\n{source.context_injection}"
                if target.context_injection
                else source.context_injection
            )

        if source.updated_input:
            target.updated_input = source.updated_input

        target.metadata.update(source.metadata)

    def output_for_gemini(self, result: CanonicalHookOutput, event: str) -> GeminiHookOutput:
        """Format for Gemini CLI."""
        out = GeminiHookOutput()

        if result.system_message:
            out.systemMessage = result.system_message

        # Set decision based on verdict
        if result.verdict == "deny":
            out.decision = "deny"
            if result.context_injection:
                out.reason = result.context_injection
                if not out.systemMessage:
                    out.systemMessage = f"Blocked: {result.context_injection}"
            elif out.systemMessage:
                out.reason = out.systemMessage
        else:
            out.decision = "allow"
            if result.context_injection:
                out.hookSpecificOutput = GeminiHookSpecificOutput(
                    hookEventName=event, additionalContext=result.context_injection
                )

        if result.updated_input:
            out.updatedInput = result.updated_input

        out.metadata = result.metadata
        return out

    def output_for_claude(
        self, result: CanonicalHookOutput, event: str
    ) -> ClaudeGeneralHookOutput | ClaudeStopHookOutput:
        """Format for Claude Code."""
        if event == "Stop" or event == "SessionEnd":
            output = ClaudeStopHookOutput()
            if result.verdict == "deny":
                output.decision = "block"
            else:
                output.decision = "approve"

            if result.context_injection:
                output.reason = result.context_injection

            if result.system_message:
                output.stopReason = result.system_message
                output.systemMessage = result.system_message

            return output

        output = ClaudeGeneralHookOutput()
        if result.system_message:
            output.systemMessage = result.system_message

        hso = ClaudeHookSpecificOutput(hookEventName=event)
        has_hso = False

        if result.verdict:
            if result.verdict == "deny":
                hso.permissionDecision = "deny"
                has_hso = True
            elif result.verdict == "ask":
                hso.permissionDecision = "ask"
                has_hso = True
            elif result.verdict == "warn":
                hso.permissionDecision = "allow"
                has_hso = True
            else:
                hso.permissionDecision = "allow"
                has_hso = True

        if result.context_injection:
            hso.additionalContext = result.context_injection
            has_hso = True

        if result.updated_input:
            hso.updatedInput = result.updated_input
            has_hso = True

        if has_hso:
            output.hookSpecificOutput = hso

        return output


# --- Main Entry Point ---


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Universal Hook Router")
    parser.add_argument(
        "--client", choices=["gemini", "claude"], help="Client type (gemini or claude)"
    )
    parser.add_argument(
        "event", nargs="?", help="Event name (required for Gemini if not in payload)"
    )

    # Parse known args to avoid issues if extra flags are passed
    args, unknown = parser.parse_known_args()

    router = HookRouter()

    # Read Input First (needed for detection)
    raw_input = {}
    try:
        if not sys.stdin.isatty():
            input_data = sys.stdin.read()
            if input_data.strip():
                raw_input = json.loads(input_data)
    except Exception as e:
        print(f"WARNING: Failed to read stdin: {e}", file=sys.stderr)

    # Debug log all input (enable with DEBUG_HOOKS=1)
    _debug_log_input(raw_input, args)

    # Detect Invocation Mode, relying on explicit --client flag
    if args.client:
        client_type = args.client
        gemini_event = args.event
    else:
        raise OSError("No --client flag provided on hook invocation.")

    # Pipeline
    ctx = router.normalize_input(raw_input, gemini_event)
    result = router.execute_hooks(ctx)

    # Output (JSON conversion happens only here)
    if client_type == "gemini":
        output = router.output_for_gemini(result, ctx.hook_event)
        print(output.model_dump_json(exclude_none=True))
    else:
        output = router.output_for_claude(result, ctx.hook_event)
        print(output.model_dump_json(exclude_none=True))


if __name__ == "__main__":
    main()
