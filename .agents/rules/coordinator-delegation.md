---
trigger: always_on
description: Interactive coordinator sessions exist for planning, triage, synthesis, and report verification; running expensive test suites or large codebase greps in-session is strictly prohibited and must be delegated to isolated polecats.
---

## Coordinator sessions delegate execution and expensive tests

Interactive and coordinator sessions (`ida`, `james`, interactive chat, or main session contexts) exist to triage user requests, plan and reify tasks, curate knowledge, and verify reported arguments. They do not execute heavy labour in-session.

- **Prohibition on expensive tests in-session**: Coordinator and interactive agents are strictly prohibited from running expensive test suites (such as `uv run pytest`, `make test`, or integration tests) or build pipelines directly in-session. All test suite execution and runtime builds must be delegated to isolated worker containers (`polecats`).
- **Prohibition on large codebase greps and scans**: Coordinator agents must not perform sweeping repository searches, large codebase greps, or full-file inspection chains across the repository in-session. When deep code investigation, refactoring analysis, or codebase exploration is required, the coordinator must dispatch an isolated probe or worker task to a polecat.
- **Delegation boundary**: Substantial implementation, code modification, runtime verification, and test execution tasks must be queued and dispatched to isolated worker containers (`polecats`) via `/dispatch`. In-session work is confined to in-turn conversational answers, PKB graph operations, task reification, and checking returned handback arguments per `premise-check`.
