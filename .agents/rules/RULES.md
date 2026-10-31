---
trigger: always_on
description: Project-local rules for the academicOps repository, applied on top of the axioms.
---

# Project Rules

These apply to this repository in addition to the axioms in `plugins/rbg/skills/axioms/`, never
in place of them. A rule belongs here only if it states a project-level
commitment a reviewer can name from the diff, and cannot be derived from an
axiom alone.

## Enforcement changes run through the pyramid and update the spec

Before proposing, adding, or modifying an enforcement mechanism, run through the enforcement pyramid options against [`specs/enforcement/enforcement.md`](../../specs/enforcement/enforcement.md) first, testing least-invasive options across its controlled vocabulary and strength gradations before escalating. Default to instructions: instructions work in the large majority of cases; the burden of proof is on adding a mechanism.

Any change that adds, modifies, escalates, or retires an enforcement mechanism
updates [`specs/enforcement/enforcement.md`](../../specs/enforcement/enforcement.md)
in the same PR, so the spec still describes reality after merge.

An enforcement mechanism is any measure intended to shape how an agent behaves —
hooks, review lenses, branch protection, and equally instructions, project rules,
and agent-persona edits. The test is not "which file did I touch?" but "does this
diff change what any agent is made to do?"

New rule content carried by a mechanism the spec already describes owes no new
section. Touch the spec only when the mechanism itself — its trigger, surface, or
scope — changed.

## Documentation goes where the taxonomy says

Any change to an instruction, skill, or documentation file complies with
[`specs/meta/doc-taxonomy.md`](../../specs/meta/doc-taxonomy.md). Placement is not
discretionary.

## Policy as Code in Tests

Do not hardcode architectural policies, messaging invariants, or enforcement levels inside Python test files.

- Policies (e.g., required text snippets, specific hook mappings, or message exemptions) must be defined in `tests/policy.toml`.
- Tests must assert against the configuration in `policy.toml`, never against hardcoded Python literals.
- This separates the _mechanism_ of the test from the _policy_ of the platform, allowing non-engineers to review and modify policies without rewriting code.
- This never licenses asserting that `policy.toml` — or any agent, skill, settings, or instruction file — still declares the same names or values it declares today. `policy.toml` supplies an input an assertion is _derived from_ (an exemption list to check real messages against, a threshold to check a real count against); the assertion itself checks something the code does with that input, never the config's own content restated as its own check.

## No Shitty NLP and Agentic-First Design

Per [Human Readability First](../../plugins/rbg/skills/axioms/human-readability-first.md), readability by future human reviewers is of paramount importance and mechanical parsing must not compromise human-visible prose. The "no shitty NLP" rule explicitly covers three prohibitions:

1. **Prohibit writing fixed-syntax phrases:** Do not force agents to compose rigid syntax formulas or unnatural template boilerplate for human-visible text.
2. **Prohibit checking natural language mechanically:** Legacy NLP (keyword matching, regex heuristics, fuzzy string matching) is forbidden for semantic decisions or checking prose. Evaluate semantically using agentic comprehension, not pattern matching.
3. **Prohibit using structured outputs for human-visible text:** Do not emit structured payloads (such as JSON or YAML documents) where readable Markdown prose is expected for human review.

Any work requiring judgment, evaluation, classification, or semantic reasoning should be designed as a skill, workflow, or agent task that a capable agent executes directly — not as a deterministic script or a programmatic wrapper around LLM APIs.

- **Don't guess semantic intent with regex or fuzzy matching:** Do not parse unstructured natural language or route workflows based on keyword tables, regex heuristics, or substring searches. Provide the agent with the index of choices and let the agent decide.
- **Don't filter documentation based on keyword matches:** Let agents select relevant reference material using semantic context or index discovery.
- **Agentic-first design over programmatic API wrappers:** Do NOT propose building scripts or tools that call LLM APIs programmatically (e.g., Python scripts invoking OpenAI/Anthropic/Gemini APIs or custom evaluation harnesses wrapping model calls). This framework runs on agentic platforms (Claude Code, Gemini CLI, Jules, GitHub agents). These agents _are_ the LLM. Smarts should be agentic; code should be minimised.
- **Observed failure that would justify turning this rule on:** PRs or tools introducing regex/keyword heuristics to classify natural language intent, or PRs introducing Python scripts that wrap LLM API client calls to perform qualitative evaluations instead of delegating to agent workflows and skills.

## Task and Filename Naming Standard

Task titles and filenames must be brief, descriptive, and unambiguous:

- **Task titles are verb-led imperatives:** Every task title begins with an active imperative verb describing the concrete outcome to achieve (e.g., `Implement X`, `Verify Y`, `Refactor Z`).
- **No person's name in titles or filenames:** A task title, note title, or filename must **never** contain a person's name or persona prefix (e.g., no `<name>: decision: ...`, `<name>-task-...`, `for-<name>.md`). Assignment belongs exclusively in the `assigned_to` or `assignee` frontmatter field.
- **Filenames are kebab-case and purpose-driven:** All lowercase alphanumeric characters with hyphens, stating what the file contains or does.
- **Task bodies are strictly concise:** Follow the canonical template in [`specs/meta/naming-and-decisions.md`](../../specs/meta/naming-and-decisions.md) (Goal, Deliverable, Scope, Acceptance criteria, Pointers). Never add narrative sections (`Background`, `References`, `Implementation Plan`) or prose task-to-task links.
- **Parent/child is already an edge:** Setting `parent_id` links the hierarchy; do not redundantly wire edges between siblings/descendants of the parent without specific interactions. Tasks requiring review or follow-up must be structured either as a single task with internal subtasks (if single session) or as a dedicated epic with child tasks (if multi-session), never as loose siblings under an external parent.

## Decisions Emerge from Graph Relationships, Not Standalone Tasks

Agents must never create un-actionable "decision" tasks or file conversational questions as backlog tickets. Where research investigates an open design question or architectural alternatives, it must by default include a decision task assigned to the user (`assignee: user`) that depends on the research findings to decide an implementation route before downstream implementation tasks can proceed.

- **Represent forks as mutually exclusive option nodes:** Architectural choices and trade-offs are modelled on the graph as competing option nodes with mutual blocking edges. Choosing an option resolves the conflict and cancels the competing node, unblocking downstream dependencies.
- **Model unknowns as empirical probes:** Missing information is gathered via focused probe tasks (`classification: probe`).
- **Ask in-turn questions directly:** Interactive clarifications in an active session use `AskUserQuestion` directly rather than polluting the graph with un-actionable decision tasks.

## Rule Waivers and Reservations

A rule is waived only by another rule or a direct instruction from the user. Agents must never waive a rule on their own guess, infer reservations from batch or third-party text mentioning the user, or leave known rule breaches in place as "the user's call". When an agent encounters content or behavior violating governing specifications or rules within its active custodial or task scope, it must fix the violation immediately. Out-of-scope defects are escalated under Mandatory Upward Reporting of Rule Violations.

## PKB Linking: One-Way and Project Hierarchy

Links in the PKB are strictly one-way to prevent link rot. Tasks link upward to their parent project or epic; tasks never link to Maps of Content or indexes. Indexes (type: index) organize reference documentation, not actionable tasks.

## Mandatory Upward Reporting of Rule Violations

Every agent must always report all rule violations -- whether committed during execution or discovered in examined material -- up the chain to the coordinator and user. Handback reports and handover summaries must explicitly disclose rule violations with rule citations and reasons. An agent must never omit, downplay, or hide a rule violation.
