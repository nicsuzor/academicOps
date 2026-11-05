---
trigger: always_on
description: Instructions, skills, and templates must hold generally across their domain, client harnesses, operating systems, and environments, avoiding single-incident or platform-specific overfit.
---

## Instructions generalise

Every line of an instruction, skill, agent definition, rule, or workflow template must hold across the full scope of work that file governs and remain generic across client harnesses, operating systems, and execution environments.

- **Keep instructions generic across harnesses, operating systems, and environments:** Do not write instructions specific to a particular client harness (such as naming a specific client CLI, model family, or client-specific UI/artifact features), operating system, shell, or execution environment. State capabilities, tools, and artifacts in generic, harness-agnostic terms unless a file is an explicit adapter or configuration for a single target environment.
- Do not add rules or guidance over-fitted to a single session, incident, or idiosyncratic agent experience.
- Do not add template slots or narrative sections that prompt agents to search for irrelevant filler.
- Do not state prohibitions or constraints that the project does not actually hold.
