# Evidence Base

Empirical findings and adjudications governing the craft standard. Cite relevant rows when a rule is contested.

## Measured Findings

| Finding                                           | Measurement                                                 | Source                                  |
| ------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------- |
| Curated skills raise task pass rates              | 33.9% -> 50.5% (+16.6pp) across 87 tasks                    | SkillsBench, arXiv:2602.12670           |
| Small skills outperform sprawling ones            | 1-3 focused modules (+19.0pp) vs 4+ modules (+10.1pp)       | SkillsBench                             |
| Self-generated skills degrade performance         | up to -11.5pp vs no skill                                   | SkillsBench                             |
| Positive imperatives outperform negative rules    | Significantly higher compliance on affirmative instructions | IFEval, arXiv:2507.22462                |
| Attention across long context is U-shaped         | Reliable recall at start and end; misses in middle          | Lost in the Middle, arXiv:2307.03172    |
| Instruction hierarchy privileges system/developer | Injection resistance requires privileged placement          | Instruction Hierarchy, arXiv:2404.13208 |
| Reason clauses improve generalization             | Functional "why" maps rules to pre-trained concepts         | arXiv:2310.00492                        |

## Format Limits

- `name`: Kebab-case, <=64 characters, matching directory name.
- `description`: <=1024 characters; front-loaded intent and exclusions.
- Frontmatter: Plain YAML without XML tags.
- Bundled references: Stored exactly one directory deep (`references/`, `scripts/`).
- Body budget: Target 30-80 lines, ceiling 200 lines.

## Adjudications

1. **Reasoning vs bare imperatives**: Explain reasoning. Functional clauses help models generalize to unseen cases.
2. **Capitalized emphasis**: Prohibited. Typography normalizes away and creates attention noise; use position and headers.
3. **Assertive descriptions**: Mandatory. Routers under-trigger by default, so descriptions must explicitly claim matching tasks.
4. **Subagent descriptions**: One concise sentence. Long descriptions dilute orchestrator routing heuristics.
5. **Trigger fields**: Description-only. Auxiliary fields (`when_to_use`) are non-portable across harnesses.
