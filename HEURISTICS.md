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

Working hypotheses validated by evidence. Evidence lives in bd issues (label: `learning`).

## H1: Verification Before Assertion

Agents must run verification commands BEFORE claiming success, not after.

### H1a: Check Documentation Before Guessing Syntax

When uncertain about tool/command syntax, CHECK documentation (--help, guides, MCP tools) instead of saying "maybe." Never guess tool behavior.

## H2: Explicit Instructions Override Inference

When a user provides explicit instructions, follow them literally. Do not interpret, soften, or "improve" them. This includes mid-task input: if user provides a hypothesis or correction during your work, STOP your current approach and test their suggestion FIRST.

## H3: Error Messages Are Primary Evidence

When an error occurs, quote the error message exactly. Never paraphrase.

## H4: Link, Don't Repeat

Reference information rather than restating it. Brief inline context OK; multi-line summaries are not.

## H5: Light Instructions via Reference

Framework instructions should be brief and reference authoritative sources rather than hardcoding content.

## H6: Context Over Algorithms

Give agents enough context to make decisions. Never use algorithmic matching (fuzzy, keyword, regex).

## H7: Use AskUserQuestion Tool for User Decisions

When you need user input to proceed (clarification, choice between options, approval), use the AskUserQuestion tool. Questions in prose text get lost in transcripts.

## H8: Check Skill Conventions Before File Creation

Check relevant skill for naming/format conventions before creating files in domain-specific locations.

## H9: Questions Require Answers, Not Actions

When user asks a question, ANSWER first. Do not jump to implementing or debugging. After reflection, STOP - do not proceed to fixing unless explicitly directed.

## H10: Critical Thinking Over Blind Compliance

Apply judgment to instructions. When instructions seem wrong, say so.

## H11: Indices Before Exploration

Check index files (ROADMAP.md, README.md, INDEX.md) before using glob/grep to explore.

## H12: Debug, Don't Redesign

When debugging, propose fixes within current design. Don't pivot architectures without approval.

## H13: Design-First, Not Constraint-First

Start from "what do we need?" not "what do we have?" Current state is not a constraint.

## H14: Delete, Don't Deprecate

When consolidating files, DELETE old ones. Don't mark "superseded". Git has history.

## H15: LLM Semantic Evaluation Over Keyword Matching

When verifying outcomes, use LLM semantic understanding to evaluate whether the INTENT was satisfied.

NEVER use keyword/substring matching (`any(x in text for x in list)`) as this creates Volkswagen tests that pass on surface patterns without verifying actual behavior.

### H15a: Full Evidence for Human Validation

Demo tests and verification output must show FULL untruncated content so humans can visually validate. Truncating evidence defeats the purpose of verification.

### H15b: Execution Over Inspection

Compliance verification REQUIRES actual execution. Comparing fields, validating YAML, pattern matching specs - all are Volkswagen tests. The ONLY proof a component works is running it and observing correct behavior.

## H16: Test Failure Requires User Decision

When a test fails during verification, agents MUST report failure and STOP. Agents cannot modify test assertions, redefine success criteria, or rationalize failures as "edge cases." Only the user decides whether to fix the code, revise criteria, or investigate further.

## H17: No Horizontal Line Dividers

Use headings for structure, not horizontal lines (`---`, `***`, `___`). Horizontal lines are visual noise. Enforced by markdownlint at pre-commit.

## H18: Optimize for Conciseness

Long files harm both humans and agents. Invest in keeping things short.

- **Thresholds**: ≤300 lines for instructions, ≤500 lines for references
- **Rationale**: 300 lines ≈ 12K tokens (fits minimal context budget); 500 allows richer reference content
- **Actions**: Remove content not useful for target audience; link don't repeat; shorten verbose explanations
- **Exceptions**: Document in audit log with justification if threshold cannot be met

"I apologize for the length of this letter; I didn't have time to make it shorter." — Blaise Pascal

## H19: No Selfish Workarounds

When you need to debug or investigate framework behavior and current tools are inadequate, HALT instead of writing ad-hoc solutions.

**If every agent works around tool gaps, the framework never improves.**

When encountering inadequate tooling:

1. **HALT** - Don't write throwaway bash/jq/grep commands
2. **IDENTIFY** - What tool/capability is missing?
3. **PROPOSE** - How should this work for future agents?
4. **WAIT** - Let user decide whether to build proper tool

## Domain-Specific Heuristics

Some heuristics apply only within specific domains. See the relevant skill or document:

- **aOps repo work**: `AGENTS.md` (skill-first action, skill invocation framing, core-first expansion)
- **Framework development**: `framework` skill (namespace collisions, no dynamic content in skills, spec-first modification, file taxonomy, no meta-content, no LLM in hooks, synthesize after resolution, ship scripts)
- **Feature development**: `feature-dev` skill (mandatory second opinion, user-centric acceptance criteria, mandatory acceptance testing, real data fixtures)
- **Knowledge persistence**: `remember` skill (semantic vs episodic, wikilink conventions, semantic search, link density)
- **Research data**: `analyst` skill (Streamlit hot reloads)
- **Task management**: `tasks` skill (TodoWrite vs persistent tasks)
