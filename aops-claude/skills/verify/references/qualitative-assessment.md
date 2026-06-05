# Qualitative Assessment — Moved

The persona-immersion, scenario-design, and dimension methodology that used to live here has moved to **`/aops-core:design-rubric`** — a skill owned by pauli, invoked at design time, not QA time.

## Why

Persona immersion at QA time is contamination. The reviewer has the artifact in front of them, no original context, and the temptation to rationalise. Persona immersion at _design_ time shapes the spec: the acceptance criteria encode the persona's needs, and the verifier's job becomes "did the artifact meet the AC the persona drove?" — a judgement call grounded in the spec, not in retrospective empathy.

See `/aops-core:design-rubric` for:

- Persona immersion (one paragraph, situational)
- Scenario design (golden / stressed / edge)
- Quality dimensions (judgement questions, not checkboxes)
- Quality spectrum (narrative description of excellent vs. poor)
- Output format: the `## Fitness Rubric` section that lives on the spec body

## What stays in `/verify`

The judgement-based QA pass itself — baseline sanity, evidence-based judgment, demand excellence — lives in `/verify`. The rubric is the _input_ to that pass, not part of the methodology.

Data-pipeline forensic tracing also stays in `/verify` (it is a QA-time technique, not a design-time one).

For the structural dimensions of visual artifacts (legibility, layout, hierarchy), see [[visual-analysis.md]]. Cognitive-load and emotional-response dimensions are design-time, see `/design-rubric`.
