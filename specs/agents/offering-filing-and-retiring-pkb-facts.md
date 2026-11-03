---
title: Offering, Filing, and Retiring Knowledge Base Facts
status: ready
type: spec
tags: [ida, pauli, james, sara, marsha, pkb, capture, curation, remember, pull, dump]
---

# Offering, Filing, and Retiring Knowledge Base Facts

This specification establishes the framework protocol across the conversational front, coordination, and execution agents (`ida`, `sara`, `james`, `marsha`) and worker lifecycle skills (`pull`, `dump`) to systematically recognize and offer durable facts to the knowledge base custodian (`pauli`), defines the filing and concision standards Pauli applies to prevent knowledge sprawl, and unifies the rules governing the retirement of conflicting, unnecessary, demonstrably false, and stale content on sight across Pauli and the `remember` skill.

## User stories

### US-1 Recognizing and offering durable facts to the custodian

As an agent or worker executing tasks, verifying deliverables, or conversing with the user, I want clear instructions to recognize durable facts and offer them to Pauli as content, so that valuable institutional knowledge, architectural constraints, and discovered errors are preserved in the knowledge base without each agent attempting uncoordinated direct graph curation.

- **AC-1.1** Given Ida encountering a durable fact (a user decision, an architectural constraint, a verified finding about current behavior, or an incorrect knowledge base statement), when Ida processes the turn, then Ida offers the fact to Pauli as content without mutating knowledge base notes directly or minting unprompted backlog tasks.
- **AC-1.2** Given Sara receiving a worker report or brief containing a durable fact, when Sara synthesises the checked report, then Sara offers the durable fact to Pauli as content.
- **AC-1.3** Given James executing a unit of work or supervising dialectical review, when James encounters a durable fact, then James offers the fact to Pauli as content rather than curating, consolidating, or pruning the knowledge base directly.
- **AC-1.4** Given Marsha verifying deliverables or discovering live operational findings or incorrect knowledge base claims, when Marsha completes evaluation, then Marsha offers the durable findings or corrections to Pauli as content.
- **AC-1.5** Given a worker executing a task via `pull` encountering a durable fact, when the worker completes task execution, then the worker offers the durable fact to Pauli, or records it in the task record under a dedicated durable facts section if Pauli is unreachable.
- **AC-1.6** Given a worker finalizing a session via `dump`, when generating the final handover report and releasing claimed tasks, then the worker offers any encountered durable facts to Pauli, or includes them in the handover report and task release under a dedicated durable facts section when operating in an isolated context where Pauli cannot be messaged.
- **AC-1.7** Given an isolated or headless worker operating without direct communication to Pauli, when the worker encounters a durable fact, then the worker records the fact under a dedicated durable facts section in the task record and handover summary so Pauli picks it up during graph reconciliation and truth maintenance.

### US-2 Filing offered facts without sprawl and at calibrated detail

As Pauli receiving offered facts from agents and workers, I want explicit filing instructions that prevent knowledge sprawl and maintain high signal-to-noise density, so that the knowledge base remains compact, up-to-date, and readily navigable by semantic search.

- **AC-2.1** Given Pauli receiving an offered fact from an agent or discovering unfiled facts in a completed task record, when Pauli files the fact, then Pauli queries existing topic notes and augments the canonical note in place rather than creating a new note, creating a separate document only when the fact represents a genuinely novel domain concept with no matching canonical note.
- **AC-2.2** Given Pauli incorporating an offered fact into the knowledge base, when Pauli updates or creates a note, then Pauli extracts durable principles, architectural decisions, invariants, and verified current-state findings while discarding ephemeral execution trivia, line numbers, temporary debugging outputs, and transient timestamps, keeping note bodies concise and within standard length budgets (30–80 lines).
- **AC-2.3** Given completed task records or session handover summaries containing unfiled durable facts under a dedicated durable facts section, when Pauli executes graph maintenance, hydration, or consolidation, then Pauli ingests the facts into the appropriate canonical topic notes and marks them incorporated.

### US-3 Unified content retirement on sight across custodian and skills

As an agent maintaining or consolidating knowledge in the knowledge base, I want one consistent rule governing content retirement across Pauli's instructions and the `remember` skill, so that conflicting, unnecessary, demonstrably false, and stale information is corrected or retired immediately on sight without ambiguity between deletion and archival.

- **AC-3.1** Given conflicting, unnecessary, demonstrably false, or stale content encountered in the knowledge base, when Pauli or an agent running the `remember` skill discovers the defect, then the agent resolves, corrects, or removes the content immediately on sight without deferring to a later pass, filing a maintenance ticket, or reserving it as the user's call.
- **AC-3.2** Given contradictory assertions between knowledge base documents or between a note and live verified reality, when Pauli or `remember` processes the conflict, then the agent resolves the contradiction to verified current state, updates the canonical note, and deletes the losing assertion outright without recording historical debate.
- **AC-3.3** Given duplicate notes, overlapping concepts, or undigested observation scraps, when Pauli or `remember` consolidates, then the agent merges the durable insight into the single canonical topic note and removes the redundant note.
- **AC-3.4** Given an assertion in the knowledge base that contradicts live system state or primary source verification, when Pauli or `remember` encounters the assertion, then the agent deletes or corrects the false statement immediately on sight.
- **AC-3.5** Given an episodic note or superseded document whose durable knowledge has been extracted to a canonical destination note, when Pauli or `remember` retires the source record, then both Pauli's instructions and the `remember` skill apply one consistent rule: set status to archived on notes that are moved to the archival repository by the archival pipeline, and delete outright without tombstones internal superseded sections and replaced atomic memories.

## Design

### Behavioral Contract

1. **Observer vs. Custodian Model**:
   - **Knowledge Scouts (Ida, Sara, James, Marsha, workers)**: Recognize durable facts encountered during interaction, dispatch, review, and execution. A durable fact is defined as: an explicit user or system decision, an architectural constraint, a verified finding about current system behavior, or an incorrect or missing assertion in the knowledge base. Scouts do not perform direct graph surgery or mutate knowledge notes; they deliver the raw fact, context, and source pointer to Pauli.
   - **Knowledge Custodian (Pauli)**: Acts as the sole curator and synthesizer of the knowledge base graph. Evaluates incoming facts, identifies canonical topic homes, updates notes in place, rejects sprawl and noise, and polices the knowledge graph for decay.
   - **Relief of James from Graph Curation**: James is relieved of direct knowledge base pruning, deletion, and consolidation duties, aligning James strictly with lead execution and review supervision under the principle of doing one thing.

2. **Dual-Path Fact Delivery**:
   - **Direct Delivery**: When communicating in session or over the agent message bus, the observing agent sends the fact directly to Pauli as content with its source pointer.
   - **Asynchronous Pickup**: When an isolated worker operates in a headless container without bus or subagent access to Pauli, it records the fact in the task record under `## Durable Facts` and includes it in the final handover report emitted by `dump`. Pauli scans these records during routine graph maintenance and consolidation passes, extracts the facts, updates the canonical notes, and clears the pending items.

3. **Anti-Sprawl Filing & Concision Standard**:
   - **Search-First, Augment-in-Place**: Pauli searches for existing topic notes before creating any document. One canonical note per topic. New documents are created only for novel concepts with zero semantic overlap with existing topics.
   - **High-Density Invariants**: Notes capture durable invariants, operational contracts, and transferable principles. Operational noise (execution transcripts, stack traces, temporary line numbers, environment-specific scratch paths) is stripped prior to writing.
   - **Concision Ceiling**: Notes are bounded to 30–80 lines (<1,500 characters) so that documents can be read and rewritten whole.

4. **Unified Four-Category Retirement Rule**:
   - **Conflicting**: Resolve to current verified truth, update the canonical note, and delete the losing claim outright.
   - **Unnecessary**: Consolidate overlapping notes into the single canonical note and delete the duplicate.
   - **Demonstrably False**: Delete or correct immediately upon discovery. False claims degrade semantic retrieval and must not persist.
   - **Stale**: When a primary note's durable knowledge is consolidated into a canonical destination note, mark the primary note with `status: archived` to enable the archival pipeline to transfer it to the historical sessions repository. Superseded subsections within living notes and replaced atomic memories are deleted outright without tombstones.

### Instruction Surfaces and Enforcement-Map Placement

The following inventory identifies every surface governing how agents recognize, offer, file, and retire knowledge base facts, along with its current placement in `specs/ENFORCEMENT-MAP.md`:

| Area | Surface | Scope & Current Text | Enforcement-Map Placement | Required Action |
| :- | :- | :- | :- | :- |
| **Agent Persona** | `plugins/ida/agents/ida.md` (`## Governing Rules`) | Defines Ida's boundaries; currently contains no direction to recognize durable facts or offer them to Pauli. | `unenforced` | Add imperative rule directing Ida to recognize durable facts (decisions, constraints, verified findings, incorrect lines) and offer them to Pauli as content. |
| **Agent Persona** | `plugins/ida/agents/sara.md` (`## Checking and Synthesising Reports`) | Directs Sara on report synthesis; currently lacks instruction to extract durable facts and offer them to Pauli. | `unenforced` | Add imperative rule directing Sara to offer durable facts from checked reports to Pauli. |
| **Agent Persona** | `plugins/ida/agents/james.md:37-38` (`## Ephemeral state`) | Instructs James: `Curate durable knowledge in the structured PKB graph... Delete outdated information, consolidate overlapping content, prune stale nodes...` | `specs/ENFORCEMENT-MAP.md:23` under `[Axiom: Do One Thing]` | Replace direct curation instructions with a clear directive to offer durable facts to Pauli, leaving graph curation to Pauli. |
| **Agent Persona** | `plugins/ida/agents/marsha.md` (`## Review Boundaries`) | Outlines Marsha's review scope; contains no instruction on routing discovered live findings or erroneous notes. | `unenforced` | Add instruction directing Marsha to offer verified durable findings and identified knowledge base errors to Pauli as content upon completing reviews. |
| **Agent Persona** | `plugins/ida/agents/pauli.md:11,15,53,169` (`## The graph is yours`, `## Maintenance`) | Directs Pauli to maintain the graph, delete out-of-date content, and `set archived on anything you do not want to delete`; lacks clear filing guidelines for offered facts. | `unenforced` (curation protocol unmapped in `specs/ENFORCEMENT-MAP.md`) | Clarify anti-sprawl filing procedure and detail thresholds for offered facts; harmonize retirement rules across the four categories (conflicting, unnecessary, false, stale). |
| **Skill** | `plugins/ida/skills/pull/SKILL.md` (`### 2. Execute and Supervise`, `### 3. Consolidate Findings`) | Instructs workers on claiming and executing; contains no guidance on capturing durable facts met during execution. | `unenforced` | Add instruction to recognize durable facts during execution and offer them to Pauli, or record them under `## Durable Facts` if Pauli is unreachable. |
| **Skill** | `plugins/ida/skills/dump/SKILL.md` (`### 2. Release Claimed Tasks`, `### 3. Emit Final Handover Report`) | Directs session finalization; lacks instructions for handing over durable facts. | `unenforced` | Add instruction to emit offered durable facts in task releases and handover summaries under `## Durable Facts`. |
| **Skill** | `plugins/ida/skills/remember/SKILL.md:48` (`## Consolidation`) | Instructs: `Delete outright -- no tombstone, no status: archived, no archive copy.` Directly contradicts Pauli's instructions and the deployed archival pipeline. | `specs/ENFORCEMENT-MAP.md:38` under `[Axiom: Single Source of Truth]` | Harmonize retirement instruction with Pauli: retire episodic source notes via `status: archived` for archival migration, while deleting superseded sections and replaced memories outright. |

### Proportional Intervention Options Pass

In accordance with `specs/enforcement/enforcement.md`, this intervention is evaluated through the enforcement pyramid from least-invasive to most-invasive:

| Level | Mechanism Category | Evaluation and Disposition |
| :- | :- | :- |
| 1 | `doctrine only` | **Insufficient.** Universal axioms (`Durable Capture`, `Single Source of Truth`, `Do One Thing`) establish the high-level intent, but existing instructions contained explicit contradictions (e.g. `remember` forbidding `archived` while `pauli` required it, and `james` being told to curate the graph directly). Doctrine alone cannot resolve contradictory instructions. |
| 2 | `instructions` (`imperative`) | **Adopted.** Adding clear, imperative instructions across agent personas (`ida`, `sara`, `james`, `marsha`, `pauli`) and skills (`pull`, `dump`, `remember`) provides the least-invasive, most proportionate mechanism. Instructions operate at the exact cognitive point of deliberation without imposing rigid mechanical hurdles or tool overhead. |
| 3 | `JIT injection` | **Rejected.** Dynamic hook injection of fact-checking reminders on every tool use would consume significant token budget and cause conversational friction without improving semantic comprehension of facts. |
| 4 | `structural` | **Rejected.** Deterministic keyword filters, AST sniffers, or regex scrapers cannot reliably assess whether an assertion represents a durable fact or an ephemeral log, violating the axiom that judgment is non-delegable. |
| 5 | `process` | **Adopted for verification.** Independent PR review lenses (`rbg`, `marsha`, `pauli`) evaluate candidate instruction changes to verify compliance with craftsmanship standards, authority boundaries, and quality requirements. |
| 6 | `post-hoc` | **Adopted for observation.** Normal session traces and git commit history record fact-offering events and graph updates for ongoing observability. |

### Evidence for the Move

1. **Direct User Directive**: The framework principal explicitly ordered this capability (console goal, 2026-11-03):
   > "ensure agents recognise important facts and offer them to pauli, and that pauli knows how to file things without making the PKB sprawl, knows the level of detail we should keep, actively consolidates knowledge and corrects conflicting, unecessary, demonstrably false, and stale information, and does all that fast and efficiently".
   > Under the direct user instructions rule, this directive carries an immediate execution obligation.
2. **Elimination of Active Instruction Contradiction**: `plugins/ida/skills/remember/SKILL.md:48` explicitly ordered agents to "Delete outright -- no tombstone, no status: archived, no archive copy", while `plugins/ida/agents/pauli.md:15` commanded Pauli to "set archived on anything you do not want to delete", and a completed framework task deployed an automated pipeline that moves notes marked `status: archived` to the historical sessions repository. This direct conflict created operational confusion and inconsistent graph cleanup.
3. **Role Boundary Realignment**: `plugins/ida/agents/james.md:38` instructed James to delete, consolidate, and prune the knowledge base. This violated the core division of labor where Pauli is the sole knowledge base custodian, creating a risk of conflicting simultaneous graph edits during parallel execution.
4. **Preventing Knowledge Sprawl**: Prior practice suffered from sprawl due to agents creating shallow, fragmented notes or leaving valuable decisions buried inside ephemeral task records. Establishing an explicit anti-sprawl filing rule with clear concision limits protects knowledge retrieval performance.

### Enforcement Map Extract (for Downstream Implementation)

The following rows will be updated or incorporated into `specs/ENFORCEMENT-MAP.md` during downstream implementation when the instruction text is merged:

| Rule | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| [Axiom: Durable Capture](../plugins/rbg/skills/axioms/durable-capture.md) -- Capture knowledge not verdicts; agents offer durable facts to Pauli; Pauli files without sprawl and retires obsolete content on sight. | instructions, JIT injection, process | imperative, warning, required gate | `plugins/rbg/skills/axioms/durable-capture.md:9`, `plugins/ida/agents/ida.md`, `plugins/ida/agents/sara.md`, `plugins/ida/agents/james.md`, `plugins/ida/agents/marsha.md`, `plugins/ida/agents/pauli.md`, `plugins/ida/skills/pull/SKILL.md`, `plugins/ida/skills/dump/SKILL.md`, `plugins/ida/skills/remember/SKILL.md`, `wf-reconcile.md` |
| [Knowledge Base Curation: Offering, Anti-Sprawl Filing & Unified Retirement](agents/offering-filing-and-retiring-pkb-facts.md) -- Agents offer durable facts to Pauli; Pauli files into canonical notes without sprawl; conflicting, unnecessary, false, and stale content is retired on sight. | instructions, process | imperative, required gate | `plugins/ida/agents/pauli.md`, `plugins/ida/skills/remember/SKILL.md`, `plugins/ida/agents/james.md`: Governs fact recognition across agents, anti-sprawl consolidation in Pauli, and consistent status: archived vs outright deletion rules. |
| [Axiom: Do One Thing](../plugins/rbg/skills/axioms/do-one-thing.md) -- Execute precisely the requested task to the specified standard; agents leave knowledge graph curation exclusively to Pauli. | instructions, structural, process | imperative, scoped, required gate | `plugins/rbg/skills/axioms/do-one-thing.md:9-21`, `plugins/ida/agents/james.md:10-38`, `plugins/ida/agents/pauli.md:13-18`: Restricts direct knowledge graph mutation to Pauli; coordinating and execution agents offer facts rather than performing direct curation. |

### Outcome-Level Build Criteria (for Downstream Implementation)

Stage 2 implementation must satisfy the following verifiable criteria across the specified instruction files:

- **BC-1 (Ida Fact Offering)**: `plugins/ida/agents/ida.md` carries an imperative rule instructing Ida to recognize durable facts (decisions, constraints, verified current-state findings, or incorrect knowledge base claims) and offer them to Pauli as content without directly editing notes or creating tasks.
- **BC-2 (Sara Fact Offering)**: `plugins/ida/agents/sara.md` carries an imperative rule instructing Sara to extract durable facts from incoming worker reports and offer them to Pauli as content.
- **BC-3 (James Scope Realignment)**: `plugins/ida/agents/james.md` replaces direct knowledge graph curation instructions with a requirement to recognize durable facts and offer them to Pauli as content, leaving graph curation to Pauli.
- **BC-4 (Marsha Fact Offering)**: `plugins/ida/agents/marsha.md` instructs Marsha to offer verified operational findings and identified knowledge base errors to Pauli as content upon concluding reviews.
- **BC-5 (Worker Skills Fact Handling)**: `plugins/ida/skills/pull/SKILL.md` and `plugins/ida/skills/dump/SKILL.md` instruct workers to recognize durable facts and offer them to Pauli, or record them under `## Durable Facts` in the task record and handover summary if operating in an isolated context where Pauli is unreachable.
- **BC-6 (Pauli Anti-Sprawl Filing & Concision)**: `plugins/ida/agents/pauli.md` specifies the anti-sprawl filing process (search first, augment canonical notes in place, create new notes only for novel concepts) and concision thresholds (retaining principles and verified state, stripping execution trivia, targeting 30–80 lines).
- **BC-7 (Unified Content Retirement on Sight)**: `plugins/ida/agents/pauli.md` and `plugins/ida/skills/remember/SKILL.md` define an identical, consistent rule for retiring content on sight across the four categories:
  1. _Conflicting_: resolve to verified truth and delete losing assertion outright.
  2. _Unnecessary_: merge duplicates into canonical note and delete redundant notes.
  3. _Demonstrably false_: delete or correct immediately on sight.
  4. _Stale_: set `status: archived` on episodic notes destined for the sessions archival repository once durable content is extracted; delete outright without tombstones internal superseded sections and replaced atomic memories.
