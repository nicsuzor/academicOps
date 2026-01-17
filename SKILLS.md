---
name: skills
title: Skills Index
type: index
category: framework
description: Quick reference for routing user requests to skills and commands
permalink: skills
tags: [framework, routing, skills, index]
---

# Skills Index

Quick reference for routing user requests to skills/commands. When a request matches triggers below, use `[[direct-skill]]` workflow and invoke directly.

## Commands (User-Invocable)

| Command | Triggers | Description |
|---------|----------|-------------|
| `/daily` | "daily list", "daily note", "morning briefing", "update daily", "daily update" | Daily note lifecycle - briefing, tasks, session sync |
| `/pull` | "pull task", "get work", "what should I work on", "next task" | Pull task from queue, execute with guidance |
| `/q` | "queue this", "add to queue", "do this later", "file task" | Queue task for later execution |
| `/email` | "process email", "email to task", "handle this email" | Create bd issues from emails |
| `/learn` | "framework issue", "fix this pattern", "improve the system" | Graduated framework improvement |
| `/log` | "log observation", "note this", "framework feedback" | Log observations to bd issues |
| `/dump` | "emergency handoff", "save work", "interrupted" | Emergency work handover |
| `/diag` | "what's loaded", "session status", "diagnostic" | Session diagnostic check |
| `/aops` | "show capabilities", "what can you do", "help with framework" | Show framework capabilities |

## Skills (Auto-Triggered)

These skills activate based on task context, not explicit invocation:

| Skill | Triggers | Description |
|-------|----------|-------------|
| `/remember` | "remember this", "save to memory", "store knowledge" | Persist knowledge to markdown + memory |
| `/analyst` | dbt/ directory, Streamlit app, data analysis | Research data analysis with dbt/Streamlit |
| `/python-dev` | Python code, .py files, type safety | Production Python with fail-fast philosophy |
| `/pdf` | "convert to PDF", "make PDF", markdown to PDF | Academic-style PDF generation |
| `/flowchart` | "create flowchart", "mermaid diagram", process flow | Mermaid flowchart creation |
| `/excalidraw` | "draw diagram", "mind map", "visual diagram" | Hand-drawn style diagrams |
| `/garden` | "prune knowledge", "consolidate notes", PKM maintenance | Incremental knowledge base maintenance |
| `/convert-to-md` | "convert document", DOCX/PDF/XLSX conversion | Batch document to markdown |
| `/annotations` | HTML comments, `<!-- @nic: -->` patterns | Process inline collaboration comments |
| `/audit` | "framework audit", "check structure" | Framework governance audit |
| `/session-insights` | "session summary", "generate insights" | Session transcript analysis |
| `/dashboard` | "show dashboard", "task visibility" | Cognitive load dashboard |
| `/framework` | framework development, hooks, agents | Framework infrastructure work |

## Routing Rules

1. **Explicit match**: User says "/daily" or "update my daily" → invoke `/daily` directly
2. **Trigger match**: User request matches trigger phrases → suggest skill, confirm if ambiguous
3. **Context match**: File types or project structure indicate skill → apply skill guidance
4. **No match**: Route through normal workflow selection (WORKFLOWS.md)

## Why This Index Exists

Hydrator uses this to immediately recognize skill invocations without memory search, reducing latency for known workflows.
