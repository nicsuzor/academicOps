# crew Plugin Core

- **Rule Hierarchy**: Governing law applies in strict priority: (1) Universal Axioms (`crew:axioms`), (2) project-local rules (`.agents/rules/`), (3) PKB user rules (`type: rule`).
- **Universal Baseline**: Universal axioms form the inviolable constitutional baseline governing all operations; narrower rules may add obligations but never weaken or override an axiom.
- **Scope of Authority**: Operate strictly within delegated jurisdiction; acting beyond assigned scope (_ultra vires_) is prohibited.
- **Fail-Fast**: Halt verbatim on infrastructure failures, missing dependencies, or unconfirmed defaults; workarounds and silent fallbacks are prohibited.
- **Shared Memory (PKB) & Session Attribution**: Durable knowledge, task context, and state live in the PKB via MCP; pass your active session ID (`caller_session` when provided, else your active session ID) on every PKB and instrumented proxy MCP call, and treat error-free writes as landed without reading them back.
- **Dynamic Workflows**: Compose task workflows at run time via `crew:reify` and manage workflow templates via `crew:workflow-library`.
