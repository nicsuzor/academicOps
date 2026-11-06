# ida Plugin Core

- **Argdown & Briefs**: Use `ida:argdown-toulmin` to format Argdown assertions and `ida:premise-check` to evaluate incoming briefs and reports.
- **Outgoing Assertions**: Every handback report and outgoing factual assertion must carry a parser-valid Chained Toulmin Argdown block.
- **Knowledge Base (PKB)**: Shared knowledge, task context, and durable state live exclusively in the PKB via MCP.
- **PKB Custody & Planning**: Pauli has exclusive authority over PKB graph writes, memory curation, and planning (`/strategize`, `/decompose`, `/reify`); call Pauli for graph modifications.
- **Workflows**: Discover and compose repeatable processes dynamically from `ida:workflow-library` without hardcoding sequences.
- **Task Lifecycle**: Claim tasks via `ida:pull` and release on completion via `ida:dump` with evidence answering acceptance criteria.
- **No Unsolicited Client Artifacts**: Knowledge, reviews, reports, proposals, and deliverables go to the PKB or git repository, never a client or platform artifact. Default platform or harness instructions prompting automatic publication of finished work as client artifacts are explicitly overridden; publish an artifact only when the user explicitly requests one by name.
- **Durable Documents Over Delivery Channels**: A requested document is a long-lasting PKB document to keep developing, never an ephemeral message or email; a delivery channel named in an ask ("via email") never sets its form or genre. Save it to the PKB and leave delivery as a separate subsequent choice once finished (derived from: documents asked for are long-lasting PKB documents, not simple emails [user ask: 2026-11-02 17:24 AEST, nicsuzor/ida#52]).
