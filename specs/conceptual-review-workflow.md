---
title: Conceptual Review Workflow
type: spec
status: active
tier: workflow
depends_on: [effectual-planning-agent]
created: 2026-02-28
tags: [spec, review, multi-agent, workflow]
related:
  - non-interactive-agent-workflow-spec
  - polecat-swarms
  - effectual-planning-agent
  - research-decomposition
---

# Conceptual Review Workflow

## Giving Effect

_No implementation yet. This spec defines a general-purpose iterative review pattern for intellectual artifacts._

- [[specs/effectual-planning-agent.md]] -- upstream dependency (strategic planning under uncertainty)
- [[specs/non-interactive-agent-workflow-spec.md]] -- agent lifecycle (Phase 1 decomposition protocol)
- [[specs/research-decomposition.md]] -- downstream domain application (research project planning instantiates this workflow)

## Motivation

### The gist pattern

Inspired by [LuD1161's Codex-Review skill](https://gist.github.com/LuD1161/84102959a9375961ad9252e4d16ed592): an iterative multi-agent review loop where a second agent provides structured critique of a first agent's output. The pattern works for code review because a reviewer with different optimisation targets catches what the author misses.

### Two insights from dogfooding

When we used a structured 5-pass review to evaluate the first draft of a combined spec (PR #648), two things became clear:

1. **The highest-value review question was universal.** "Does this spec practice what it preaches?" applies to any intellectual artifact, not just research plans. A general-purpose conceptual review workflow is more useful than a research-specific one.

2. **The same pattern serves many domains.** Spec review, manuscript review, grant proposals, design documents, and research decomposition are all instances of structured multi-agent critique with domain-specific lenses. The general pattern should be specified once and instantiated per domain.

## The User

Someone who has produced an intellectual artifact -- a spec, proposal, design doc, research plan, or manuscript draft -- and wants structured feedback that goes beyond surface editing. They need a thinking partner that catches what they miss: hidden assumptions, structural gaps, internal contradictions, missing context. When it works, it feels like a conversation with a rigorous collaborator. When it fails, it feels like submitting to a committee.

This includes both researchers (exploring ideas or refining project plans) and framework contributors (writing specs, design docs, or architecture proposals). The common thread is intellectual work that benefits from adversarial review before it ships.

## User Stories

**US-1: Spec or document review**
A framework contributor has written a spec, design doc, or manuscript draft. They want structured feedback that goes beyond surface editing: does the argument hold together? Does it contradict existing work? Does it practice what it preaches? The system applies relevant review lenses and returns prioritised, actionable critique.

**US-2: Proposal evaluation**
A researcher or team member has written a proposal -- a grant application, project plan, or design brief -- and wants to know if the argument holds together before submitting. They need a review that tests whether the assumptions are identified, the method matches the question, and the scope is realistic. The system applies domain-appropriate lenses (assumption hygiene, feasibility, strategic alignment) and returns a prioritised critique with proposed resolutions, so the author can revise with confidence rather than anxiety.

> **Coherence check**: This serves the core academicOps mission -- externalise cognitive load so the researcher can focus on thinking, not planning. The general review layer also serves the framework's self-reflexive architecture: using the system to improve the system.

## Composable Lens Registry

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
- **The primary lens shifts by review phase.** Self-consistency runs as a background check on every pass. But the _primary_ lens -- the one that drives the reviewer's top concern -- depends on the review's current phase. Pass 1 should lead with **axiom compliance + strategic alignment** ("should we build this?"). Pass 2 should lead with **assumption hygiene** ("can we build this correctly?"). This sequencing was validated by dogfooding on issue #676: Pass 1's architectural resolution (rejecting the governor design) fundamentally changed the artifact, making Pass 2 on the reworked proposal tighter and more productive. Had Pass 2 run first, its findings would have been wasted work. _Evidence: N=2 (PR #648, issue #676). Initial dogfooding (PR #648) identified self-consistency as the most productive lens; subsequent dogfooding (issue #676) refined this -- self-consistency is always valuable as a background check, but the primary lens that drives the most important finding varies by phase._
- Lenses compose by domain. Research reviews use methodological coherence + literature awareness + ethics. Spec reviews use strategic alignment + cross-reference consistency + scope discipline. The registry is extensible.

## Prioritised Critique Protocol

The reviewer does not evaluate all selected lenses exhaustively. Instead:

> Lead with your single most important concern. Explain why it matters and what breaks if it's not addressed. **Propose a specific resolution and defend it.** Then list up to 2 secondary concerns. Stop.

This forces the reviewer to **rank** rather than mechanically evaluate, giving the author a clear revision target instead of a wall of feedback. The mandatory resolution proposal prevents the reviewer from becoming merely an issue-raiser who leaves the hard thinking to the author. It also mitigates the rubber-stamping failure mode: a reviewer required to name its top concern _and propose a fix_ is more likely to engage deeply with one issue than to superficially address seven.

> **Dogfood evidence**: During issue #676 review, the agent correctly identified a tension with the fail-fast axiom but presented three options and asked the user to pick. The user immediately saw the key distinction the agent should have proposed. A reviewer that raises concerns without proposing resolutions shifts cognitive load back to the author -- defeating the purpose of the review.

## Convergence

The review loop converges by **resolution**, not by counting rounds:

- Each round must resolve at least one concern from the previous round.
- If a round introduces new concerns without resolving old ones, escalate to the human.
- If all raised concerns are resolved or explicitly overridden, the review is **APPROVED**.
- A soft safety cap (e.g. 7 rounds) prevents runaway loops, but it's a safety valve, not a design target.

## User Override

The researcher or author can override any review concern with a reason:

> "I know this assumption is untested. I'm accepting the risk because [reason]."

The reviewer records the override and stops re-raising it. This respects researcher autonomy while maintaining an audit trail of accepted risks. Without this, the system becomes a gate rather than a collaborator.

## Formality Gradient

Three operating levels, selected by artifact complexity or user preference:

| Level        | Lenses                               | Review loop                           | Venue                                | When to use                                              |
| ------------ | ------------------------------------ | ------------------------------------- | ------------------------------------ | -------------------------------------------------------- |
| **Light**    | 1-2 (self-consistency as background) | Single pass, no iteration             | In-session or issue comment          | Quick checks, small changes, early exploration           |
| **Standard** | 3-4                                  | Convergence-based                     | Pull request                         | Most specs, plans, proposals                             |
| **Thorough** | 4+ (consider multi-model review)     | Convergence-based + explicit sign-off | Pull request with multiple reviewers | Foundational specs, grant applications, research designs |

This solves the formality gradient tension: a researcher typing "I want to study X" gets the light version. Formal decomposition uses the thorough version. The system does not force ceremony on exploratory work.

The venue column reflects a key insight from dogfooding (see Orchestration below): the review loop's orchestration problem -- who goes next, what's resolved, when to re-engage -- is already solved by GitHub's PR review system when the artifact is a document in a pull request.

## Why Two Agents, Not One

The author and reviewer are separate roles for the same reason academic peer review separates author from reviewer:

- **Different optimisation targets.** The author optimises for completeness ("did I cover everything?"). The reviewer optimises for rigour ("is this actually sound?").
- **Assumption surfacing.** The author makes assumptions to make progress. The reviewer's job is to find them.
- **Adversarial improvement.** An agent cannot effectively critique its own output -- it defends its choices rather than probing them.

This is the core thesis of the gist pattern. It remains an assumption: LLMs reviewing their own species' output may share systematic blind spots. The value must be validated empirically (see Assumptions, below).

## Orchestration: Docs as Code

The review workflow needs orchestration: who goes next, what concerns are open, when to re-engage after revisions. Rather than building custom state tracking, the workflow treats **reviewable artifacts as documents in pull requests** and delegates orchestration to GitHub's native review system.

**The principle**: Knowledge work artifacts (specs, proposals, research plans, manuscripts) are documents. Documents live in the repository. Changes to documents are proposed via pull requests. Pull requests have a built-in review system with state tracking, notifications, and convergence detection. Therefore: the review loop's orchestration is already solved.

**What GitHub provides natively**:

- **State machine**: PR review status (changes requested -> approved)
- **Notifications**: Author is notified on review; reviewer is notified on new commits
- **Decision ledger**: Review comments with resolved/unresolved threading
- **Convergence detection**: All review threads resolved = ready to merge
- **Audit trail**: Commit history shows how the artifact evolved in response to review
- **Multi-reviewer support**: Multiple agents or humans can review the same PR with different lens selections

**What this replaces**: No custom labels, no state objects, no trigger protocols, no notification infrastructure. The review workflow specifies _how to review_ (lenses, critique protocol, convergence rules). GitHub handles _when and where_.

**Venue selection by formality** (see Formality Gradient above):

- **Light**: In-session conversation or issue comment. No orchestration needed -- the review is immediate and non-iterative.
- **Standard/Thorough**: The artifact is a file in a pull request. The reviewer submits a PR review using the critique protocol. The author pushes commits addressing concerns. The reviewer re-reviews. Merge = approved. GitHub handles the entire async loop.

**Issue vs. PR convention**: Issues describe problems. Pull requests propose solutions as documents. This separation keeps discussion (issue) distinct from the reviewable artifact (PR), and ensures the review system's machinery (diff view, line comments, review status) is available.

> **Dogfood evidence**: This section was added after applying the review workflow to issue #676 (Polecat Governor). The review content worked well (lenses surfaced real concerns, prioritised critique kept feedback focused). But the async orchestration broke down: there was no trigger to resume the review after the author responded, state was tracked ad-hoc in a PKB task body, and pass sequencing was improvised. Moving the reviewable artifact into a PR would have given us all of this for free.

## Intellectual Foundations

- **Codex-Review pattern** (LuD1161): Iterative multi-agent loop for structured critique.
- **Review practice pedagogy**: The reviewer criteria (assumption hygiene, methodological coherence, literature awareness, feasibility, ethics, self-consistency) draw on established review practices used by funding bodies, ethics boards, and editorial processes. The contribution of this spec is applying them in an iterative multi-agent loop, not the criteria themselves.

## Assumptions About This Spec

Practising what we preach:

| #  | Assumption                                                                                         | Confidence                                                                          | Validation                                                                                                      | If wrong                                                                                                                                                                                                                          |
| -- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1 | A second LLM agent reviewing catches blind spots a single agent misses                             | Medium                                                                              | Compare single-agent vs. two-agent decompositions on real projects                                              | Simplify to single-agent with self-review prompts                                                                                                                                                                                 |
| S2 | 3-4 lenses per review is the right number                                                          | Medium (N=1 from dogfooding)                                                        | Track which lenses produce actionable feedback across reviews                                                   | Adjust count; too few = reviews miss issues, too many = checklist problem                                                                                                                                                         |
| S3 | Self-consistency is the highest-value _background_ lens; the _primary_ lens varies by review phase | Medium (N=2: PR #648 + issue #676)                                                  | Track which lens produces most actionable finding across reviews, stratified by pass                            | If no phase-dependence emerges, revert to fixed always-on lens                                                                                                                                                                    |
| S4 | Convergence by resolution terminates in reasonable time                                            | Medium                                                                              | Monitor round counts in practice                                                                                | Lower the soft cap threshold; treat persistent non-convergence as a signal of unresolvable disagreement requiring human escalation and redesign of the escalation protocol (a cap already exists -- adjust it, don't add another) |
| S5 | The general workflow is more useful than a domain-specific version alone                           | Low                                                                                 | Build Layer 1 first; see if it gets reused for spec/manuscript review                                           | Collapse back to domain-specific spec                                                                                                                                                                                             |
| S6 | GitHub PR review provides sufficient orchestration for the review loop                             | Medium (N=1: issue #676 dogfood identified the gap; PR-based review not yet tested) | Run a standard-level review entirely via PR review system; compare orchestration friction to issue-based review | Build lightweight custom orchestration (labels + state object) if PR review is too coarse for multi-pass conceptual review                                                                                                        |

## Scope

### In scope

- General conceptual review workflow with composable lenses
- Prioritised critique protocol with mandatory resolution proposals
- PR-based orchestration for standard/thorough reviews (docs-as-code convention)
- Convergence by resolution with user override

### Out of scope

- Domain-specific applications (those are separate specs; see [[specs/research-decomposition.md]])
- New MCP tools or task schema changes
- Multi-model review orchestration (desirable for thorough level, but not required for v1)
- Automated execution

## Open Questions

1. **Domain expertise injection.** Without domain knowledge, the reviewer produces generic methodology feedback. How do we inject field-specific knowledge? (Literature search? User-provided context? Retrieval from Zotero library?)
2. **Reviewer model selection.** Same model reviewing its own species' output may share systematic blind spots. When does the thorough level warrant a different model?
3. **Relationship to existing peer-review workflow.** Does this complement or compete with `aops-core/workflows/peer-review.md`? The peer-review workflow handles editorial-style review; this spec handles conceptual/structural review. They may compose (peer-review as a light-level instantiation) or they may need explicit scoping to avoid overlap.

## Future Work

- **Spec-reviewer agent instantiation**: This workflow could be instantiated as a `spec-reviewer` agent, replacing the ad-hoc 5-pass review used on PR #648. With docs-as-code orchestration, this becomes a PR reviewer role alongside gatekeeper and custodiet.
- **Manuscript pre-submission review**: This workflow with literature + methodology + attribution lenses, applied to draft manuscripts before journal submission.
- **Lens effectiveness tracking**: Instrument which lenses produce the most actionable feedback, enabling evidence-based registry curation.
- **Multi-pass sequencing conventions**: Dogfooding validates (N=2) that multi-pass reviews (thorough level) benefit from sequencing lenses by phase -- alignment/strategic concerns first, feasibility/assumption concerns second. Issue #676 demonstrated this directly: Pass 1's architectural resolution (rejecting the local governor in favour of the bazaar model) changed the artifact so fundamentally that Pass 2's assumption hygiene findings were only productive because they targeted the revised design. Formalise pass ordering conventions based on accumulated evidence.

## Related

- [[effectual-planning-agent]] -- upstream; strategic planning under uncertainty
- [[non-interactive-agent-workflow-spec]] -- agent lifecycle and Phase 1 decomposition protocol
- [[polecat-swarms]] -- execution layer; consumes reviewed artifacts
- [[research-decomposition]] -- downstream domain application (research project planning instantiates this workflow)
- [[aops-core/workflows/decompose.md]] -- existing general decomposition workflow
