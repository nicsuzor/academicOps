# Evidence Base

The measured findings and adjudications the craft standard applies. Cite the
relevant row when a rule is contested; overrule a row only with a stronger
measurement, never with an asserted preference.

## Measured Findings

| Finding                                                                                                                     | Measurement                                                                | Source                                  |
| --------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | --------------------------------------- |
| Curated skills raise agent task pass rates                                                                                  | 33.9% → 50.5% (+16.6pp) across 87 tasks, 18 model-harness configurations   | SkillsBench, arXiv:2602.12670           |
| Small skills outperform sprawling ones                                                                                      | 1–3 focused modules +19.0pp vs 4+ modules +10.1pp                          | SkillsBench                             |
| Self-generated skills degrade performance                                                                                   | up to −11.5pp vs no skill at all                                           | SkillsBench                             |
| Negative constraints fail more often than positive instructions                                                             | significantly higher violation rates on "do not X" than "do Y" imperatives | IFEval, arXiv:2507.22462                |
| Attention across a long context is U-shaped; mid-file instructions are dropped                                              | reliable recall at start and end of context, routine misses in the middle  | Lost in the Middle, arXiv:2307.03172    |
| Models are trained to privilege instruction sources: system/developer over user over tool output                            | injection resistance depends on constraints living at the privileged level | Instruction Hierarchy, arXiv:2404.13208 |
| Reason clauses improve generalisation: instruction tuning maps rules onto pre-trained concepts, so the "why" carries signal | instruction tuning rotates concepts in feed-forward layers toward the task | arXiv:2310.00492                        |

## Format Limits

- `name`: kebab-case, 64 characters or fewer, identical to the skill's
  directory name.
- `description`: 1,024 characters or fewer; harness listings truncate around
  1,500 characters of combined trigger fields, so the first sentence carries
  the routing load.
- Frontmatter is plain YAML — no XML or angle-bracket tags.
- Bundled files live exactly one directory level deep (`references/`,
  `scripts/`, `assets/`).
- Harness guidance allows bodies to 500 lines; this standard holds 200 because
  the attention findings above bite well before the ceiling.

## Adjudications

Published authorities contradict each other on five authoring questions. The
rulings this standard applies, with their basis:

1. **Explain reasoning vs. bare imperatives** — explain. A functional reason
   clause lets the model generalise the rule to unseen cases (arXiv:2310.00492);
   only provenance, history, and design narrative are excluded.
2. **Capitalised emphasis vs. none** — none. Emphasis normalises away as files
   grow, and the absolutes are usually negative constraints, which fail at
   higher rates (IFEval). Emphasise through position and headers instead.
3. **Detached vs. assertive descriptions** — assertive. Routers under-trigger
   by default, so the description must advocate with the caller's vocabulary;
   grammatical person is immaterial.
4. **Subagent descriptions: example blocks vs. one sentence** — one short
   sentence. The orchestrator uses it solely as a routing heuristic; length
   dilutes the signal and spends the orchestrator's budget.
5. **Auxiliary trigger fields (`when_to_use`) vs. description-only** —
   description-only. The field is deprecated in part of the ecosystem and live
   in another, so it is not portable; the description carries all triggering.

Synthesised 2026-08-31 from the Agent Skills specification, vendor guidance
(Anthropic skill-creator, OpenAI structured outputs and instruction hierarchy,
Google verification-loop guidance), and the benchmarks cited above.
