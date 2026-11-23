# ida Plugin Core

- **Argdown & Formal Compliance Review**: Report inter-agent handbacks solely in clean Argdown prose and run administrative-law formal compliance review strictly on the face of the record (zero _de novo_ fact-checking) per `ida:premise-check`; reserve `ida:argdown-toulmin` for standalone formal `.argdown` maps and audits.
- **Shared Memory (PKB) & Session Attribution**: Durable knowledge, task context, and state live in the PKB via MCP; pass your active session ID (`caller_session` when provided, else your active session ID) on every PKB and instrumented proxy MCP call, and treat error-free writes as landed without reading them back.
- **Custody & Planning**: Route PKB curation, planning (`/strategize`, `/decompose`, `/reify`), and graph queries to `pauli`; do non-PKB build/test work in-session or through subagents, or ask the supervisor to clarify without declining; launch worker containers only when your own agent definition routes you to `/dispatch`.
- **Dynamic Workflows**: Compose task workflows at run time via `ida:reify` and manage workflow templates via `ida:workflow-library`.
- **Durable Deliverables**: Requested documents are durable PKB documents, never ephemeral channel messages or unsolicited client artifacts unless explicitly requested by the user.
