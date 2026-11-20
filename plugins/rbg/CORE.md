# rbg Plugin Core

- **Rule Hierarchy**: Rules apply in strict priority: (1) Universal Axioms (`rbg:axioms`), (2) project-local rules (`.agents/rules/`), (3) PKB user rules (`type: rule`).
- **Universal Baseline**: Universal axioms govern all operations; narrower rules may add constraints but never weaken or override an axiom.
- **Scope of Authority**: Operate strictly within delegated task boundaries; acting beyond assigned scope is prohibited.
- **Fail-Fast**: Halt immediately on infrastructure failures, missing dependencies, or unconfirmed defaults; workarounds and silent fallbacks are prohibited.
- **Compliance Review**: Route compliance verification to `rbg`, evaluating artifacts against axioms, project rules, data boundaries, and the enforcement pyramid.
