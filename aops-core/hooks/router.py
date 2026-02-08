#!/usr/bin/env python3
"""
Universal Hook Router.

Handles hook events from both Claude Code and Gemini CLI.
Consolidates multiple hooks per event into a single invocation.
Manages session persistence for Gemini.

Architecture:
- Gate functions are imported directly from gate_registry.py
- GateResult objects used internally, converted to JSON only at final output
- Shell scripts (session_env_setup.sh) still executed via subprocess
"""

import json
import os
import signal
import sys
import tempfile
import time
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
    from lib.gate_model import GateResult
    from lib.session_paths import get_pid_session_map_path, get_session_status_dir

    from hooks.gate_config import (
        GATE_EXECUTION_ORDER,
        MAIN_AGENT_ONLY_GATES,
    )
    from hooks.gate_registry import GATE_CHECKS
    from hooks.schemas import (
        CanonicalHookOutput,
        ClaudeGeneralHookOutput,
        ClaudeHookOutput,
        ClaudeHookSpecificOutput,
        ClaudeStopHookOutput,
        GeminiHookOutput,
        GeminiHookSpecificOutput,
        HookContext,
    )
    from hooks.unified_logger import log_hook_event
    from lib import session_state
except ImportError as e:
    # Fail fast if schemas missing
    print(f"CRITICAL: Failed to import: {e}", file=sys.stderr)
    sys.exit(1)


# --- Configuration ---

# Event mapping: Gemini -> Claude (internal normalization)
GEMINI_EVENT_MAP = {
    "SessionStart": "SessionStart",
    "BeforeTool": "PreToolUse",
    "AfterTool": "PostToolUse",
    "BeforeAgent": "UserPromptSubmit",  # Mapped to UPS for unified handling
    "AfterAgent": "AfterAgent",
    "SessionEnd": "Stop",  # Map SessionEnd to Stop to trigger stop gates
    "Notification": "Notification",
    "PreCompress": "PreCompact",
}

# Gate configuration is now in gate_config.py
# GATE_EXECUTION_ORDER and MAIN_AGENT_ONLY_GATES imported from there


# --- Gate Status Display ---

# Gate icons: shown when gate is CLOSED (blocking)
# When a gate is open (passed), it's not shown - only blocking gates are displayed
GATE_ICONS = {
    "hydration": "💧",  # Needs hydration (water drop)
    "task": "📌",  # Needs task binding (pin)
    "critic": "👁",  # Needs critic review (eye)
    "custodiet": "🛡",  # Needs compliance check (shield)
    "qa": "🧪",  # Needs QA verification (test tube)
    "handover": "🤝",  # Needs handover (handshake)
}


def format_gate_status_icons(session_id: str) -> str:
    """Format current gate statuses as a compact icon line.

    Shows only BLOCKING gates (closed state) for a clean display.
    When all gates are open, shows a simple ready indicator.

    Gate icons (shown when blocking):
        💧 = hydration needed
        📌 = task binding needed
        👁 = critic review needed
        🛡 = custodiet check needed
        🧪 = QA verification needed
        🤝 = handover needed

    Args:
        session_id: Session ID to check gates for

    Returns:
        Formatted status line like "[💧 📌]" (blocking gates) or "[✓ ready]" (all passed)

    Raises:
        ValueError: If session state cannot be loaded (fail fast)
    """
    state = session_state.load_session_state(session_id)
    if not state:
        raise ValueError(f"Cannot load session state for {session_id}")

    state_data = state.get("state", {})
    gates_state = state_data.get("gates", {})

    # Collect blocking (closed) gates
    blocking_gates = []

    # Check each gate - uses gates state dict if available, falls back to legacy checks
    # Hydration: closed if pending
    hydration_pending = state_data.get("hydration_pending", True)
    if gates_state.get("hydration") == "closed" or hydration_pending:
        blocking_gates.append("hydration")

    # Task: closed if no current task bound
    task_bound = state.get("main_agent", {}).get("current_task") is not None
    if gates_state.get("task") == "closed" or ("task" not in gates_state and not task_bound):
        # Only show task as blocking if gates dict says so, or if explicitly unbound
        # Default is open per GATE_INITIAL_STATE
        if gates_state.get("task") == "closed":
            blocking_gates.append("task")

    # Critic: check gates state (default open per GATE_INITIAL_STATE)
    if gates_state.get("critic") == "closed":
        blocking_gates.append("critic")

    # Custodiet: check gates state (default open per GATE_INITIAL_STATE)
    if gates_state.get("custodiet") == "closed":
        blocking_gates.append("custodiet")

    # QA: closed by default, opens when QA is invoked
    qa_invoked = state_data.get("qa_invoked", False)
    if gates_state.get("qa") == "closed" or ("qa" not in gates_state and not qa_invoked):
        blocking_gates.append("qa")

    # Handover: check gates state or legacy flag
    handover_ok = state_data.get("handover_skill_invoked", False)
    if gates_state.get("handover") == "closed" or (
        "handover" not in gates_state and not handover_ok
    ):
        # Only show if explicitly closed - default is open per GATE_INITIAL_STATE
        if gates_state.get("handover") == "closed":
            blocking_gates.append("handover")

    # Format output
    if not blocking_gates:
        return "[✓ ready]"

    # Show blocking gate icons
    icons = " ".join(GATE_ICONS[g] for g in blocking_gates if g in GATE_ICONS)
    return f"[{icons}]"


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
        self._MAX_CALLS_PER_WINDOW = 35
        self._WINDOW_SECONDS = 5.0

    def _check_for_loops(self, session_id: str):
        """Detect if execute_hooks is being called in a tight loop across processes."""
        # Use a dedicated heartbeat file in the session status directory
        status_dir_env = os.environ.get("AOPS_SESSION_STATE_DIR")
        if not status_dir_env:
            return

        heartbeat_file = Path(status_dir_env) / "hook-heartbeat.json"
        now = time.time()

        try:
            # Read previous heartbeats
            heartbeats = []
            if heartbeat_file.exists():
                try:
                    heartbeats = json.loads(heartbeat_file.read_text())
                except (json.JSONDecodeError, OSError):
                    pass

            # Add current heartbeat and prune old ones (older than window)
            heartbeats.append(now)
            heartbeats = [t for t in heartbeats if (now - t) < self._WINDOW_SECONDS]

            # Atomically write back
            fd, temp_path = tempfile.mkstemp(dir=str(heartbeat_file.parent), text=True)
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(heartbeats, f)
                Path(temp_path).rename(heartbeat_file)
            except Exception:
                Path(temp_path).unlink(missing_ok=True)

            if len(heartbeats) >= self._MAX_CALLS_PER_WINDOW:
                # Loop detected
                error_msg = (
                    f"CRITICAL: Infinite loop detected in hook router. "
                    f"Over {len(heartbeats)} hook calls in {self._WINDOW_SECONDS:.1f} seconds across processes. "
                    f"Terminating process {os.getpid()} to protect system RAM."
                )
                print(error_msg, file=sys.stderr)

                # Log to unified logger if possible
                try:
                    loop_ctx = HookContext(
                        session_id=session_id,
                        hook_event="RouterLoop",
                        raw_input={"error": error_msg, "heartbeats": heartbeats},
                    )
                    log_hook_event(
                        loop_ctx,
                        output=CanonicalHookOutput(
                            verdict="deny", system_message="Infinite loop detected."
                        ),
                    )
                except Exception as e:
                    print(f"WARNING: Failed to log loop detection: {e}", file=sys.stderr)

                # Terminate the current process forcefully.
                os.kill(os.getpid(), signal.SIGKILL)

        except Exception as e:
            # Don't let loop detection failure block the hook
            print(f"WARNING: Loop detection failed: {e}", file=sys.stderr)

    @staticmethod
    def _normalize_json_field(value: Any) -> Any:
        """Normalize a field that may be a JSON string to its parsed form.

        Gemini CLI sometimes passes tool_input and tool_result as JSON strings
        instead of dicts. This centralizes parsing so downstream gates don't need
        defensive json.loads calls.

        Args:
            value: Value that may be a JSON string or already-parsed dict/list

        Returns:
            Parsed value if it was a JSON string, otherwise unchanged
        """
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
            raw_event = raw_input.get("hook_event_name")
            if not raw_event:
                # Raise KeyError for backward compatibility with tests
                raise KeyError("hook_event_name")
            hook_event = GEMINI_EVENT_MAP.get(raw_event, raw_event)

        # 2. Determine Session ID
        session_id = raw_input.get("session_id")
        if not session_id:
            session_id = self.session_data.get("session_id")

        if not session_id and hook_event == "SessionStart":
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            short_uuid = str(uuid.uuid4())[:8]
            session_id = f"gemini-{timestamp}-{short_uuid}"

        if not session_id:
            session_id = f"unknown-{str(uuid.uuid4())[:8]}"

        # 3. Transcript Path / Temp Root
        transcript_path = raw_input.get("transcript_path")

        # Set AOPS_SESSION_STATE_DIR via centralized session_paths
        status_dir = get_session_status_dir(session_id, raw_input)
        os.environ["AOPS_SESSION_STATE_DIR"] = str(status_dir)

        # Persist session data on start
        if hook_event == "SessionStart":
            persist_session_data({"session_id": session_id})

        # 4. Normalize JSON string fields from Gemini
        # Gemini sometimes passes tool_input/tool_result as JSON strings
        tool_input = self._normalize_json_field(raw_input.get("tool_input", {}))
        if not isinstance(tool_input, dict):
            tool_input = {}

        # Normalize tool_result and toolResult in raw_input (for PostToolUse/SubagentStop)
        tool_output = {}
        raw_tool_output = (
            raw_input.get("tool_result")
            or raw_input.get("toolResult")
            or raw_input.get("tool_response", {})
        )
        if raw_tool_output:
            tool_output = self._normalize_json_field(raw_tool_output)
        elif "subagent_result" in raw_input:
            tool_output = self._normalize_json_field(raw_input["subagent_result"])
        subagent_type = os.environ.get("CLAUDE_SUBAGENT_TYPE")
        return HookContext(
            session_id=session_id,
            hook_event=hook_event,
            agent_id=raw_input.get("agentId"),
            slug=raw_input.get("slug"),
            is_sidechain=raw_input.get("isSidechain"),
            tool_name=raw_input.get("tool_name"),
            tool_input=tool_input,
            tool_output=tool_output,
            transcript_path=transcript_path,
            cwd=raw_input.get("cwd"),
            raw_input=raw_input,
            subagent_type=subagent_type,
        )

    def execute_hooks(self, ctx: HookContext) -> CanonicalHookOutput:
        """Run all configured gates for the event and merge results."""
        self._check_for_loops(ctx.session_id)
        merged_result = CanonicalHookOutput()

        # Build input dict for gate context
        gate_input = ctx.raw_input.copy()
        gate_input["hook_event_name"] = ctx.hook_event
        gate_input["session_id"] = ctx.session_id

        # Execute gate functions directly (no subprocess)
        gate_names = GATE_EXECUTION_ORDER.get(ctx.hook_event, [])

        # Filter: Certain gates ONLY run for the main agent to prevent recursion
        # and unnecessary overhead in subagent tool calls.
        subagent_type = os.environ.get("CLAUDE_SUBAGENT_TYPE")
        if subagent_type:
            gate_names = [g for g in gate_names if g not in MAIN_AGENT_ONLY_GATES]

        for gate_name in gate_names:
            check_func = GATE_CHECKS.get(gate_name)
            if not check_func:
                merged_result.metadata.setdefault("warnings", []).append(
                    f"Gate '{gate_name}' not found"
                )
                continue

            start_time = time.monotonic()
            try:
                result = check_func(ctx)
                duration = time.monotonic() - start_time
                merged_result.metadata.setdefault("gate_times", {})[gate_name] = duration

                if result:
                    hook_output = self._gate_result_to_canonical(result)
                    self._merge_result(merged_result, hook_output)

                    if hook_output.verdict == "deny":
                        break

            except Exception as e:
                import traceback

                error_msg = f"Gate '{gate_name}' failed: {e}"
                merged_result.metadata.setdefault("errors", []).append(error_msg)
                merged_result.metadata.setdefault("tracebacks", []).append(traceback.format_exc())

        # Append gate status icons to system message (non-intrusive display)
        # Function raises on failure (fail fast), but we catch here to avoid blocking hooks
        try:
            gate_status = format_gate_status_icons(ctx.session_id)
            if merged_result.system_message:
                merged_result.system_message = f"{merged_result.system_message} {gate_status}"
            else:
                merged_result.system_message = gate_status
        except Exception as e:
            print(f"WARNING: Gate status icons failed: {e}", file=sys.stderr)

        # Log hook event with output AFTER all gates complete
        # We already have a normalized context 'ctx' and result 'merged_result'
        # Pass them directly to the logger (no JSON conversion here)
        try:
            log_hook_event(ctx, output=merged_result)
        except Exception as e:
            print(f"WARNING: Failed to log hook event: {e}", file=sys.stderr)

        return merged_result

    def _gate_result_to_canonical(self, result: GateResult) -> CanonicalHookOutput:
        """Convert GateResult to CanonicalHookOutput."""
        return CanonicalHookOutput(
            verdict=result.verdict.value,
            system_message=result.system_message,
            context_injection=result.context_injection,
            metadata=result.metadata,
        )

    def _normalize_hook_output(self, raw: dict[str, Any]) -> CanonicalHookOutput:
        """Convert raw dictionary to CanonicalHookOutput."""
        if "verdict" in raw:
            return CanonicalHookOutput(**raw)

        canonical = CanonicalHookOutput()

        if "systemMessage" in raw:
            canonical.system_message = raw["systemMessage"]

        hso = raw.get("hookSpecificOutput", {})
        if hso:
            decision = hso.get("permissionDecision")
            if decision == "deny":
                canonical.verdict = "deny"
            elif decision == "ask":
                canonical.verdict = "ask"

            if "additionalContext" in hso:
                canonical.context_injection = hso["additionalContext"]

            if "updatedInput" in hso:
                canonical.updated_input = hso["updatedInput"]

        if raw.get("decision") == "block":
            canonical.verdict = "deny"
            if raw.get("reason"):
                canonical.context_injection = raw["reason"]

        return canonical

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

    def output_for_claude(self, result: CanonicalHookOutput, event: str) -> ClaudeHookOutput:
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
