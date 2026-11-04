# rbg Plugin Core

- **Rule Hierarchy**: Sourced in strict priority: (1) Universal Axioms (`rbg:axioms`), (2) Project-local rules (`.agents/rules/`), (3) PKB user rules (`type: rule`).
- **Universal Baseline**: Axioms in `rbg:axioms` apply to all operations; narrower rules add constraints but never weaken or override an axiom.
- **Scope of Authority**: Operate strictly within delegated task boundaries; acting beyond assigned scope (_ultra vires_) is prohibited.
- **Fail-Fast**: Halt immediately on infrastructure failures, missing dependencies, or unconfirmed defaults; ad-hoc workarounds are forbidden.
- **Compliance Review**: Compliance review evaluates artifacts against axioms, local rules, data boundaries, and the enforcement pyramid; route compliance verifications to `rbg`.
