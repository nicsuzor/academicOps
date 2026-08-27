---
trigger: off
description: Project-local rules for the academicOps repository, applied on top of the axioms.
---

# Project Rules

These apply to this repository in addition to the axioms in `lib/axioms/`, never
in place of them. A rule belongs here only if it states a project-level
commitment a reviewer can name from the diff, and cannot be derived from an
axiom alone.

## Enforcement changes update the spec in the same PR

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

## No Shitty NLP and Agentic-First Design

Legacy NLP (keyword matching, regex heuristics, fuzzy string matching) is forbidden for semantic decisions. We have smart LLMs — use them. This extends to acceptance criteria: evaluate semantically, not with pattern matching. Any work requiring judgment, evaluation, classification, or semantic reasoning should be designed as a skill, workflow, or agent task that a capable agent executes directly — not as a deterministic script or a programmatic wrapper around LLM APIs.

- **Don't guess semantic intent with regex or fuzzy matching:** Do not parse unstructured natural language or route workflows based on keyword tables, regex heuristics, or substring searches. Provide the agent with the index of choices and let the agent decide.
- **Don't filter documentation based on keyword matches:** Let agents select relevant reference material using semantic context or index discovery.
- **Agentic-first design over programmatic API wrappers:** Do NOT propose building scripts or tools that call LLM APIs programmatically (e.g., Python scripts invoking OpenAI/Anthropic/Gemini APIs or custom evaluation harnesses wrapping model calls). This framework runs on agentic platforms (Claude Code, Gemini CLI, Jules, GitHub agents). These agents *are* the LLM. Smarts should be agentic; code should be minimised.
- **Observed failure that would justify turning this rule on:** PRs or tools introducing regex/keyword heuristics to classify natural language intent, or PRs introducing Python scripts that wrap LLM API client calls to perform qualitative evaluations instead of delegating to agent workflows and skills.

