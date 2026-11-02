**Rule check before stop.** Verify compliance against governing rules and provide verifiable evidence before final handback.

1. **Evaluate all three rule scopes in order**: the `axioms` skill's files, `skills/axioms/` (baseline), project rules in `.agents/rules/`, and user rules in `$COPE_USER_RULES_DIR/` (when set). If the rule evaluator is unreachable, perform manual evaluation across all three scopes.
2. **Cite verifiable proof**: Reference `file:line`, command invocations, exit codes, or observed outputs.
3. **Disclose all violations**: Report every violation with reasons and citations, including unaddressed items and unchecked rules.
4. **Preserve handback**: The rule check annotates the handback without replacing deliverables.
