---
name: learn
description: Diagnose systemic root causes of errors from session logs and file anonymised issues in the appropriate repository. Diagnoses only; does not inspect repository source code, propose fixes, or implement remedies directly.
---

# Learn

Perform root-cause analysis on systemic failure classes using session execution records. Diagnose observable failure mechanisms from OpenTelemetry spans (or session logs where the surface does not emit traces) and file an issue at the responsible layer; do not inspect source code or propose fixes directly.

## Protocol

1. **Retrieve session execution record**:
   - Query session logs via OpenTelemetry spans using the `ida:session-trace` skill.
   - If the surface does not emit traces, proceed using the session's execution log or transcript directly. If the surface emits traces but the trace is absent, unexported, or incomplete, halt immediately and state that the trace is unavailable.
   - Do not fall back to inspecting, grepping, or reading repository source code.
2. **Diagnose systemic cause from execution evidence**:
   - Ground findings in observable runtime mechanisms shown in the trace (or session log if the surface does not emit traces): failing tool invocations, unexpected tool error payloads, schema mismatches, hook blocks, timeout spikes.
   - Describe what the session attempted and where execution broke down. The runtime execution record is the evidence; do not inspect source files or name responsible code lines.
   - Address the class of failure rather than proximate mistakes. Focus on mechanisms and contracts rather than speculating on agent psychology or internal states.
3. **Generalise the instance**: when the ask names one instance, take both steps below yourself, even if the instance is already fixed.
   - _General bug_: name the mechanism that produced the instance and will produce more like it.
   - _Verification miss_: name the check that should have caught the instance before it reached the user, and why it passed or did not run.
4. **Determine scope** of each finding:
   - _Project_: Project-specific configuration, workflow templates, or repository guidelines.
   - _User/PKB_: User preferences, habits, or personal knowledge base.
   - _Framework_: Universal axioms, agent roles, or core tooling.
5. **File issues**:
   - Determine whether one issue is filed or two: when the primary failure is already well known and has a handler, file one issue for the handler's failure only; file both issues (the general bug and the verification miss) only when the primary failure is not already handled.
   - File each required issue in its owning repository.
   - For each, search existing issues within the owning repository for the error class before creating a new one to avoid duplicate reports. Target the remote repository directly by name (`owner/repo`) for both search and creation rather than relying on a local checkout.
   - Ground the issue description in the execution record (tool calls, error payloads, latencies). Strip personal names, credentials, file paths containing sensitive usernames, and raw environment details.
6. **No direct fixes**:
   - Diagnose only; do not propose fixes, select enforcement mechanisms, or open tasks to implement remedies. Findings serve as evidence for the framework enforcement loop (`specs/enforcement/enforcement.md`).

## Output

Return a markdown report containing:

- **Evidence**: Session ID, relevant OTel span IDs (or session log excerpts if the surface does not emit traces), and execution excerpts (tool calls, error payloads, latencies).
- **Root cause**: The systemic defect in execution flow, contract, or mechanism demonstrated by the execution record.
- **Verification miss**: The check that should have caught the instance, and why it did not.
- **Impact estimate**: Projected frequency and severity.
- **Artifacts**: Links to the filed issue(s) (handler's failure only if the primary failure is handled; both the general bug and verification miss if unhandled).
