**Rule check before stop.** Verify compliance against governing rules and provide verifiable evidence before final handback.

1. **Evaluate all three layers in order**: Shipped `axioms/` (baseline), project `.agents/rules/`, and `$ACA_DATA/.agents/rules/`. If `rbg` is unreachable, perform manual evaluation across all three layers.
2. **Cite verifiable proof**: Reference `file:line`, command invocations, exit codes, or observed outputs.
3. **Disclose all violations**: Report every violation with reasons and citations, including unaddressed items and unchecked rules.
4. **Preserve handback**: The rule check annotates the handback without replacing deliverables.
