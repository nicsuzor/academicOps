# ida Plugin Core

- **Argdown & Briefs**: Format Argdown with `ida:argdown-toulmin` and evaluate incoming briefs and reports with `ida:premise-check`.
- **Outgoing Reports**: Include a parser-valid Chained Toulmin Argdown block on every outgoing evidence-backed report and factual assertion.
- **Shared Memory (PKB) & Session Attribution**: Durable knowledge, task context, and state live in the PKB via MCP; pass your active session ID (`caller_session` when provided, else your active session ID) on every PKB and instrumented proxy MCP call, and treat error-free writes as landed without reading them back.
- **Custody & Planning**: Route PKB curation, planning (`/strategize`, `/decompose`, `/reify`), and knowledge graph queries exclusively to the custodian (`pauli`).
- **Dynamic Workflows**: Compose task workflows at run time via `ida:reify` and manage workflow templates via `ida:workflow-library`.
- **Durable Deliverables**: Requested documents are durable PKB documents, never ephemeral channel messages or unsolicited client artifacts unless explicitly requested by the user.
