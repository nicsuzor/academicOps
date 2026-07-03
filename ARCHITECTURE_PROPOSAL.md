# Architectural Proposal: Refactoring the Hook Router

## 1. Context and Problem Statement

The `aops-core` framework relies on intercepting CLI lifecycle hooks via `router.py` to enforce academic QA pipelines. The router operates as a "bottom-up" wrapper around upstream CLIs (Claude Code and Antigravity `agy`).

The core problem is the high volatility of the upstream CLI payload structures (stdout/stdin). When a CLI changes its payload schema (e.g., nesting tool parameters differently, removing a field, changing an event name), the `normalize_input` and `output_for_*` methods in `router.py` break silently or raise unexpected errors. Currently, the I/O translation is heavily coupled within the `HookRouter` class using cascading dictionary `.get()` lookups (`tool_result`, `toolResult`, `subagent_result`, `error`, etc.), making the router fragile and difficult to maintain as new CLI versions are released.

## 2. Proposed Architecture: The Adapter Pattern

To isolate the core framework logic from the fragility of upstream CLI schemas, we should introduce an **Adapter Layer**. The router should operate *exclusively* on internal, canonical schemas (e.g., `HookContext`, `CanonicalHookOutput`), completely detached from the specific JSON shapes emitted by `claude`, `gemini`, or `agy`.

### 2.1 Core Components

1.  **Client Adapters (`aops-core/hooks/adapters/`)**
    *   Create a dedicated adapter for each supported CLI: `ClaudeAdapter`, `GeminiAdapter`, and `AgyAdapter`.
    *   Each adapter implements a common interface (e.g., `ClientAdapterProtocol`) containing two primary methods:
        *   `parse_input(raw_json: dict) -> HookContext`
        *   `format_output(result: CanonicalHookOutput, event: str) -> BaseModel | dict`
    *   All CLI-specific fallback logic, wire-event mapping, and quirky schema traversals are encapsulated within these adapters.

2.  **Strict Pydantic Validation at the Edge**
    *   Instead of traversing unstructured dictionaries (`raw_input.get("...")`), each adapter should define strict Pydantic models representing the *exact* expected wire format for that CLI version (e.g., `AgyPreToolUsePayload`, `ClaudeStopPayload`).
    *   The `parse_input` method will attempt to parse the raw JSON into these strict models. If the upstream CLI changes its schema (e.g., renames a field), the Pydantic validation will fail immediately with a clear validation error, providing "fail-fast" behavior instead of silent propagation of empty fields (which breaks gates).

3.  **Refactored `HookRouter` (`aops-core/hooks/router.py`)**
    *   The `HookRouter` class will be stripped of all `normalize_input` and `output_for_*` logic.
    *   It will act purely as an orchestrator:
        1. Identify the client (`--client`).
        2. Instantiate the appropriate `ClientAdapter`.
        3. Call `adapter.parse_input(raw_input)` to get a canonical `HookContext`.
        4. Pass `HookContext` to the `GateRegistry` for evaluation.
        5. Receive `CanonicalHookOutput`.
        6. Call `adapter.format_output(canonical_output)` and print the result.

### 2.2 Integration with Existing Systems

*   **`client_spec.py`:** This module currently holds the event mapping dictionaries (`_INBOUND`, `_OUTBOUND`). The adapters will consume these mappings internally to translate wire events to canonical events during `parse_input`, and vice versa during `format_output`.
*   **`schemas.py`:** The existing output schemas (`ClaudeHookSpecificOutput`, `GeminiHookOutput`, etc.) are already Pydantic models. They will be moved to or utilized directly by their respective adapters.

## 3. Benefits

*   **Isolation of Volatility:** Changes in the `agy` CLI schema only require updating the `AgyAdapter` and its Pydantic models. The core routing and gate logic remains untouched.
*   **Fail-Fast Edge Validation:** By using strict Pydantic inbound models, we immediately catch unannounced upstream CLI changes, preventing silent logic failures (e.g., a missing tool name causing a gate to be bypassed).
*   **Enhanced Readability:** `router.py` shrinks significantly, focusing purely on orchestration rather than deep dictionary traversal.

## 4. Execution Plan (Future)

1.  Create `aops-core/hooks/adapters/base.py` defining the `ClientAdapterProtocol`.
2.  Implement `claude.py`, `gemini.py`, and `agy.py` in the `adapters` directory.
3.  Migrate the `normalize_input` logic for each client into the respective `parse_input` method.
4.  Migrate the `output_for_*` logic into the respective `format_output` method.
5.  Refactor `router.py` to instantiate and use these adapters dynamically based on the `--client` flag.
