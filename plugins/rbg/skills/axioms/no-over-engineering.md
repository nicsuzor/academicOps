---
description: Never build a mechanical engine, script, or programmatic wrapper where an agent workflow instructing agents to exercise qualitative judgment meets the request.
trigger: always_on
---

## Don't Over-Engineer Things

Never build a mechanical engine, script, CLI tool, programmatic API wrapper, or automated test harness where an agent workflow instructing agents to exercise qualitative judgment meets the request.

- **Default to agentic workflows:** This framework runs on intelligent, multimodal agents. When a task requires sampling, curating, classifying, evaluating, or recommending, write an agent workflow template (`wf-*`) or skill instruction (`SKILL.md`) that directs an agent to do the work directly. Never write deterministic code to do an agent's job.
- **Code is a permanent maintenance liability:** Every script, module, CLI, and test suite is complexity that someone must maintain, debug, and migrate. Executable code is strictly reserved for deterministic operations where LLMs cannot act directly (e.g., hardware drivers, protocol serialization, container runtime isolation).
- **Over-engineering is an axiom defect:** Building machinery that exceeds what the request needs is a fatal violation of proportionality and non-delegation. A proposal that builds mechanical engines where instructions suffice must be rejected at intake, reification, and review.
