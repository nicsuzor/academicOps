---
name: skills
title: Skills Index
type: index
category: framework
description: |
    Quick reference for routing user requests to skills and commands.
    Hydrator uses this to immediately recognize skill invocations
    without memory search, reducing latency for known workflows.
permalink: skills
tags: [framework, routing, skills, index]
---

> **Curated by audit skill** - Regenerate with Skill(skill="audit")

# Skills Index

Quick reference for routing user requests to skills/commands. When a request matches triggers below, use direct routing and invoke.

## Skills and Commands

| Skill               | Type    | Triggers                                                                                                                      | Modifies Files | Needs Task | Mode           | Domain                | Description                                                                 |
| :------------------ | :------ | :---------------------------------------------------------------------------------------------------------------------------- | :------------- | :--------- | :------------- | :-------------------- | :-------------------------------------------------------------------------- |
| `/aops`             | command | "show capabilities", "what can you do", "help with framework"                                                                 | no             | no         | conversational | framework             | Show framework capabilities - commands, skills, agents, and how to use them |
| `/bump`             | command | "agent stuck", "continue", "nudge agent", "keep going"                                                                        | no             | yes        | execution      | operations            | Nudge an agent back into action                                             |
| `/dump`             | command | "emergency handoff", "save work", "interrupted", "session end", "stop hook blocked"                                           | yes            | yes        | execution      | operations            | Comprehensive work handover and session closure                             |
| `/email`            | command | "process email", "email to task", "handle this email"                                                                         | yes            | no         | execution      | email                 | Create "ready for action" tasks from emails                                 |
| `/learn`            | command | "framework issue", "fix this pattern", "improve the system", "knowledge capture", "bug report"                                | yes            | no         | execution      | framework             | Rapid async knowledge capture for framework failures                        |
| `/path`             | command | "show path", "recent work", "what happened", "session history", "narrative timeline"                                          | no             | no         | conversational | operations            | Show narrative path reconstruction                                          |
| `/pull`             | command | "pull task", "get work", "what should I work on", "next task"                                                                 | yes            | no         | execution      | operations            | Pull a task from queue, claim it, and mark complete                         |
| `/q`                | command | "queue task", "save for later", "add to backlog", "new task:"                                                                 | yes            | no         | execution      | operations            | Quick-queue a task for later without hydration overhead                     |
| `/analyst`          | skill   | "data analysis", "dbt project", "streamlit app", "research pipeline"                                                          | yes            | yes        | execution      | academic, development | Support academic research data analysis using dbt and Streamlit             |
| `/annotations`      | skill   | "annotations", "inline comments", "respond to comments", "@nic: comment", "@ns: comment"                                      | yes            | no         | execution      | collaboration         | Scan and process inline HTML comments                                       |
| `/audit`            | skill   | "framework audit", "check structure"                                                                                          | yes            | yes        | execution      | framework             | Comprehensive framework governance audit                                    |
| `/briefing-bundle`  | skill   | "morning brief", "briefing bundle", "generate bundle", "decision brief"                                                       | yes            | no         | execution      | operations            | Generate morning briefing bundle with decision coversheets                  |
| `/convert-to-md`    | skill   | "convert document", "DOCX/PDF/XLSX conversion"                                                                                | yes            | yes        | batch          | operations            | Batch convert documents to markdown                                         |
| `/daily`            | skill   | "daily list", "daily note", "morning briefing", "update daily", "daily update"                                                | yes            | no         | execution      | operations            | Daily note lifecycle - briefing, task recommendations, sync                 |
| `/decision-apply`   | skill   | "apply decisions", "process decisions", "execute decisions"                                                                   | yes            | yes        | execution      | operations            | Process annotated decisions from daily note                                 |
| `/decision-extract` | skill   | "pending decisions", "what decisions", "decision queue", "decisions blocking"                                                 | yes            | no         | execution      | operations            | Extract pending decisions from task queue                                   |
| `/email-triage`     | skill   | "triage inbox", "email triage", "process inbox", "archive emails"                                                             | yes            | no         | execution      | email                 | Email triage workflow with mandatory archive logging                        |
| `/excalidraw`       | skill   | "draw diagram", "mind map", "visual diagram"                                                                                  | yes            | yes        | execution      | design                | Creating visually compelling, hand-drawn diagrams                           |
| `/extract`          | skill   | "extract information", "extract from document", "ingest", "extract decisions", "extract training data"                        | yes            | yes        | execution      | operations            | General extraction/ingestion skill                                          |
| `/flowchart`        | skill   | "create flowchart", "mermaid diagram", "process flow"                                                                         | yes            | yes        | execution      | design                | Creating clear, readable, and attractive Mermaid flowcharts                 |
| `/framework`        | skill   | "framework development", "hooks", "agents"                                                                                    | yes            | yes        | execution      | framework             | Primary entry point for framework infrastructure work                       |
| `/garden`           | skill   | "prune knowledge", "consolidate notes", "PKM maintenance"                                                                     | yes            | no         | execution      | operations            | Incremental PKM and task graph maintenance                                  |
| `/hdr`              | skill   | "HDR student", "reference letter", "supervision", "dissertation review", "research student"                                   | yes            | yes        | execution      | academic              | HDR student task conventions and workflows                                  |
| `/hypervisor`       | skill   | "atomic locking", "batch file processing", "file queue processing"                                                            | yes            | yes        | batch          | operations            | Atomic locking patterns for batch operations                                |
| `/pdf`              | skill   | "convert to PDF", "make PDF", "markdown to PDF"                                                                               | yes            | yes        | batch          | academic              | Convert markdown documents to formatted PDFs                                |
| `/planning`         | skill   | "decomposition patterns", "spike tasks", "dependency types"                                                                   | no             | yes        | conversational | operations            | Patterns for decomposing work under uncertainty                             |
| `/process-bundle`   | skill   | "process bundle", "process annotations", "execute bundle decisions"                                                           | yes            | yes        | execution      | operations            | Process annotated briefing bundle                                           |
| `/python-dev`       | skill   | "Python code", ".py files", "type safety"                                                                                     | yes            | yes        | execution      | development           | Write production-quality Python code                                        |
| `/qa`               | skill   | "verify", "QA check", "acceptance test", "quality check", "is it done", "validate work"                                       | yes            | yes        | execution      | quality-assurance     | QA verification and test planning                                           |
| `/remember`         | skill   | "remember this", "save to memory", "store knowledge"                                                                          | yes            | no         | execution      | operations            | Write knowledge to markdown AND sync to PKB                                 |
| `/session-insights` | skill   | "session summary", "generate insights"                                                                                        | yes            | no         | execution      | operations            | Generate comprehensive session insights from transcripts                    |
| `/strategy`         | skill   | "strategic thinking", "planning session", "explore complexity"                                                                | no             | no         | conversational | planning              | Strategic thinking partner for exploration and clarity                      |
| `/swarm-supervisor` | skill   | "polecat swarm", "polecat herd", "spawn polecats", "run polecats", "parallel workers", "batch tasks", "parallel processing"   | yes            | yes        | batch          | operations            | Orchestrate parallel polecat workers                                        |
| `/task-viz`         | skill   | "task visualization", "visualize tasks", "bd visualization", "task chart", "issue mind map", "network map", "knowledge graph" | yes            | no         | execution      | operations            | Generate network graph of notes/tasks                                       |

## Routing Rules

1. **Explicit match**: User says "/daily" or "update my daily" → invoke `/daily` directly
2. **Trigger match**: User request matches trigger phrases → suggest skill, confirm if ambiguous
3. **Context match**: File types or project structure indicate skill → apply skill guidance
4. **No match**: Route through normal workflow selection (WORKFLOWS.md)
