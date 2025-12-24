---
title: Framework Capabilities Index
type: config
description: All available capabilities for intent routing. Updated when adding/removing skills, commands, agents.
---

# Framework Capabilities

This file is the source of truth for the intent router. When you add a new skill, command, or agent, add it here.

## Skills

| Name | Description |
|------|-------------|
| analyst | Research data analysis (dbt, Streamlit, statistics) |
| framework | Framework conventions, categorical imperative |
| remember | Store/retrieve memories via memory server |
| tasks | Task management + email extraction |
| python-dev | Production Python (fail-fast, typed, TDD) |
| pdf | Markdown → professional PDF |
| osb-drafting | IRAC analysis, citation verification |
| transcript | Session JSONL → markdown |
| session-insights | Batch transcript mining for learnings |
| learning-log | Pattern logging to thematic files |
| excalidraw | Hand-drawn diagrams and mind maps |
| ground-truth | Ground truth labels for evals |
| training-set-builder | Training data extraction |
| extractor | Email archive processing |
| skill-creator | Skill packaging (anti-bloat) |
| dashboard | Live task/session dashboard |

## Commands

| Name | Description |
|------|-------------|
| meta | Strategic brain + executor |
| email | Email → tasks extraction |
| log | Log patterns to learning files |
| qa | Verify against acceptance criteria |
| ttd | TDD orchestration |
| pull | Process high-priority tasks |
| add | Quick-add task |
| strategy | Strategic thinking (no execution) |
| parallel-batch | Parallel file processing |
| learn | Minimal framework tweaks |
| diag | Session diagnostic |
| consolidate | Consolidate LOG.md into thematic files |
| task-viz | Task graph visualization |

## Agents

| Name | Description |
|------|-------------|
| Explore | Fast codebase exploration |
| Plan | Implementation planning |
| critic | Second-opinion review |

## MCP

| Name | Description |
|------|-------------|
| memory server | Semantic search/storage (mcp__memory__*) |
| GitHub | GitHub operations (mcp__gh__*) |
