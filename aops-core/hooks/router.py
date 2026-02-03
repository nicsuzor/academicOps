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
import subprocess
import tempfile
import time
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# --- Path Setup ---
HOOK_DIR = Path(__file__).parent # aops-core/hooks
AOPS_CORE_DIR = HOOK_DIR.parent  # aops-core

# Add aops-core to path for imports
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

try:
    from hooks.schemas import (
        HookContext,
        CanonicalHookOutput,
        ClaudeHookOutput,
        GeminiHookOutput,
        GeminiHookSpecificOutput,
        ClaudeHookSpecificOutput,
        ClaudeGeneralHookOutput,
        ClaudeStopHookOutput
    )
    from hooks.gate_registry import GATE_CHECKS, GateContext
    from hooks.unified_logger import log_hook_event
    from lib.gate_model import GateResult, GateVerdict
    from lib.session_paths import get_pid_session_map_path
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
    "BeforeAgent": "UserPromptSubmit", # Mapped to UPS for unified handling
    "AfterAgent": "AfterAgent",
    "SessionEnd": "Stop", # Map SessionEnd to Stop to trigger stop gates
    "Notification": "Notification",
    "PreCompress": "PreCompact",
}

# Shell scripts that must run via subprocess (can't be Python functions)
SHELL_SCRIPTS: Dict[str, List[str]] = {
    "SessionStart": ["session_env_setup.sh"],
}

# Gate configuration: Maps events to ordered list of gate function names
# Gates are called directly from gate_registry.GATE_CHECKS - no subprocess
GATE_CONFIG: Dict[str, List[str]] = {
    "SessionStart": ["unified_logger", "session_start"],
    "UserPromptSubmit": ["user_prompt_submit", "unified_logger"],
    "PreToolUse": [
        "unified_logger",
        "subagent_restrictions",
        "hydration",
        "task_required",
        "axiom_enforcer",
        "custodiet",
        "qa_enforcement",
    ],
    "PostToolUse": [
        "unified_logger",
        "task_binding",
        "accountant",
        "post_hydration",
        "post_critic",
        "skill_activation",
    ],
    "AfterAgent": ["unified_logger", "agent_response"],
    "SubagentStop": ["unified_logger"],
    "Stop": [
        "unified_logger",
        "stop_gate",
        "hydration_recency",
        "generate_transcript",
        "session_end_commit",
    ],
    "SessionEnd": ["unified_logger"],
}

# --- Session Management ---

def get_session_data() -> Dict[str, Any]:
    """Read session metadata."""
    try:
        session_file = get_pid_session_map_path()
        if session_file.exists():
            return json.loads(session_file.read_text().strip())
    except (OSError, json.JSONDecodeError):
        pass
    return {}

def persist_session_data(data: Dict[str, Any]) -> None:
    """Write session metadata atomically."""
    try:
        session_file = get_pid_session_map_path()
        existing = get_session_data()
        existing.update(data)
        
        # Atomic write
        fd, temp_path = tempfile.mkstemp(dir=str(session_file.parent), text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(existing, f)
            Path(temp_path).rename(session_file)
        except Exception:
            Path(temp_path).unlink(missing_ok=True)
            raise
    except OSError:
        pass # Silent failure to avoid protocol noise


# --- Router Logic ---

class HookRouter:
    def __init__(self):
        self.session_data = get_session_data()
        self._execution_timestamps = deque(maxlen=20)  # Store last 20 timestamps
        self._MAX_CALLS_PER_WINDOW = 15
        self._WINDOW_SECONDS = 5.0

    def _extract_gemini_state_dir(self, transcript_path: str) -> Optional[str]:
        """Extract Gemini state directory from transcript path.

        Gemini transcript paths look like:
        ~/.gemini/tmp/<hash>/chats/session-<uuid>.json

        Returns the ~/.gemini/tmp/<hash>/ directory.

        FAIL-FAST (P#8): Directory MUST exist. Gemini CLI creates it.
        We do NOT auto-create - if missing, Gemini CLI failed to initialize.
        """
        path = Path(transcript_path)
        for parent in path.parents:
            if parent.name in ("chats", "logs"):
                # Parent of chats/logs is the hash directory
                state_dir = parent.parent
                if not state_dir.exists():
                    raise RuntimeError(
                        f"Gemini state directory missing: {state_dir}\n"
                        f"Gemini CLI must create ~/.gemini/tmp/<hash>/ before hooks run.\n"
                        f"This indicates Gemini CLI failed to initialize the project."
                    )
                return str(state_dir)
        return None

    def _check_for_loops(self):
        """Detect if execute_hooks is being called in a tight loop."""
        now = time.monotonic()
        self._execution_timestamps.append(now)

        if len(self._execution_timestamps) < self._MAX_CALLS_PER_WINDOW:
            return

        # Check if the last N calls happened within the time window
        window_start_time = self._execution_timestamps[0]
        if (now - window_start_time) < self._WINDOW_SECONDS:
            # Loop detected
            error_msg = (
                f"CRITICAL: Infinite loop detected in hook router. "
                f"Over {self._MAX_CALLS_PER_WINDOW} hook calls in {self._WINDOW_SECONDS:.1f} seconds. "
                f"Terminating process {os.getpid()}."
            )
            print(error_msg, file=sys.stderr)
            
            # Log to unified logger if possible, but don't fail if it doesn't work
            try:
                log_hook_event(
                    self.session_data.get("session_id", "unknown"),
                    "RouterLoop",
                    {"error": error_msg},
                    output_data={"verdict": "deny", "system_message": "Infinite loop detected."},
                )
            except Exception:
                pass # Do not prevent termination

            # Terminate the current process forcefully.
            os.kill(os.getpid(), signal.SIGKILL)

    def normalize_input(self, raw_input: Dict[str, Any], gemini_event: Optional[str] = None) -> HookContext:
        """Create a normalized HookContext from raw input."""
        
        # 1. Determine Event Name
        # Always apply GEMINI_EVENT_MAP for Gemini clients, whether event comes
        # from command line arg or from JSON payload (hook_event_name field)
        if gemini_event:
            hook_event = GEMINI_EVENT_MAP.get(gemini_event, gemini_event)
        else:
            # Fail-fast: hook_event_name is required in payload when not passed as arg
            raw_event = raw_input["hook_event_name"]
            # Apply mapping even when reading from JSON - fixes bug where
            # BeforeTool wasn't mapped to PreToolUse, causing gates to not run
            hook_event = GEMINI_EVENT_MAP.get(raw_event, raw_event)

        # 2. Determine Session ID
        session_id = raw_input.get("session_id")
        if not session_id:
            session_id = self.session_data.get("session_id")
        
        if not session_id and hook_event == "SessionStart":
            # Generate new ID for Gemini if missing
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            short_uuid = str(uuid.uuid4())[:8]
            session_id = f"gemini-{timestamp}-{short_uuid}"
            
        if not session_id:
            session_id = f"unknown-{str(uuid.uuid4())[:8]}"

        # 3. Transcript Path / Temp Root
        transcript_path = raw_input.get("transcript_path")

        # For Gemini sessions, set AOPS_SESSION_STATE_DIR from transcript_path
        # This ensures session_state.py can find/write files to correct location
        # Without this, Gemini state files go to wrong location or aren't created
        if transcript_path and "/.gemini/" in transcript_path:
            gemini_state_dir = self._extract_gemini_state_dir(transcript_path)
            if gemini_state_dir:
                os.environ["AOPS_SESSION_STATE_DIR"] = gemini_state_dir

        # Persist session data on start
        if hook_event == "SessionStart":
            persist_session_data({"session_id": session_id})
            if transcript_path:
                 pass 

        return HookContext(
            session_id=session_id,
            hook_event=hook_event,
            tool_name=raw_input.get("tool_name"),
            tool_input=raw_input.get("tool_input", {}),
            transcript_path=transcript_path,
            cwd=raw_input.get("cwd"),
            raw_input=raw_input
        )

    def execute_hooks(self, ctx: HookContext) -> CanonicalHookOutput:
        """Run all configured gates for the event and merge results.

        Gates are called directly as Python functions (no subprocess).
        Shell scripts are still executed via subprocess.
        """
        self._check_for_loops()
        merged_result = CanonicalHookOutput()

        # Build input dict for gate context
        gate_input = ctx.raw_input.copy()
        gate_input["hook_event_name"] = ctx.hook_event
        gate_input["session_id"] = ctx.session_id

        # 1. Execute shell scripts first (only SessionStart has them)
        shell_scripts = SHELL_SCRIPTS.get(ctx.hook_event, [])
        for script_name in shell_scripts:
            self._execute_shell_script(script_name, ctx, merged_result)
            if merged_result.verdict == "deny":
                return merged_result

        # 2. Execute gate functions directly (no subprocess)
        gate_names = GATE_CONFIG.get(ctx.hook_event, [])
        gate_ctx = GateContext(ctx.session_id, ctx.hook_event, gate_input)

        for gate_name in gate_names:
            check_func = GATE_CHECKS.get(gate_name)
            if not check_func:
                merged_result.metadata.setdefault("warnings", []).append(f"Gate '{gate_name}' not found")
                continue

            try:
                result = check_func(gate_ctx)
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

        # Log hook event with output AFTER all gates complete
        try:
            output_data = {
                "verdict": merged_result.verdict,
                "system_message": merged_result.system_message,
                "context_injection": merged_result.context_injection,
                "metadata": merged_result.metadata,
                "argv": sys.argv,  # Debug: log how hook was invoked
            }
            log_hook_event(
                ctx.session_id, ctx.hook_event, gate_input, output_data=output_data
            )
        except Exception:
            pass # Silent failure for logging to avoid protocol issues

        return merged_result

    def _execute_shell_script(
        self, script_name: str, ctx: HookContext, merged_result: CanonicalHookOutput
    ) -> None:
        """Execute a shell script via subprocess."""
        script_path = HOOK_DIR / script_name
        if not script_path.exists():
            merged_result.metadata.setdefault("warnings", []).append(f"Shell script not found: {script_path}")
            return

        env = os.environ.copy()
        current_pp = env.get("PYTHONPATH", "")
        if str(AOPS_CORE_DIR) not in current_pp:
            env["PYTHONPATH"] = f"{AOPS_CORE_DIR}{os.pathsep}{current_pp}" if current_pp else str(AOPS_CORE_DIR)

        subprocess_input = ctx.raw_input.copy()
        subprocess_input["hook_event_name"] = ctx.hook_event
        subprocess_input["session_id"] = ctx.session_id
        json_input = json.dumps(subprocess_input)

        try:
            result = subprocess.run(
                ["bash", str(script_path)],
                input=json_input,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
                cwd=HOOK_DIR
            )

            if result.stderr:
                merged_result.metadata.setdefault("shell_stderr", {}).update({script_name: result.stderr})

            if result.returncode == 0 and result.stdout.strip():
                try:
                    raw_output = json.loads(result.stdout)
                    hook_output = self._normalize_hook_output(raw_output)
                    self._merge_result(merged_result, hook_output)
                except json.JSONDecodeError:
                    merged_result.metadata.setdefault("warnings", []).append(f"Invalid JSON from {script_name}")

            elif result.returncode != 0:
                 merged_result.metadata.setdefault("errors", []).append(f"{script_name} failed with code {result.returncode}")

        except Exception as e:
            merged_result.metadata.setdefault("errors", []).append(f"Executing {script_name}: {e}")

    def _gate_result_to_canonical(self, result: GateResult) -> CanonicalHookOutput:
        """Convert GateResult to CanonicalHookOutput."""
        return CanonicalHookOutput(
            verdict=result.verdict.value,
            system_message=result.system_message,
            context_injection=result.context_injection,
            metadata=result.metadata,
        )

    def _normalize_hook_output(self, raw: Dict[str, Any]) -> CanonicalHookOutput:
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
            target.system_message = f"{target.system_message}\n{source.system_message}" if target.system_message else source.system_message
            
        if source.context_injection:
             target.context_injection = f"{target.context_injection}\n\n{source.context_injection}" if target.context_injection else source.context_injection
             
        if source.updated_input:
            target.updated_input = source.updated_input
            
        target.metadata.update(source.metadata)


    def output_for_gemini(self, result: CanonicalHookOutput, event: str) -> GeminiHookOutput:
        """Format for Gemini CLI.

        Per Gemini CLI docs (2026):
        - context_injection -> hookSpecificOutput.additionalContext (for prompt injection)
        - reason is ONLY for explaining denial decisions, not context injection
        - decision: "allow", "deny", or "block"
        """
        out = GeminiHookOutput()

        if result.system_message:
            out.systemMessage = result.system_message

        # Set decision based on verdict
        if result.verdict == "deny":
            out.decision = "deny"
            # For denials, put context in reason (explanation for denial)
            if result.context_injection:
                out.reason = result.context_injection
                if not out.systemMessage:
                    out.systemMessage = f"Blocked: {result.context_injection}"
        else:
            out.decision = "allow"
            # For allows, context goes to hookSpecificOutput.additionalContext
            if result.context_injection:
                out.hookSpecificOutput = GeminiHookSpecificOutput(
                    hookEventName=event,
                    additionalContext=result.context_injection
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
    parser.add_argument("--client", choices=["gemini", "claude"], help="Client type (gemini or claude)")
    parser.add_argument("event", nargs="?", help="Event name (required for Gemini if not in payload)")
    
    # Parse known args to avoid issues if extra flags are passed
    args, unknown = parser.parse_known_args()
    
    router = HookRouter()
    
    # Read Input First (needed for detection)
    try:
        if not sys.stdin.isatty():
            # Check if stdin has content
            input_data = sys.stdin.read()
            if input_data.strip():
                raw_input = json.loads(input_data)
            else:
                raw_input = {}
        else:
            raw_input = {}
    except Exception:
        raw_input = {}

    # Detect Invocation Mode, relying on explicit --client flag    
    if args.client:
        client_type = args.client
        gemini_event = args.event

    else:
        raise OSError("No --client flag provided on hook invocation.")
        
    # Pipeline
    ctx = router.normalize_input(raw_input, gemini_event)
    result = router.execute_hooks(ctx)
    
    # Output
    if client_type == "gemini":
        # Gemini typically passes event as argument, but we normalize in ctx
        output = router.output_for_gemini(result, ctx.hook_event)
        print(output.model_dump_json(exclude_none=True))
        sys.exit(0)
    else:
        output = router.output_for_claude(result, ctx.hook_event)
        print(output.model_dump_json(exclude_none=True))
        sys.exit(0)

if __name__ == "__main__":
    main()