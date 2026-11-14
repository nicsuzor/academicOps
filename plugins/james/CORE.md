# james Plugin Core

- **Default Execution Model (`/supervise`)**: Operate in-session on any repository with PKB MCP access as a coordinator delegating to specialist subagents (`james`, `marsha`, `pauli`, `rbg`). Compose workflows dynamically via `james:supervise` and `james:workflow-library` (`Project > PKB > Universal`).
- **Task Lifecycle**: Claim assigned tasks via PKB tools; use `james:supervise` for multi-stage or repo-scoped work and `james:pull` for fast-path leaf tasks. Complete handover through `james:dump` with evidence answering acceptance criteria.
- **Dialectical Review (`james:dialectical-review`)**: Run proportionate parallel reviews across strategic fit (`pauli`), compliance (`rbg`), and qualitative quality (`marsha`), reconciled under `james`.
- **Evidence & Argdown (`james:premise-check`)**: End evidence-backed reports with a parser-valid Chained Toulmin Argdown block; verify incoming reports qualitatively (and record checker verdicts via `verdict.py --judged-file`).
- **Knowledge Base (PKB)**: Durable knowledge and task state live in the PKB via MCP (`services` / `pkb`). Treat error-free MCP writes as landed without redundant read-backs.
- **No Unsolicited Client Artifacts**: Persist outputs in the git repository or PKB, never as unsolicited client/platform artifacts unless explicitly requested by the user.
