---
id: related-sections-ban
title: Enforcement Design -- Ban on Related Sections in PKB Bodies
status: ready
type: spec
tags: [enforcement, pkb, task-contract, graph-density, review]
---

# Ban on Related Sections in PKB Bodies

This specification establishes the enforcement design for the standing rule governing Personal Knowledge Base (PKB) bodies: graph density is achieved exclusively through structured frontmatter edges, and no PKB body may carry a dedicated "related tasks", "related notes", or cross-reference section. A body links another node exclusively where it substantively discusses that node in prose, with an explicit structural exception for Maps of Content (MoCs) and indexes whose defining purpose is indexing nodes.

## User stories

### US-1 Elimination of Dedicated Related Sections across All PKB Bodies

As a knowledge base curator, planner, or reviewer, I want all PKB node bodies to omit dedicated "related tasks", "related notes", or cross-reference list sections, so that relationship topology remains single-sourced in header edges rather than accumulating stale prose duplicates.

- **AC-1.1** Given any newly created or updated PKB task, note, or document, when the body content is authored or released, then the body contains zero dedicated sections titled "Related Tasks", "Related Notes", "Related Documents", "Cross-References", "See Also", or equivalent variations.
- **AC-1.2** Given a task body carrying frontmatter relationship edges (`parent`, `depends_on`, `contributes_to`, `supersedes`), when the body is formatted, then the body omits bulleted lists or enumerations duplicating those relationships as unstructured text.
- **AC-1.3** Given an index or Map of Content (`type: index` or `type: moc`), when its body is authored, then the body may link related nodes in its index sections because curating navigational node pointers is the intrinsic structural function of an index.

### US-2 Substantive Discussion Boundary for Body Wikilinks

As an execution worker or planning agent, I want clear boundaries governing when wikilinks are permitted in body text, so that essential context can be linked without degrading into link laundry lists.

- **AC-2.1** Given a PKB task or note body, when a wikilink to another node is included, then the link appears within explanatory or directive prose that directly discusses the specific referenced node.
- **AC-2.2** Given a task body `## Pointers` section, when pointers are provided, then each pointer references durable knowledge (specifications, architecture notes, reference standards) with an explicit purpose statement, and never links sibling tasks or loose task lists.

### US-3 Evidence Citation Boundary for Work-Unit Release Reports

As a reviewer or coordinator evaluating task releases, I want worker completion reports to cite primary evidence for findings without compiling cross-reference indexes of consulted nodes, so that release reports remain concise and focused on verification.

- **AC-3.1** Given a worker composing a task release report (`## Report` argument or premise-check block), when the worker cites authority for a claim or finding, then the worker cites the specific factual basis directly supporting that claim.
- **AC-3.2** Given a worker concluding execution, when formatting the release report, then the worker omits aggregate "Related PKB records", "Consulted tasks", or cross-reference indexes.

## Design

### 1. Architectural Principle: Density from Edges, Not Prose Lists

The PKB graph is designed to be dense, but density is established through structured frontmatter edges (`parent`, `depends_on`, `contributes_to`, `supersedes`), not through narrative task-to-task cross-references in body markdown.

Prose lists of related tasks or notes introduce severe failure modes:

1. **Competing Sources of Truth:** Frontmatter edges are updated dynamically by lifecycle tools and graph algorithms, whereas body text remains static and immediately drifts out of date.
2. **Search Index Pollution:** Semantic and vector searches return obsolete body link lists as current relevance signals, misdirecting retrieval.
3. **Context Window Waste:** Unnecessary laundry lists consume scarce context tokens across every agent turn that hydrates or reads the task.

The rule therefore prohibits dedicated related-work sections while preserving the two legitimate linking paths:

1. **Substantive Discussion:** Mentioning and linking a specific node where the body actively discusses that node's contents, decisions, or constraints.
2. **Structural Indexes:** Maps of Content and indexes whose canonical function is curating links.

### 2. Enforcement-Map Extracts (Current State vs Target State)

#### Current State across PKB Body Writing Surfaces

Six distinct surfaces generate or modify PKB body content today. An evaluation of each surface reveals where the ban was missing or scoped away:

| Writing Surface | Primary Agents & Tools | Governing Mechanism Today | Current Severity | Observed Failure Mode |
| - | - | - | - | - |
| **Planning & Reification** | Pauli (`reify`, `decompose`, graph upkeep) | `instructions` (`plugins/ida/agents/pauli.md:63`) | imperative | Instruction stated an absolute ban ("never link tasks") rather than the user's calibrated rule (no related sections; link only when discussing; MoCs exempt); did not reach other agents. |
| **Direct Task Creation & Intake** | Ida, front agents (`q`, `portal_codemode_execute` -> `create_task`) | Unenforced (no instruction, no rule in `.agents/rules/RULES.md`) | none | Ida created tasks with `## Context` lines listing "Related: [[]], [[]]" linking parents already wired as edges (#3337). |
| **Worker Release Reports** | Polecat workers, James (`/dump`, `/pull`, `wf-finish`, `update_body`, `release_task`) | Unenforced / scoped away (`specs/enforcement/task-contract.md:65`) | none | `task-contract.md` scoped the ban strictly to capture-time brevity (50-150 words). Workers compiled 17-link "Private Cross-Reference Indexes" in release reports (#3337) because the evidence contract demanded citations and lacked reach boundaries. |
| **Durable Knowledge Capture** | All agents (`remember`, `daily`, `create`, `update_body`) | Unenforced | none | No rule barred "related notes" sections in captured topic notes or daily notes. |
| **Sibling Defect Capture** | All agents (via `## Pointers` in task templates) | `doctrine only` (`specs/meta/naming-and-decisions.md:86`) | none | Minimal template `## Pointers` accepted unconstrained sibling task cross-links (#3337). |
| **Substrate / MCP Level** | Upstream PKB server (`create`, `create_task`, `update_body`) | Unenforced (no mechanical validation on body headings) | none | Server accepts any body text without validation. |

#### Target Enforcement-Map Extract

In accordance with `specs/enforcement/enforcement-map.md`, the rule is entered into `specs/ENFORCEMENT-MAP.md` as an escalated multi-carrier rule combining universal project-rule instructions with mandatory reviewer verification:

```markdown
| [Rule: Ban on Related Sections in PKB Bodies](enforcement/related-sections-ban.md) -- PKB graph density comes from header edges; dedicated related tasks or notes sections in bodies are prohibited. | instructions, process | imperative, required gate | `.agents/rules/RULES.md:70`, `.agents/rules/pkb-body-linking.md:1-25`, `specs/enforcement/task-contract.md:65-75`, `plugins/ida/agents/pauli.md:63`, `plugins/ida/skills/dump/SKILL.md:20`, `wf-dialectical-review.md:35` |
```

### 3. Evidence for the Move

Empirical forensic analysis across recent graph modifications (documented in GitHub issues #3337 and #3338) proves that existing prompt-only placement in a single persona file does not hold:

1. **Empirical Distribution:** A scan of 600 tasks modified between 2026-10-15 and 2026-10-31 revealed 16 task bodies linking three or more other tasks in body text.
2. **Traced Worker Release Leakage:** A polecat worker session on an assessment task loaded `task-contract.md`, but wrote a release body via `update_body` containing a "Private Cross-Reference Index" with 17 wikilinks (9 to tasks) and an Argdown basis block citing further task IDs (#3337). The worker interpreted the evidence contract's demand for cited claims as an invitation to catalog all consulted tasks.
3. **Traced Direct Write Leakage:** A user-facing Ida session created an investigation task via `create_task` with a `## Context` line "Related: [[]], [[note]], [[note]]" referencing its own parent (#3337). No span in the session loaded the ban because the rule was absent from repository project rules.
4. **Untraced Sibling Cross-Linking:** Defect tasks under one project carried reciprocal lists of sibling defect IDs under `## Pointers` ("fix the two together"), bypassing graph edges.
5. **Principal Mandate:** The user explicitly directed elevating this rule on the enforcement map, clarifying that graph density belongs in header edges, dedicated related sections are banned, bodies link nodes only where discussed in text, and MoCs link in body by definition.

### 4. Enforcement Pyramid & Proportionality Analysis

Following `specs/enforcement/enforcement.md`, intervention is calibrated to the least invasive mechanism that completely answers the evidence:

1. **`doctrine only` (Rejected):** Present in `specs/meta/naming-and-decisions.md`; failed because executing agents and workers do not load architectural design specs at runtime.
2. **`instructions` (`imperative`) (Selected as Primary Carrier):**
   - The failure of instructions was a coverage defect, not a behavioral refusal: the ban was never formulated as a universal project rule, was missing from front-agent personas, and was scoped away from worker release contracts.
   - Deploying the rule as an always-on Project Rule in `.agents/rules/` ensures every agent across all harnesses (Claude Code, Antigravity, Jules) receives the directive at turn start.
   - Clarifying `specs/enforcement/task-contract.md`, `pauli.md`, and `dump/SKILL.md` eliminates the scope gap between capture brevity and release report evidence.
3. **`JIT injection` (Deferred):** Runtime injection of reminder snippets on PKB write tool calls adds continuous token overhead; instructions and review gates must be exhausted first.
4. **`structural` (Rejected at this stage):**
   - Programmatic regex or AST linters checking body text for headings like `## Related` or banning `[[task-...]]` links violate `judgment-non-delegable` and `human-readability-first`.
   - Mechanical filters cannot distinguish between a prohibited "Related tasks" list, an authorized substantive prose discussion of a dependency, and an index node.
   - Substrate modifications in the PKB server represent heavier intervention that is premature before universal instructions and review gates are deployed.
5. **`process` (`required gate`) (Selected as Companion Review Lens):**
   - Reviewers (`marsha`, `rbg`, `pauli`) evaluate candidate changes, task bodies, and release handbacks against the related-sections ban during dialectical review and QA workflows (`wf-dialectical-review`, `wf-qa`, `wf-strategic-fit`).
6. **`post-hoc` (`observability`) (Retained):**
   - Phoenix span traces and graph audit queries monitor PKB write payloads to measure compliance across sessions.

### 5. Proposed One-Step Move: Universal Rule & Lifecycle Harmonization

The one-step move implements the rule across four synchronized areas:

1. **Universal Project Rule (`.agents/rules/RULES.md` and `.agents/rules/pkb-body-linking.md`):**
   - Declares the standing rule for all agents: PKB graph density comes from header edges. Dedicated "Related Tasks" or "Related Notes" sections are forbidden across all bodies. Bodies link another node only where it is substantively discussed; MoCs and indexes link in body by definition.
2. **Task Contract Invariant (`specs/enforcement/task-contract.md`):**
   - Extends the brevity invariant to explicitly govern the full lifecycle through release: release reports (`## Report`) and evidence citations must cite primary factual sources for claims, and are forbidden from assembling aggregate cross-reference lists or consulted-node inventories.
3. **Pauli Persona Alignment (`plugins/ida/agents/pauli.md`):**
   - Replaces the overly rigid "never link tasks" phrasing with the user's exact specification: header edges carry density, bodies link nodes only where discussed in text, MoCs link in body by definition, and dedicated related sections are strictly banned.
4. **Release and Reporting Skills (`plugins/ida/skills/dump/SKILL.md`, `plugins/ida/skills/premise-check/SKILL.md`):**
   - Explicitly instructs workers that reporting evidence requires citing specific supporting facts, forbidding the compilation of related-work lists or basis catalogs.
5. **Review Lens Verification (`specs/enforcement/reviewer-class-standard-check.md`, `wf-dialectical-review.md`, `wf-qa.md`):**
   - Instructs quality and compliance reviewers to verify that task bodies, release handbacks, and documentation PRs contain zero dedicated related-work sections.

### 6. Outcome-Level Build Criteria for Implementation (Stage 2: Build)

The implementation worker on Stage 2 must satisfy the following verifiable criteria:

1. **Project Rule Declaration:** A dedicated project-local rule file `.agents/rules/pkb-body-linking.md` is authored with `trigger: always_on`, and referenced in `.agents/rules/RULES.md`, stating the ban on dedicated related sections and the discussion/index exceptions.
2. **Task Contract Harmonization:** `specs/enforcement/task-contract.md` carries an updated task body and evidence invariant explicitly barring related-work cross-reference sections across both capture bodies and release reports.
3. **Pauli Persona Calibration:** `plugins/ida/agents/pauli.md` accurately reflects the user's rule and exception definitions.
4. **Release Reporting Guidelines:** `plugins/ida/skills/dump/SKILL.md` and `plugins/ida/skills/premise-check/SKILL.md` instruct workers that basis citations are strictly direct claim evidence, barring aggregate cross-reference lists.
5. **Enforcement Register Update:** `specs/ENFORCEMENT-MAP.md` is updated with the new 4-column row complying with the concision and schema rules of `specs/enforcement/enforcement-map.md`.
6. **Review Lens Integration:** Review templates (`wf-dialectical-review.md`, `wf-qa.md`) include verification of the related-sections ban in artifact checks.

### 7. Baseline-vs-Changed Verification Protocol & Observable Impact

#### Specimen Scenarios (Derived from Issue #3337)

- **Scenario A (Worker Handback):** An assessment worker finishes a task where 15 PKB nodes were read during background orientation.
  - _Baseline Behavior:_ Worker writes `## Report` containing a "Private Cross-Reference Index" listing 17 wikilinks to tasks and notes.
  - _Changed Behavior:_ Worker writes `## Report` answering each acceptance criterion with specific primary evidence (quoted command outputs, test runs, file citations); zero cross-reference lists or consulted-task rosters are emitted.
- **Scenario B (Direct Task Creation):** An agent session creates an investigation task with an existing parent epic.
  - _Baseline Behavior:_ Agent writes `## Context` with "Related: [[parent-epic]], [[sibling-task]]".
  - _Changed Behavior:_ Agent sets `parent: <id>` in frontmatter, and writes body context describing the defect without duplicating the parent or siblings in body text.

#### Observable Verification Metric

A longitudinal scan of 600 tasks modified following deployment of the build stage will show 0 task bodies containing sections matching `## Related Tasks`, `## Related Notes`, or `## Cross-References`, and a 90%+ reduction in task-to-task wikilinks outside MoCs and explicit textual discussions.

## Open questions

None. The architectural boundaries, carrier mechanisms, and build criteria are fully specified.
