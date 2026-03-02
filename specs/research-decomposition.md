---
title: Conceptual Review and Research Decomposition
type: spec
status: draft
created: 2026-02-28
supersedes: PR #648
tags: [spec, review, research, decomposition, multi-agent, planning]
related:
  - effectual-planning-agent
  - non-interactive-agent-workflow-spec
  - mcp-decomposition-tools-v2
  - polecat-swarms
---

# Conceptual Review and Research Decomposition

## Giving Effect

_No implementation yet. This spec defines two separable layers:_

- (proposed) General conceptual review workflow (Layer 1)
- (proposed) Research decomposition application (Layer 2)
- [[specs/effectual-planning-agent.md]] -- upstream dependency (strategic planning under uncertainty)
- [[specs/mcp-decomposition-tools-v2.md]] -- task graph tools (reused)
- [[specs/non-interactive-agent-workflow-spec.md]] -- Phase 1 decomposition protocol (extended)

## Motivation

### The gist pattern

Inspired by [LuD1161's Codex-Review skill](https://gist.github.com/LuD1161/84102959a9375961ad9252e4d16ed592): an iterative multi-agent review loop where a second agent provides structured critique of a first agent's output. The pattern works for code review because a reviewer with different optimisation targets catches what the author misses.

### Two insights from dogfooding

When we used a structured 5-pass review to evaluate the first draft of this spec (PR #648), two things became clear:

1. **The highest-value review question was universal.** "Does this spec practice what it preaches?" applies to any intellectual artifact, not just research plans. A general-purpose conceptual review workflow is more useful than a research-specific one.

2. **The same pattern serves many domains.** Spec review, manuscript review, grant proposals, design documents, and research decomposition are all instances of structured multi-agent critique with domain-specific lenses. The general pattern should be specified once and instantiated per domain.

This spec therefore defines two layers: a **general conceptual review workflow** (Layer 1) and a **research decomposition application** (Layer 2) that instantiates it.

## The User

A researcher with multiple active projects and limited working memory. They might be starting from a vague idea ("I want to study how platform governance affects content moderation outcomes") or refining an existing project plan. They need a thinking partner that catches what they miss -- hidden assumptions, methodology gaps, missing literature -- without forcing ceremony on exploratory work. When it works, it feels like a conversation with a rigorous collaborator. When it fails, it feels like submitting to a committee.

## User Stories

**US-1: Early exploration (Seedling)**
A researcher has a half-formed idea and wants to know if it's worth pursuing. They throw it at the system and get back a sketch: what's interesting, what's assumed, what they'd need to find out first. The system respects the idea's immaturity -- no formal task graphs, no time estimates. Just: "here's what you're betting on, and here's how you'd find out if you're right."

**US-2: Project planning (Forest)**
A researcher has a defined project and needs to decompose it into a realistic work plan. The system produces a dependency-aware task graph that surfaces hidden assumptions, identifies knowledge gaps, and sequences work so that cheap information-gathering precedes expensive commitments. A second agent reviews the plan for methodological soundness, flagging concerns the decomposer missed.

**US-3: Spec or document review**
A framework contributor has written a spec, design doc, or manuscript draft. They want structured feedback that goes beyond surface editing: does the argument hold together? Does it contradict existing work? Does it practice what it preaches? The system applies relevant review lenses and returns prioritised, actionable critique.

> **Coherence check**: This serves the core academicOps mission -- externalise cognitive load so the researcher can focus on thinking, not planning. The general review layer also serves the framework's self-reflexive architecture: using the system to improve the system.

## Layer 1: Conceptual Review Workflow

A general-purpose iterative review pattern for intellectual artifacts. Not research-specific.

### Composable Lens Registry

Instead of a fixed set of review criteria, the reviewer selects from a registry of **review lenses** based on artifact type. Each lens is a focused evaluation perspective with a core question.

| Lens                        | Applies to         | Core question                                         |
| --------------------------- | ------------------ | ----------------------------------------------------- |
| **Self-consistency**        | Everything         | Does it practice what it preaches?                    |
| Strategic alignment         | Specs, designs     | Does this fit the larger vision?                      |
| Assumption hygiene          | Plans, proposals   | Are load-bearing assumptions identified and testable? |
| Scope discipline            | Everything         | Is it building for now or for hypothetical futures?   |
| Cross-reference consistency | Specs, docs        | Does it contradict existing work?                     |
| Attribution                 | Intellectual work  | Is the intellectual debt acknowledged?                |
| Methodological coherence    | Research, analysis | Does the method match the question?                   |
| Literature awareness        | Research, academic | Is it building on or reinventing existing work?       |
| Ethics and governance       | Research, data     | Are ethical obligations addressed?                    |
| Feasibility                 | Plans, proposals   | Can this actually be done with available resources?   |

**Design principles:**

- A given review selects **3-4 lenses**, not all of them. Breadth kills depth.
- **Self-consistency is always on.** It was the single most productive lens in our initial dogfooding (PR #648). However, subsequent dogfooding (issue #676) found that the _primary_ lens shifts by review pass: Pass 1's most productive lens was axiom compliance + strategic alignment ("should we build this?"), while Pass 2's was assumption hygiene ("can we build this correctly?"). Self-consistency remains always-on as a background check, but the primary lens should be selected based on the review's current phase.
- Lenses compose by domain. Research reviews use methodological coherence + literature awareness + ethics. Spec reviews use strategic alignment + cross-reference consistency + scope discipline. The registry is extensible.

### Prioritised Critique Protocol

The reviewer does not evaluate all selected lenses exhaustively. Instead:

> Lead with your single most important concern. Explain why it matters and what breaks if it's not addressed. Then list up to 2 secondary concerns. Stop.

This forces the reviewer to **rank** rather than mechanically evaluate, giving the author a clear revision target instead of a wall of feedback. It also mitigates the rubber-stamping failure mode: a reviewer required to name its top concern is more likely to engage deeply with one issue than to superficially address seven.

### Convergence

The review loop converges by **resolution**, not by counting rounds:

- Each round must resolve at least one concern from the previous round.
- If a round introduces new concerns without resolving old ones, escalate to the human.
- If all raised concerns are resolved or explicitly overridden, the review is **APPROVED**.
- A soft safety cap (e.g. 7 rounds) prevents runaway loops, but it's a safety valve, not a design target.

### User Override

The researcher or author can override any review concern with a reason:

> "I know this assumption is untested. I'm accepting the risk because [reason]."

The reviewer records the override and stops re-raising it. This respects researcher autonomy while maintaining an audit trail of accepted risks. Without this, the system becomes a gate rather than a collaborator.

### Formality Gradient

Three operating levels, selected by artifact complexity or user preference:

| Level        | Lenses                                 | Review loop                           | Venue                                | When to use                                              |
| ------------ | -------------------------------------- | ------------------------------------- | ------------------------------------ | -------------------------------------------------------- |
| **Light**    | 1-2 (always includes self-consistency) | Single pass, no iteration             | In-session or issue comment          | Quick checks, small changes, early exploration           |
| **Standard** | 3-4                                    | Convergence-based                     | Pull request                         | Most specs, plans, proposals                             |
| **Thorough** | 4+ (consider multi-model review)       | Convergence-based + explicit sign-off | Pull request with multiple reviewers | Foundational specs, grant applications, research designs |

This solves the formality gradient tension: a researcher typing "I want to study X" gets the light version. Formal decomposition uses the thorough version. The system does not force ceremony on exploratory work.

The venue column reflects a key insight from dogfooding (see Orchestration below): the review loop's orchestration problem -- who goes next, what's resolved, when to re-engage -- is already solved by GitHub's PR review system when the artifact is a document in a pull request.

### Why Two Agents, Not One

The decomposer/author and reviewer are separate roles for the same reason academic peer review separates author from reviewer:

- **Different optimisation targets.** The author optimises for completeness ("did I cover everything?"). The reviewer optimises for rigour ("is this actually sound?").
- **Assumption surfacing.** The author makes assumptions to make progress. The reviewer's job is to find them.
- **Adversarial improvement.** An agent cannot effectively critique its own output -- it defends its choices rather than probing them.

This is the core thesis of the gist pattern. It remains an assumption: LLMs reviewing their own species' output may share systematic blind spots. The value must be validated empirically (see Assumptions, below).

### Orchestration: Docs as Code

The review workflow needs orchestration: who goes next, what concerns are open, when to re-engage after revisions. Rather than building custom state tracking, the workflow treats **reviewable artifacts as documents in pull requests** and delegates orchestration to GitHub's native review system.

**The principle**: Knowledge work artifacts (specs, proposals, research plans, manuscripts) are documents. Documents live in the repository. Changes to documents are proposed via pull requests. Pull requests have a built-in review system with state tracking, notifications, and convergence detection. Therefore: the review loop's orchestration is already solved.

**What GitHub provides natively**:

- **State machine**: PR review status (changes requested → approved)
- **Notifications**: Author is notified on review; reviewer is notified on new commits
- **Decision ledger**: Review comments with resolved/unresolved threading
- **Convergence detection**: All review threads resolved = ready to merge
- **Audit trail**: Commit history shows how the artifact evolved in response to review
- **Multi-reviewer support**: Multiple agents or humans can review the same PR with different lens selections

**What this replaces**: No custom labels, no state objects, no trigger protocols, no notification infrastructure. The review workflow specifies _how to review_ (lenses, critique protocol, convergence rules). GitHub handles _when and where_.

**Venue selection by formality** (see Formality Gradient above):

- **Light**: In-session conversation or issue comment. No orchestration needed — the review is immediate and non-iterative.
- **Standard/Thorough**: The artifact is a file in a pull request. The reviewer submits a PR review using the critique protocol. The author pushes commits addressing concerns. The reviewer re-reviews. Merge = approved. GitHub handles the entire async loop.

**Issue vs. PR convention**: Issues describe problems. Pull requests propose solutions as documents. This separation keeps discussion (issue) distinct from the reviewable artifact (PR), and ensures the review system's machinery (diff view, line comments, review status) is available.

> **Dogfood evidence**: This section was added after applying the review workflow to issue #676 (Polecat Governor). The review content worked well (lenses surfaced real concerns, prioritised critique kept feedback focused). But the async orchestration broke down: there was no trigger to resume the review after the author responded, state was tracked ad-hoc in a PKB task body, and pass sequencing was improvised. Moving the reviewable artifact into a PR would have given us all of this for free.

## Layer 2: Research Decomposition

Everything below instantiates Layer 1 for the specific domain of academic research project planning.

### Why Research Decomposition is Hard

Research projects fail for different reasons than software projects:

| Software failure mode | Research failure mode                                 |
| --------------------- | ----------------------------------------------------- |
| Wrong architecture    | Wrong question                                        |
| Missing requirements  | Unexamined assumptions                                |
| Scope creep           | Scope collapse (question too narrow for contribution) |
| Integration bugs      | Methodology doesn't match question                    |
| Tech debt             | Citation debt (building on work you haven't read)     |

These failure modes are well-documented in research methods pedagogy. They motivate the research-specific review lenses (methodological coherence, literature awareness, ethics) and decomposition primitives below.

### Research-Specific Lenses

When reviewing research decompositions, Layer 1's lens registry is extended with:

- **Methodological coherence**: Does the method match the question? Are analytical choices justified?
- **Literature awareness**: Is the lit review scoped appropriately? Are key papers missing?
- **Ethics and governance**: Is IRB planned? Is data governance addressed?
- **Feasibility** (with academic constraints): Are time estimates realistic for academic timelines? Is data access validated?

A standard research decomposition review selects 3-4 of these plus self-consistency.

### Research Decomposition Primitives

Standard task types (task, action, bug, feature) do not capture research work. The decomposer uses these semantic primitives, mapped to existing types via tags:

| Primitive           | Purpose                                    | Maps to       |
| ------------------- | ------------------------------------------ | ------------- |
| **spike**           | Resolve an unknown before planning further | `learn`       |
| **lit-review**      | Systematic examination of existing work    | `learn`       |
| **methodology**     | Design and justify analytical approach     | `task`        |
| **ethics**          | IRB, consent, data governance              | `task` + gate |
| **data-collection** | Gathering primary or secondary data        | `task`        |
| **analysis**        | Running the actual analysis                | `task`        |
| **writing**         | Manuscript, presentation, or report        | `task`        |
| **pilot**           | Small-scale test of feasibility            | `task`        |
| **collaboration**   | Gate requiring another person's input      | `task` + gate |

No new task types or schema changes. Primitives are labels that carry semantic meaning for the decomposer and reviewer agents.

### Decomposition Rules

1. **Start with unknowns.** Every unknown becomes a spike or pilot. Information-gathering precedes commitment.
2. **Assumptions are first-class.** Every load-bearing assumption gets: confidence level, validation path, and contingency (what happens if wrong).
3. **Non-linear dependencies.** Research is iterative. Use `depends_on` for hard gates, `soft_depends_on` for informational dependencies where findings reshape downstream work. When an upstream soft dependency completes, propagate its findings to any downstream task whose scope or approach may be affected (knowledge-flow pattern from `aops-core/workflows/decompose.md`). The downstream task is not blocked — it proceeds with current knowledge — but should be revisited once upstream findings arrive.
4. **Collaboration gates.** Any step requiring human judgment or external input is a separate task marked as a gate.
5. **Artifact-aware.** Each task specifies its output type: document, dataset, code, presentation, decision.

### Output

The decomposition produces:

- **Assumptions table**: Load-bearing assumptions with confidence, validation path, and contingency
- **Task graph**: Dependency-aware graph using research primitives
- **Dependency visualisation**: Mermaid graph showing non-linear dependencies
- **Minimum viable contribution**: A narrative paragraph identifying the minimum publishable claim and the tasks required to substantiate it, with those tasks tagged `mvc: true` in the task graph. Purpose: prevents scope collapse by anchoring what the project is already committed to, even if ambition expands later

### Seedling vs. Forest

**Seedling mode** (maps to Layer 1's "light" level): Researcher has a vague idea. The system produces a sketch -- what's interesting, what's assumed, what to find out first. No task graph. No time estimates. Just assumptions and spikes.

**Forest mode** (maps to Layer 1's "standard" or "thorough" level): Researcher has a defined project. Full decomposer/reviewer loop. Produces structured task graph with dependencies, assumptions table, and visualisation.

The entry path is selected by the system based on input maturity, or explicitly by the researcher.

## Intellectual Foundations

- **Codex-Review pattern** (LuD1161): Iterative multi-agent loop for structured critique.
- **Effectual mapping** (Sarasvathy, 2001): Start with means, not goals. Bird-in-hand thinking.
- **Discovery-Driven Planning** (McGrath & MacMillan, 1995): Explicit assumption tracking, knowledge milestones, cheap validation before commitment.
- **Research methods pedagogy**: The reviewer criteria (assumption hygiene, methodological coherence, literature awareness, feasibility, ethics) draw on established research proposal review practices used by funding bodies and ethics boards. The contribution of this spec is applying them in an iterative multi-agent loop, not the criteria themselves.

## Assumptions About This Spec

Practising what we preach:

| #  | Assumption                                                                                         | Confidence                                                                          | Validation                                                                                                      | If wrong                                                                                                                                                                                                                                     |
| -- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1 | A second LLM agent reviewing catches blind spots a single agent misses                             | Medium                                                                              | Compare single-agent vs. two-agent decompositions on real projects                                              | Simplify to single-agent with self-review prompts                                                                                                                                                                                            |
| S2 | 3-4 lenses per review is the right number                                                          | Medium (N=1 from dogfooding)                                                        | Track which lenses produce actionable feedback across reviews                                                   | Adjust count; too few = reviews miss issues, too many = checklist problem                                                                                                                                                                    |
| S3 | Self-consistency is the highest-value _background_ lens; the _primary_ lens varies by review phase | Medium (N=2: PR #648 + issue #676)                                                  | Track which lens produces most actionable finding across reviews, stratified by pass                            | If no phase-dependence emerges, revert to fixed always-on lens                                                                                                                                                                               |
| S4 | Convergence by resolution terminates in reasonable time                                            | Medium                                                                              | Monitor round counts in practice                                                                                | Lower the soft cap threshold; treat persistent non-convergence as a signal of unresolvable disagreement requiring human escalation and redesign of the escalation protocol (a cap already exists at line 102 — adjust it, don't add another) |
| S5 | The general workflow (Layer 1) is more useful than the research-specific version alone             | Low                                                                                 | Build Layer 1 first; see if it gets reused for spec/manuscript review                                           | Collapse back to research-specific spec                                                                                                                                                                                                      |
| S6 | Researchers will use formal decomposition for complex projects                                     | Low                                                                                 | Track adoption; compare projects planned with/without the system                                                | Reduce friction or simplify; the system must feel like collaboration, not submission                                                                                                                                                         |
| S7 | GitHub PR review provides sufficient orchestration for the review loop                             | Medium (N=1: issue #676 dogfood identified the gap; PR-based review not yet tested) | Run a standard-level review entirely via PR review system; compare orchestration friction to issue-based review | Build lightweight custom orchestration (labels + state object) if PR review is too coarse for multi-pass conceptual review                                                                                                                   |

## Scope

### In scope

- General conceptual review workflow with composable lenses (Layer 1)
- Research project decomposition as domain application (Layer 2)
- Integration with existing effectual planner and task graph
- PR-based orchestration for standard/thorough reviews (docs-as-code convention)

### Out of scope

- New MCP tools or task schema changes
- Automated execution of decomposed tasks
- Multi-model review orchestration (desirable for thorough level, but not required for v1)

## Open Questions

1. **Domain expertise injection.** Without domain knowledge, the reviewer produces generic methodology feedback. How do we inject field-specific knowledge? (Literature search? User-provided context? Retrieval from Zotero library?)
2. **When to decompose.** Not every research idea needs formal decomposition. What heuristics determine when seedling mode is sufficient vs. when forest mode adds value?
3. **Reviewer model selection.** Same model reviewing its own species' output may share systematic blind spots. When does the thorough level warrant a different model?
4. **Integration with existing decompose workflow.** The `workflows/decompose.md` already handles task decomposition for software. How do the research primitives compose with the existing academic methodology layer?

## Future Work

- **Spec review workflow**: Layer 1 could be instantiated as a `spec-reviewer` agent, replacing the ad-hoc 5-pass review used on PR #648. With docs-as-code orchestration, this becomes a PR reviewer role alongside gatekeeper and custodiet.
- **Manuscript pre-submission review**: Layer 1 with literature + methodology + attribution lenses, applied to draft manuscripts before journal submission.
- **Lens effectiveness tracking**: Instrument which lenses produce the most actionable feedback, enabling evidence-based registry curation.
- **Multi-pass sequencing conventions**: Dogfooding suggests that multi-pass reviews (thorough level) benefit from sequencing lenses by phase — alignment/strategic concerns first, feasibility/assumption concerns second. Formalise pass ordering conventions based on accumulated evidence.

## Related

- [[effectual-planning-agent]] -- upstream; this spec specialises it for research
- [[non-interactive-agent-workflow-spec]] -- Phase 1 decomposition; this extends it with research primitives
- [[mcp-decomposition-tools-v2]] -- task graph tools; reused for structured output
- [[polecat-swarms]] -- execution layer; consumes decomposed task graphs
- [[aops-core/workflows/decompose.md]] -- existing general decomposition workflow; this spec adds iterative multi-agent review and research-specific primitives on top of it (see Open Questions §4 on composing with the academic methodology layer)
