---
trigger: always_on
description: Workflows decide everything at run time; plugins hardcode no review, routing, or reviewer choice.
---

## Runtime workflow composition

- Workflows determine everything: what gets reviewed, where work goes, and who looks at what. No universal plugin file (agent, skill, hook, template, or spec) hardcodes any of these; remove any such rule wherever it is found.
- Never name or chain workflow templates in instructions, skills, specs, or templates; composers pick at run time from index and description.
- Templates state input/output contracts only; only claim and release are fixed.
