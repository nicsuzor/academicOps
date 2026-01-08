---
name: heuristics
title: Heuristics
type: instruction
category: instruction
description: Empirically validated rules that implement axioms.
permalink: heuristics
tags: [framework, principles, empirical]
---

# Heuristics

Working hypotheses validated by evidence. Evidence lives in GitHub Issues (label: `learning`).

## H1: Skill Invocation Framing

When directing an agent to use a skill, explain it provides needed context and use explicit syntax: `call Skill(name) to...`

## H2: Skill-First Action Principle

Almost all agent actions should follow skill invocation for repeatability. This includes investigation/research tasks about framework infrastructure.

### H2a: Skill Design Enablement

Well-designed skills should enable all action on user requests. Missing skills are framework bugs.

### H2b: Just-In-Time Skill Reminders

Agents should be reminded to invoke relevant skills just-in-time before required.

## H3: Verification Before Assertion

Agents must run verification commands BEFORE claiming success, not after.

### H3a: Check Documentation Before Guessing Syntax

When uncertain about tool/command syntax, CHECK documentation (--help, guides, MCP tools) instead of saying "maybe." Never guess tool behavior.

## H4: Explicit Instructions Override Inference

When a user provides explicit instructions, follow them literally. Do not interpret, soften, or "improve" them. This includes mid-task input: if user provides a hypothesis or correction during your work, STOP your current approach and test their suggestion FIRST.

## H5: Error Messages Are Primary Evidence

When an error occurs, quote the error message exactly. Never paraphrase.

## H6: Context Uncertainty Favors Skills

When uncertain whether a task requires a skill, invoke it. The cost of unnecessary context is lower than missing it.

## H7: Link, Don't Repeat

Reference information rather than restating it. Brief inline context OK; multi-line summaries are not.

### H7a: Wikilinks in Prose Only

Only add [[wikilinks]] in prose text. Never inside code fences, inline code, or table cells with technical content.

### H7b: Semantic Wikilinks Only

Use [[wikilinks]] only for semantic references in prose. NO "See Also" or cross-reference sections.

## H8: Avoid Namespace Collisions

Framework objects (skills, commands, hooks, agents) must have unique names across all namespaces.

## H9: Skills Contain No Dynamic Content

Skill files contain only static instructions. Current state lives in `$ACA_DATA/`.

## H10: Light Instructions via Reference

Framework instructions should be brief and reference authoritative sources rather than hardcoding content.

## H11: No Promises Without Instructions

Agents must not promise to "do better" without creating persistent instructions.

## H12: Semantic Search Over Keyword Matching

Use memory server semantic search for `$ACA_DATA/` content. Never grep for markdown in the knowledge base.

### H12a: Context Over Algorithms

Give agents enough context to make decisions. Never use algorithmic matching (fuzzy, keyword, regex).

## H13: Edit Source, Run Setup

Never modify runtime config files directly. Edit authoritative source and run setup script.

## H14: Mandatory Second Opinion

Plans and conclusions must be reviewed by critic agent before presenting to user.

## H15: Streamlit Hot Reloads

Don't restart Streamlit after code changes. It hot-reloads automatically.

## H16: Use AskUserQuestion Tool for User Decisions

When you need user input to proceed (clarification, choice between options, approval), use the AskUserQuestion tool. Questions in prose text get lost in transcripts.

## H17: Check Skill Conventions Before File Creation

Check relevant skill for naming/format conventions before creating files in domain-specific locations.

## H18: Distinguish Script Processing from LLM Reading

When documenting workflows, explicitly distinguish script processing (mechanical) from LLM reading (semantic).

## H19: Questions Require Answers, Not Actions

When user asks a question, ANSWER first. Do not jump to implementing or debugging. After reflection, STOP - do not proceed to fixing unless explicitly directed.

## H20: Critical Thinking Over Blind Compliance

Apply judgment to instructions. When instructions seem wrong, say so.

## H21: Core-First Incremental Expansion

Only concern ourselves with the core. Expand slowly, one piece at a time.

## H22: Indices Before Exploration

Check index files (ROADMAP.md, README.md, INDEX.md) before using glob/grep to explore.

## H23: Synthesize After Resolution

After implementation, strip deliberation artifacts from specs. Specs become timeless documentation of what IS.

## H24: Ship Scripts, Don't Inline Python

When a skill needs Python, create a script that ships with it. Never inline Python in skill instructions.

## H25: User-Centric Acceptance Criteria

Acceptance criteria describe USER outcomes, not technical metrics. Never add performance criteria unless user requests.

## H26: Semantic vs Episodic Storage

Classify content before creating: Semantic (current state) → `$ACA_DATA`. Episodic (observations) → GitHub Issues.

## H27: Debug, Don't Redesign

When debugging, propose fixes within current design. Don't pivot architectures without approval.

## H28: Mandatory Acceptance Testing

Feature development MUST include acceptance testing as tracked TODO. /qa requires full e2e verification. Tests are contracts - fix the code, not the test.

## H29: TodoWrite vs Persistent Tasks

TodoWrite for tracking approved work steps only. Work requiring approval/rollback uses `/tasks` skill.

## H30: Design-First, Not Constraint-First

Start from "what do we need?" not "what do we have?" Current state is not a constraint.

## H31: No LLM Calls in Hooks

Hooks never call LLM directly. Spawn background subagent for reasoning.

## H32: Delete, Don't Deprecate

When consolidating files, DELETE old ones. Don't mark "superseded". Git has history.

## H33: Real Data Fixtures Over Fabrication

Test fixtures use real captured data, not fabricated examples.

## H34: Semantic Link Density

Files about same topic/project/event MUST link to each other in prose. Project hubs link to key content files.

## H35: Spec-First File Modification

When modifying any framework file, agents must: (1) check/update the SPEC governing what the file SHOULD contain, (2) if the file is generated/STATE, modify the skill that generates it instead, (3) check/update any index or documentation referencing the file.

## H36: File Category Classification

Every framework file belongs to exactly one category: SPEC (our design), REF (external knowledge), DOCS (implementation guides), SCRIPT (executable code), INSTRUCTION (agent workflows), TEMPLATE (fill-in patterns), or STATE (auto-generated). Category determines editing rules and is declared via `category:` in frontmatter.

## H37: LLM Semantic Evaluation Over Keyword Matching

When verifying outcomes, use LLM semantic understanding to evaluate whether the INTENT was satisfied. NEVER use keyword/substring matching (`any(x in text for x in list)`) as this creates Volkswagen tests that pass on surface patterns without verifying actual behavior.

### H37a: Full Evidence for Human Validation

Demo tests and verification output must show FULL untruncated content so humans can visually validate. Truncating evidence defeats the purpose of verification.

### H37b: Real Fixtures Over Contrived Examples

E2E tests must use REAL framework prompts (actual skill invocations, actual workflows) not contrived examples. Testing fake scenarios proves nothing about real behavior.

### H37c: Execution Over Inspection

Compliance verification REQUIRES actual execution. Comparing fields, validating YAML, pattern matching specs - all are Volkswagen tests. The ONLY proof a component works is running it and observing correct behavior.

### H37d: Side-Effects Over Response Text for Allow Tests

When verifying something IS ALLOWED (not blocked), response text is weak evidence. Use observable side-effects: file creation, state changes, command output redirected to files.

## H38: Test Failure Requires User Decision

When a test fails during verification, agents MUST report failure and STOP. Agents cannot modify test assertions, redefine success criteria, or rationalize failures as "edge cases." Only the user decides whether to fix the code, revise criteria, or investigate further.

## H39: No Horizontal Line Dividers

Use headings for structure, not horizontal lines (`---`, `***`, `___`). Horizontal lines are visual noise. Enforced by markdownlint at pre-commit.

## H40: Optimize for Conciseness

Long files harm both humans and agents. Invest in keeping things short.

- **Thresholds**: ≤300 lines for instructions, ≤500 lines for references
- **Rationale**: 300 lines ≈ 12K tokens (fits minimal context budget); 500 allows richer reference content
- **Actions**: Remove content not useful for target audience; link don't repeat; shorten verbose explanations
- **Exceptions**: Document in audit log with justification if threshold cannot be met

"I apologize for the length of this letter; I didn't have time to make it shorter." — Blaise Pascal

## H41: No Meta-Content in Instructions

Instruction files (skills, commands, workflows) MUST NOT include sections irrelevant to the agent at execution time:

- ❌ "When to invoke this workflow" - agent has ALREADY invoked it
- ❌ "Version History" - belongs in git log
- ❌ "Future Enhancements" - belongs in specs or issues
- ❌ "Background/Rationale" - belongs in specs

Invocation guidance belongs in: frontmatter `description:`, README.md inventory, routing logic (hydrator, hooks).
