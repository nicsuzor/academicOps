---
name: files-index
title: Framework Files Index
type: index
category: framework
description: Index of key framework files categorized by purpose.
---

# Framework Files Index

This index categorizes key files within the `aops-core/` directory and the root project.

## Core Governance

- `[[aops-core/AXIOMS.md]]`: Inviolable principles.
- `[[aops-core/HEURISTICS.md]]`: Validated hypotheses and guidelines.
- `[[aops-core/RULES.md]]`: Combined quick reference for rules.
- `[[aops-core/REMINDERS.md]]`: Periodic agent reminders.

## Agents

- `[[aops-core/agents/prompt-hydrator.md]]`: The hydration agent.
- `[[aops-core/agents/effectual-planner.md]]`: Strategic planning agent.
- `[[aops-core/agents/critic.md]]`: Second-opinion agent.
- `[[aops-core/agents/qa.md]]`: Quality assurance agent.
- `[[aops-core/agents/custodiet.md]]`: Drift detection agent.

## Hooks

- `[[aops-core/hooks/sessionstart_load_axioms.py]]`: Initial context loader.
- `[[aops-core/hooks/gate_registry.py]]`: Central enforcement gate.
- `[[aops-core/hooks/reflection_check.py]]`: Session-end handover validation.
- `[[aops-core/hooks/user_prompt_submit.py]]`: Pre-hydration trigger.

## Configuration

- `[[pyproject.toml]]`: Project dependencies and metadata.
- `[[gemini-extension.json]]`: Extension definition.
- `[[.pre-commit-config.yaml]]`: Git pre-commit hooks.
