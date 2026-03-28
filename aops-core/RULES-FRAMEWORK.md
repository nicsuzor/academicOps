---
name: framework-rules
title: Agent/Framework Context Rules
type: instruction
category: instruction
description: Non-negotiable rules for working on or within the academicOps framework. Enforced by the framework operations agent.
---

# Agent/Framework Context Rules

These rules are non-negotiable when working on the academicOps framework itself or when agents operate within it. They activate alongside the universal axioms in framework contexts.

## Always Dogfooding (P#22)

Use real projects as development guides, test cases, and tutorials. Never create fake examples. When testing deployment workflows, test the ACTUAL workflow.

## Skills Are Read-Only (P#23)

Skills MUST NOT contain dynamic data. All mutable state lives in $ACA_DATA.

## No Workarounds (P#25)

If tooling or instructions don't work PRECISELY, log the failure and HALT. NEVER use `--no-verify`, `--force`, or skip flags.

## Maintain Relational Integrity (P#29)

Atomic, canonical markdown files that link to each other rather than repeating content.

## Just-In-Time Context (P#43)

Context surfaces automatically when relevant. Missing context is a framework bug.

## Current State Machine (P#46)

$ACA_DATA is a semantic memory store containing ONLY current state. Episodic memory (observations) lives in bd issues.

## Agents Execute Workflows (P#47)

Agents are autonomous entities with knowledge who execute workflows. Workflow-specific instructions belong in workflow files, not agent definitions.

## No Shitty NLP (P#49)

Legacy NLP (keyword matching, regex heuristics, fuzzy string matching) is forbidden for semantic decisions. We have smart LLMs — use them. This extends to acceptance criteria: evaluate semantically, not with pattern matching.

**Corollaries**:

- Don't try to guess user intent with regex
- Don't filter documentation based on keyword matches
- Provide the Agent with the _index of choices_ and let the Agent decide
- **Agentic-first design**: Do NOT propose building scripts or tools that call LLM APIs programmatically. This framework runs on agentic platforms — Claude Code, Gemini CLI, Jules, GitHub agents. These agents ARE the LLM. Any work requiring judgment, evaluation, classification, or semantic reasoning should be designed as a skill, workflow, or agent task that a capable agent executes directly — not as a deterministic program that wraps API calls.
- **The Bazaar Model Extension**: Stop trying to build rigid, hook-based mechanical controls. Clients are unpredictable. Instead, define strict requirements in the Task Graph and use asynchronous agentic gates to verify those standards _before_ ratification. We don't control how the agent executes; we control whether the output is accepted.

**Derivation**: LLMs understand semantics; regex does not. Agentic frameworks already provide full LLM capabilities with tool access, context management, and iterative reasoning. Building programmatic API wrappers duplicates this capability poorly.

## Non-interactive Execution (P#55)

Agents MUST NOT run commands that require interactive input. Always use non-interactive flags (e.g., `--fill`, `--yes`, `-y`, `--no-interaction`) or ensure prerequisites are met before execution. If a command blocks for input, it is a framework bug.

**Corollaries**:

- If pushing a new branch, use `git push -u origin <branch>` before creating a PR to avoid `gh` interactive prompts.
- When scaffolding or installing, pass `-y` or similar flags.

**Derivation**: Interactive prompts in terminal commands hang agent execution loops, causing timeouts and requiring manual intervention to unblock. Agents must operate purely asynchronously.
