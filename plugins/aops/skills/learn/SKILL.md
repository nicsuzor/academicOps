---
name: learn
description: Diagnose systemic root causes of errors from session logs and file anonymised issues in the appropriate repository. Diagnoses only; does not inspect repository source code, propose fixes, or implement remedies directly.
---

# Learn

Perform root-cause analysis on systemic failure classes using session execution records. Diagnose observable failure mechanisms from OpenTelemetry spans and file an issue at the responsible layer; do not inspect source code or propose fixes directly.

## Protocol

1. **Retrieve session execution record**:
   - Query session logs via OpenTelemetry spans using the `aops:session-trace` surface (`python3 plugins/aops/skills/session-trace/scripts/phoenix_trace.py <session-id>` or Phoenix REST API). Spans capture complete tool calls, arguments, outputs, errors, latencies, and subagent trees.
   - If the trace is absent, unexported, or incomplete, halt immediately and state that the trace is unavailable. Do not fall back to inspecting, grepping, or reading repository source code.
2. **Diagnose systemic cause from trace evidence**:
   - Ground findings in observable runtime mechanisms shown in the trace (failing tool invocations, unexpected tool error payloads, schema mismatches, hook blocks, timeout spikes).
   - Describe what the session attempted and where execution broke down. The trace itself is the evidence; do not inspect source files or name responsible code lines.
   - Address the class of failure rather than proximate mistakes. Focus on mechanisms and contracts rather than speculating on agent psychology or internal states.
3. **Determine scope**:
   - _Project_: Project-specific configuration, workflow templates, or repository guidelines.
   - _User/PKB_: User preferences, habits, or personal knowledge base.
   - _Framework_: Universal axioms, agent roles, or core tooling.
4. **File an issue**:
   - Search existing issues for the error class before creating a new one to avoid duplicate reports.
   - File an anonymized issue in the repository of the owning layer.
   - Ground the issue description in the trace record (tool calls, error spans, latencies). Strip personal names, credentials, file paths containing sensitive usernames, and raw environment details.
5. **No direct fixes**:
   - Diagnose only; do not propose fixes, select enforcement mechanisms, or open tasks to implement remedies. Findings serve as evidence for the framework enforcement loop (`specs/enforcement/enforcement.md`).

## Output

Return a markdown report containing:

- **Evidence**: Session ID, relevant OTel span IDs, and trace excerpts (tool calls, error payloads, latencies).
- **Root cause**: The systemic defect in execution flow, contract, or mechanism demonstrated by the trace.
- **Impact estimate**: Projected frequency and severity.
- **Artifact**: Link to the filed GitHub issue or PKB reference.
