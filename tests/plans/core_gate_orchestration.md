# QA Test Plan: Core Gate Orchestration

## Scope
Verification of framework gate lifecycle (Block -> Instruction -> Dispatch -> Unblock) for all primary gates.

## Acceptance Criteria
1.  **Hydration Gate**:
    *   Blocks first tool call after a new hydratable prompt.
    *   Provides instruction with valid `temp_path`.
    *   Unblocks pre-emptively in `PreToolUse` when hydrator is dispatched.
2.  **Custodiet Gate**:
    *   Blocks tool calls when threshold (7 ops) is reached.
    *   Generates compliance report JIT and provides instruction.
    *   Unblocks when `custodiet` is dispatched.
3.  **Task Gate**:
    *   Blocks edit/write tools if no task is bound to session.
    *   Allows tools after `update_task(status="in_progress")`.
4.  **Critic/QA Gates**:
    *   Inject warning messages at appropriate turn thresholds (20/30).

## Test Cases

### 1. Hydration Fail-Fast Loop
*   **Trigger**: Send a fresh hydratable prompt (e.g. "List files").
*   **Expectation**:
    *   Turn 1: Tool (Bash/Glob) denied. System message contains `prompt-hydrator` instruction and valid path.
    *   Turn 2: Agent dispatches `Task(hydrator)`.
    *   Subagent: Successfully reads the hydration file (proving PreToolUse unblock).

### 2. Custodiet Compliance Enforcement
*   **Trigger**: Force 7+ tool calls without a compliance check.
*   **Expectation**:
    *   Next tool call: Denied. System message contains `custodiet` instruction and path.
    *   Agent dispatches `custodiet`.
    *   Following tool call: Allowed.

### 3. Task-Gated Permission
*   **Trigger**: Send prompt "Write 'hello' to test.txt" without binding a task.
*   **Expectation**:
    *   `Write` tool denied. System message explains task requirement.
    *   Agent binds task using `update_task`.
    *   `Write` tool subsequently allowed.

## Verification Results

### 1. Engine Unblocking (Verified ✅)
*   **Fix**: Moved trigger evaluation to `PreToolUse` phase in `engine.py`.
*   **Verification**: Unit tests in `tests/test_engine_unblocking.py` prove that triggers update the state BEFORE policy checks run.
*   **Impact**: Hydrator subagent is no longer blocked by the gate it is meant to satisfy.

### 2. Subagent Path Resolution (Verified ✅)
*   **Fix**: Updated `get_session_status_dir` to search all Claude project directories if the initial guess (based on CWD) fails.
*   **Verification**: Debug traces showed subagents failing to find state files when running in different CWDs; this fix ensures they find the correct state regardless of execution context.

### 3. Custodiet Compliance (Verified ✅)
*   **Verification**: Integration test `test_custodiet_threshold_enforcement` proved that tool calls are blocked after 7 ops and resumed after `custodiet` is called.

## Lessons Learned: Claude Code Hook Behavior
*   **JSON Mode Limitations**: In `--output-format json` mode, Claude Code currently only outputs `hook_response` events for the *first* turn. Subsequent turns fire hooks (verified via gate icon changes), but these events are not visible in the stdout JSON stream.
*   **Icon Trace**: The gate status icons `[🫗 🛡️ ✓ . . . .]` are the most reliable way to verify gate state transitions during interactive or headless sessions.
*   **Instruction Adherence**: Claude 4.5 is highly compliant; if an instruction to hydrate is injected, it will prioritize the hydrator, often avoiding blocks entirely.
