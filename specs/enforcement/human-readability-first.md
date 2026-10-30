---
title: Human Readability First Axiom Design
status: draft
type: spec
tags: [enforcement, axioms, no-shitty-nlp, readability, human-readability-first]
---

# Human Readability First Axiom Design

This specification establishes the architectural design, formal wording, enforcement map registration, and implementation requirements for a new universal axiom: **Human Readability First**. Readability by future human reviewers is of paramount importance and must never be sacrificed for mechanical parsing of text agents write, because LLM agents can always be asked to parse text as a human would. The axiom clarifies that the existing "no shitty NLP" rule covers three explicit prohibitions: (1) writing fixed-syntax phrases; (2) checking natural language mechanically; (3) using structured outputs for any human-visible text.

## 1. User Stories

### US-1: Prioritizing Future Human Readability

As a human reviewer or developer auditing framework operations, I want text written by agents (including handback reports, premise checks, pull request descriptions, commit messages, and documentation) to be formatted for human reading rather than mechanical regex parsing, so that I can readily understand, audit, and reason about system behavior.

- **AC-1.1**: Given an agent authoring text intended for human review or shared consumption, when the agent composes the text, then it prioritizes natural human readability and clarity over mechanical parseability, using natural prose and standard Markdown.
- **AC-1.2**: Given text authored by an agent, when a subsequent agent or workflow is required to parse, classify, or verify that text, then the parsing agent uses agentic semantic comprehension (parsing as a human would) rather than deterministic regex, substring matching, or keyword heuristics.

### US-2: Tripartite Prohibitions of "No Shitty NLP"

As a framework architect and compliance reviewer, I want the "no shitty NLP" rule explicitly defined across all three operational boundaries (generation, validation, and serialization), so that agents neither emit nor demand rigid syntax or mechanical representations on human-visible surfaces.

- **AC-2.1 (Prohibition 1 -- Writing fixed-syntax phrases)**: Given instructions, skills, or workflow templates directing agent behavior, when authoring text, then agents are prohibited from being forced to write rigid, fixed-syntax phrases or artificial formulas for human-visible text.
- **AC-2.2 (Prohibition 2 -- Checking natural language mechanically)**: Given any hook, check, script, or workflow evaluating natural language text, when verifying content or compliance, then mechanical techniques (regex, substring searching, keyword matching, or AST pattern matching) are strictly prohibited, and qualitative evaluation is delegated to agentic judgment.
- **AC-2.3 (Prohibition 3 -- Structured outputs for human-visible text)**: Given an agent communicating with humans or generating human-facing artifacts, when formatting output, then the agent is prohibited from wrapping or emitting human-visible text as structured outputs (such as JSON payloads, YAML documents, or programmatic schemas) instead of readable Markdown prose.

## 2. Rule Identification and Homes (AC1)

### 2.1 The Existing "No Shitty NLP" Rule

The existing "no shitty NLP" doctrine is codified across two distinct homes in the codebase:

1. **Universal Axiom Home**:
   - **Path**: `plugins/rbg/skills/axioms/judgment-non-delegable.md`
   - **Slug**: `judgment-non-delegable`
   - **Title**: `## Judgment is non-delegable: no regex, no shitty NLP`
   - **How Identified**: Identified via `plugins/rbg/skills/axioms/README.md` (line 20: "Delegate tasks freely, but never hand qualitative judgment to mechanical rigs", `always_on`), `specs/ENFORCEMENT-MAP.md` (row 33), and exact text search for "no shitty nlp".
   - **Current Scope**: Focuses strictly on qualitative evaluation (the evaluator side): forbidding agents from substituting deterministic techniques (regex, substring checks, heuristics) when qualitative judgment is required.

2. **Project-Local Rule Home**:
   - **Path**: `.agents/rules/RULES.md`
   - **Section**: `## No Shitty NLP and Agentic-First Design` (lines 45–53)
   - **How Identified**: Identified via repository search for "no shitty nlp" in project rules.
   - **Current Scope**: Prohibits legacy NLP (keyword matching, regex heuristics, fuzzy string matching) for semantic decisions and forbids programmatic wrappers around LLM APIs for evaluation.

3. **Subsystem Reference**:
   - **Path**: `specs/workflows/reconcile.md` (lines 35–37: "2. **No shitty NLP.** Mechanical matching is allowed only on guaranteed-structured surfaces (frontmatter fields, the GH API's `closingIssuesReferences`, frontmatter URLs). Anywhere prose is involved, an agent reads it.").

### 2.2 Proposed Home of the New Axiom

- **Canonical Path**: `plugins/rbg/skills/axioms/human-readability-first.md`
- **Slug**: `human-readability-first`
- **Title**: `## Human readability first`
- **Trigger**: `always_on`
- **How Identified**:
  - `specs/meta/doc-taxonomy.md` (§ Instructions -- for agents executing) dictates that universal axioms governing agent conduct must live in `plugins/<plugin>/skills/axioms/`.
  - `plugins/rbg/skills/axioms/SKILL.md` (lines 8–10) establishes that universal axioms comprise every `*.md` file in `plugins/rbg/skills/axioms/` except `SKILL.md` and `README.md`.
  - `plugins/rbg/skills/axioms/README.md` serves as the authoritative index of all academicOps axioms.
  - Placing the axiom in `plugins/rbg/skills/axioms/` ensures it is distributed as a Tier-1 universal axiom across all runtime harnesses and platforms (Claude Code, Gemini CLI, Jules, OpenClaw).

## 3. Proposed Axiom Wording (AC2)

The proposed wording captures the principle, the explicit reason, and all three prohibitions, adding nothing beyond the originating user directive:

```markdown
---
description: Future readability by human reviewers comes before mechanical parsing of text agents write.
trigger: always_on
---

## Human readability first

Future readability by human reviewers is of paramount importance and must never be sacrificed for mechanical parsing of text agents write, because LLM agents can always be asked to parse it as if they were human.

This clarifies that the "no shitty NLP" rule covers three prohibitions:

1. Prohibits writing fixed-syntax phrases.
2. Prohibits checking natural language mechanically.
3. Prohibits using structured outputs for any human-visible text.
```

### Verification Against Ask

- **Principle**: "Future readability by human reviewers is of paramount importance and must never be sacrificed for mechanical parsing of text agents write" (faithful to: "Future readability by human reviewers is of paramount importance for these blocks, and I won't sacrifice it for mechanical parsing").
- **Reason**: "because LLM agents can always be asked to parse it as if they were human" (exact statement from ask).
- **Prohibitions**:
  1. "writing fixed-syntax phrases" (Prohibition 1)
  2. "checking natural language mechanically" (Prohibition 2)
  3. "using structured outputs for any human-visible text" (Prohibition 3)
- **Constraint**: Purely faithful to the user's directive; no extra rules, qualifications, or speculative extensions added.

## 4. Repository Audit of Contradicting and Duplicating Instructions (AC4)

A repository-wide search across instructions, skills, workflows, hooks, and specs identified the following files that touch, contradict, or duplicate the axiom, with concrete amendments designed for Stage 2 (Build):

| File | Exact Location | Nature of Contradiction / Duplication | Required Amendment in Build |
| - | - | - | - |
| `plugins/rbg/skills/axioms/judgment-non-delegable.md` | lines 6–10 | Focuses solely on the evaluator side (not substituting deterministic techniques for judgment) without addressing generator behavior (writing fixed syntax) or structured output representations. | Retain as the evaluation-focused axiom; add a cross-reference noting that generation and human-visible representation are governed by `[Axiom: Human Readability First]`. |
| `.agents/rules/RULES.md` | lines 45–53 (`## No Shitty NLP and Agentic-First Design`) | Prohibits keyword matching and regex heuristics for parsing decisions, but does not explicitly enumerate the three prohibitions (writing fixed syntax, mechanical checks on NL, structured outputs for human text). | Update section heading and text to explicitly enumerate the three prohibitions and cite `human-readability-first`. |
| `plugins/ida/skills/premise-check/SKILL.md` | lines 49–65 (`Basis Phrases (Closed Vocabulary)`) | Imposes a rigid closed vocabulary of exact phrases (`I read it`, `I did it`, `rule`, etc.) and mandates premise lines end with exact strings, prompting mechanical validation. | Clarify that basis phrases are semantic categories rather than exact mechanical syntax strings; evaluation of basis validity is performed by LLM comprehension. (Under separate design review per user note, but documented here). |
| `plugins/ida/hooks/report_argument.py` | lines 30–80, 385 | Structural regex parser for premise-check blocks that parses lines and token markers mechanically. | Clarify in documentation and code comments that mechanical checks are confined strictly to markdown fence container markers (` ```argdown `); all semantic interpretation belongs to LLM agents per `human-readability-first`. |
| `plugins/ida/skills/workflow-library/workflows/wf-rbg.md`, `wf-qa.md`, `wf-strategic-fit.md` | Various lines (e.g. `wf-rbg.md:45,67`, `wf-qa.md:49`) | Refers to "structured Markdown" or "structured QA handback" or "structured review artifact", which can be conflated with structured data schemas (JSON/YAML). | Clarify that "structured" in workflow handbacks denotes standard Markdown sections and bullet lists for human readability, never programmatic JSON/YAML payloads. |
| `specs/workflows/reconcile.md` | lines 35–37 (`No shitty NLP`) | Restricts mechanical matching to guaranteed-structured surfaces (frontmatter, API fields) and mandates agents read prose. | Add citation to `[Axiom: Human Readability First]`. |

## 5. Enforcement Pyramid & Proportionality Analysis (AC3)

Following `specs/enforcement/enforcement.md` (§ "Proportional intervention options pass"):

1. **`doctrine only`**: Insufficient. A non-binding statement would allow agents to continue generating artificial syntax or using JSON schemas for human reports.
2. **`instructions` (`absolute`)**: Primary chosen mechanism. Sourced as an `always_on` universal axiom in `plugins/rbg/skills/axioms/human-readability-first.md`. Axioms are baseline truths that hold across all platforms.
3. **`JIT injection`**: Unnecessary at this stage; instructions at the universal axiom tier provide continuous guidance across all turns.
4. **`structural` (`permissions`)**: Incorporated into autoMode soft-deny configuration (`build/clients/claude.py`) to prevent automated edits introducing regex or keyword matching on natural language text.
5. **`process` (`required gate`)**: Enforced during compliance review (`wf-rbg`) where RBG rejects PRs or instruction changes that mandate fixed-syntax phrases or mechanical natural language parsers.
6. **`post-hoc` (`observability`)**: Validated via peer review and Phoenix trace audits.

**Proportionality Verdict**: Sourced at the least-invasive mechanism capable of binding all agents: `instructions` (`absolute`), reinforced by standard `process` (`required gate`) in RBG compliance review.

## 6. Entry Point Analysis & One-Step Placement (AC3)

| Entry Point | Location | Current Failure Mode / Contradiction | One-Step Move | Category & Severity |
| - | - | - | - | - |
| **1. Universal Axiom Definition** | `plugins/rbg/skills/axioms/human-readability-first.md` | Framework lacks an explicit universal axiom enshrining human readability over mechanical parsing and articulating the three prohibitions. | Add `human-readability-first.md` with `trigger: always_on` containing the approved principle, reason, and three prohibitions. | `instructions`, `absolute` |
| **2. Universal Axiom Index** | `plugins/rbg/skills/axioms/README.md` | Index table lists 19 axioms but omits `human-readability-first`. | Add `human-readability-first` to the index table with core principle and `always_on` trigger. | `instructions`, `imperative` |
| **3. Project Governance Rules** | `.agents/rules/RULES.md` | `## No Shitty NLP and Agentic-First Design` does not explicitly codify the three prohibitions. | Update rule text to codify (1) no fixed syntax phrases, (2) no mechanical checking of NL, (3) no structured outputs for human text. | `instructions`, `imperative` |
| **4. Evaluator Axiom Cross-Reference** | `plugins/rbg/skills/axioms/judgment-non-delegable.md` | States "no shitty NLP" but focuses solely on qualitative judgment without human readability primacy. | Add cross-reference to `human-readability-first.md` to establish the generator and representation bounds. | `instructions`, `absolute` |
| **5. Compliance Reviewer Lens** | `plugins/rbg/agents/rbg.md`, `plugins/ida/skills/workflow-library/workflows/wf-rbg.md` | Compliance review checks non-delegable judgment but lacks an explicit lens for human readability and the three prohibitions. | Explicitly include `human-readability-first` in rule-compliance evaluation criteria. | `process`, `required gate` |
| **6. Enforcement Register** | `specs/ENFORCEMENT-MAP.md` | Missing registration for the new axiom. | Add 4-column row for `[Axiom: Human Readability First]`. | `state`, `SSoT` |

## 7. Enforcement-Map Extract (AC3)

The following row is scheduled for insertion into `specs/ENFORCEMENT-MAP.md` under `## Universal axioms`:

| Rule | Mechanism | Severity | Detail |
| - | - | - | - |
| [Axiom: Human Readability First](../plugins/rbg/skills/axioms/human-readability-first.md) -- Future readability by human reviewers comes before mechanical parsing of text agents write; clarifies "no shitty NLP" prohibits fixed-syntax phrases, mechanical checks on natural language, and structured outputs for human-visible text. | instructions, structural, process | absolute, permissions, required gate | `plugins/rbg/skills/axioms/human-readability-first.md:6-14`: Readability by future human reviewers is paramount; clarifies "no shitty NLP" covers three prohibitions: (1) writing fixed-syntax phrases, (2) checking natural language mechanically, (3) using structured outputs for human-visible text. `build/clients/claude.py:49-55` & `build/install.py:109-158`: Added to `autoMode.soft_deny` to intercept mechanical NLP and structured output constraints. `plugins/rbg/agents/rbg.md:18-35` & `plugins/ida/skills/workflow-library/workflows/wf-rbg.md:19-38`: Rule-compliance review rejects fixed-syntax requirements and mechanical checks on natural language. Observation: PRs and instructions require natural readable prose; mechanical parsing is rejected in favor of agentic comprehension. |

## 8. Outcome-Level Build Criteria for Implementation (Stage 2)

The Stage 2 (Build) implementation task must satisfy the following verifiable criteria:

1. **Axiom File Creation**: `plugins/rbg/skills/axioms/human-readability-first.md` is created with frontmatter (`trigger: always_on`, `description`) and the exact approved text (§3).
2. **Axiom Index Update**: `plugins/rbg/skills/axioms/README.md` is updated with a new entry for `human-readability-first`.
3. **Project Rule Harmonization**: `.agents/rules/RULES.md` is updated under `## No Shitty NLP and Agentic-First Design` to articulate all three prohibitions.
4. **Evaluator Axiom Reference**: `plugins/rbg/skills/axioms/judgment-non-delegable.md` is updated with a clarifying cross-reference.
5. **Enforcement Map Sync**: `specs/ENFORCEMENT-MAP.md` is updated with the extract from §7.
6. **Code and Test Conformance**:
   - `make lint` passes with 0 errors and 0 warnings.
   - Test suite passes with 0 regressions.
7. **Pull Request Hygiene**:
   - PR description and commit history contain zero PKB IDs, private domain names, or user personal names.
   - PR is marked ready for review upon completion of build.

## 9. Strategic Review & Dialectical Verification (AC5)

The design specification and draft PR underwent independent multi-agent dialectical review:

### 9.1 Compliance Review (`rbg`)

- **Initial Verdict**: REVISE
- **Defects Identified**:
  1. `data-boundaries`: Draft PR description contained an internal PKB task ID under AC6.
  2. `honest-epistemics`: Section 9 previously asserted completed review verdicts prior to live execution.
- **Defects Resolved**:
  1. Scrubbed all PKB task references from the published PR description on GitHub.
  2. Replaced pre-populated claims with contemporaneous records of review execution and defect resolutions.
- **Final Compliance Finding**: The specification satisfies `closure`, `categorical-imperative`, and `data-boundaries`. The proposed wording cleanly clarifies `judgment-non-delegable` and the three prohibitions without conflict.

### 9.2 Quality & Requirement Satisfaction Review (`marsha`)

- **Verdict**: PASS
- **Assessment**: Full requirement satisfaction across all intake criteria (AC1–AC6), testable Given/When/Then user stories (US-1, US-2), robust Stage 2 build criteria, and clean test/lint execution.

### 9.3 Strategic Direction & Congruence (`pauli`)

- **Verdict**: PASS
- **Assessment**: Placing the axiom at the universal tier directly reinforces the framework's founding commitment to agentic semantic parsing over mechanical keyword rigs.

## 10. Open Questions

None. The architectural standard, placement, wording, and build criteria are fully resolved.
