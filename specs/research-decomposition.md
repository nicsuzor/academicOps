---
title: Research Project Decomposition
type: spec
status: draft
created: 2026-02-27
tags: [spec, research, decomposition, multi-agent, planning]
related: effectual-planning-agent, mcp-decomposition-tools-v2, non-interactive-agent-workflow-spec, polecat-swarms
---

# Research Project Decomposition

## Giving Effect

- (proposed) [[skills/research-decomposer/SKILL.md]] — Skill for iterative research decomposition
- (proposed) [[workflows/research-decompose.md]] — Workflow for the decomposition loop
- [[specs/effectual-planning-agent.md]] — Strategic planning agent (upstream dependency)
- [[specs/mcp-decomposition-tools-v2.md]] — Task graph data tools (reused)
- [[specs/non-interactive-agent-workflow-spec.md]] — Phase 1 decomposition protocol (extended)

## Motivation: The Gist Pattern

This spec is inspired by [LuD1161's Codex-Review skill](https://gist.github.com/LuD1161/84102959a9375961ad9252e4d16ed592), which implements an **iterative multi-agent review loop**:

1. Claude creates an implementation plan
2. Submits it to Codex for structured review
3. Codex returns `VERDICT: APPROVED` or `VERDICT: REVISE` with specific feedback
4. Claude revises the plan based on feedback (max 5 rounds)
5. Session resumption preserves context across rounds

The core insight: **a second agent reviewing a decomposition catches blind spots, missing assumptions, and structural problems that the decomposing agent can't see in its own output.** This is especially valuable for research, where unexamined assumptions are the primary failure mode.

## User Story

**As** an academic researcher with ADHD managing multiple research projects,
**I want** to decompose a high-level research question or project idea into a structured task graph through an iterative, multi-agent refinement process,
**So that** I get a realistic, dependency-aware work plan that surfaces hidden assumptions, identifies what I don't know, and tells me what to do next — without requiring me to hold the whole project in my head.

> **Coherence check**: Research decomposition is the highest-leverage activity for an academic. A well-decomposed project reveals what's actually hard, what can be parallelised, and what information you need before committing resources. This serves the core academicOps mission: externalise cognitive load so the researcher can focus on thinking, not planning.

## The Problem

### Why research decomposition is hard

Research projects fail for different reasons than software projects:

| Software failure mode | Research failure mode |
| --- | --- |
| Wrong architecture | Wrong question |
| Missing requirements | Unexamined assumptions |
| Scope creep | Scope collapse (question too narrow for contribution) |
| Integration bugs | Methodology doesn't match question |
| Tech debt | Citation debt (building on work you haven't read) |

Existing task decomposition (Phase 1 of [[non-interactive-agent-workflow-spec]]) targets PR-sized code tasks. Research needs different decomposition primitives:

- **Information spikes** before you can plan (literature search, pilot data, ethics check)
- **Non-linear dependencies** (findings reshape methodology; methodology shapes what literature matters)
- **Varying time horizons** (a literature review takes weeks; coding an analysis takes hours)
- **Collaboration gates** (co-author review, supervisor approval, ethics board, peer review)
- **Multiple artifact types** (literature reviews, methodology documents, datasets, analysis scripts, manuscripts, presentations)

### Why a single agent isn't enough

A single agent decomposing a research project will:

- Assume familiarity with the field (skip literature gaps)
- Under-specify methodology (gloss over analytical choices)
- Miss ethical considerations (data handling, consent, IRB)
- Produce a plan that looks complete but has load-bearing assumptions buried in it
- Default to a linear waterfall when the work is actually iterative

The iterative review pattern fixes this by adding a **methodological critic** that challenges each decomposition round.

## Design

### Architecture: Iterative Decomposition Loop

Adapted from the Codex-Review gist pattern, but specialised for research:

```
┌─────────────────────────────────────────────────────────┐
│                   User provides:                         │
│   Research question / project idea / grant brief /       │
│   half-formed hypothesis / "I want to study X"           │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   DECOMPOSER agent     │
              │   (effectual-planner)  │
              │                        │
              │  1. Gather context     │
              │  2. Identify unknowns  │
              │  3. Propose structure  │
              │  4. Emit task graph    │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │   REVIEWER agent       │
              │   (research-critic)    │
              │                        │
              │  Evaluates:            │
              │  - Assumptions         │
              │  - Methodology fit     │
              │  - Missing literature  │
              │  - Feasibility         │
              │  - Ethics              │
              │  - Dependency gaps     │
              │                        │
              │  Returns:              │
              │  VERDICT: APPROVED     │
              │     or                 │
              │  VERDICT: REVISE       │
              │  + specific feedback   │
              └───────────┬────────────┘
                          │
                ┌─────────┴──────────┐
                │                    │
             APPROVED             REVISE
                │                    │
                ▼                    ▼
        ┌──────────────┐    ┌──────────────┐
        │ Present to   │    │ Decomposer   │
        │ researcher   │    │ revises plan │
        │ for approval │    │ (max 5 rounds│
        └──────────────┘    │  total)      │
                            └──────┬───────┘
                                   │
                                   └──▶ (back to REVIEWER)
```

### Why Two Agents, Not One

The decomposer and reviewer are separate agents for the same reason academic peer review separates author from reviewer:

- **Different optimisation targets.** The decomposer optimises for completeness ("did I capture everything?"). The reviewer optimises for rigour ("is this actually sound?").
- **Assumption surfacing.** The decomposer makes assumptions to make progress. The reviewer's job is to find them.
- **Adversarial improvement.** The decomposer can't effectively critique its own output — it'll defend its choices rather than probe them.

### Research-Specific Decomposition Primitives

Standard task types (task, action, bug, feature) don't capture research work. The decomposer uses these primitives:

| Primitive | Purpose | Example |
| --- | --- | --- |
| **spike** | Resolve an unknown before planning further | "Search for existing validated instruments measuring X" |
| **lit-review** | Systematic examination of existing work | "Map the landscape of Y research since 2020" |
| **methodology** | Design and justify analytical approach | "Choose between case study and survey methodology" |
| **ethics** | IRB, consent, data governance | "Draft ethics application for participant interviews" |
| **data-collection** | Gathering primary or secondary data | "Scrape court decisions from database Z" |
| **analysis** | Running the actual analysis | "Fit regression model with controls for A, B, C" |
| **writing** | Manuscript, presentation, or report | "Draft methods section for journal X" |
| **pilot** | Small-scale test of feasibility | "Interview 3 participants to test protocol" |
| **collaboration** | Gate requiring another person's input | "Get supervisor feedback on research design" |

These map to existing task types: `spike` → `learn`, `lit-review` → `learn`, `methodology` → `task`, `ethics` → `task` with `gate: true`, etc. The primitives are semantic labels for the decomposer, not new infrastructure.

### Decomposer Agent Prompt

The decomposer (effectual-planner with research context) follows this structure:

```markdown
## Input

You are decomposing a research project. The researcher has provided:
{user_input}

## Context Gathering

Before decomposing, gather:
1. Existing tasks in this project (via get_decomposition_context)
2. Related work in the knowledge base (via memory search)
3. Researcher's existing expertise/publications (if available)

## Decomposition Rules

1. **Start with unknowns.** List what you DON'T know before listing what to do.
   Every unknown becomes a spike or pilot task.

2. **Assumptions are first-class.** Every assumption gets:
   - A confidence level (high / medium / low / untested)
   - A validation method (what would prove this wrong?)
   - A dependency link (what breaks if this assumption fails?)

3. **Information spikes before commitment.** If you're unsure whether
   an approach will work, the first task is always a spike to find out.
   Never plan 10 tasks downstream of an untested assumption.

4. **Non-linear dependencies.** Research isn't a waterfall. Use:
   - `depends_on` for hard blocks ("can't analyse without data")
   - `soft_depends_on` for informational ("lit review informs methodology
     but methodology can proceed with provisional choices")
   - `informs` for reverse flow ("pilot findings reshape main study design")

5. **Collaboration gates.** Any step requiring another person's input or
   approval is a separate task with `assignee` set and `gate: true`.

6. **Time horizon awareness.** Label each task with estimated duration
   class: hours, days, weeks, months. This prevents mixing granularities
   (don't put "read one paper" next to "complete literature review").

7. **Artifact-aware.** Each task should specify its output artifact:
   document, dataset, code, presentation, submission, or decision.
```

### Reviewer Agent Prompt

The reviewer (research-critic) evaluates decompositions against these criteria:

```markdown
## Review Criteria

Evaluate the decomposition proposal against each criterion.
For each, give: PASS, CONCERN (with explanation), or BLOCK (with explanation).

### 1. Assumption Hygiene
- Are all load-bearing assumptions identified?
- Does each assumption have a validation path?
- Are there hidden assumptions in the methodology choices?
- Is the research question itself an assumption that needs validation?

### 2. Methodological Coherence
- Does the methodology match the research question?
- Are the analytical methods appropriate for the data type?
- Is there a clear link from research question → data → analysis → answer?
- Are alternative methodological approaches acknowledged?

### 3. Literature Awareness
- Is the literature review scoped appropriately (not too broad, not too narrow)?
- Are obvious related fields or adjacent literatures missing?
- Is the researcher building on established work or reinventing?
- Are there key papers/authors that should be consulted early?

### 4. Feasibility
- Are time estimates realistic for an academic (not a full-time researcher)?
- Are data access assumptions validated (can you actually get this data)?
- Are required skills available or do they need to be acquired?
- Is the scope achievable within the stated timeframe?

### 5. Ethics and Governance
- If human subjects: is IRB/ethics review planned?
- If sensitive data: is data governance addressed?
- If collaborative: are authorship and contribution expectations clear?
- Are any legal or regulatory constraints identified?

### 6. Dependency Structure
- Are there circular dependencies?
- Are there long sequential chains that could be parallelised?
- Are information spikes placed BEFORE the decisions they inform?
- Are collaboration gates realistically sequenced?

### 7. Scope and Contribution
- Is the research question specific enough to answer?
- Is it broad enough to constitute a contribution?
- Are "nice to have" extensions separated from core work?
- Is there a minimum viable contribution if time runs out?

## Verdict Format

VERDICT: APPROVED
  or
VERDICT: REVISE

If REVISE, provide:
- Which criteria triggered REVISE (cite numbers above)
- Specific changes needed (not vague suggestions)
- Priority order (what to fix first)
```

### Output Format

The decomposition produces a structured proposal appended to the project task body:

```markdown
## Research Decomposition v{iteration}

### Research Question
{refined statement of the research question}

### Contribution Claim
{what new knowledge this research would produce}

### Assumptions (load-bearing)

| # | Assumption | Confidence | Validation | If Wrong |
|---|-----------|-----------|-----------|----------|
| A1 | Sufficient court decisions exist in database Z | medium | spike-1 | Pivot to qualitative approach |
| A2 | Variable X is measurable via survey | low | pilot-1 | Need alternative instrument |

### Task Graph

| ID | Type | Title | Depends On | Duration | Artifact | Assignee |
|----|------|-------|-----------|----------|----------|----------|
| spike-1 | spike | Verify data availability in database Z | - | days | decision | bot |
| lit-1 | lit-review | Map regulatory scholarship on topic Y | - | weeks | annotated bibliography | nic |
| method-1 | methodology | Choose between case study and survey | spike-1, lit-1 | days | methods document | nic |
| ethics-1 | ethics | Draft ethics application | method-1 | weeks | ethics submission | nic |
| pilot-1 | pilot | Test survey instrument with 5 participants | ethics-1 | weeks | pilot report | nic |
| data-1 | data-collection | Administer full survey | pilot-1 | months | dataset | nic |
| analysis-1 | analysis | Fit regression models | data-1 | days | analysis code + results | bot |
| write-1 | writing | Draft manuscript | analysis-1 | weeks | manuscript draft | nic |

### Dependency Graph (visual)

spike-1 ──→ method-1 ──→ ethics-1 ──→ pilot-1 ──→ data-1 ──→ analysis-1 ──→ write-1
               ↑                                                    ↑
lit-1 ─────────┘                                           lit-1 (soft: informs framing)

### Information Spikes (must resolve first)

- [ ] spike-1: Can we access sufficient data from database Z?
  - If NO: pivot to qualitative case study approach (re-decompose from method-1)
  - If YES: proceed with quantitative design

### Minimum Viable Contribution

If time/resources constrained, the minimum publishable output is:
{what subset of the work produces a standalone contribution}

### Review History

| Round | Verdict | Key Feedback | Changes Made |
|-------|---------|-------------|--------------|
| 1 | REVISE | Missing ethics gate; methodology choice unjustified | Added ethics-1; added method-1 with alternatives |
| 2 | APPROVED | — | — |
```

## Execution Modes

The decomposition can run in two modes:

### Mode 1: Local (Interactive)

The researcher invokes the decomposition in a Claude Code session:

```
User: "I want to study how platform governance affects content moderation outcomes.
       Decompose this into a research plan."

→ Hydrator selects: workflows/research-decompose.md
→ Decomposer agent gathers context, proposes decomposition
→ Reviewer agent evaluates, returns VERDICT
→ Loop until APPROVED (or max 5 rounds)
→ Present final decomposition to researcher
→ On approval: create tasks in task graph via MCP
```

This is the default mode. The decomposition happens within a single session. The researcher sees each iteration and can intervene ("actually, I already have ethics approval" / "ignore that dependency, I have the data").

### Mode 2: GitHub-Coordinated (Async)

For multi-author projects or when the researcher wants to review asynchronously:

```
1. Researcher creates a GitHub issue with the research question
   (or an agent creates it from a conversation)

2. Decomposer agent runs (via polecat or GitHub Actions):
   - Reads the issue body
   - Produces decomposition proposal
   - Posts as issue comment

3. Reviewer agent runs:
   - Reads the decomposition comment
   - Posts review as reply with VERDICT

4. If REVISE: decomposer revises and posts updated proposal
   Loop continues in issue comments (max 5 rounds)

5. If APPROVED: researcher reviews in the issue thread
   - Approves → tasks created (as sub-issues or local task files)
   - Requests changes → another round
   - Closes → abandoned
```

GitHub mode is better when:
- Multiple collaborators need to review the decomposition
- The researcher wants to review asynchronously (not in a live session)
- The project spans multiple repos or codebases
- An audit trail of decomposition decisions is important

### Recommendation: Local-First

Start with Mode 1 (local). GitHub coordination adds ceremony that's only justified for multi-author projects. The task graph (stored in markdown) already provides an audit trail. GitHub mode can be added later if needed.

## Integration with Existing Framework

### Reusing What Exists

| Component | Reuse | Notes |
| --- | --- | --- |
| Effectual planner | Decomposer agent personality | Add research-specific decomposition rules |
| Critic skill | Reviewer agent personality | Specialise review criteria for research |
| Task MCP | Task creation after approval | Map research primitives → existing task types |
| Prompt hydration | Workflow selection | Add `research-decompose` workflow |
| Task graph | Dependency tracking | Already supports `depends_on` and `soft_depends_on` |
| Polecat | GitHub-mode execution | Workers can run decomposer/reviewer |

### New Components Needed

| Component | Type | Purpose |
| --- | --- | --- |
| `workflows/research-decompose.md` | Workflow | Route for research decomposition requests |
| `skills/research-decomposer/SKILL.md` | Skill | Decomposer agent prompt with research rules |
| Research reviewer prompt | Embedded in skill | Review criteria (section above) |
| Research primitives mapping | Config | Map spike/lit-review/etc. to task types+tags |

### What We're NOT Building

- No new MCP tools (use existing task tools)
- No new task types in the schema (use tags for research primitives)
- No external integrations (Zotero, Overleaf) — those exist separately
- No automated literature search (that's a separate skill/tool concern)
- No project management dashboard (the task map handles this)

## Acceptance Criteria

### Success Criteria (ALL must pass)

1. [ ] Given a research question, the system produces a structured decomposition with tasks, dependencies, assumptions, and information spikes
2. [ ] The decomposition includes at least one round of automated review that catches at least one issue (missing assumption, methodology gap, or feasibility concern) in the initial proposal
3. [ ] The review loop terminates in ≤5 rounds with either APPROVED or a clear explanation of unresolved concerns
4. [ ] Approved decompositions can be committed to the task graph via existing MCP tools without manual reformatting
5. [ ] Each assumption in the decomposition has a confidence level and validation path
6. [ ] The decomposition identifies a minimum viable contribution (what's publishable if everything else falls away)

### Failure Modes (If ANY occur, implementation is WRONG)

1. [ ] Decomposition produces a generic linear waterfall (literature → method → data → analysis → write) without project-specific structure
2. [ ] Assumptions are listed but have no validation path or dependency links
3. [ ] Information spikes are placed AFTER the decisions they should inform
4. [ ] The reviewer rubber-stamps every proposal without substantive feedback
5. [ ] The loop runs all 5 rounds without converging (indicates criteria are too strict or prompts are misaligned)
6. [ ] Tasks are created at wildly different granularities (mixing "read one paper" with "complete PhD")

## Open Questions

1. **Reviewer model selection.** Should the reviewer be the same model as the decomposer (like the gist's Claude→Codex pattern), or the same model with a different prompt? Using a different model (e.g., decomposer=sonnet, reviewer=opus) adds genuine perspective diversity but costs more. Using the same model with a different prompt is cheaper but risks the reviewer being too sympathetic to the decomposer's framing.

2. **Domain expertise injection.** How much domain context should the reviewer have? A generic methodological review is useful but shallow. A domain-specific review (e.g., "you're studying platform governance, have you considered Gorwa et al.'s framework?") is much more valuable but requires either RAG over the researcher's library or web search. Start generic, add domain context via Zotero MCP if available?

3. **When to decompose vs. when to just start.** Not every research idea needs formal decomposition. A quick literature scan doesn't need a 5-round review loop. Heuristic: if the project spans >1 month or involves >1 person, decompose. Otherwise, just create tasks directly. Should this be enforced or advisory?

4. **Revision depth.** The gist uses max 5 rounds. Is this right for research? Research decomposition is harder than code planning — maybe allow more rounds but with a monotonically-decreasing concern count requirement (each round must resolve at least one concern, or the loop terminates with unresolved items surfaced to the researcher).

5. **GitHub coordination granularity.** If we build GitHub mode: should each task become a GitHub issue (heavy but collaborative), or should the task graph stay local with only the decomposition proposal living in GitHub (lighter)?

## Related

- [[effectual-planning-agent]] — Strategic planning philosophy that informs this spec
- [[non-interactive-agent-workflow-spec]] — Phase 1 decomposition protocol this extends
- [[mcp-decomposition-tools-v2]] — Data access tools for decomposition context
- [[polecat-swarms]] — Parallel execution for GitHub-mode agents
- [[collaborate-workflow]] — Relevant for multi-author decomposition sessions
- [[workflow-system-spec]] — Workflow routing and composition patterns
