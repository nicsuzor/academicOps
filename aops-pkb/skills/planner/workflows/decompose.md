---
id: decompose
name: decompose-workflow
category: planning
bases: [base-task-tracking, base-handover]
description: Break down goals and epics into structured task trees using workflow steps
permalink: workflows/decompose
tags: [workflow, planning, decomposition, tasks, epics]
version: 2.0.0
---

# Decompose Workflow

**Purpose**: Break down a goal or epic into a structured task tree. When the epic has an assigned workflow, derive tasks from the workflow's steps.

**When to invoke**: User says "plan X", "break this down", "what steps are needed?", or an epic is ready for concrete work after [[strategic-intake]].

**Skill**: [[planning]] for decomposition patterns (spikes, dependency types, knowledge flow).

## Core Process

0. **Earn-its-keep gate** — Before authorising decomposition, apply the five prompts from [[../SKILL.md#3-decompose]] (SSoT). If the idea does not survive, record why and halt. Good ideas killed here cost a sentence; bad ideas survived to PR cost a revert. ([[aops-8d4a2e14]] primary-catch intent · [[mem-231996ac]] no-shitty-NLP corollary · [[aops-8c7f7b88]] arch-fit backstop)
1. **Understand the Target**: What are we decomposing -- a project, an epic (needs tasks), or a task (needs actions)? Clarify the primary objective and constraints.
   - **Target structure**: `Project → Epic → Task → Action` (see [[../../remember/references/TAXONOMY.md]])
   - **Property Check**: Examine the parent's `scope`, `uncertainty`, and `criticality`.
   - **High Uncertainty**: Priority is to reduce uncertainty. The decomposition should lean heavily into evidence gathering, audits, or probes (Step 3).
   - **Low Uncertainty + High Scope**: Parent is well-understood but large. The decomposition should focus on creating independent, parallelizable execution tasks.
   - **Intent before mechanism**: for a build/change task, first pin down what the thing should _do_ and _why_ (spec-of-intent); confirming how the existing plumbing works is necessary but never a substitute for specifying the intent.

2. **Search for Context**: Query PKB for existing related work, prior decompositions of similar scope, and established patterns. Use `pkb_context(id, hops=2)` to understand the neighbourhood.

3. **Map Unknowns**: Before planning execution, identify what you _don't_ know. Classify each as: **researchable** (others may have solved it → evidence-gathering task), **internal** (we have unanalysed data → audit/survey task), or **probeable** (unknown-unknown → time-boxed spike). High parent `uncertainty` means most subtasks should start here.

3.5. **Interrogate the task's epistemics** — before structuring, put three questions to the task _itself_. They are prompts, not steps; answer each in a line, then let the answers shape the tree:

- **What evidence best answers this?** Name the _rawest, highest-signal_ source for _this_ question — including the negative/diagnostic record (rejected or closed PRs, reverts, abandoned spikes, recent lived complaints in daily notes), not only the distilled corpora you already reach for (open issues, retros). Where a mechanical fix was _tried and rejected_ is often the sharpest evidence of a problem only judgment can catch.
- **What must be observable before success can be judged?** If the result's effect is not already visible in the artifacts you can inspect, building that instrumentation is a prerequisite task, not an afterthought — you cannot verify a gate you cannot see fire.
- **Does the artifact's nature dictate the verification shape?** A qualitative or judgment-based output is proven by observation in the wild and deliberate boundary-probing; crafted pass/fail cases supplement but do not substitute for it. Match the test to the nature of the thing; do not mechanise a qualitative target.

4. **Cross-cutting Impact & Prerequisites** — Ask two questions: (a) "What other projects consume or depend on what's changing?" Search PKB for affected tasks/epics — scope per-project queries with `list_tasks(project=<project-id>)` rather than inferring membership from ID prefixes or walking parent chains. Create sibling tasks in THOSE projects with `depends_on` pointing back here. (b) "What must be true for this change to work?" For each unmet prerequisite, create a prep task that implementation `depends_on`. Both often live in different projects.

5. **Derive a composite Workflow**:
   - Identify which workflow or combination of workflows are relevant for the particular task.
   - Every epic needs phases, but the phases depend on the type of work.
   - The composite workflow's steps become the decomposition skeleton.

6. **Map workflow steps to tasks**: Each step becomes one or more tasks. See [[decomposition-patterns]] for temporal, functional, and complexity patterns.

7. **Define Deliverables**: For each task, specify the concrete output. A task without a clear deliverable isn't actionable.

8. **Identify Dependencies**: Which tasks must complete before others can start?
   - Use the [[planning]] skill's dependency-type heuristic: "What happens if the dependency never completes?" If impossible → hard dependency. If less informed → soft dependency.

9. **Estimate Effort**: Assign rough duration (0.5d, 1d, 1w). Tasks over 0.5d probably need further decomposition. Single-session tasks (1–4 hours) are the right duration. This single-session vs multi-session call feeds **thin-brief / `partial`-stop eligibility** (recorded at step 16): under the NARROW default ([[spec-partial-work]]), a single-session leaf may legitimately be dispatched thin and stop at `partial`, while epics and multi-session work keep the full review gate.

10. **Extract Structured Metadata**: Extract `due` and `consequence` for subtasks if mentioned or implied by the parent task.

11. **Leave Priority at default P3**: Subtasks stay at the uncurated default band (**P3**). Agents never originate a non-default band: do NOT propagate the parent's priority to children, and do NOT infer it from subtask content or apparent importance. Write a non-default band only when Nic expressly directs that value for that subtask. Canonical rule: [[framework-conventions-summary#intent-authority]] (see also [[../SKILL.md#priority-assignment-rules]]).

12. **Apply the Decision Surfacing Heuristic** — Before drafting any user-facing "design conversation" or ratification message, classify each open decision as DECIDE / DEFER / SURFACE per [[../SKILL.md#decision-surfacing-heuristic]]. Bundling DECIDE-class items with SURFACE-class items trains rubber-stamping (issue #816).

12.5. **Hydrate: write a `## Context` section into every subtask body** — the precondition for contextless dispatch (a worker holding only this task body, with no session history, must be able to start). For each drafted subtask, before creating it:

- **Semantic search**: `search(query=<subtask's core question or title>, boost_id=<parent epic id>, limit≈5)` — surfaces prior work by content even without an explicit link.
- **Graph neighbours**: reuse (or extend) the `pkb_context(id, hops=2)` neighbourhood already gathered in step 2 for the parent, plus `get_semantic_neighbors(id)` scoped to this specific subtask's topic — filter to what's actually relevant to _this_ subtask, not the whole epic.
- **Project doc**: the relevant project/spec doc already loaded for this epic (e.g. `.agents/CORE.md` component entry, a `specs/*.md` SSoT, or the PKB note the epic cites).
- Compose 2–5 bullets naming **prior attempts, decisions already made, superseded approaches, and known confounds** — each bullet ends with a wikilink to the real node id it's sourced from (`[[node-id]]`) so a reviewer can spot-check the claim against the cited node. Never cite a node id you haven't actually opened and verified says what you claim — a fabricated or stale citation is worse than an empty section.
- If a good-faith search genuinely returns nothing relevant (rare for a live backlog), write `## Context\nNo directly relevant prior history found (searched: <queries run>).` rather than omitting the section or padding it with generic filler.
- This is additive to — not a replacement for — the existing "Self-contained context" guidance in [Task Handoff Quality](#task-handoff-quality-p120): that section covers _why this task exists_; `## Context` covers _what the graph already knows that bears on how to do it_.

13. **Create in PKB** — Use `mcp__pkb__decompose_task(parent_id, subtasks)` for batch creation under the epic. Include dependencies, effort, due, consequence, deliverable descriptions, and each subtask's `## Context` section (step 12.5) as explicit fields in `body`. **Leave `priority` at the default P3** (per step 11): never infer, estimate, or propagate a band — only Nic sets intent ([[framework-conventions-summary#intent-authority]]). To make a subtask **more important**, raise the `stated_weight` of its `contributes_to` edge (Renooij-Witteman verbal scale; see [[wire-edges]] / [[../../remember/references/TAXONOMY.md#target-nodes]]), never bump priority.

14. **Apply Multi-agent Review Gate (default, mandatory)** — For each proposed epic, file ONE blocking `james review of <epic-title> (pauli + rbg + revise)` child (epic stays `inbox` until it lands). For each proposed standalone task, file `pauli + rbg review of planned approach` as the first subtask (execution children `depends_on` it) and `james review of work against original instructions, user intent, and project rules` as the last subtask (`depends_on` execution children). State only the artifact and link to parent; defer methodology to the agents' framework instructions. Stacks with — does not replace — the lens-based profile in step 15.

15. **Apply Review Profile** — Create SEPARATE child subtasks for review based on work type. Tag with `lens: <name>` (use `aops-core/skills/planner/references/verification-template.md` as a base).
    - **Methodology/Analysis**: Agent methodology critique followed by binary Human "accept/redesign" approval (`assignee="nic"`). Block promotion on these.
    - **Citation-heavy Writing**: Citation verification & Argument review (runs AFTER execution, does not block promotion).
    - **Outbound Comms**: Alignment, Quality, & Voice review (runs AFTER execution, does not block promotion).
    - **Student Assessment**: Rubric fidelity & Consistency review (runs AFTER execution, does not block promotion).
    - **Exploratory**: _Escape Hatch_ — Create minimal verification tasks and do not block promotion to ready for exploratory work.

16. **Record Promotion Decision** — Write a `## Promotion Log` entry to the parent body capturing the readiness rationale (AC defined, effort estimated, hard dependencies resolved). **Do NOT manually flip `inbox → ready`**: `ready` is computed automatically once decomposition is complete and dependencies are resolved (canonical status set + lifecycle: [[../../remember/references/TAXONOMY.md#status-values-and-transitions]]). Your job here is to make the task _ripe_, not to write the `ready` band; the only manual status gate downstream is the human `ready → queued`. Record **thin-brief / `partial`-stop eligibility** in this same entry ([[spec-partial-work]]): whether this node may be dispatched on a thin brief and whether a worker may stop at `partial` (draft PR + continue task). This is the promotion-log author's call — **not** a worker frontmatter field, because a worker cannot self-promote its own latitude. NARROW default: full gate for epics/multi-session; a single-session leaf (step 9) may go thin and stop `partial`.

## Hierarchy and Depth

- **Prefer depth over breadth**: If decomposition produces >10 tasks, group into sub-epics.
- **Avoid the star pattern**: A flat list of sibling tasks is a failure of decomposition.
- **Every task belongs to an epic**: No orphans. If a task exists, its epic gives it purpose.

## Workflow-Step Mapping Example

See [[decomposition-patterns#workflow-step-mapping]] for a worked workflow-step → task mapping (the `feature-dev` example).

## Task Handoff Quality (P#120)

Tasks will be picked up by a **different agent** with only the task body as context. This is the canonical compose-then-dispatch shape: decompose writes the brief to PKB; a separate invocation (the worker, the next supervisor tick) reads it fresh. See [[../../aops/references/authoring-discipline#3-compose-then-dispatch-separation]].

- **Intent + AC, not prescription**: Apply the Task-Body Authoring Discipline ([[../../aops/references/authoring-discipline]]). Task bodies must state intent and observable Acceptance Criteria without prescribing implementation or adding phantom review gates.
- **Self-contained context**: Include enough background that someone with no session context understands _why_ this task exists and _what decisions led to it_.
- **`## Context` section (step 12.5)**: every subtask body carries a `## Context` section hydrated from PKB history (semantic search + graph neighbours + project doc) naming prior attempts, decisions, supersessions, and known confounds, each citing a real, spot-checkable node id. This is what turns "self-contained context" from an aspiration into a checkable artifact — a contextless agent reading only this task should not need to ask what's already been tried or decided.
- **Include data findings**: Record actual numbers discovered during decomposition, not just summaries.
- **Link to related tasks**: Use explicit task ID wikilinks (e.g., [[task-id]]), not "the other task."
- **Record design decisions and terminology**: Capture user choices as design constraints with rationale; define new terms in the task body.

## Critical Rules

- **Completeness & Actionability**: All tasks together must achieve the original epic; every task must be completable in a single session.
- **Verification**: Every epic must include at least one QA/review task. The Multi-agent Review Gate (step 14) is the default and is non-optional — `james` blocker on every new epic; `pauli + rbg` first / `james` last on every new standalone task. The user is often not the right substantive reviewer; do not skip the gate just because they look ready to approve.
- **Contextless-executable**: Every subtask body includes a hydrated `## Context` section (step 12.5) before creation. A subtask without one is not ready to dispatch — hydration is not optional polish, it's the precondition for delegating to an agent with no session history.
- **Conservative expansion**: If a task can be done in one sitting, don't decompose further.
- **Graph placement, drift & supersession**: Every task must be parented under a live epic with dependencies; when upstream work changes scope, update affected task bodies. If this decomposition carves an _existing_ task's work into the new subtasks (or siblings), **cancel** that original (`status: cancelled`) in the same operation so it leaves the `queued`/`ready` dispatchable set, and add a `supersedes` edge on each new subtask so the redirect is discoverable from the live side — do not rewrite its stale body. See [[../../remember/references/TAXONOMY.md#supersession-and-retirement]].
- **No parallel tracking**: After creating subtasks, remove any `- [ ]` checklists from the parent body that duplicate the subtask graph. Replace with a summary reference (e.g., "Decomposed into N subtasks — see children"). Body checklists and subtask graphs inevitably diverge over time.
