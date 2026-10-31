---
id: two-reader-reports-and-tasks
title: Two-Reader Task Layout and Readable Agent Reports Design
status: draft
type: spec
tags: [enforcement, readability, task-contract, reify, pull-request, review, rbg]
---

# Two-Reader Task Layout and Readable Agent Reports Design

This specification establishes the architectural design, template specifications, enforcement analysis, and rule amendments for readable agent comments and two-reader task layouts across `academicOps`.

- **Stated Purpose:** Eliminate unreadable, bloated agent comments on human-visible surfaces (pull request descriptions, compliance review comments, handback notes) and decouple supervisor process evidence from reviewer quality criteria on task records.
- **Primary Audience:** Framework architects, system developers, workflow designers, planning agents, and compliance auditors.
- **Companion Specification:** [`specs/enforcement/agent-comments.md`](agent-comments.md) defines the standalone one-feature contract for agent comments.

## 1. Context and Problem Statement

### 1.1 Observed Failures from PR 3265

Investigation of framework operations--specifically PR #3265 (enforcement map specification and register rewrite), its task record, pull request description, and compliance review comment--reveals nine recurring failure patterns when agents write for human consumption:

1. **Coined compounds in headings:** Headings use invented multi-word Title Case terms ("Closed Binary Inclusion Filter", "Four-Column Schema & Detail Invariants", "non-instruction carrier category"). None is a standard industry term of art; each translates to a simpler phrase. Bold Title Case misleads readers into searching for non-existent formal constructs.
2. **Bold labels followed by circular restatements:** Headings echo their content immediately after the colon (e.g. `Universal Axiom Standing: It is a universal axiom declared in the framework's universal axiom set.`).
3. **The all-clear itemized:** All-pass evaluation lists enumerate every passed check with repetitive justifications (e.g. five checklist questions yielding five "Yes" paragraphs), producing visual clutter without informative variance.
4. **Provenance and blessing words over relay results:** Relaying agents apply evaluative endorsement words ("Independent Compliance Review", "Clean pass", "Verified by compliance reviewer") over another component's output rather than reporting direct observations.
5. **Cross-surface duplication:** Core inclusion criteria and tables appear three times verbatim: once in the specification, once in the PR description, and once in the compliance review comment. The verdict `PASS` appears twice within a single comment.
6. **Bare unglossed tokens:** Shorthand tokens, flags, and rule coordinates (`[DISABLED]`, `[MAP DRIFT]`, `AC-1.1 through AC-2.3`, `US-1`, `R5.6`, `JIT`) appear with zero inline explanation for external readers.
7. **One report blending two distinct readers:** A single task heading (`## Acceptance`) forces workers to blend the supervisor's process-verification question (_did I complete the assigned steps with valid evidence?_) with the reviewer's output-quality question (_is the deliverable substantively good, clear, and fit for purpose?_).
8. **Criteria testing process evidence rather than substantive aims:** Task acceptance criteria measure evidence collection ("recorded", "compared", "listed") rather than substantive aims. When an ask directs "make the register shorter", the task records before-and-after line counts rather than bounding the output to an observable length target.
9. **Stale PR descriptions across pipeline stages:** Multi-stage branches push subsequent commits (e.g. rewriting `specs/ENFORCEMENT-MAP.md`) while the PR description remains frozen at the initial specification stage.

### 1.2 Root Cause Analysis

Language models trained on developer platforms interpret `Acceptance criteria` as the ticket's mechanical "definition of done" for the supervisor. Because the task template provides a single `## Acceptance` heading, the reviewer's distinct question has no home. Workers default to filing process evidence under acceptance, producing blended documents that satisfy automated gates while remaining opaque to human reviewers.

## 2. The Agent Comment Standard (AC1)

The one-feature contract governing agent comments is codified in [`specs/enforcement/agent-comments.md`](agent-comments.md).

### 2.1 Conformance Checklist (`specs/meta/writing-specs.md`)

| Question | Assessment | Evidence |
| :- | :- | :- |
| **1. Does it cover exactly one feature?** | **YES** | Covers solely the contract for short-form text posted by agents for humans in passing. Implementation details and task layout live here in the companion design. |
| **2. Can every acceptance criterion be marked pass or fail by observation?** | **YES** | US-1 through US-10 contain 10 Given/When/Then acceptance criteria (AC-1.1 through AC-10.1) testable by reading the comment alone without inspecting code or repository state. |
| **3. Does every design requirement trace to a story?** | **YES** | The ten invariants in § 2 trace 1:1 to user stories US-1 through US-10. |
| **4. Is it free of implementation detail, enforcement, links to other parts of the framework, and statements of what the feature does not do?** | **YES** | Contains zero relative links, no mention of Python files, hooks, regex parsers, or specific personas, and avoids non-goal disclaimers. |
| **5. Would it survive unchanged if any other feature were rewritten?** | **YES** | Invariants (outcome first, plain language, one screen, collapsed all-clear) govern human-visible comment text regardless of execution runtime or repository tooling. |

## 3. The Ten Tests and PR 3265 Specimen Analysis (AC2)

Each of the ten rules in the comment standard can be evaluated by an observer reading the comment alone:

| # | Rule | Observational Test | Specimen from PR 3265 | Evaluation |
| - | - | - | - | - |
| **1** | **Outcome first** | Stop after line one; do you know what happened and to what? | Review comment: Line 1: `## Independent Compliance Review Verdict: PASS`. PR description: Line 1: `## Summary`, Line 3: `Establishes a dedicated specification...` | Review passes rule 1; PR description fails rule 1 (stop after line 1 gives no outcome or object). |
| **2** | **Show, don't assert** | Can each claim be matched to something the reader could open? | Review comment: `reviewed against specs/meta/writing-specs.md and framework axioms.` | Fails rule 2: asserts check against framework axioms, but shows zero axioms, links, or checks. |
| **3** | **Plain words** | Would a capable reader who has not opened the spec understand it? | PR description: `Four-Column Schema & Detail Invariants`, `Closed Binary Inclusion Filter`. Review: `Closed Row-by-Row Inclusion Filter`. | Fails rule 3: Title Case coined compounds sound like non-existent formal external constructs. |
| **4** | **Bold is a heading, not a label** | No sentence after a bold phrase repeats its meaning. | Review comment: `1. **Universal Axiom Standing:** It is a universal axiom declared in the framework's universal axiom set;` | Fails rule 4: bold label followed immediately by circular restatement. |
| **5** | **Lists are lists** | No line contains "; or", "; and", or two claims. | Review comment: `1. **Universal Axiom Standing:** ...; OR`. PR description: Key Changes #2 contains three distinct claims. | Fails rule 5: chained conditional operators and multiple claims per bullet. |
| **6** | **Collapse the all-clear** | No list in which every item ends "Yes" or "passed". | Review comment: Items 1 to 5 under `Review Checklist`: 5 questions, 5 "Yes" answers, zero defects. | Fails rule 6: itemizes 100% all-clear passes over 10 lines instead of collapsing to a single summary line. |
| **7** | **Attribute, don't bless** | Each evaluative endorsement word is the writer's own direct observation or is deleted. | Review: `Clean pass (secret detection...)`. PR description: `Verified by compliance reviewer... with a PASS verdict.` | Fails rule 7: relaying agents bless other agents' work with "Verified", "Independent", "Clean pass". |
| **8** | **Say it once** | No paragraph also appears in a linked file; verdict appears once. | Review comment: Verbatim copy of inclusion filter from `specs/enforcement/enforcement-map.md`. Verdict `PASS` appears twice. | Fails rule 8: duplicates spec text; repeats verdict token. |
| **9** | **Gloss every token** | No bare `[FLAG]`, `AC-1.1`, `R5.6`, `JIT`. | Review comment: bare unglossed tokens `US-1`, `US-2`, `AC-1.1`, `JIT injection`, `R5.6`, `[DISABLED]`, `[MAP DRIFT]`. | Fails rule 9: assumes internal coordinate jargon without glossing. |
| **10** | **One screen** | At most 12 lines, about 120 words; headings only with three or more sections. | Review comment: 22 lines, 230 words, 4 headings. PR description: 24 lines, 218 words. | Fails rule 10: exceeds line ceiling (22 > 12) and word ceiling (230 > 120). |

### 3.1 Specimen Compliance Review Comment Rewrite

Applying the ten rules to the PR #3265 compliance review comment transforms a 230-word, 22-line comment into a scannable 56-word, 5-line comment:

```markdown
PASS: specs/enforcement/enforcement-map.md (spec) and ENFORCEMENT-MAP.md (register)

- Writing-specs checklist: 5 of 5 questions pass (single feature, observable Given/When/Then criteria, design traces to stories, no implementation mechanisms, decoupled).
- Inclusion filter: 52 rows retained; 21 single-instruction rules without automated gates relocated to instruction files.
- Checks: pre-commit hooks clean; 742 unit tests passed.
```

## 4. The Two-Reader Task Layout (Goal 2)

### 4.1 Layout Schema

The reified task contract splits the single `## Acceptance` heading into two purpose-built sections, explicitly naming the reader each section serves:

```markdown
## Ask

[ Verbatim ask, who, when, source id. Immutable referent. ]

## Goal

[ One sentence: what is true of the world when done. ]

## Quality bar

[ For the reviewer: observable properties of the output. Stated as measurable end states, not process tasks. ]

## Evidence

[ For the supervisor: what the worker must show to close the task. Process deliverables, citations, test runs. ]

## Instructions

[ Concise numbered imperative steps composed from workflow templates. ]

## Outputs

[ Two documents, each naming its reader and the heading it answers:

1. Pull request description: answers Quality bar in order under the comment standard for the reviewer.
2. Handback report: answers Evidence checklist items by id under the report argument standard for the supervisor. ]

## Report

[ Handback proof: Chained Toulmin Argdown report argument answering Evidence ids. ]

## Appendix: Sources

[ Workflow templates and skills composed for this task. ]
```

### 4.2 Rules for the Task Writer (`/reify`)

1. **Quality criteria state observable output properties:** Every aim in `## Ask` or `## Goal` translates into a quality criterion with a concrete target (e.g. `≤ 150 lines`, `passes lint with 0 warnings`). Where the brief says "too long", the task writer sets a target; "record the length" never substitutes for a quality target.
2. **Evidence criteria own verification process:** "Recorded", "compared", "listed", and command output citations belong strictly under `## Evidence`.
3. **Headings name their reader:** `Quality bar` serves the code/PR reviewer; `Evidence` serves the supervisor closing the task.
4. **Outputs name two distinct documents:**
   - The _Pull Request Description_ answers `## Quality bar` in order under the comment standard, omitting internal session logs.
   - The _Task Handback Report_ answers `## Evidence` items by id under the report argument standard, repeating nothing from the PR description.
5. **Legacy compatibility:** Tasks already queued on the graph retain their existing `## Acceptance` heading without forced rewriting.

## 5. Surfaces, Carriers, and Enforcement-Map Placements (AC3)

Goal 2 defines five operational surfaces. Each surface is mapped below to its carrier file, mechanism, severity, enforcement-map row, and empirical justification:

| Surface | Carrier File(s) | Mechanism & Severity | Enforcement-Map Row | Justification & Evidence |
| :- | :- | :- | :- | :- |
| **1. Two-Reader Task Writer** | `plugins/ida/skills/reify/SKILL.md:56-88`, `specs/enforcement/task-contract.md:65-67` | `instructions`, `imperative` | `[Rule: In-Session Task Contract]` | Specimen PR 3265 task conflated evidence collection with substantive quality. Splitting headings stops blending and guarantees measurable targets. |
| **2. PR Description Template** | `plugins/ida/skills/workflow-library/workflows/wf-finish.md`, `wf-code-task-base.md` | `instructions`, `imperative` | `[Axiom: Human Readability First]` & `[Rule: PR Risk Taxonomy]` | Current PR descriptions (PR 3265) run >200 words, use coined compounds, duplicate specs, and go stale across commits. Template enforces ≤12 lines and outcome-first structure. |
| **3. Handback Template** | `plugins/ida/skills/dump/SKILL.md:30-43`, `plugins/ida/skills/pull/SKILL.md:26-28` | `instructions`, `imperative` | `[Rule: The Evidence Contract]` | Workers duplicate PR prose into task handbacks. Dedicated handback template answers `## Evidence` items by id using Argdown without repeating PR prose. |
| **4. Advisory Review Lens** | `plugins/ida/skills/workflow-library/workflows/wf-rbg.md`, `plugins/rbg/agents/rbg.md` | `process`, `advisory check` | `[Axiom: Human Readability First]` | Systematic evaluation of comments against 10 rules. Configured as `advisory check`: **never blocks** automated workflows, returns `PASS` or `REVISE` with rule numbers and specimens, leaving the merge call to humans. |
| **5. Compliance Reviewer Verdict Comment** | `plugins/rbg/agents/rbg.md:85-100`, `wf-rbg.md:45-60` | `instructions`, `imperative` | `[Axiom: Human Readability First]` | RBG's legacy review comments run 230+ words and 22 lines, breaking 9 of 10 rules. Updating output schema to the comment standard produces concise 50-word verdicts. |

### 5.1 Enforcement Pyramid Analysis (`specs/enforcement/enforcement.md`)

Evaluating the proposed mechanisms against the enforcement options pass:

1. **`doctrine only`:** Insufficient. Principles in axioms alone did not prevent 230-word comments on PR 3265.
2. **`instructions` (`imperative`):** Primary carrier for surfaces 1, 2, 3, and 5. Clear prompt directives in `reify`, `dump`, `wf-finish`, and `rbg` shape generation at authoring time.
3. **`JIT injection`:** Unnecessary. Authoring instructions and workflow templates govern generation without JIT hook overhead.
4. **`structural`:** Explicitly rejected for comment text. Deterministic regex or line-counting CI linters violate `human-readability-first` and `judgment-non-delegable`.
5. **`process` (`advisory check`):** Selected for Surface 4. The 10-rule review lens runs inside RBG compliance review as an advisory check that highlights defects without blocking automated pipelines.
6. **`post-hoc` (`observability`):** PR comments and task records provide transparent audit trails in git and GitHub history.

## 6. Rule Conflict Audit and Drafted Amendments (Goal 3 & AC4)

A repository-wide audit was conducted across `.agents/rules/`, `plugins/rbg/skills/axioms/`, `specs/enforcement/`, `specs/meta/`, and `plugins/ida/skills/`. Six existing rules and specifications reference legacy single-reader structures:

### 6.1 Audit Findings & Amendments

#### 1. Task Intake Contract in `plugins/ida/skills/pull/SKILL.md` (lines 14–16)

- **Current Text:** "On receiving a direction or work brief, the receiving agent must record its own summary stating deliverables as a frozen `## Acceptance` checklist on a PKB task before work starts."
- **Conflict:** Enforces the singular `## Acceptance` heading for frozen intake deliverables.
- **Drafted Amendment:**
  ```markdown
  On receiving a direction or work brief, the receiving agent must record its own summary stating deliverables as a frozen checklist on a PKB task before work starts: under `## Evidence` (and quality expectations under `## Quality bar`) for two-reader tasks, or under `## Acceptance` for legacy tasks.
  ```
- **Implications:** Enables workers to freeze evidence requirements under the new heading while maintaining full backward compatibility for existing tasks.

#### 2. Project Task Template Rule in `.agents/rules/RULES.md` (lines 65–70)

- **Current Text:** "Task bodies are strictly concise: Follow the canonical template in `specs/meta/naming-and-decisions.md` (Goal, Deliverable, Scope, Acceptance criteria, Pointers)."
- **Conflict:** Lists `Acceptance criteria` as the mandatory section name.
- **Drafted Amendment:**
  ```markdown
  Task bodies are strictly concise: Follow the canonical template in `specs/meta/naming-and-decisions.md` (Goal, Deliverable, Scope, Quality bar, Evidence, Pointers; or legacy Acceptance criteria).
  ```
- **Implications:** Authorizes both two-reader task authoring and legacy single-reader task bodies across project guidelines.

#### 3. Canonical Task Template in `specs/meta/naming-and-decisions.md` (§ 5, lines 89–105)

- **Current Text:** The template defines `## Acceptance criteria` with items `AC1`, `AC2`.
- **Conflict:** Does not provide the two-reader structure.
- **Drafted Amendment:** Update the template to include `## Quality bar` (for reviewer) and `## Evidence` (for supervisor), adding an explanatory note that queued tasks retain `## Acceptance`.
- **Implications:** Aligns task capture documentation with the two-reader standard.

#### 4. Task Brevity & Outcome Invariants in `specs/enforcement/task-contract.md` (lines 65, 67)

- **Current Text:** Mandates expansion into `(Ask, Goal, Context, Acceptance, Instructions, Output, Report, Appendix: Sources)`.
- **Conflict:** Prescribes `Acceptance` as the sole contract section.
- **Drafted Amendment:**
  ```markdown
  ...expanded by `/reify` into the dispatchable contract (`Ask`, `Goal`, `Context`, `Quality bar`, `Evidence`, `Instructions`, `Outputs`, `Report`, `Appendix: Sources`). `Quality bar` defines observable end-state output properties for the reviewer; `Evidence` defines verifiable deliverable receipts for the supervisor.
  ```
- **Implications:** Formally codifies the two-reader contract in the architectural work-unit specification.

#### 5. Compliance Review Output Schema in `plugins/rbg/agents/rbg.md` and `wf-rbg.md`

- **Current Text:** Prescribes a multi-section markdown schema with `### Proportion Assessment`, `### Mechanisms`, `### Required Changes`, and `### Suggested Improvements`, which easily reaches 200+ words.
- **Conflict:** Violates Rule 10 (≤12 lines, ≤120 words), Rule 6 (collapse all-clear), and Rule 1 (outcome first) when posted as a GitHub comment.
- **Drafted Amendment:**
  ```markdown
  When posted as a pull request comment or external notice, the compliance review verdict follows the agent comment standard:
  Line 1: `VERDICT: <object>` (e.g. `PASS: <spec-path>`)
  Bullet 1: Collapsed all-clear summary (count of passed axioms and rules)
  Bullet 2+: Itemized Required Changes (rule violations with pinpoint citations)
  Bullet N: Suggested Improvements (non-blocking suggestions)
  Bounded strictly to ≤ 12 lines and ≤ 120 words. Full mechanism traces remain in internal execution logs.
  ```
- **Implications:** Restricts public GitHub review noise while preserving exhaustive evaluation in telemetry.

#### 6. Evidence Contract Frozen Acceptance in `specs/enforcement/evidence-contract.md` (line 214)

- **Current Text:** "deliverables are recorded as a frozen acceptance checklist on the task record before work begins."
- **Conflict:** Implicitly pairs frozen checklists with `Acceptance`.
- **Drafted Amendment:** Clarifies that the frozen checklist resides under `## Evidence` in two-reader tasks, and that report arguments answer evidence item IDs.
- **Implications:** Eliminates ambiguity in hook-level hearsay arming reminders.

## 7. Stage 2 Build Acceptance Criteria & Test Strategy

The downstream build task will implement the changes specified herein against five verifiable acceptance criteria:

1. **BAC-1 (Advisory Lens Verification):** The review lens returns `REVISE` on PR #3265's original compliance review comment (identifying violations of rules 2 through 10) and returns `PASS` on its rewrite (§ 3.1).
2. **BAC-2 (PR Description Self-Conformance):** The build PR's own description satisfies all ten rules under the advisory lens.
3. **BAC-3 (Task Writer Two-Reader Output):** The updated `/reify` task writer, given the enforcement-map ask ("the enforcement-map is too long again"), writes a task putting aims under `## Quality bar` with concrete targets (e.g. line ceilings), and process items under `## Evidence`.
4. **BAC-4 (Specimen Rewrites):** Three historical PR descriptions are rewritten to the comment standard, with lens evaluations recorded for each pair.
5. **BAC-5 (Enforcement-Map & Template Updates):** `specs/ENFORCEMENT-MAP.md` rows, workflow templates (`wf-reify`, `wf-finish`, `wf-rbg`), and skill instructions are updated on the branch.
