---
trigger: always_on
description: Leave workflow composition to run time; never tie instructions, templates, or docs to particular dynamic workflows.
---

## Workflows are composed at run time

No plugin instruction, skill, spec, doc, or workflow template names, references, or chains to a particular workflow template. The composing agent decides at run time which templates to assemble.

- A template states the contract it expects of its inputs and the output it owes — never which template precedes or follows it.
- No template (such as a finish or approval step) is singled out in specs or instructions. A template's only claim to selection is its presence in the index and its description.
- Only the mechanical lifecycle steps every task shares — claiming and releasing the task — are fixed. Do not prescribe fixed stages or layers for the work between them.
