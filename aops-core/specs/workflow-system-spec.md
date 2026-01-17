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
**I want** a composable workflow system where workflows are simple markdown files that LLMs can read and compose
**So that** I can systematically guide work through human-readable processes that are version-controlled, auditable, and continuously improvable

## Key Insight: LLM-Native Design

**Pre-LLM thinking**: Parse YAML frontmatter, deterministic ordering, structured data

**LLM thinking**:
- Workflows are markdown written for humans to read
- LLMs are smart - they can read, understand, and compose workflows themselves
- No need for deterministic code or complex parsing
- [[Wikilinks]] work because the LLM reads the referenced file and understands it
- Simple > Structured

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

1. ✅ Workflows stored as simple markdown in git (e.g., `workflows/feature-dev.md`)
2. ✅ Index files exist: `AXIOMS.md`, `HEURISTICS.md`, `WORKFLOWS.md`
3. ✅ Workflows can reference other workflows using `[[workflow-name]]` syntax
4. ✅ Hydrator (LLM) reads and understands workflows without parsing
5. ✅ Hydrator composes workflows by reading referenced files inline
6. ✅ Workflows decompose into mid-grained bd issues (not every git command)
7. ✅ Agents can pick up bd issues and follow workflow guidance
8. ✅ Visual graph representation shows workflow dependencies (via wikilink tools)

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

**Workflow Format (Simple Markdown):**
```markdown
# Feature Development Workflow

Full TDD feature development with critic review and QA verification.

## When to Use

- Adding new features
- Complex modifications affecting multiple files
- Work requiring architectural decisions

## Steps

### 1. Claim work in bd

Find or create a bd issue and mark it in-progress:
```bash
bd ready                    # Find available work
bd update <id> --status=in_progress
```

### 2. Define acceptance criteria

What constitutes success for this feature?
- Specific, verifiable conditions
- What functionality must work?
- What tests must pass?

### 3. Create a plan

Design the implementation approach and document it in the bd issue.

### 4. Get critic review

Follow the [[spec-review]] workflow to get critic feedback on your plan before implementing.

### 5. Implement with TDD

Follow the [[tdd-cycle]] workflow:
- Write failing tests
- Minimal implementation
- Refactor
- Repeat until complete

### 6. Verify with QA

Follow the [[qa-demo]] workflow for independent verification before completing.

### 7. Land the changes

Format, commit, and push:
```bash
./scripts/format.sh
git add -A
git commit -m "..."
git push
bd close <id>
```

## Success Criteria

- All acceptance criteria met
- All tests pass
- QA verifier approves
- Changes pushed to remote
```

**Key points**:
- Human-readable markdown
- References other workflows with [[wikilinks]]
- LLM reads and understands it
- No parsing needed

**Prompt Hydrator (LLM-Native Composition):**
- Reads WORKFLOWS.md to select appropriate workflow
- Reads the selected workflow file (e.g., `workflows/feature-dev.md`)
- When it sees `[[spec-review]]`, reads `workflows/spec-review.md` inline
- **Composes by understanding**: LLM reads all referenced workflows and generates a unified TodoWrite plan
- No parsing - just reads markdown and understands it
- Returns TodoWrite plan with mid-grained tasks (not every git command)
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
| Workflow directory | `workflows/` | Store simple markdown workflow files |
| Workflow index | `WORKFLOWS.md` | List all workflows with decision tree |
| Workflow compositor | In hydrator (LLM) | Read and compose workflows by understanding markdown |
| Workflow selector | In hydrator (LLM) | Match prompt intent → workflow file |

**What we DON'T need**:
- ❌ Workflow parser (LLM reads markdown directly)
- ❌ Wikilink resolver utility (LLM reads referenced files)
- ❌ Issue decomposer agent (hydrator generates TodoWrite at appropriate granularity)

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

### Principle #0: Skills vs Workflows

**Skills** and **Workflows** serve fundamentally different purposes:

| Aspect | Skills | Workflows |
|--------|--------|-----------|
| **Purpose** | HOW to do a known thing | WHAT to do (sequence of steps) |
| **Nature** | Fungible instructions | Composable chains |
| **Examples** | Create a PDF, generate a mindmap, format code | Feature development, debugging, TDD cycle |
| **Reusability** | Interchangeable - any skill can be swapped for another that does the same thing | Compositional - workflows reference other workflows |
| **Invocation** | Direct: `Skill(skill="pdf")` | Selected by hydrator based on intent |

**Key insight**: Skills are the building blocks (the "how"); workflows orchestrate them into coherent processes (the "what"). A workflow might use multiple skills, but a skill never contains a workflow.

### Principle #1: LLM-Native Design
- **Workflows are markdown for humans** - not structured data for parsers
- **LLMs read and understand** - no parsing logic needed
- **Composition by comprehension** - LLM reads [[spec-review]] and understands it
- **Simple > Structured** - optimize for human editing and LLM understanding

### Principle #2: [[Wikilinks]] for Composition
- Use `[[workflow-name]]` to reference other workflows
- LLM sees the link and reads the referenced file
- **Inline expansion**: Hydrator reads all referenced workflows and generates unified plan
- Enables visual graph representation
- Works with existing wikilink tools (Obsidian, graph generators)

### Principle #3: Human-Readable Markdown
- Written for humans first, LLMs second
- Clear explanations, not just commands
- Code examples where helpful
- Easy to edit, review, and understand
- Version-controlled in git for auditability

### Principle #4: Mid-Grained bd Issues
- **bd issues are mid-grained tasks** - not every git command
- A task can include a list: "format, commit, push" without each being separate
- If a list item needs expansion → make it a subtask/new issue
- Example good granularity: "Implement user authentication" with steps like "create model, add JWT, write tests"
- Example too fine: separate issues for "git add", "git commit", "git push"

### Principle #5: Hydrator as Intelligent Compositor
- Reads WORKFLOWS.md to select workflow
- Reads selected workflow file
- When it sees [[wikilink]], reads that file too
- **Composes by understanding the content** - not by parsing structures
- Generates TodoWrite plan at appropriate mid-grained level
- Returns unified plan that includes all workflow guidance

## Implementation Phases

### Phase 1: Foundation ✓ COMPLETED
- [x] Create `workflows/` directory
- [x] Create `WORKFLOWS.md` index file
- [x] Write workflow files as simple markdown (feature-dev, spec-review, tdd-cycle, qa-demo, minor-edit, debugging, batch-processing, simple-question, direct-skill)
- [x] Update hydrator to read WORKFLOWS.md and select workflows
- [x] Update hydrator to read workflow files
- [x] Add tests for workflow file structure

**Status**: ✓ COMPLETED

### Phase 2: LLM-Native Composition ✓ COMPLETED
- [x] **Simplify existing workflow files** - Remove YAML frontmatter, keep simple markdown
- [x] Update hydrator instructions: "When you see [[spec-review]], read workflows/spec-review.md"
- [x] **Inline expansion by understanding**: Hydrator reads all referenced workflows and generates unified TodoWrite plan
- [x] Updated tests to verify minimal frontmatter (id, category only)
- [x] Updated WORKFLOWS.md to reflect simplified structure
- [ ] Test composition in practice: Does feature-dev correctly expand [[spec-review]], [[tdd-cycle]], [[qa-demo]]? (To be validated in actual usage)
- [ ] Verify TodoWrite plans are mid-grained (not every git command) (To be validated in actual usage)

**Key insight**: No code needed - just update hydrator instructions and simplify workflow files. ✓ Confirmed.

### Phase 3: Enrichment (FUTURE)
- [ ] Integrate axioms (P#) references into workflow files
- [ ] Integrate heuristics (H#) references into workflow files
- [ ] Hydrator naturally includes these when reading workflows
- [ ] Add vector memory context to hydration process

**Key insight**: Enrichment happens naturally - LLM reads axioms/heuristics references and understands them.

### Phase 4: Mid-Grained bd Issues (FUTURE)
- [ ] Document bd issue granularity guidelines
- [ ] Update hydrator to generate mid-grained TodoWrite plans
- [ ] Hydrator creates bd issues for multi-session work
- [ ] Tasks include lists of steps (not separate issues per step)

**Key insight**: No decomposer agent needed - hydrator judges appropriate granularity.

## Open Questions

1. **Workflow selection**: How does hydrator map prompt → workflow?
   - **Answer**: LLM reads WORKFLOWS.md decision tree and selects based on understanding user intent

2. **bd issue granularity**: When is a task too fine-grained?
   - **Guideline**: If it's a single command or < 30 seconds of work, include it in a list on another task
   - **Guideline**: If it needs decision-making or > 5 minutes, make it a separate task
   - **Examples**: "git push" = list item. "Implement JWT auth" = separate task.

3. **Composition depth**: How deep do [[wikilink]] references go?
   - **Current**: We have 2-level depth (feature-dev → spec-review, tdd-cycle, qa-demo)
   - **Future**: Should we support deeper nesting? (Probably not needed)

4. **Workflow versioning**: How do we handle workflow changes across sessions?
   - **Answer**: Git history is sufficient - workflows evolve like any other documentation

5. **Minimal YAML**: Do we need ANY frontmatter?
   - **Proposal**: Optional minimal frontmatter for metadata only: `id`, `category` (no steps, no structure)
   - **Reason**: Enables tooling (search, graph visualization) without dictating structure

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
