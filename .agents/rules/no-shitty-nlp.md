---
trigger: always_on
description: Prohibit fixed-syntax phrases, mechanical NLP/regex intent matching, and programmatic LLM wrappers where agentic comprehension applies.
---

## No Shitty NLP and Agentic-First Design

Per [Human Readability First](../../plugins/rbg/skills/axioms/human-readability-first.md), readability by future human reviewers is of paramount importance and mechanical parsing must not compromise human-visible prose. The "no shitty NLP" rule explicitly covers three prohibitions:

1. **Prohibit writing fixed-syntax phrases:** Do not force agents to compose rigid syntax formulas or unnatural template boilerplate for human-visible text.
2. **Prohibit checking natural language mechanically:** Legacy NLP (keyword matching, regex heuristics, fuzzy string matching) is forbidden for semantic decisions or checking prose. Evaluate semantically using agentic comprehension, not pattern matching.
3. **Prohibit using structured outputs for human-visible text:** Do not emit structured payloads (such as JSON or YAML documents) where readable Markdown prose is expected for human review.

Any work requiring judgment, evaluation, classification, or semantic reasoning should be designed as a skill, workflow, or agent task that a capable agent executes directly -- not as a deterministic script or a programmatic wrapper around LLM APIs.

- **Don't guess semantic intent with regex or fuzzy matching:** Do not parse unstructured natural language or route workflows based on keyword tables, regex heuristics, or substring searches. Provide the agent with the index of choices and let the agent decide.
- **Don't filter documentation based on keyword matches:** Let agents select relevant reference material using semantic context or index discovery.
- **Agentic-first design over programmatic API wrappers:** Do NOT propose building scripts or tools that call LLM APIs programmatically (e.g., Python scripts invoking OpenAI/Anthropic/Gemini APIs or custom evaluation harnesses wrapping model calls). This framework runs on agentic platforms (Claude Code, Gemini CLI, Jules, GitHub agents). These agents _are_ the LLM. Smarts should be agentic; code should be minimised.
- **Observed failure that would justify turning this rule on:** PRs or tools introducing regex/keyword heuristics to classify natural language intent, or PRs introducing Python scripts that wrap LLM API client calls to perform qualitative evaluations instead of delegating to agent workflows and skills.
