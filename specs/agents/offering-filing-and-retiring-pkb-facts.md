---
title: Offering, Filing, and Retiring Knowledge Base Facts
status: ready
type: spec
tags: [pkb, capture, curation, remember, agents, skills]
---

# Offering, Filing, and Retiring Knowledge Base Facts

This specification establishes the framework protocol across all agents and worker lifecycle skills to systematically recognize and offer durable facts to the knowledge base custodian (`pauli`), defines the filing and concision standards the custodian applies to prevent knowledge sprawl, and unifies the rules governing the retirement of conflicting, unnecessary, demonstrably false, and stale content on sight across the custodian and the `remember` skill.

## User stories

### US-1 Capturing and routing durable facts to the custodian

As a user interacting with or relying on autonomous agents, I want any agent or worker that encounters or discovers a durable fact to recognise it and offer it to the knowledge base custodian (or record it where the custodian can collect it), so that institutional knowledge is preserved reliably without uncoordinated graph curation.

- **AC-1.1 (Generic fact offering)**: Given any agent encountering or discovering a durable fact (a user decision, an architectural constraint, a verified finding about current system state, or an incorrect knowledge base statement) during conversation, dispatch, execution, or review, when the agent processes the turn, then the agent offers the fact to the knowledge base custodian as content without mutating knowledge base notes directly or minting unprompted backlog tasks.
- **AC-1.2 (Headless / isolated worker recording)**: Given an agent or worker operating in an isolated or headless execution context where direct communication with the custodian is unavailable, when it encounters or discovers a durable fact during task execution or session completion, then it records the fact under a dedicated `## Durable Facts` section in the task record and handover summary so the custodian collects it during truth maintenance.
- **AC-1.3 (Coordination role boundaries)**: Given an agent coordinating tasks or supervising reviews, when managing execution or synthesizing findings, then the agent leaves direct graph curation, consolidation, and pruning to the custodian and offers any durable facts to the custodian as content.

### US-2 Filing offered facts without sprawl and at calibrated detail

As a user querying or navigating the knowledge base, I want the knowledge base custodian to file facts into canonical topics without sprawl and at calibrated concision, so that notes remain compact, accurate, and easily retrievable.

- **AC-2.1 (Search-first canonical filing)**: Given the knowledge base custodian receiving an offered fact or collecting facts from completed task records and handover summaries, when filing the fact, then the custodian queries existing topic notes and augments the canonical note in place, creating a new document only when the fact represents a genuinely novel domain concept with no matching canonical note.
- **AC-2.2 (High-density concision)**: Given the custodian incorporating an offered fact into the knowledge base, when updating or creating a note, then the custodian extracts durable principles, architectural decisions, invariants, and verified current-state findings while discarding ephemeral execution trivia, line numbers, temporary debugging outputs, and transient timestamps, keeping note bodies concise and within standard length budgets (30–80 lines).
- **AC-2.3 (Automated collection from task records)**: Given completed task records or session handover summaries containing unfiled durable facts under a dedicated durable facts section, when the custodian performs graph maintenance, hydration, or consolidation, then the custodian ingests the facts into the appropriate canonical topic notes and marks them incorporated.

### US-3 Unified content retirement on sight across custodian and skills

As a user relying on knowledge base truth, I want conflicting, unnecessary, demonstrably false, and stale content retired or corrected immediately on sight, so that the knowledge base never preserves misleading assertions or duplicate records.

- **AC-3.1 (Retirement on sight)**: Given conflicting, unnecessary, demonstrably false, or stale content encountered in the knowledge base, when the custodian or an agent performing knowledge consolidation discovers the defect, then the agent resolves, corrects, or removes the content immediately on sight without deferring to a later pass, filing a maintenance ticket, or reserving it as the user's call.
- **AC-3.2 (Resolving contradictions)**: Given contradictory assertions between knowledge base documents or between a note and live verified reality, when consolidating knowledge, then the agent resolves the contradiction to verified current state, updates the canonical note, and deletes the losing assertion outright without recording historical debate.
- **AC-3.3 (Deduplication)**: Given duplicate notes, overlapping concepts, or undigested observation scraps, when consolidating knowledge, then the agent merges the durable insight into the single canonical topic note and removes the redundant note.
- **AC-3.4 (Correcting false claims)**: Given an assertion in the knowledge base that contradicts live system state or primary source verification, when encountered, then the agent deletes or corrects the false statement immediately on sight.
- **AC-3.5 (Archival vs deletion lifecycle)**: Given an episodic note or superseded document whose durable knowledge has been extracted to a canonical destination note, when retiring the source record, then both the custodian's instructions and knowledge curation skills apply one consistent rule: set status to archived on notes that are moved to the archival repository by the archival pipeline, and delete outright without tombstones internal superseded sections and replaced atomic memories.

## Design

### Behavioral Contract

1. **Observer vs. Custodian Model**:
   - **Knowledge Observers (all agents and workers)**: Any agent encountering a durable fact during interaction, dispatch, review, or execution recognizes it as such. A durable fact is defined as: an explicit user or system decision, an architectural constraint, a verified finding about current system behavior, or an incorrect or missing assertion in the knowledge base. Observers do not perform direct graph surgery or mutate knowledge notes; they deliver the raw fact, context, and source pointer to the custodian.
   - **Knowledge Custodian (`pauli`)**: Acts as the sole curator and synthesizer of the knowledge base graph. Evaluates incoming facts, identifies canonical topic homes, updates notes in place, rejects sprawl and noise, and polices the knowledge graph for decay.
   - **Relief of Coordination Roles from Direct Curation**: Coordination agents (such as `james`) are relieved of direct knowledge base pruning, deletion, and consolidation duties, aligning them strictly with lead execution and review supervision under the principle of doing one thing.

2. **Dual-Path Fact Delivery**:
   - **Direct Delivery**: When communicating in session or over the agent message bus, the observing agent sends the fact directly to the custodian as content with its source pointer.
   - **Asynchronous Pickup**: For isolated or headless workers operating without subagent messaging tools by architectural design, the designated native channel is recording the fact in the task record under `## Durable Facts` and in the final handover report emitted by `dump`. The custodian scans these records during routine graph maintenance and consolidation passes, extracts the facts, updates the canonical notes, and marks them incorporated.

3. **Anti-Sprawl Filing & Concision Standard**:
   - **Search-First, Augment-in-Place**: The custodian searches for existing topic notes before creating any document. One canonical note per topic. New documents are created only for novel concepts with zero semantic overlap with existing topics.
   - **High-Density Invariants**: Notes capture durable invariants, operational contracts, and transferable principles. Operational noise (execution transcripts, stack traces, temporary line numbers, environment-specific scratch paths) is stripped prior to writing.
   - **Concision Ceiling**: Notes are bounded to 30–80 lines (<1,500 characters) so that documents can be read and rewritten whole.

4. **Unified Four-Category Retirement Rule**:
   - **Conflicting**: Resolve to current verified truth, update the canonical note, and delete the losing claim outright.
   - **Unnecessary**: Consolidate overlapping notes into the single canonical note and delete the duplicate.
   - **Demonstrably False**: Delete or correct immediately upon discovery. False claims degrade semantic retrieval and must not persist.
   - **Stale**: When a primary note's durable knowledge is consolidated into a canonical destination note, mark the primary note with `status: archived` to enable the archival pipeline to transfer it to the historical sessions repository. Superseded subsections within living notes and replaced atomic memories are deleted outright without tombstones.

### Instruction Surfaces and Enforcement-Map Placement

The following inventory identifies the primary instruction surfaces governing how agents recognize, offer, file, and retire knowledge base facts, along with their placement in `specs/ENFORCEMENT-MAP.md`:

| Area | Surface | Scope & Current Text | Enforcement-Map Placement | Required Action |
| :- | :- | :- | :- | :- |
| **Agent Personas** | `plugins/ida/agents/ida.md`, `sara.md`, `marsha.md` | Persona definitions; currently lack general direction to recognize durable facts or offer them to the custodian. | `unenforced` | Add generic imperative rule directing agents to recognize durable facts (decisions, constraints, verified findings, incorrect lines) and offer them to the custodian as content. |
| **Agent Persona** | `plugins/ida/agents/james.md:37-38` (`## Ephemeral state`) | Instructs: `Curate durable knowledge in the structured PKB graph... Delete outdated information, consolidate overlapping content, prune stale nodes...` | `specs/ENFORCEMENT-MAP.md:23` under `[Axiom: Do One Thing]` | Replace direct curation instructions with a clear directive to offer durable facts to the custodian, leaving graph curation to the custodian. |
| **Agent Persona** | `plugins/ida/agents/pauli.md:11,15,53,169` (`## The graph is yours`, `## Maintenance`) | Directs Pauli to maintain the graph, delete out-of-date content, and `set archived on anything you do not want to delete`; lacks clear filing guidelines for offered facts. | `unenforced` (curation protocol unmapped in `specs/ENFORCEMENT-MAP.md`) | Clarify anti-sprawl filing procedure and detail thresholds for offered facts; harmonize retirement rules across the four categories (conflicting, unnecessary, false, stale). |
| **Skills** | `plugins/ida/skills/pull/SKILL.md`, `plugins/ida/skills/dump/SKILL.md` | Worker execution and session finalization skills; contain no instructions for handling durable facts met during execution. | `unenforced` | Add instructions to recognize durable facts during execution and offer them to the custodian, or record them under `## Durable Facts` if operating in an isolated context. |
| **Skill** | `plugins/ida/skills/remember/SKILL.md:48` (`## Consolidation`) | Instructs: `Delete outright -- no tombstone, no status: archived, no archive copy.` Directly contradicts custodian instructions and the deployed archival pipeline. | `specs/ENFORCEMENT-MAP.md:38` under `[Axiom: Single Source of Truth]` | Harmonize retirement instruction with custodian: retire episodic source notes via `status: archived` for archival migration, while deleting superseded sections and replaced memories outright. |

### Proportional Intervention Options Pass

In accordance with `specs/enforcement/enforcement.md`, this intervention is evaluated through the enforcement pyramid from least-invasive to most-invasive:

| Level | Mechanism Category | Evaluation and Disposition |
| :- | :- | :- |
| 1 | `doctrine only` | **Insufficient.** Universal axioms (`Durable Capture`, `Single Source of Truth`, `Do One Thing`) establish the high-level intent, but existing instructions contained explicit contradictions (e.g. `remember` forbidding `archived` while `pauli` required it, and `james` being told to curate the graph directly). Doctrine alone cannot resolve contradictory instructions. |
| 2 | `instructions` (`imperative`) | **Adopted.** Adding clear, imperative instructions across agent personas and skills (`pull`, `dump`, `remember`) provides the least-invasive, most proportionate mechanism. Instructions operate at the exact cognitive point of deliberation without imposing rigid mechanical hurdles or tool overhead. |
| 3 | `JIT injection` | **Rejected.** Dynamic hook injection of fact-checking reminders on every tool use would consume significant token budget and cause conversational friction without improving semantic comprehension of facts. |
| 4 | `structural` | **Rejected.** Deterministic keyword filters, AST sniffers, or regex scrapers cannot reliably assess whether an assertion represents a durable fact or an ephemeral log, violating the axiom that judgment is non-delegable. |
| 5 | `process` | **Adopted for verification.** Independent PR review lenses evaluate candidate instruction changes to verify compliance with craftsmanship standards, authority boundaries, and quality requirements. |
| 6 | `post-hoc` | **Adopted for observation.** Normal session traces and git commit history record fact-offering events and graph updates for ongoing observability. |

### Evidence for the Move

1. **Direct User Directive**: The framework principal explicitly ordered this capability (console goal, 2026-11-03):
   > "ensure agents recognise important facts and offer them to pauli, and that pauli knows how to file things without making the PKB sprawl, knows the level of detail we should keep, actively consolidates knowledge and corrects conflicting, unecessary, demonstrably false, and stale information, and does all that fast and efficiently".
   > Under the direct user instructions rule, this directive carries an immediate execution obligation.
2. **Elimination of Active Instruction Contradiction**: `plugins/ida/skills/remember/SKILL.md:48` explicitly ordered agents to "Delete outright -- no tombstone, no status: archived, no archive copy", while `plugins/ida/agents/pauli.md:15` commanded Pauli to "set archived on anything you do not want to delete", and a completed framework task deployed an automated pipeline that moves notes marked `status: archived` to the historical sessions repository. This direct conflict created operational confusion and inconsistent graph cleanup.
3. **Role Boundary Realignment**: `plugins/ida/agents/james.md:38` instructed James to delete, consolidate, and prune the knowledge base. This violated the core division of labor where Pauli is the sole knowledge base custodian, creating a risk of conflicting simultaneous graph edits during parallel execution.
4. **Preventing Knowledge Sprawl**: Prior practice suffered from sprawl due to agents creating shallow, fragmented notes or leaving valuable decisions buried inside ephemeral task records. Establishing an explicit anti-sprawl filing rule with clear concision limits protects knowledge retrieval performance.

### Enforcement Map Extract (for Downstream Implementation)

The following rows will be updated in `specs/ENFORCEMENT-MAP.md` during downstream implementation when the instruction text is merged, consolidating controls strictly under active governing axioms:

| Rule | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| [Axiom: Durable Capture](../plugins/rbg/skills/axioms/durable-capture.md) -- Capture knowledge not verdicts, update existing documents rather than creating duplicates, and route durable facts to Pauli. | instructions, JIT injection, process | imperative, warning, required gate | `plugins/rbg/skills/axioms/durable-capture.md:9`, `plugins/ida/agents/ida.md`, `plugins/ida/agents/sara.md`, `plugins/ida/agents/james.md`, `plugins/ida/agents/marsha.md`, `plugins/ida/agents/pauli.md`, `plugins/ida/skills/pull/SKILL.md`, `plugins/ida/skills/dump/SKILL.md`, `plugins/ida/skills/remember/SKILL.md:10-70`, `plugins/ida/hooks/handlers.py:594-638`, `wf-reconcile.md:1-55` |
| [Axiom: Single Source of Truth](../plugins/rbg/skills/axioms/single-source-of-truth.md) -- Maintain exactly one authoritative copy of every fact, rule, or artifact without duplication, retiring conflicting or obsolete content on sight. | instructions, structural, process | imperative, protection, required gate | `build/build.py:42-95`, `plugins/ida/agents/pauli.md`, `plugins/ida/skills/remember/SKILL.md:10-48`, `wf-reconcile.md:15-50` |
| [Axiom: Do One Thing](../plugins/rbg/skills/axioms/do-one-thing.md) -- Execute precisely the requested task to the specified standard, keeping agents within delegated authority and leaving graph curation to Pauli. | instructions, structural, process | imperative, scoped, required gate | `plugins/rbg/skills/axioms/do-one-thing.md:9-21`, `plugins/ida/agents/ida.md:28-34`, `plugins/ida/agents/pauli.md:19-33`, `plugins/ida/agents/james.md:10-38`, `plugins/ida/agents/sara.md:14-40`, `plugins/ida/skills/pull/SKILL.md:14-39`, `wf-task-base.md:1-45` |

### Outcome-Level Build Criteria (for Downstream Implementation)

Stage 2 implementation must satisfy the following verifiable criteria across the specified instruction files:

- **BC-1 (Generic Fact Offering in Agent Personas)**: Agent persona instructions carry the generic imperative rule directing agents to recognize durable facts (decisions, constraints, verified current-state findings, or incorrect knowledge base claims) and offer them to the custodian as content without directly editing notes or creating tasks.
- **BC-2 (Coordination Scope Realignment)**: Coordination persona instructions (`plugins/ida/agents/james.md`) replace direct knowledge graph curation instructions with a requirement to recognize durable facts and offer them to the custodian as content, leaving graph curation to the custodian.
- **BC-3 (Worker Skills Fact Handling)**: Worker lifecycle skills (`plugins/ida/skills/pull/SKILL.md` and `plugins/ida/skills/dump/SKILL.md`) instruct workers to recognize durable facts and offer them to the custodian, or record them under `## Durable Facts` in the task record and handover summary if operating in an isolated context where the custodian is unreachable.
- **BC-4 (Custodian Anti-Sprawl Filing & Concision)**: The custodian instructions (`plugins/ida/agents/pauli.md`) specify the anti-sprawl filing process (search first, augment canonical notes in place, create new notes only for novel concepts) and concision thresholds (retaining principles and verified state, stripping execution trivia, targeting 30–80 lines).
- **BC-5 (Unified Content Retirement on Sight)**: Custodian instructions (`plugins/ida/agents/pauli.md`) and knowledge curation skills (`plugins/ida/skills/remember/SKILL.md`) define an identical, consistent rule for retiring content on sight across the four categories:
  1. _Conflicting_: resolve to verified truth and delete losing assertion outright.
  2. _Unnecessary_: merge duplicates into canonical note and delete redundant notes.
  3. _Demonstrably false_: delete or correct immediately on sight.
  4. _Stale_: set `status: archived` on episodic notes destined for the sessions archival repository once durable content is extracted; delete outright without tombstones internal superseded sections and replaced atomic memories.
