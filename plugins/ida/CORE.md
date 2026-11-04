# ida Plugin Core

- **Argdown & Briefs**: Use `ida:argdown-toulmin` to format Argdown assertions and `ida:premise-check` to evaluate incoming briefs and reports.
- **Outgoing Assertions**: Every handback report and outgoing factual assertion must carry a parser-valid Chained Toulmin Argdown block.
- **Knowledge Base (PKB)**: Shared knowledge, task context, and durable state live exclusively in the PKB via MCP.
- **PKB Custody & Planning**: Pauli has exclusive authority over PKB graph writes, memory curation, and planning (`/strategize`, `/decompose`, `/reify`); call Pauli for graph modifications.
- **Workflows**: Discover and compose repeatable processes dynamically from `ida:workflow-library` without hardcoding sequences.
- **Task Lifecycle**: Claim tasks via `ida:pull` and release on completion via `ida:dump` with evidence answering acceptance criteria.
