# ida Plugin Core

- **Argdown & Briefs**: Format factual assertions with `ida:argdown-toulmin` and evaluate incoming briefs and reports per `ida:premise-check`.
- **Outgoing Assertions**: Every handback report and outgoing factual assertion must carry a parser-valid Chained Toulmin Argdown block.
- **Worker Dispatch**: Route implementation, build, and test execution to isolated container sessions via `ida:dispatch`.
- **Knowledge Base & MCP Attribution**: Shared knowledge, task context, and durable state live in the PKB via MCP; pass active `session_id` explicitly on every MCP tool call accepting it, and treat error-free MCP writes as landed without reading back.
- **Output Discipline**: Deliver knowledge, reviews, and deliverables to the PKB or git repository rather than unsolicited client artifacts or ephemeral channels.
