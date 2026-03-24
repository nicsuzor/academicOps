---
name: skills
title: Skills Index
type: index
category: framework
description: |
    Quick reference for routing user requests to skills and commands.
    The [[BUTLER.md]] guide defines how this index is used for
    non-blocking routing hints.
permalink: skills
tags: [framework, routing, skills, index]
---

> **Curated by audit skill** - Regenerate with Skill(skill="audit")

# Skills Index

Quick reference for routing user requests to skills/commands. When a request matches triggers below, use direct routing and invoke.

## Skills and Commands

| Skill               | Type    | Triggers                                                                                                                                                                                                | Modifies Files | Needs Task | Mode           | Domain               | Description                                                                 |
| :------------------ | :------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------- | :--------- | :------------- | :------------------- | :-------------------------------------------------------------------------- |
| `/aops`             | command | "show capabilities", "what can you do", "help with framework"                                                                                                                                           | no             | no         | conversational | framework            | Show framework capabilities - commands, skills, agents, and how to use them |
| `/bump`             | command | "agent stuck", "continue", "nudge agent", "keep going"                                                                                                                                                  | no             | yes        | execution      | operations           | Nudge an agent back into action                                             |
| `/dump`             | command | "emergency handoff", "save work", "interrupted", "session end", "stop hook blocked"                                                                                                                     | yes            | yes        | execution      | operations           | Comprehensive work handover and session closure                             |
| `/hydrate`          | command | "hydrate task", "enrich task", "prepare task for execution"                                                                                                                                             | no             | no         | execution      | operations           | Enrich a PKB task with execution context for worker execution               |
| `/hydrator`         | skill   | "hydrate", "enrich task context", "prepare for worker"                                                                                                                                                  | no             | no         | execution      | operations           | Skill: enrich PKB tasks with context, workflows, AC, guardrails             |
| `/email`            | command | "process email", "email to task", "handle this email"                                                                                                                                                   | yes            | no         | execution      | email                | Create "ready for action" tasks from emails                                 |
| `/framework`        | skill   | "framework development", "hooks", "agents"                                                                                                                                                              | yes            | yes        | execution      | framework            | Butler: Self-aware core for framework governance and institutional memory.  |
| `/learn`            | command | "framework issue", "fix this pattern", "improve the system", "knowledge capture", "bug report"                                                                                                          | no             | no         | observation    | framework            | File high-quality, anonymised bug reports to GitHub Issues                  |
| `/path`             | command | "show path", "recent work", "what happened", "session history", "narrative timeline"                                                                                                                    | no             | no         | conversational | operations           | Show narrative path reconstruction                                          |
| `/intend`           | command | "I intend to", "set intention", "focus on", "what am I working on", "what are my intentions"                                                                                                            | yes            | no         | execution      | operations           | Declare, list, or complete active intentions                                |
| `/pull`             | command | "pull task", "get work", "what should I work on", "next task"                                                                                                                                           | yes            | no         | execution      | operations           | Pull a task from queue, claim it, and mark complete                         |
| `/planner`          | skill   | "queue task", "save for later", "plan X", "break this down", "strategic thinking", "prune knowledge", "densify tasks", "decompose task", "I had an idea", "what should I work on", "garden", "reparent" | yes            | no         | conversational | planning, operations | Unified planning agent — capture, plan, decompose, explore, maintain        |
| `/daily`            | skill   | "daily list", "daily note", "morning briefing", "update daily", "daily update", "reflect", "end of day", "how did today go", "weekly review", "review my progress"                                      | yes            | no         | execution      | operations           | Daily note lifecycle - briefing, task recommendations, sync, and reflection |
| `/qa`               | skill   | "verify", "QA check", "acceptance test", "quality check", "is it done", "validate work"                                                                                                                 | yes            | yes        | execution      | quality-assurance    | QA verification and test planning                                           |
| `/remember`         | skill   | "remember this", "save to memory", "store knowledge"                                                                                                                                                    | yes            | no         | execution      | operations           | Write knowledge to markdown AND sync to PKB                                 |
| `/sleep`            | skill   | "sleep cycle", "consolidation", "brain maintenance"                                                                                                                                                     | yes            | no         | execution      | operations           | Periodic consolidation agent — session backfill, replay, index, sync        |
| `/swarm-supervisor` | skill   | "polecat swarm", "polecat herd", "spawn polecats", "run polecats", "parallel workers", "batch tasks", "parallel processing"                                                                             | yes            | yes        | batch          | operations           | Orchestrate parallel polecat workers                                        |

## Routing Rules

1. **Explicit match**: User says "/daily" or "update my daily" -> invoke `/daily` directly
2. **Trigger match**: User request matches trigger phrases -> suggest skill, confirm if ambiguous
3. **Context match**: File types or project structure indicate skill -> apply skill guidance
4. **No match**: Route through normal workflow selection (WORKFLOWS.md)
