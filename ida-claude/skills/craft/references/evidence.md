# Evidence Base

Empirical findings and adjudications governing the craft standard. Cite relevant rows when a rule is contested.

## Measured Findings

| Finding | Measurement | Source |
| - | - | - |
| Curated skills raise task pass rates | 33.9% -> 50.5% (+16.6pp) across 87 tasks | SkillsBench, arXiv:2602.12670 |
| Small skills outperform sprawling ones | 1-3 focused modules (+19.0pp) vs 4+ modules (+10.1pp) | SkillsBench, arXiv:2602.12670 |
| Self-generated skills degrade performance | up to -11.5pp vs no skill | SkillsBench, arXiv:2602.12670 |
| Positive imperatives outperform negative rules | Significantly higher compliance on affirmative instructions | IFEval, arXiv:2507.22462 |
| Attention across long context is U-shaped | Reliable recall at start and end; misses in middle | Lost in the Middle, arXiv:2307.03172 |
| Instruction hierarchy privileges system/developer | Injection resistance requires privileged placement | Instruction Hierarchy, arXiv:2404.13208 |
| Reason clauses improve generalization | Functional "why" maps rules to pre-trained concepts | arXiv:2310.00492 |
| System prompt rule trimming preserves accuracy | Slashed >80% legacy rules with zero eval degradation | Anthropic Engineering (2025–2026) |
| Static prompt prefix optimizes caching | Up to 90% read-token cost and latency reduction | Anthropic / OpenAI Prompt Caching |
| Boundary-checked tool descriptions reduce failure | Mini-manual descriptions minimize bad tool calls | MCP Discovery Specifications |
| Passive references suffer from low retrieval | Unprompted file references drop to <20% read rate vs >95% under explicit procedural gates | SkillsBench, arXiv:2602.12670 |
| Negative instruction dilution | Long negative enumerations degrade affirmative task recall by up to 25% | IFEval, arXiv:2507.22462 |

## Format Limits

- `name`: Kebab-case, <=64 characters, matching directory name.
- `description`: 1–3 sentences (150–400 characters, <=1024 chars); front-loaded intent and explicit exclusions.
- Agent persona / system prompt: Target 30–60 lines (~200–500 tokens), ceiling 100 lines (<2,500 chars).
- Frontmatter: Plain YAML without XML tags.
- Skill body (`SKILL.md`): Target 30–80 lines (~400–1,000 tokens), ceiling 150–200 lines (~1,500 tokens).
- Workflow template: Target 30–60 lines, ceiling 100 lines.
- Tool description: 150–400 characters, ceiling 800 characters.
- Bundled references (Level 3): Stored exactly one directory deep (`references/`, `scripts/`); target 50–150 lines, ceiling 300 lines.

## Adjudications

1. **Reasoning vs bare imperatives**: Explain reasoning. Functional clauses help models generalize to unseen cases.
2. **Capitalized emphasis**: Prohibited. Typography normalizes away and creates attention noise; use position and headers.
3. **Assertive, affirmative descriptions**: Mandatory. Routers under-trigger by default, so descriptions must explicitly claim matching tasks. Structure descriptions affirmative-first (>=75% positive capability and trigger intent; <=25% contrastive exclusions naming the alternative peer skill). Prohibit speculative laundry lists of what the skill is not (IFEval, arXiv:2507.22462).
4. **Subagent descriptions**: One concise sentence. Long descriptions dilute orchestrator routing heuristics.
5. **Trigger fields**: Description-only. Auxiliary fields (`when_to_use`) are non-portable across harnesses.
6. **Persona vs. skill decoupling**: Personas define persistent identity and authority; skills define reusable execution recipes. Personas do not inline skill internals, and skills do not couple to specific personas.
7. **Progressive disclosure**: Frontmatter router (Level 1) -> JIT skill body (Level 2) -> dynamic reference assets (Level 3).
8. **Categorical generality**: Prohibit ad-hoc quotas or single-session fixes in agent instructions; formulate rules covering the entire category.
9. **Entity abstraction**: Use "the user" instead of personal names.
10. **No PKB leakage**: No PKB note/task IDs or wikilinks in distributed framework files.
11. **Zero provenance**: Strip incident/PR references from operational instructions.
12. **Level 3 reference incorporation**: Never rely on passive suggestions ("see references/..."). Incorporate Level 3 references via imperative procedural gates (`If <condition>, read <exact-path>`). Inline the structural shape in Level 2 and reserve Level 3 for non-median deep dives (SkillsBench, arXiv:2602.12670).
13. **Empirical evidence isolation**: Operational skill bodies define current rules and contracts without inlining citations. Evidence bases (Level 3) are consulted solely when rules or budgets are contested in review, keeping median execution lean.
