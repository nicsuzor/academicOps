# Design: Reduce Hydration Investigation Overhead

**Status**: Draft
**Task**: aops-3f9f7d5d
**Date**: 2026-02-04

## Problem Analysis

The `prompt-hydrator` system introduces latency ("investigation overhead") in two phases:
1.  **Hook Execution (`user_prompt_submit.py`)**: Synchronous gathering of context before the agent starts.
    -   Calls `task_cli list` (subprocess) twice.
    -   Loads multiple markdown files.
2.  **Agent Execution (`prompt-hydrator`)**:
    -   Step 3: "Check for prior implementation" often results in the agent emitting a plan that requires the Main Agent to check files/tasks, leading to round-trips.
    -   Step 9: "Correlate with existing tasks" relies on the limited `task_state` (top 20 active/inbox) or memory search.

## Proposed Approaches

### 1. Optimize Context Loading (Hook Level)

**Current**: `get_task_work_state` runs `task_cli.py` as a subprocess twice.
**Proposal**:
-   Use direct python import of `task_cli` logic instead of subprocess (if safe/clean).
-   Or cache the "task state" in a file that is updated only when tasks change (event-driven), rather than querying on every prompt.

### 2. Pre-loaded Task Graph (Routing)

**Current**: `task_state` only shows top 20 active/inbox. Hidden tasks (backlog/blocked) are invisible, risking duplication.
**Proposal**:
-   Maintain a lightweight "routing index" (JSON) of ALL open tasks (ID, title, status, project).
-   Inject this entire index into the hydrator context (if size permits, ~2-3k tokens for 100 tasks).
-   **Benefit**: Hydrator can route to *any* open task deterministically without "investigation" (memory search).

### 3. Shift Investigation to Execution Phase

**Current**: Hydrator tries to verify if files exist ("Step 3: Check for prior implementation").
**Proposal**:
-   **Remove Step 3** from Hydrator.
-   Hydrator should assume intent is valid and route to a task.
-   If the task turns out to be invalid (file doesn't exist), the *Worker* (Main Agent) handles that failure fast.
-   **Principle**: "It is cheaper to fail at execution time than to verify at planning time for every request."

### 4. Trust Task-Creator Classification

**Current**: Hydrator re-evaluates scope/complexity.
**Proposal**:
-   If the user provides a strong signal (e.g., explicit task ID, or "Reply to [Task]"), trust the context and skip the general routing logic.
-   (Note: `should_skip_hydration` already handles `/pull` and specific commands. This applies to natural language references).

## Recommended Plan

1.  **Immediate**: Modify `prompt-hydrator.md` to remove/soften "Step 3: Check for prior implementation". Instruct it to *plan* the check as the first step of execution, rather than asking the Main Agent to check *before* the plan.
    -   *Change*: "Do not ask main agent to check files. Assume files exist or plan a 'Verify existence' step."
2.  **Short-term**: Implement `task_routing_index.json`.
    -   Updated by `task_cli` on write.
    -   Read by `user_prompt_submit.py` (fast read, no subprocess).
3.  **Long-term**: Event-driven context updates.

## Decision Required

-   Approve removal of "Step 3" verification from Hydrator agent?
-   Approve "Fail-fast execution" philosophy over "Verified planning"?

