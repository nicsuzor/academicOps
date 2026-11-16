# ida Plugin Core

- **Argdown & Briefs**: Use `ida:argdown-toulmin` to format Argdown assertions and `ida:premise-check` to evaluate incoming briefs and reports.
- **Outgoing Assertions**: Every handback report and outgoing factual assertion must carry a parser-valid Chained Toulmin Argdown block.
- **Knowledge Base (PKB)**: Shared knowledge, task context, and durable state live exclusively in the PKB via MCP. Every PKB tool call (all reads and writes, including `pkb.*` calls inside `portal_codemode_execute`) requires your own active `session_id` (`CLAUDE_CODE_SESSION_ID` / `ANTIGRAVITY_CONVERSATION_ID` or session context). When an MCP write returns without error, treat the write as landed.
- **Custodian & Planning**: Pauli owns PKB graph writes, memory curation, planning (`/james:strategize`, `/james:decompose`, `/james:reify`), and takes PKB queries and targeted read-only GitHub queries (`gh`), handing back non-PKB/non-`gh` requests; see `.agents/rules/pkb.md` for write authority and basic usage.
- **Workflows & Execution**: Workflows compose dynamically via `james:reify` and `james:workflow-library`. Tasks execute via `/james:supervise` (repo-scoped epic tasks in containers) or `/james:pull` (fast-path leaf tasks), releasing via `/james:dump`. Only Face Ida runs session handover `/james:dump`.
- **No Unsolicited Client Artifacts**: Deliverables go to the PKB or git repository, never a client or platform artifact unless explicitly requested by name.
- **Durable Documents Over Delivery Channels**: A requested document is a long-lasting PKB document to keep developing, never an ephemeral message or email; persist it to the PKB and leave delivery as a separate subsequent choice.
