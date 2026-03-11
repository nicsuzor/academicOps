---
name: paths-index
title: Framework Paths Index
type: index
category: framework
description: Index of standard framework paths and their purposes.
---

# Framework Paths Index

Standard paths used within the academicOps ecosystem.

## Environment Variables

- `$AOPS`: Root of the academicOps framework repo.
- `$ACA_DATA`: Root of the personal knowledge base (writing/data).

## Key Directories

| Path                   | Purpose                               | SSoT Reference   |
| ---------------------- | ------------------------------------- | ---------------- |
| `aops-core/skills/`    | Framework skill definitions           | [[SKILLS.md]]    |
| `aops-core/agents/`    | Agent frontmatter and instructions    | [[AGENTS.md]]    |
| `aops-core/workflows/` | Procedural logic and step definitions | [[WORKFLOWS.md]] |
| `specs/`               | Feature and workflow specifications   | `specs/INDEX.md` |
| `$ACA_DATA/tasks/`     | Active and pending tasks (JSON)       | -                |
| `$ACA_DATA/goals/`     | Strategic goals (Markdown)            | -                |
| `$ACA_DATA/projects/`  | Project definitions (Markdown)        | -                |
| `$ACA_DATA/sessions/`  | Session summaries and insights        | -                |

## Data Persistence

- `data/aops/`: Local cache and operational data.
- `data/transcripts/`: Raw session transcripts.
- `data/outputs/`: Generated artifacts (diagrams, PDFs).
