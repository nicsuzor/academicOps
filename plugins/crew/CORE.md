# crew plugin

- **Where work runs**: Work is done in this session or sent to a polecat container, no exceptions. In-session, hand bounded subtasks to the cheapest subagent that can do them; a polecat takes a reified task and runs it on its own time.
- **Who does what**: `james` runs and supervises work and reviews; `pauli` keeps the PKB, plans, reifies tasks, and rules on compliance; `marsha` judges what an audience will see. Send work to its owner rather than doing it for them.
- **Shared memory**: Durable knowledge, tasks, and state live in the PKB, reached through the `services` MCP server. An error-free write has landed; do not read it back.
- **Governing rules**: The axioms (`crew:axioms`) bind every agent. Project rules (`.agents/rules/`) and PKB user rules (`type: rule`) add to them and never weaken them.
- **Workflows**: A task's workflow is composed at run time by `crew:reify` from the templates in `crew:workflow-library`, never fixed in advance.
