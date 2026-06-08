---
id: agent-definition-content
title: Agent Definition Content Boundary
type: spec
status: draft
tier: core
depends_on: [agent-authority, agent-permissions]
tags: [spec, agents, content-discipline, governance]
created: 2026-06-08
---

# Agent Definition Content Boundary

**Status**: Draft. Audit use tracked under `aops-35e31b8c`.

**Companion specs**: [[agent-authority]] (`specs/agents/agent-authority.md`) — frontmatter schema, skill delegation, non-transit rule. [[agent-permissions]] (`specs/agents/agent-permissions.md`) — four-axis permissions model. Read all three together for the complete agent specification layer. This spec does not restate their content; it governs what else goes — or stays out — of the agent body.

## Purpose

This spec answers a single question: **what content belongs in an agent identity definition, and what does not?**

Agent files are loaded on every invocation and paid for in tokens each time. They are identity files, not procedure manuals, not skill repositories, not documentation. The content discipline in this spec keeps them tight, purposive, and auditable.

## What Belongs In an Agent Definition

An agent definition file (`aops-core/agents/<name>.md`) may contain exactly four categories of content:

### 1. Identity and role statement

A brief declaration of who the agent is and what it does. One to three sentences. This is what a caller needs to decide whether to route work here.

**In**: "You are RBG: the axiom-violation reviewer. Judge the artifact for axiom compliance and return a verdict."

**Out**: "You are RBG. You were created because we needed a rigorous reviewer. The following explains how reviewing works as a practice…"

The identity statement serves routing and context-setting, not orientation or motivation.

### 2. Behavioral rules and operating constraints

Terse directives that describe how the agent must conduct itself: epistemic standards, safety invariants, delegation rules, verdict format requirements, never-block obligations. These are load-bearing constraints the agent must hold regardless of which task it is given.

**In**: "Verify runtime behaviour. Do not infer from source. If execution is impossible, report the gap."

**In**: "Never read, store, or broker credentials."

**Out**: Explanations of _why_ the rule exists. Rationale, history, worked examples, "you might be tempted to…" hedges. Those are documentation.

The test: remove the sentence. If the agent's behaviour becomes underconstrained, it stays. If the agent would have behaved the same way without it, it is documentation and must be removed or relocated to a reference file.

### 3. Verdict / output schema

When an agent produces structured output (verdicts, reports, scored findings), the schema for that output belongs here. Callers need to know what shape the return takes.

**In**: Verdict states (`APPROVE` / `REVISE` / `ESCALATE`), required sections of a report, response format.

**Out**: Methodology, worked examples of verdicts, tutorial on how to apply the schema.

### 4. Routing table (orchestrators only)

Orchestrator-class agents (james, junior, supervisor) hold a routing table mapping task types to agents and skills. This is identity-adjacent: it declares the orchestrator's scope of awareness. It belongs in the agent file.

The table must be a table — not prose. And it must be the table only — not a narrative explanation of why each route was chosen, not documentation of the agents being routed to.

## What Does Not Belong

### Skill matter

Procedural steps that belong in a skill file. If the instruction reads like a procedure ("Step 1: do X. Step 2: do Y. If Z, then W…"), it is a skill, not an identity property.

An agent definition may reference a skill by name. It must not reproduce the skill's procedure inline.

**Indicator**: The agent's file grows when the procedure is updated. That is drift.

### Documentation

Reference material, convention definitions, "how it works" explanations, methodology descriptions, and rationale prose have no place in agent instruction files.

This applies even when the documentation is accurate and useful. Its cost is incurred on every invocation whether the agent needs it or not. Documentation belongs in `specs/`, `README.md`, `.agents/CAPABILITIES.md`, or PKB documents.

This is an **explicit exception to the project's documentation-as-code principle**: agent instruction files are not code artefacts where documentation belongs alongside logic. They are runtime-loaded instruction surfaces. Every byte is a budget line.

The rule supersedes [[aops-9de50bad]] (which tracked this as a separate item — landing this spec closes that task).

**Indicator**: You can read the section in isolation and understand it as a standalone explanation of a concept. That is documentation.

### Operational mechanics duplicated from harness or hooks

If a behaviour is enforced by a hook, a gate, or the harness — and the agent does not need to be _instructed_ to do it because the harness handles it — the instruction is redundant. Redundant instructions add noise and create a maintenance surface.

**Indicator**: Removing the instruction would not change what happens when the agent runs, because the harness fires regardless.

### Policy or convention that duplicates `AXIOMS.md` / `CORE.md`

Universal axioms are loaded separately and apply everywhere. Restating them in an agent file does not strengthen the constraint; it creates a second copy that drifts.

**Indicator**: The instruction is a paraphrase of a rule already in `AXIOMS.md` or `CORE.md`.

### Content relevant only at authoring time

Design rationale, issue history, decision logs, "this was changed because…" commentary. These belong in the git history, the PR body, or the task that prompted the change.

## The Token Budget Test

When reviewing a candidate passage, apply this test:

> If this passage were removed, would the agent behave differently on the median task it handles?

If no: the passage is documentation or redundant constraint. Remove it or relocate it.

If yes: the passage is operative. Verify it cannot be shortened, then keep it.

A passage that would only affect the agent's behaviour on rare or hypothetical tasks fails the median-task test. Those edge-case instructions belong in the skill or procedure for that specific task, not in the always-loaded identity file.

## Frontmatter

Permissions, model, tools, skills allowlists, and sub-agent allowlists live in frontmatter only. The body does not redeclare them in prose. See [[agent-authority]] and [[agent-permissions]] for the complete frontmatter schema.

## Relation to Skills

Skills hold procedural matter. Agent definitions hold identity matter. The boundary:

| Agent file                             | Skill file                                      |
| -------------------------------------- | ----------------------------------------------- |
| Who the agent is                       | What the agent does when invoked for a task     |
| Standing behavioral constraints        | Task-specific procedural steps                  |
| Output schema (what the agent returns) | Reference material (taxonomy, examples, detail) |
| Routing table (orchestrators only)     | Methodology and worked examples                 |

An agent that does only one type of task well (a highly specialised agent) may appear to have procedure-like instructions. The test is not the topic but the _type_: if the instruction is a standing property that the agent must carry regardless of which task it is given, it belongs in the agent file. If it is a step that applies only when the agent is performing a specific operation, it belongs in a skill or workflow.

## Applying This as an Audit Rubric

The sibling audit task ([[aops-35e31b8c]]) uses this spec as its rubric. For each agent file, the audit checks:

1. **Body content classification**: does every passage in the body fall into one of the four in-scope categories?
2. **Skill matter test**: are there procedural step sequences that belong in skill files?
3. **Documentation test**: are there reference passages, rationale explanations, or convention definitions that could be relocated?
4. **Redundancy test**: are any instructions already enforced by the harness, hooks, `AXIOMS.md`, or `CORE.md`?
5. **Frontmatter/body boundary**: does the body restate permissions or tool grants declared in frontmatter?

A passage that fails any of these tests is a content violation. Violations are either remediated inline (for clear cases) or filed as follow-up tasks.

## Cross-References

- [[agent-authority]] (`specs/agents/agent-authority.md`) — Frontmatter schema, skill delegation, sub-agent spawning, non-transit rule.
- [[agent-permissions]] (`specs/agents/agent-permissions.md`) — Four-axis permissions model; what goes in frontmatter for tools, bash scopes, file access.
- `aops-35e31b8c` — Audit task: apply this spec to all agent files.
- `aops-9de50bad` — Superseded by this spec. The "no documentation in agent instructions" rule is now codified here.
- `aops-0bc1d9c5` — Sibling spec: skill content discipline (parallel document for skills, not agents).

## Non-Goals

- **Skill content discipline.** That is covered by [[aops-0bc1d9c5]]. This spec is agent-side only.
- **Frontmatter schema correctness.** Covered by [[agent-authority]] and [[agent-permissions]].
- **Agent behaviour at runtime.** This spec governs what is written in the file, not what the agent does once running.
- **Cross-agent routing policy.** Covered by orchestrator specs and `specs/agents/supervisor.md`.
