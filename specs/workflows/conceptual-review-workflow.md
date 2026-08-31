---
id: conceptual-review
title: Conceptual Review Workflow
type: spec
status: ready
tier: workflow
depends_on: [pauli]
created: 2026-02-28
tags: [spec, review, multi-agent, workflow]
related:
  - non-interactive-agent-workflow-spec
  - polecat-swarms
  - pauli
  - research-decomposition
---

# Conceptual Review Workflow

Multi-agent review of an intellectual artifact — a spec, proposal, design doc, research plan, or
manuscript draft. Author and reviewer are separate identities; no agent reviews its own output.

## Composable lens registry

The reviewer selects lenses by artifact type. Each lens is one evaluation perspective with a core
question.

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

Selection rules:

- A given review selects **3–4 lenses**, not all of them. Breadth kills depth.
- **Self-consistency runs as a background check on every pass.** The _primary_ lens — the one
  driving the top concern — shifts by phase: pass 1 leads with **axiom compliance + strategic
  alignment** ("should we build this?"), pass 2 with **assumption hygiene** ("can we build this
  correctly?").
- Lenses compose by domain. Research reviews use methodological coherence, literature awareness,
  and ethics. Spec reviews use strategic alignment, cross-reference consistency, and scope
  discipline.
- Domain applications may substitute their own lens set for this registry; see
  [[specs/workflows/research-decomposition.md]].

## Prioritised critique protocol

The reviewer ranks rather than evaluating every selected lens:

> Lead with your single most important concern. Explain why it matters and what breaks if it's
> not addressed. **Propose a specific resolution and defend it.** Then list up to 2 secondary
> concerns. Stop.

## Output contract

- A "Needs attention" section containing at most 3 prioritised items.
- Every item carries a proposed resolution, stated as an actionable instruction.
- After the author responds with a commit or comment, the next pass recognises the resolution or
  the override.

## Convergence

The loop converges by resolution, not by counting rounds.

- Each round must resolve at least one concern from the previous round.
- A round that introduces new concerns without resolving old ones escalates to the human.
- All concerns resolved or explicitly overridden → **APPROVED**.
- A soft cap of 7 rounds is a safety valve, not a design target.

## User override

The author may override any concern with a stated reason ("I know this assumption is untested;
I'm accepting the risk because X"). The reviewer records the override and stops re-raising it.

## Formality gradient

| Level        | Lenses                               | Review loop                           | Venue                                | When to use                                              |
| ------------ | ------------------------------------ | ------------------------------------- | ------------------------------------ | -------------------------------------------------------- |
| **Light**    | 1-2 (self-consistency as background) | Single pass, no iteration             | In-session or issue comment          | Quick checks, small changes, early exploration           |
| **Standard** | 3-4                                  | Convergence-based                     | Pull request                         | Most specs, plans, proposals                             |
| **Thorough** | 4+ (consider multi-model review)     | Convergence-based + explicit sign-off | Pull request with multiple reviewers | Foundational specs, grant applications, research designs |

## Orchestration

Orchestration — who goes next, which concerns are open, when to re-engage — is delegated to
GitHub's review system, not tracked separately.

- **Light**: in-session conversation or issue comment. No orchestration; the review is immediate
  and non-iterative.
- **Standard / Thorough**: the artifact is a file in a pull request. The reviewer submits a PR
  review using the critique protocol; the author pushes commits addressing concerns; the reviewer
  re-reviews. Merge = approved.

**Issues describe problems; pull requests propose solutions as documents.** Keep the discussion
on the issue and the reviewable artifact in the PR, so the diff view, line comments, and review
status are available.

Add no custom labels, state objects, trigger protocols, or notification infrastructure. This spec
governs _how to review_; GitHub governs _when and where_.

## Out of scope

- Domain-specific applications — separate specs; see [[specs/workflows/research-decomposition.md]].
- New MCP tools or task schema changes.
- Multi-model review orchestration.
- Automated execution.

## Open questions

1. **Domain expertise injection.** Without domain knowledge the reviewer produces generic
   feedback. Literature search, user-provided context, or Zotero retrieval?
2. **Reviewer model selection.** A model reviewing its own species' output may share systematic
   blind spots. When does the thorough level warrant a different model?
3. **Relationship to `plugins/tools/skills/peer-review/SKILL.md`.** That skill handles
   editorial-style review; this spec handles conceptual/structural review. Whether they compose or
   need explicit scoping is unresolved.

## Related

- [[plugins/aops/agents/pauli.md]] — upstream; strategic planning under uncertainty
- [[specs/workflows/research-decomposition.md]] — downstream domain application
- [[plugins/aops/skills/brief/SKILL.md]] — records this workflow's review obligations as
  acceptance criteria on the task body
- [[polecat-swarms]] — execution layer; consumes reviewed artifacts
