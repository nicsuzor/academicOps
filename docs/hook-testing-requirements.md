---
title: Hook Testing Requirements
type: docs
category: docs
description: TTD requirements and strategy for hook development
permalink: hook-testing-requirements
tags: [testing, hooks, TTD]
---

# Hook Testing Requirements

This document defines the Test-Driven Development (TDD) requirements for `aops-core` hooks, based on the audit of existing E2E infrastructure.

## 1. Testing Strategy

Hook development must follow a pyramid testing strategy:

### Level 1: Unit Tests (`tests/hooks/`)

**Target**: Individual hook classes and logic.
**When**: For ALL hook changes.
**Requirements**:

- **Event Parsing**: Verify that `PreToolUse`, `PostToolUse`, `SessionStart`, etc., are parsed correctly.
- **State Transitions**: Verify internal state changes (e.g., `hydration_pending` -> `hydrated`).
- **Output Formatting**: Verify the exact structure of the hook's return value (e.g., `{"result": {...}}`).
- **Mocking**: Use mocks for external dependencies (other hooks, file system, API calls).

### Level 2: Integration Tests (`tests/integration/`)

**Target**: Interaction between multiple hooks or between a hook and the router.
**When**: When a hook interacts with another hook or relies on shared state (e.g., `Context`).
**Requirements**:

- **Router Compliance**: Verify the hook adheres to the `Hook` protocol.
- **Context Propagation**: Verify data flows correctly through the `Context` object.

### Level 3: E2E Tests (`tests/e2e/`)

**Target**: Full agent behavior with the hook enabled.
**When**:

- A new **gate** type is added (blocking behavior).
- A hook significantly modifies the **agent's loop** (e.g., injecting prompts).
- A new **event type** is handled.
  **Requirements**:
- **Real Scenarios**: Use real framework prompts, not "hello world".
- **Session Tracking**: Use `claude_headless_tracked` (or Gemini equivalent) to verify tool calls.
- **No Keyword Matching**: Do NOT check `output` for substrings. Check `tool_calls` or structural artifacts.

### Level 4: Demo Tests (`tests/demo/`)

**Target**: Human validation of semantic output.
**When**: The hook produces text intended for the user (e.g., a welcome message, a warning).
**Requirements**:

- **Full Output**: Print the full output to stdout.
- **Visual Inspection**: Designed for a human to run with `pytest -m demo -s`.

## 2. Required Fixtures

To support this strategy, the following fixtures must be developed/used:

### 2.1 Hook Unit Test Fixtures

_To be implemented in `tests/hooks/conftest.py`_

- **`mock_hook_context`**: A `Context` object populated with standard test data.
- **`event_factory`**: A helper to generate valid event payloads (`PreToolUse`, `SessionStart`) with minimal boilerplate.
  ```python
  event = event_factory.create_pre_tool_use(tool="run_shell_command", args={"command": "ls"})
  ```
- **`mock_output_sink`**: To capture and inspect what the hook writes to stdout/stderr (if applicable).

### 2.2 E2E Fixtures

_Existing in `tests/conftest.py`_

- **`cli_headless`**: For general execution.
- **`claude_headless_tracked` / `gemini_headless_tracked`**: For verifying tool calls.
- **`test_data_dir`**: For file system isolation.

## 3. TTD Workflow for Hook Changes

1. **Write the Unit Test**:
   - Create a test case in `tests/hooks/test_<hook_name>.py`.
   - Mock the input event.
   - Assert the expected output structure or state change.
   - _Run test -> Fail._

2. **Implement the Logic**:
   - Modify the hook class to handle the event.
   - _Run test -> Pass._

3. **Write the E2E/Demo Test (if applicable)**:
   - If it's a user-facing change, add a demo test in `tests/demo/`.
   - If it's a logic gate, add an E2E test in `tests/e2e/`.
   - _Run test -> Pass._

4. **Verify Coverage**:
   - Ensure both happy path and error cases are covered.

## 4. Specific Gaps to Address

Refactoring efforts should prioritize closing these gaps:

1. **SessionEnd Formatting**: Add unit tests for `SessionEnd` event handling to prevent regression of the "JSON decode error" bug.
2. **Hook State Logic**: Extract state logic (e.g., in `PolicyEnforcer`) into testable methods, separating it from the I/O of the `run()` method.
3. **Error Handling**: specific tests for when a hook encounters invalid input or internal errors.

## 5. Anti-Patterns to Avoid

- **Testing via `run_shell_command` only**: Do not rely solely on spawning the CLI to test a hook. Unit tests should instantiate the Python class directly.
- **Coupling to Global State**: Avoid hooks that rely on global variables. Inject dependencies via `__init__` or `Context`.
