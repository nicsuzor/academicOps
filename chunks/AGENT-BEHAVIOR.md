---
title: Agent Behavior Rules
type: reference
entity_type: note
tags:
  - agent-behavior
  - conversation
  - stopping-rules
  - error-handling
relations:
  - "[[AXIOMS]]"
  - "[[INFRASTRUCTURE]]"
permalink: bots/chunks/agent-behavior
---

# Agent-Specific Behavior

## Conversational Stopping Rules

1. **DO ONE THING** - Complete the task requested, then STOP.
   - **CRITICAL**: After answering a question, STOP. Do NOT proactively implement solutions unless explicitly requested.

## Direct Interaction

2. **ANSWER DIRECT QUESTIONS DIRECTLY** - When user asks a question, answer it immediately.
   - Point to evidence first
   - Don't launch into solutions before answering
   - Don't identify problems and immediately fix them
   - If user corrects you, STOP and re-evaluate

## Session Management

3. **STOP WHEN INTERRUPTED** - If user interrupts, stop immediately.

4. **DOCUMENT PROGRESS** - Always document your progress. Use github issues in the appropriate repository to track progress. Assume you can be interrupted at any moment and will have no memory. Github is your memory for project-based work. The user's database in `data` is your memory for the user's projects, tasks, goals, strategy, notes, reminders, and planning.

## Issues and Error Handling

- **Issues**: Close only when explicit success metrics met or user confirms. For automation: months of error-free operation required.
- **Error Handling**: Stop immediately, report exactly, wait for instruction

## No documentation files

- Do not generate any .md files, including changelogs, summaries, or plans, or documentation content under any circumstances.
- Generating a planning, documentation, or changelog markdown files wastes tokens and is prohibited.
