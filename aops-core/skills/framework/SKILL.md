---
name: framework
category: instruction
description: "Framework Architecture and Design Principles — the core patterns used to build academicOps."
---

# Framework Architecture

These principles describe how the academicOps framework itself is built. They were originally defined as axioms but were moved to this dedicated skill to distinguish framework design patterns from universal agent conduct rules.

## Self-Documenting (P#10)

Documentation-as-code first; never make separate documentation files.

**Derivation**: Separate documentation drifts from code. Embedded documentation stays synchronized with implementation.

## Always Dogfooding (P#22)

Use real projects as development guides, test cases, and tutorials. Never create fake examples.

**Derivation**: Fake examples don't surface real-world edge cases. Dogfooding ensures the framework works for actual use cases.

## Skills Are Read-Only (P#23)

Skills MUST NOT contain dynamic data. All mutable state lives in $ACA_DATA.

**Derivation**: Skills are framework infrastructure shared across sessions. Dynamic data in skills creates state corruption and merge conflicts.

## Trust Version Control (P#24)

We work in git repositories — git is the backup system.

**Corollaries**:

- NEVER create backup files: `_new`, `.bak`, `_old`, `_ARCHIVED_*`, `file_2`, `file.backup`
- NEVER preserve directories/files "for reference" — git history IS the reference
- Edit files directly, rely on git to track changes
- Commit AND push after completing logical work units
- Commit promptly — don't hesitate or wait for review. Git makes reversion trivial.

**Derivation**: Backup files create clutter and confusion. Git provides complete history with branching, diffing, and recovery.

## Plan-First Development (P#41)

No coding without an approved plan.

**Derivation**: Coding without a plan leads to rework and scope creep. Plans ensure alignment with user intent before investment. Not universal — trivial non-functional changes (typos, whitespace, comment wording) don't need a formal plan.

## Just-In-Time Context (P#43)

Context surfaces automatically when relevant. Missing context is a framework bug.

**Derivation**: Agents cannot know what they don't know. The framework must surface relevant information proactively.

## Memory Model (P#46)

$ACA_DATA contains both semantic and episodic memory. Semantic memory (synthesized knowledge) is durable, decontextualized, and always kept current. Episodic memory (daily notes, meeting notes, task bodies) is time-stamped, preserved as-is, and serves as primary source material for synthesis. The consolidation pipeline transforms episodic into semantic through extraction, pattern detection, and provenance-tracked synthesis.

**Corollaries**:

- Semantic notes must be understandable without reading their sources
- Episodic notes are never edited after creation — only frontmatter flags added
- All synthesized claims must cite their episodic sources (provenance required)
- The /sleep cycle's consolidation phases test the hypothesis that agents can perform this transformation

**Derivation**: The original "semantic only" rule prevented legitimate episodic content (meeting notes, daily summaries) from living alongside the knowledge it informs. Cognitive science shows that episodic→semantic transformation requires active retrieval and reprocessing, not just storage. Separating the two creates a capture gap where valuable temporal context is lost before it can be synthesized.

## Agents Execute Workflows (P#47)

Agents are autonomous entities with knowledge who execute workflows. Agents don't "own" or "contain" workflows.

**Corollaries**:

- Workflow-specific instructions (step-by-step procedures) belong in workflow files, not agent definitions
- Agents have domain knowledge and decision-making guidance about when to use which workflow
- Agents select and execute workflows based on context
- Think: Agents = people with expertise; Workflows = documented processes

**Derivation**: Clear separation enables reusable workflows across different agents and maintainable agent definitions focused on expertise rather than procedures.

## No Shitty NLP (P#49)

Legacy NLP (keyword matching, regex heuristics, fuzzy string matching) is forbidden for semantic decisions. We have smart LLMs — use them. This extends to acceptance criteria: evaluate semantically, not with pattern matching (see P#78).

**Corollaries**:

- Don't try to guess user intent with regex
- Don't filter documentation based on keyword matches
- Provide the Agent with the _index of choices_ and let the Agent decide
- **Agentic-first design**: Do NOT propose building scripts or tools that call LLM APIs programmatically (e.g., Python scripts that invoke the Anthropic/OpenAI API, custom evaluation harnesses wrapping model calls). This framework runs on agentic platforms — Claude Code, Gemini CLI, Jules, GitHub agents. These agents ARE the LLM. Any work requiring judgment, evaluation, classification, or semantic reasoning should be designed as a skill, workflow, or agent task that a capable agent executes directly — not as a deterministic program that wraps API calls. Smarts should be agentic; code should be minimised.

**Derivation**: LLMs understand semantics; regex does not. Agentic frameworks (Claude Code, Gemini CLI) already provide full LLM capabilities with tool access, context management, and iterative reasoning. Building programmatic API wrappers duplicates this capability poorly — the wrapper is less capable than the agent, harder to maintain, and violates the framework's core architecture. The same anti-pattern manifests in two forms: (1) using regex/keyword matching instead of LLM judgment ("classic shitty NLP"), and (2) writing code that calls an LLM API instead of delegating to an agent that IS an LLM ("shiny shitty NLP"). Both attempt to replace agentic capability with deterministic code.
