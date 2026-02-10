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

## Qualitative Rubric
*   **Clarity**: Are instructions actionable?
*   **Efficiency**: Does unblocking happen immediately or require extra turns?
*   **Robustness**: Do client-specific commands (Gemini vs Claude) match the runner?
