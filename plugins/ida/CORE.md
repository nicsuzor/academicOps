# ida Plugin Core

- **Argdown & Formal Compliance Review**: Report inter-agent handbacks solely in clean Argdown prose and run administrative-law formal compliance review strictly on the face of the record (zero _de novo_ fact-checking) per `ida:premise-check`; reserve `ida:argdown-toulmin` for standalone formal `.argdown` maps and audits.
- **Shared Memory (PKB) & Session Attribution**: Durable knowledge, task context, and state live in the PKB via MCP; pass your active session ID (`caller_session` when provided, else your active session ID) on every PKB and instrumented proxy MCP call, and treat error-free writes as landed without reading them back.
- **Office & Delegation**: Route PKB curation, planning (`/strategize`, `/decompose`, `/reify`), and graph queries to `pauli`; in-session execution exclusively to `james`; and isolated polecat worker dispatch exclusively to `sara` (`sara:sara`). Other agents never dispatch polecats directly. Ask the supervisor to clarify missing inputs without declining.
- **Model Selection**: Any agent invoking subagents chooses a model calibrated to task complexity, defaulting to the `fast` tier and escalating to `mid-tier` or `flagship` only when complexity warrants.
- **Fresh Subagents**: Give each unrelated task a fresh subagent rather than recycling entrenched context, stop idle subagents when no longer needed, and invoke parallel independent perspectives when answers look dubious.
- **Dynamic Workflows**: Compose task workflows at run time via `ida:reify` and manage workflow templates via `ida:workflow-library`.
- **Durable Deliverables**: Requested documents are durable PKB documents, never ephemeral channel messages or unsolicited client artifacts unless explicitly requested by the user.
