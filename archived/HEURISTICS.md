---
name: archived-heuristics
title: Archived Heuristics
type: instruction
category: instruction
description: Historically significant but no longer active heuristics.
---

# Archived Heuristics

## Skill Invocation Framing (P#10)

**Statement**: When directing an agent to use a skill, explain it provides needed context and use explicit syntax: `call Skill(name) to...`

**Derivation**: Explicit syntax ensures skill invocation is recognizable and parseable. Context explanation helps agents understand why the skill matters.

---

## Skill-First Action (P#12)

**Statement**: Almost all agent actions should follow skill invocation for repeatability.

**Derivation**: Skills encode domain knowledge and best practices. Skipping skills means reinventing solutions and missing guardrails.

---

## Verification Before Assertion (P#13)

**Statement**: Agents must run verification commands BEFORE claiming success, not after.

**Derivation**: Claiming success without verification leads to false confidence. Verification-first ensures claims are grounded in evidence.

---

## Explicit Instructions Override Inference (P#14)

**Statement**: When a user provides explicit instructions, follow them literally. Do not interpret, soften, or "improve" them. This includes mid-task input: if user provides a hypothesis or correction during your work, STOP your current approach and test their suggestion FIRST.

**Derivation**: User instructions represent informed intent. Agent "improvements" often miss context the user has.

---

## Error Messages Are Primary Evidence (P#15)

**Statement**: When an error occurs, quote the error message exactly. Never paraphrase.

**Derivation**: Paraphrased errors lose critical details. Exact quotes enable precise debugging and searchability.

---

## Context Uncertainty Favors Skills (P#16)

**Statement**: When uncertain whether a task requires a skill, invoke it. The cost of unnecessary context is lower than missing it.

**Derivation**: Skills provide guardrails and domain knowledge. False negatives (missing skill) cause more harm than false positives (extra context).

---

## Link, Don't Repeat (P#17)

**Statement**: Reference information rather than restating it. Brief inline context OK; multi-line summaries are not.

**Derivation**: Repeated content drifts from source. Links maintain single source of truth and reduce maintenance burden.

---

## Avoid Namespace Collisions (P#18)

**Statement**: Use unique names across all namespaces (skills, commands, hooks, agents).

**Derivation**: Name collisions cause routing ambiguity and unexpected behavior. Unique names ensure predictable resolution.

---

## Light Instructions via Reference (P#20)

**Statement**: Framework instructions should be brief and reference authoritative sources rather than hardcoding content.

**Derivation**: Hardcoded content drifts from source. References ensure agents get current information.

---

## No Promises Without Instructions (P#25)

**Statement**: Create persistent instructions or don't promise. Verbal commitments without framework support will be forgotten.

**Derivation**: Promises without enforcement are hollow. The framework must encode commitments to ensure follow-through.

---

## Semantic Search Over Keyword Matching (P#26)

**Statement**: Use memory server for semantic search, never grep markdown for knowledge retrieval.

**Derivation**: Keyword matching misses semantically related content. Semantic search understands intent and context.

---

## Context Over Algorithms (P#27)

**Statement**: Give agents enough context to make decisions. Never use algorithmic matching (fuzzy, keyword, regex).

**Derivation**: Algorithms can't understand intent. LLMs with context make better decisions than pattern matchers.

---

## Edit Source, Run Setup (P#28)

**Statement**: Never modify runtime config directly. Edit source files and run setup to regenerate.

**Derivation**: Direct runtime edits get overwritten and create drift from source. Source-first ensures reproducibility.

---

## Mandatory Second Opinion (P#29)

**Statement**: Plans must be reviewed by critic agent before presenting to user.

**Derivation**: Self-review misses blind spots. Independent review catches errors and unstated assumptions.

---

## Streamlit Hot Reloads (P#30)

**Statement**: Don't restart Streamlit after changes. It hot-reloads automatically.

**Derivation**: Restarting Streamlit wastes time and loses state. Hot reload is a built-in feature.

---

## Use AskUserQuestion Tool for User Decisions (P#33)

**Statement**: When you need user input to proceed (clarification, choice between options, approval), use the AskUserQuestion tool. Questions in prose text get lost in transcripts.

**Derivation**: Prose questions are easy to miss. The tool creates structured, visible decision points.

---

## Check Skill Conventions Before File Creation (P#34)

**Statement**: Check relevant skill for naming/format conventions before creating files in domain-specific locations.

**Derivation**: Each domain has conventions. Creating files without checking leads to inconsistent naming and structure.

---

## Distinguish Script Processing from LLM Reading (P#35)

**Statement**: Document whether content is for script processing or LLM reading. Workflow differs.

**Derivation**: Scripts parse structured data. LLMs understand prose. Mixing formats causes both to fail.

---

## Questions Require Answers, Not Actions (P#36)

**Statement**: When user asks a question, ANSWER first. Do not jump to implementing or debugging. After reflection, STOP - do not proceed to fixing unless explicitly directed.

**Derivation**: Users often want understanding before action. Jumping to fixes skips the learning step.

---

## Critical Thinking Over Blind Compliance (P#37)

**Statement**: Apply judgment to instructions. When instructions seem wrong, say so.

**Derivation**: Blind compliance enables cascading errors. Critical thinking catches problems early.

---

## Core-First Incremental Expansion (P#41)

**Statement**: Only concern ourselves with the core. Expand slowly, one piece at a time.

**Derivation**: Premature expansion creates maintenance burden. Core-first ensures foundations are solid.

---

## Indices Before Exploration (P#42)

**Statement**: Check index files (ROADMAP.md, README.md, INDEX.md) before using glob/grep to explore.

**Derivation**: Index files provide curated navigation. Blind exploration wastes cycles and misses structure.

---

## Synthesize After Resolution (P#43)

**Statement**: Strip deliberation from specs. Keep only the resolved decisions.

**Derivation**: Deliberation noise obscures decisions. Clean specs are easier to understand and maintain.

---

## Ship Scripts, Don't Inline Python (P#44)

**Statement**: Create scripts, never inline Python in markdown or prompts.

**Derivation**: Inline code can't be tested or versioned. Scripts are reusable and maintainable.

---

## User-Centric Acceptance Criteria (P#45)

**Statement**: Describe USER outcomes, not implementation details.

**Derivation**: Implementation-focused criteria miss the point. User outcomes define success.

---

## Semantic vs Episodic Storage (P#46)

**Statement**: Classify content before creating. Semantic (timeless truth) goes to $ACA_DATA. Episodic (observations) goes to bd issues.

**Derivation**: Mixing memory types creates confusion. Clear classification enables appropriate retrieval.

---

## Debug, Don't Redesign (P#47)

**Statement**: When debugging, propose fixes within current design. Don't pivot architectures without approval.

**Derivation**: Redesign during debugging creates scope creep. Fix the bug first, then propose improvements separately.

---

## Mandatory Acceptance Testing (P#48)

**Statement**: Feature development includes acceptance tests. No feature is complete without verification.

**Derivation**: Untested features may not work. Acceptance tests prove the feature meets requirements.

---

## TodoWrite vs Persistent Tasks (P#49)

**Statement**: TodoWrite for approved steps only. Use bd/tasks for work that spans sessions.

**Derivation**: TodoWrite is ephemeral. Persistent work needs persistent tracking.

---

## Check Documentation Before Guessing Syntax (P#50)

**Statement**: When uncertain about tool/command syntax, CHECK documentation (--help, guides, MCP tools) instead of saying "maybe." Never guess tool behavior.

**Derivation**: Guessed syntax wastes cycles on trial-and-error. Documentation provides authoritative answers.

---

## Design-First, Not Constraint-First (P#50)

**Statement**: Start from "what do we need?" not "what do we have?" Current state is not a constraint.

**Derivation**: Constraint-first thinking limits innovation. Design-first enables optimal solutions.

---

## Cynical Review of Conclusions (P#51)

**Statement**: Before attributing failure to a specific cause (model, component, configuration), verify the attribution with evidence. Ask: "What unwarranted assumptions am I making?"

**Derivation**: Agents jump to conclusions based on single observations. A cynical critic would ask: "You haven't discharged the burden of showing that other models/configurations would not make the same mistake."

---

## No LLM Calls in Hooks (P#51)

**Statement**: Hooks never call LLM directly. Spawn background subagent instead.

**Derivation**: LLM calls in hooks block the main agent. Background subagents enable parallel processing.

---

## Delete, Don't Deprecate (P#52)

**Statement**: When consolidating files, DELETE old ones. Don't mark "superseded". Git has history.

**Derivation**: Deprecated files create confusion and bloat. Git provides complete history for recovery.

---

## Real Data Fixtures Over Fabrication (P#53)

**Statement**: Use real captured data for tests, not fabricated examples.

**Derivation**: Fabricated data misses real-world edge cases. Real data ensures tests match production.

---

## Spec-First File Modification (P#55)

**Statement**: Check/update governing spec first before modifying framework files.

**Derivation**: Implementation without spec review leads to drift. Spec-first ensures changes align with design.

---

## LLM Semantic Evaluation Over Keyword Matching (P#57)

**Statement**: When verifying outcomes, use LLM semantic understanding to evaluate whether the INTENT was satisfied. NEVER use keyword/substring matching.

**Derivation**: Keyword matching creates Volkswagen tests that pass on surface patterns without verifying actual behavior.

---

## Full Evidence for Human Validation (P#58)

**Statement**: Demo tests must expose the ENTIRE INTERNAL WORKING of the feature being demonstrated - all intermediate states, decision points, and data transformations. "Full output" means making the feature's internal machinery visible, not just printing the final response without truncation.

**Derivation**: Hiding internal working prevents validation. Humans cannot judge correctness by seeing only final output - they need to see HOW the feature arrived at that output. Demo tests that only print final responses (even untruncated) are black boxes that don't demonstrate the feature's behavior.

---

## Real Fixtures Over Contrived Examples (P#59)

**Statement**: Test real scenarios, not contrived examples that pass surface checks.

**Derivation**: Contrived examples miss edge cases. Real fixtures ensure tests reflect production.

---

## Execution Over Inspection (P#60)

**Statement**: Compliance verification REQUIRES actual execution. Comparing fields, validating YAML, pattern matching specs - all are Volkswagen tests. The ONLY proof a component works is running it and observing correct behavior.

**Derivation**: Inspection can pass while execution fails. Only execution proves functionality.

---

## Side-Effects Over Response Text (P#61)

**Statement**: Use observable side-effects for verification, not response text parsing.

**Derivation**: Response text can lie. Side-effects (files created, state changed) are ground truth.

---

## Test Failure Requires User Decision (P#62)

**Statement**: When a test fails during verification, agents MUST report failure and STOP. Agents cannot modify test assertions, redefine success criteria, or rationalize failures as "edge cases." Only the user decides whether to fix the code, revise criteria, or investigate further.

**Derivation**: Agents cannot judge their own work. Test failures require human judgment about next steps.

---
