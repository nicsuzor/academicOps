---
name: learn
description: Diagnose systemic root causes of errors from session logs and file anonymised issues or evidence-bump comments in the appropriate repository. Diagnoses only; does not inspect repository source code, propose fixes, or implement remedies directly.
---

# Learn

Perform root-cause analysis on systemic failure classes using session execution records. Diagnose observable failure mechanisms from OpenTelemetry spans (or session logs where the surface does not emit traces) and file an issue or evidence-bump comment at the responsible layer; do not inspect source code or propose fixes directly.

## Worker

Dispatch `/learn` to **`pauli`** (`TypeName: "pauli"`), never `james`. Pauli operates strictly from session execution records (`ida:session-trace`) and the PKB graph without searching or reading repository source code.

## Protocol

1. **Retrieve session execution record**:
   - Query session logs via OpenTelemetry spans using the `ida:session-trace` skill.
   - If the surface does not emit traces, proceed using the session's execution log or transcript directly. If the surface emits traces but the trace is absent, unexported, or incomplete, halt immediately and state that the trace is unavailable.
   - Do not fall back to inspecting, grepping, or reading repository source code.
2. **Diagnose systemic cause from execution evidence**:
   - **Agent failures are framework failures.** The user is not here to allocate blame among agents. An agent's error (misreading or rewording an ask, skipping a step, never delivering a result) is the instance, never the root cause. The root cause is the instruction, workflow, template, contract or tool that let a capable agent make that error: a rule that was missing, that did not reach the agent at that point, or that another instruction contradicted. Never name an agent, its brief or its wording as the root cause.
   - Ground findings in observable runtime mechanisms shown in the trace (or session log if the surface does not emit traces): failing tool invocations, unexpected tool error payloads, schema mismatches, hook blocks, timeout spikes.
   - Describe what the session attempted and where execution broke down. The runtime execution record is the evidence; do not inspect source files or name responsible code lines.
   - Treat an agent's account of its causes as hearsay, never as evidence of mechanism. Re-read the case from the primary user words independently of the caller's framing; what each agent received, ran, and chose on the record is the evidence.
   - Address the class of failure rather than proximate mistakes. Focus on mechanisms and contracts rather than speculating on agent psychology or internal states.
3. **Generalise the instance**: when the ask names one instance, take both steps below yourself, even if the instance is already fixed.
   - _General bug_: name the mechanism that produced the instance and will produce more like it.
   - _Verification miss_: search for the existing control (in axioms, rules, skills, and enforcement maps) governing the failure class; determine why that control did not fire or pass, and never assert that no control exists without an exhaustive search.
4. **Determine scope** of each finding:
   - _Project_: Project-specific configuration, workflow templates, or repository guidelines.
   - _User/PKB_: User preferences, habits, or personal knowledge base.
   - _Framework_: Universal axioms, agent roles, or core tooling.
5. **File issues or post evidence-bump comments**:
   - For each finding, search existing issues within the owning repository for the error class before creating a new issue to avoid duplicate reports. Target the remote repository directly by name (`owner/repo`) for both search and issue/comment creation rather than relying on a local checkout.
   - When the evidence belongs to an issue that already exists, summarise that evidence into an evidence-bump comment on that existing issue; do not file a separate issue for the evidence.
   - When no existing issue covers the finding, file in the owning repository:
     - When the primary failure is already well known and has a handler, file one issue for the handler's failure only.
     - When the primary failure is not already handled, file both issues (the general bug and the verification miss).
   - Ground the issue description or evidence-bump comment in the execution record (tool calls, error payloads, latencies). Strip personal names, credentials, file paths containing sensitive usernames, and raw environment details.
6. **No direct fixes**:
   - Diagnose only; do not propose fixes, select enforcement mechanisms, or open tasks to implement remedies. Findings serve as evidence for the framework enforcement loop (`specs/enforcement/enforcement.md`).

## Output

Return a markdown report containing:

- **Evidence**: Session ID / Conversation ID, relevant OTel span IDs (or session log excerpts if the surface does not emit traces), and execution excerpts (tool calls, error payloads, latencies).
- **Root cause**: The framework or workflow defect the execution record shows let the failure happen: a missing, unreached or contradicted instruction, a workflow step, a contract, or a tool. Never an agent's choice or wording.
- **Verification miss**: The check that should have caught the instance, and why it did not.
- **Impact estimate**: Projected frequency and severity.
- **Artifacts**: Links to the filed issue(s) or evidence-bump comment(s) (evidence-bump comment when an existing issue tracks the failure; otherwise handler's failure only if the primary failure is handled, or both the general bug and verification miss if unhandled).
