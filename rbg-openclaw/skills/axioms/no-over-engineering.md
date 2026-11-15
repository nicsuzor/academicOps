---
description: Give hard tasks to capable agents with clear instructions and tools, never to a mechanical substitute (script, engine, or fixed procedure).
trigger: always_on
---

## Don't Over-Engineer Things

Give hard tasks to capable agents with clear instructions and tools, never to a mechanical substitute (script, engine, CLI tool, programmatic API wrapper, automated test harness, or fixed procedure).

- **Default to capable agents with instructions and tools:** This framework runs on intelligent, multimodal agents. When a task is hard or requires understanding -- abstracting, sampling, curating, classifying, evaluating, designing, or recommending -- write an agent workflow template (`wf-*`) or skill instruction (`SKILL.md`) and equip the agent with the tools to do the work directly. When an agent cannot yet perform a task, close the gap in understanding, instructions, or tools rather than retreating to a mechanical substitute.
- **Code is a permanent maintenance liability:** Every script, module, CLI, and test suite is complexity that someone must maintain, debug, and migrate. Executable code is strictly reserved for deterministic operations where agents cannot act directly (e.g., hardware drivers, protocol serialization, container runtime isolation).
- **Prose and procedural over-builds are over-engineering:** Over-engineering is not limited to executable code. Authoring rigid fixed procedures, unneeded specifications, multi-tier calibration frameworks, architectural design epics, or enforcement-map rows where a concise instruction or workflow edit meets the request is an over-engineering defect.
- **Over-engineering is an axiom defect:** Building mechanical engines, scripts, or procedural machinery where capable agents with instructions and tools suffice must be rejected at intake, reification, and review.
