# crew plugin

- **Where work runs**: The composed workflow determines whether work runs in-session (handing bounded subtasks to the cheapest capable subagent) or in a polecat container on its own time.
- **Who does what**: The composed workflow assigns execution, review, and curation roles across `james` (execution and review coordination), `pauli` (PKB curation, planning, task reification, and compliance), and `marsha` (qualitative excellence), without hardcoding fixed owners or forced handoffs.
- **Shared memory**: Durable knowledge, tasks, and state live in the PKB, reached through the `services` MCP server. An error-free write has landed; do not read it back.
- **Governing rules**: The axioms (`crew:axioms`) bind every agent. Project rules (`.agents/rules/`) and PKB user rules (`type: rule`) add to them and never weaken them.
- **Workflows**: Workflows composed at run time from `crew:workflow-library` (never fixed in advance) determine what gets reviewed, where work and outputs go, and who inspects what.
