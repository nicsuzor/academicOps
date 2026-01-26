---
title: Project Context Schema v1
type: spec
status: DRAFT
description: Schema for CORE.md files that provide project-specific context to worker agents
---

# Project Context Schema v1

**Goal**: Define a schema for project `CORE.md` files that give worker agents (~16K token budget) the project-specific context they need to execute single tasks without wasting tokens on exploration.

## Problem Statement

Worker agents assigned to a project-specific task often lack:

1. **Project understanding** - what is this project? what does it do?
2. **Domain vocabulary** - what does "TJA" or "flow" mean in this context?
3. **Debugging knowledge** - how do we debug issues in this project?
4. **Tool awareness** - what skills/commands work here?

Without this context, agents waste tokens on broad exploration ("mewling baby groping around") instead of targeted execution.

## Token Budget

CORE.md must fit within worker context alongside other elements:

| Component | Target Tokens |
|-----------|---------------|
| Worker instructions | ~2-3K |
| Task details | ~1-2K |
| Relevant files | ~4-6K |
| Workflow reference | ~1K |
| **CORE.md** | **~2-3K** |
| Buffer | ~2-3K |
| **Total** | **~16K** |

**Hard constraint**: CORE.md should be 1000-1500 words max.

## Schema

### Location

```
<project-root>/CORE.md          # Primary location
<project-root>/.agent/CORE.md   # Alternative (parallels .agent/workflows/)
```

The hydrator checks both locations, with `.agent/CORE.md` taking precedence if both exist. This parallels the `.agent/workflows/` pattern for project-specific workflow overrides.

### Structure

```markdown
---
project: <slug>
root: <absolute-path-to-project-root>
type: library|service|cli|framework|monorepo
primary_language: python|typescript|rust|etc
---

# <Project Name>

<1-2 sentence summary of what this project does and its primary purpose>

## Domain Concepts

| Term | Definition |
|------|------------|
| <term1> | <1-line definition> |
| <term2> | <1-line definition> |
| <term3> | <1-line definition> |

Keep to 3-7 terms. Only include domain-specific vocabulary that appears in task descriptions.

## Architecture

<2-4 sentences describing:>
- Directory structure pattern
- Key architectural decisions
- Important boundaries/constraints

## Debugging

<Project-specific debugging guidance:>
- How to run tests: <command>
- How to check logs: <command or location>
- Common issues: <brief troubleshooting tips>

## Skills

Skills that work in this project context:

| Skill | When to Use |
|-------|-------------|
| <skill-name> | <trigger condition> |

Only list skills that are project-relevant, not global skills.

## Key Files

| Path | Purpose |
|------|---------|
| <relative-path> | <1-line description> |

5-10 files max. Include entry points, configs, and frequently-modified files.

## Context References

For deeper context, reference (don't inline):

- Architecture doc: <path>
- API reference: <path>
- Contributing guide: <path>
```

### Field Reference

#### Frontmatter (Required)

| Field | Type | Description |
|-------|------|-------------|
| `project` | string | URL-safe slug (e.g., "buttermilk", "tja", "aops-core") |
| `root` | string | Absolute path to project root |
| `type` | enum | One of: library, service, cli, framework, monorepo |
| `primary_language` | string | Primary programming language |

#### Sections

| Section | Required | Token Budget | Purpose |
|---------|----------|--------------|---------|
| Summary | Yes | ~50 | What is this project? |
| Domain Concepts | Yes | ~200 | Vocabulary for task understanding |
| Architecture | Yes | ~150 | Structural orientation |
| Debugging | Yes | ~200 | How to troubleshoot |
| Skills | No | ~150 | Available project skills |
| Key Files | Yes | ~200 | Navigation shortcuts |
| Context References | No | ~100 | Pointers for deep dives |

## Decision Tree: What Goes in CORE.md?

```
Is this information needed for MOST tasks in this project?
├── Yes: Include in CORE.md
│   └── Is it a fact or a reference?
│       ├── Fact (term, command, path): Include inline
│       └── Reference (doc, spec): Include path only
└── No: Do NOT include in CORE.md
    └── Task-specific context goes in task body or relevant files
```

### Belongs in CORE.md

- Project summary (always needed)
- Domain vocabulary (task descriptions use these terms)
- Debugging commands (most tasks involve debugging)
- Key file paths (navigation shortcuts)
- Skill availability (what tools work here)

### Does NOT Belong in CORE.md

- Task-specific implementation details (goes in task body)
- Full API documentation (reference path only)
- Historical decisions (link to ADRs)
- User preferences (goes in CLAUDE.md)
- Framework rules (goes in AGENTS.md)

## Integration with Worker Context Injection

CORE.md is loaded by the hydrator when generating worker context. It becomes a new section in the context chunk:

```markdown
## Worker Task Context

**Task**: ...

### Project Context

<contents of CORE.md, without frontmatter>

### Issue Details

...
```

The hydrator:
1. Locates CORE.md from task's project field (checks `.agent/CORE.md` first, then `CORE.md`)
2. Reads and strips frontmatter
3. Inserts as "Project Context" section
4. Includes before issue details (establishes context first)

## Validation Rules

A valid CORE.md must:

1. Have all required frontmatter fields
2. Have all required sections (Summary, Domain Concepts, Architecture, Debugging, Key Files)
3. Be under 1500 words
4. Use relative paths in Key Files section
5. Not duplicate content from CLAUDE.md or AGENTS.md

## Example: Buttermilk CORE.md

```markdown
---
project: buttermilk
root: /home/nic/src/buttermilk
type: library
primary_language: python
---

# Buttermilk

A Python library for building agentic AI workflows with structured output validation, flow composition, and trace-based debugging.

## Domain Concepts

| Term | Definition |
|------|------------|
| Flow | A composable workflow unit that processes inputs and produces typed outputs |
| Step | A single operation within a flow (LLM call, tool use, transform) |
| Trace | Debug record of flow execution including all step inputs/outputs |
| TJA | "Trace JSON Archive" - serialized trace format for debugging |
| Runner | Execution engine that runs flows with concurrency and retry logic |

## Architecture

Buttermilk follows a functional composition pattern. Flows are defined in `flows/` as pure functions. Steps are building blocks in `steps/`. The `Runner` in `core/runner.py` orchestrates execution with configurable concurrency.

Key boundary: Flows must be stateless. State lives in the trace, not the flow.

## Debugging

- Run tests: `uv run pytest tests/ -v`
- Run single flow: `uv run python -m buttermilk.cli run <flow-name>`
- Inspect trace: `uv run python -m buttermilk.cli trace <tja-file>`
- Common issue: If a flow fails silently, check the TJA trace for step-level errors

## Skills

| Skill | When to Use |
|-------|-------------|
| /trace | Analyze TJA files for debugging flow failures |
| /flow | Generate new flow from specification |

## Key Files

| Path | Purpose |
|------|---------|
| src/buttermilk/core/runner.py | Flow execution engine |
| src/buttermilk/core/flow.py | Base Flow class definition |
| src/buttermilk/steps/ | Step implementations |
| src/buttermilk/flows/ | Flow definitions |
| tests/ | Test suite |
| pyproject.toml | Dependencies and config |

## Context References

- Architecture doc: docs/architecture.md
- Flow authoring guide: docs/flows.md
- Step reference: docs/steps.md
```

## Relationship to Other Context Files

| File | Purpose | Loaded When |
|------|---------|-------------|
| CLAUDE.md | Global user preferences | Every session |
| AGENTS.md | Framework rules | Every agent |
| CORE.md | Project-specific context | Worker task injection |

CORE.md complements but does not replace CLAUDE.md. They serve different purposes:

- **CLAUDE.md**: User preferences, global rules, session configuration
- **CORE.md**: Project facts, domain vocabulary, debugging commands

## Success Criteria

1. Worker agents receiving CORE.md context can execute tasks without broad exploration
2. CORE.md fits within 2-3K token budget consistently
3. Schema is simple enough to create manually in 10 minutes
4. Schema supports monorepo projects (multiple CORE.md files in subdirectories)
