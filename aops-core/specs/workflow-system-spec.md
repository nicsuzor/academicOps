---
title: Composable Workflow System Specification
type: spec
category: architecture
status: draft
related_issues: ns-6hm
created: 2026-01-14
---

# Composable Workflow System Specification

## User Story

**As a** framework developer
**I want** a composable workflow system where workflows are defined as YAML+Markdown files with [[wikilinks]]
**So that** I can systematically guide work through well-defined processes that are version-controlled, auditable, and continuously improvable

### Example Invocation (Hybrid Approach)

**Automatic detection:**
```
User: "help me design a composable workflow system..."
→ Hydrator detects: "feature development" intent
→ Hydrator selects: workflows/feature-dev.md
→ Agent reads workflow steps
→ Agent creates bd issues for each phase
→ Agent follows first step: "Define user story"
```

**Explicit invocation:**
```
User: "/workflow feature-dev --for='composable workflow system'"
→ Agent loads workflows/feature-dev.md
→ Agent executes steps with context
```

## Acceptance Criteria

1. ✅ Workflows stored as YAML+Markdown in git (e.g., `workflows/feature-dev.md`)
2. ✅ Index files exist: `AXIOMS.md`, `HEURISTICS.md`, `WORKFLOWS.md`
3. ✅ Workflows can reference other workflows using `[[workflow-name]]` syntax
4. ✅ Hydrator can select appropriate workflow based on prompt intent
5. ✅ Each workflow step can be decomposed into bd issues
6. ✅ Agents can pick up bd issues and follow workflow steps
7. ✅ Visual graph representation shows workflow dependencies (via wikilink tools)

## Current State → Desired State

### Current (v1.0 Core Loop)

**Prompt Hydrator:**
- Fixed routing table in `/tmp/claude-hydrator/hydrate_lgjzvhbr.md`
- Returns workflow name + TodoWrite plan
- Hardcoded workflow logic in agent prompt

**Problems:**
- Workflows not version-controlled or composable
- Can't visualize workflow dependencies
- Can't reuse workflow fragments
- Hydrator logic mixed with workflow definitions

### Desired (Composable Workflow System)

**Workflow Storage:**
```
workflows/
  feature-dev.md           # Feature development workflow
  spec-review.md           # Spec → critic loop
  tdd-cycle.md             # Test-driven development
  qa-demo.md               # QA verification demo

AXIOMS.md                  # Immutable principles (P# references)
HEURISTICS.md              # Practical patterns (H# references)
WORKFLOWS.md               # Index of all workflows
```

**Workflow Format (YAML frontmatter + Markdown):**
```yaml
---
id: feature-dev
title: Feature Development Workflow
type: workflow
category: development
dependencies: []
steps:
  - id: user-story
    name: Define User Story
    workflow: null
    description: Gather user story with examples
  - id: acceptance-criteria
    name: Extract Acceptance Criteria
    workflow: null
    description: Define what constitutes success
  - id: spec-review
    name: Spec Review Loop
    workflow: [[spec-review]]  # Compose other workflow
    description: Design spec with critic feedback
  - id: approval
    name: Human Approval
    workflow: null
    description: Get user sign-off on approach
  - id: tdd
    name: Test-Driven Development
    workflow: [[tdd-cycle]]
    description: Implement with tests first
  - id: qa-demo
    name: QA Demo Test
    workflow: [[qa-demo]]
    description: Independent verification
---

# Feature Development Workflow

## Overview
Systematic feature development with user stories, spec review, TDD, and QA verification.

## When to Use
- Adding new features
- Complex modifications affecting multiple files
- Work requiring architectural decisions

## Steps

### 1. Define User Story
[Detailed instructions for gathering user story...]

### 2. Extract Acceptance Criteria
[Detailed instructions for defining success criteria...]

### 3. Spec Review Loop ([[spec-review]])
This step uses the [[spec-review]] workflow...

[Continue for each step...]
```

**Prompt Hydrator:**
- Reads workflow files from `workflows/` directory
- Composes workflows by resolving [[wikilinks]]
- Enriches with axioms (P#) and heuristics (H#) from index files
- Returns TodoWrite plan derived from workflow steps
- Logs workflow selection to bd for tracking

## Component Mapping

### What We Have (Existing)

| Component | Location | Status |
|-----------|----------|--------|
| bd issue tracking | `bd` CLI | ✅ Working |
| TodoWrite planning | Main agent | ✅ Working |
| Prompt hydrator | `aops-core:prompt-hydrator` | ✅ Working (needs workflow file support) |
| Axioms | `AXIOMS.md` | ✅ Exists (P# references) |
| Heuristics | `HEURISTICS.md` | ✅ Exists (H# references) |
| Vector memory | MCP server | ✅ Working ($ACA_DATA) |

### What We Need (New)

| Component | Location | Purpose |
|-----------|----------|---------|
| Workflow directory | `workflows/` | Store workflow YAML+Markdown files |
| Workflow index | `WORKFLOWS.md` | List all workflows with metadata |
| Workflow parser | Python utility | Parse YAML frontmatter + Markdown content |
| Wikilink resolver | Python utility | Resolve [[workflow-name]] references |
| Workflow compositor | In hydrator | Compose workflows from [[wikilinks]] |
| Workflow selector | In hydrator | Match prompt intent → workflow file |
| Issue decomposer | New agent? | Create bd issues from workflow steps |

## First Example: Feature Development Workflow

The feature-dev workflow will be the first implementation, using itself as the dogfooding example.

### Steps (from user specification):
1. User story - Gather user story with concrete examples
2. Acceptance criteria - Define what constitutes success
3. Spec → critic loop - Design spec, get critic review, iterate
4. Human approval - Get user sign-off on approach
5. TDD - Test-driven development implementation
6. QA demo test - Independent verification before completion

### Composition Example:
- `feature-dev.md` references `[[spec-review]]` for step 3
- `spec-review.md` defines the spec → critic iteration loop
- `feature-dev.md` references `[[tdd-cycle]]` for step 5
- `tdd-cycle.md` defines red-green-refactor loop
- Visual tools can render workflow dependencies as graph

## Design Principles

### Principle #1: Minimal Index Files
- Only 3 index files: `AXIOMS.md`, `HEURISTICS.md`, `WORKFLOWS.md`
- Everything else lives in `workflows/` directory
- Indexes are generated/maintained by audit tools

### Principle #2: [[Wikilinks]] for Composition
- Use `[[workflow-name]]` to reference other workflows
- Enables visual graph representation
- Simple, familiar syntax (no custom DSL)
- Works with existing wikilink tools (Obsidian, graph generators)

### Principle #3: YAML + Markdown Hybrid
- YAML frontmatter: structured metadata, step definitions
- Markdown body: human-readable instructions, context
- Version-controlled in git for auditability
- Easy to edit, review, and diff

### Principle #4: bd Issues as Work Units
- Each workflow step can become a bd issue
- Agents pick up issues and follow workflow steps
- Progress tracked in bd (status, assignee, dependencies)
- Work persistence across sessions

### Principle #5: Hydrator as Compositor
- Hydrator reads workflow files
- Resolves [[wikilinks]] recursively
- Enriches with axioms (P#) and heuristics (H#)
- Generates TodoWrite plan from composed workflow
- Returns discrete steps for agent execution

## Implementation Phases

### Phase 1: Foundation (This PR)
- [ ] Create `workflows/` directory
- [ ] Create `WORKFLOWS.md` index file
- [ ] Design feature-dev workflow file format
- [ ] Write `workflows/feature-dev.md` (first example)
- [ ] Update hydrator to read workflow files (basic)

### Phase 2: Composition
- [ ] Implement wikilink resolver utility
- [ ] Create `workflows/spec-review.md`
- [ ] Create `workflows/tdd-cycle.md`
- [ ] Create `workflows/qa-demo.md`
- [ ] Update hydrator to compose workflows

### Phase 3: Enrichment
- [ ] Integrate axioms (P#) into workflow selection
- [ ] Integrate heuristics (H#) into workflow steps
- [ ] Add context from vector memory ($ACA_DATA)
- [ ] Generate TodoWrite plans from composed workflows

### Phase 4: Decomposition
- [ ] Create issue decomposer agent/utility
- [ ] Auto-create bd issues from workflow steps
- [ ] Link issues with dependencies (bd dep add)
- [ ] Enable agents to pick up and execute issues

## Open Questions

1. **Workflow selection heuristics**: How does hydrator map prompt → workflow? (Pattern matching? LLM classification? Hybrid?)
2. **Issue granularity**: When should a workflow step become one vs multiple bd issues?
3. **Cross-workflow state**: How do we pass context between composed workflows?
4. **Workflow versioning**: How do we handle workflow changes across sessions? (Git history sufficient?)
5. **Workflow validation**: Should we validate workflow files on commit? (Pre-commit hook?)

## Success Metrics

- [ ] Feature-dev workflow successfully guides itself through implementation
- [ ] Workflow dependencies visible in graph visualization
- [ ] Hydrator selects correct workflow based on prompt intent (>90% accuracy)
- [ ] Workflow steps decompose into bd issues correctly
- [ ] Agents can execute workflow-derived issues without confusion
- [ ] Workflow files easy to create, edit, and understand (developer UX)

## Next Steps

1. ✅ User story defined with examples
2. ✅ Acceptance criteria documented
3. → Get user approval on this spec design
4. → Create `workflows/` directory structure
5. → Implement first workflow file (feature-dev.md)
6. → Update hydrator to read workflow files
