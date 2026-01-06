---
name: heuristics
category: spec
title: Heuristics
type: reference
description: Empirically validated rules that implement axioms. Subject to revision based on evidence.
permalink: heuristics
tags: [framework, principles, empirical]
---

# Heuristics

**Working hypotheses validated by evidence, subject to revision.**

Empirically derived rules implementing [[AXIOMS]]. Evidence lives in GitHub Issues (label: `learning`).

**Confidence**: High (consistent success) | Medium (reliable, limited data) | Low (promising, needs validation)

---

## H1: Skill Invocation Framing
**Statement**: When directing an agent to use a skill, explain it provides needed context and use explicit syntax: `call Skill(name) to...`
**Confidence**: Medium | **Implements**: #1 | **Evidence**: #216

## H2: Skill-First Action Principle
**Statement**: Almost all agent actions should follow skill invocation for repeatability. This includes investigation/research tasks about framework infrastructure.
**Confidence**: High | **Implements**: #1, #17 | **Evidence**: #216

### H2a: Skill Design Enablement
**Statement**: Well-designed skills should enable all action on user requests. Missing skills are framework bugs.
**Confidence**: High

### H2b: Just-In-Time Skill Reminders
**Statement**: Agents should be reminded to invoke relevant skills just-in-time before required.
**Confidence**: High | **Implements**: #23

## H3: Verification Before Assertion
**Statement**: Agents must run verification commands BEFORE claiming success, not after.
**Confidence**: High | **Implements**: #15, #16 | **Evidence**: #214

## H4: Explicit Instructions Override Inference
**Statement**: When a user provides explicit instructions, follow them literally. Do not interpret, soften, or "improve" them. This includes mid-task input: if user provides a hypothesis or correction during your work, STOP your current approach and test their suggestion FIRST.
**Confidence**: High | **Implements**: #4, #22 | **Evidence**: #215

## H5: Error Messages Are Primary Evidence
**Statement**: When an error occurs, quote the error message exactly. Never paraphrase.
**Confidence**: Medium | **Implements**: #2, #15 | **Evidence**: #214

## H6: Context Uncertainty Favors Skills
**Statement**: When uncertain whether a task requires a skill, invoke it. The cost of unnecessary context is lower than missing it.
**Confidence**: Medium | **Implements**: #1, #7 | **Evidence**: #216

## H7: Link, Don't Repeat
**Statement**: Reference information rather than restating it. Brief inline context OK; multi-line summaries are not.
**Confidence**: High | **Implements**: #9, #20

### H7a: Wikilinks in Prose Only
**Statement**: Only add [[wikilinks]] in prose text. Never inside code fences, inline code, or table cells with technical content.
**Confidence**: Low

### H7b: Semantic Wikilinks Only
**Statement**: Use [[wikilinks]] only for semantic references in prose. NO "See Also" or cross-reference sections.
**Confidence**: Medium | **Implements**: #20

## H8: Avoid Namespace Collisions
**Statement**: Framework objects (skills, commands, hooks, agents) must have unique names across all namespaces.
**Confidence**: Medium | **Implements**: #7 | **Evidence**: #256

## H9: Skills Contain No Dynamic Content
**Statement**: Skill files contain only static instructions. Current state lives in `$ACA_DATA/`.
**Confidence**: High | **Implements**: #14, #9

## H10: Light Instructions via Reference
**Statement**: Framework instructions should be brief and reference authoritative sources rather than hardcoding content.
**Confidence**: Medium | **Implements**: #9

## H11: No Promises Without Instructions
**Statement**: Agents must not promise to "do better" without creating persistent instructions.
**Confidence**: High | **Implements**: #2 | **Evidence**: #253

## H12: Semantic Search Over Keyword Matching
**Statement**: Use memory server semantic search for `$ACA_DATA/` content. Never grep for markdown in the knowledge base.
**Confidence**: High | **Implements**: #15, #2

### H12a: Context Over Algorithms
**Statement**: Give agents enough context to make decisions. Never use algorithmic matching (fuzzy, keyword, regex).
**Confidence**: High

## H13: Edit Source, Run Setup
**Statement**: Never modify runtime config files directly. Edit authoritative source and run setup script.
**Confidence**: Low | **Implements**: #1, #13

## H14: Mandatory Second Opinion
**Statement**: Plans and conclusions must be reviewed by critic agent before presenting to user.
**Confidence**: Low | **Implements**: #15, #16

## H15: Streamlit Hot Reloads
**Statement**: Don't restart Streamlit after code changes. It hot-reloads automatically.
**Confidence**: Low | **Implements**: #4

## H16: Use AskUserQuestion Tool for User Decisions
**Statement**: When you need user input to proceed (clarification, choice between options, approval), use the AskUserQuestion tool. Questions in prose text get lost in transcripts.
**Confidence**: Medium | **Implements**: #4 | **Evidence**: #233

## H17: Check Skill Conventions Before File Creation
**Statement**: Check relevant skill for naming/format conventions before creating files in domain-specific locations.
**Confidence**: Low | **Implements**: #1 | **Evidence**: #215

## H18: Distinguish Script Processing from LLM Reading
**Statement**: When documenting workflows, explicitly distinguish script processing (mechanical) from LLM reading (semantic).
**Confidence**: Low | **Implements**: #9

## H19: Questions Require Answers, Not Actions
**Statement**: When user asks a question, ANSWER first. Do not jump to implementing or debugging. After reflection, STOP - do not proceed to fixing unless explicitly directed.
**Confidence**: Medium | **Implements**: #4, #17 | **Evidence**: #215, #237

## H20: Critical Thinking Over Blind Compliance
**Statement**: Apply judgment to instructions. When instructions seem wrong, say so.
**Confidence**: High | **Implements**: #2

## H21: Core-First Incremental Expansion
**Statement**: Only concern ourselves with the core. Expand slowly, one piece at a time.
**Confidence**: High | **Implements**: #9

## H22: Indices Before Exploration
**Statement**: Check index files (ROADMAP.md, README.md, INDEX.md) before using glob/grep to explore.
**Confidence**: Low | **Implements**: #26

## H23: Synthesize After Resolution
**Statement**: After implementation, strip deliberation artifacts from specs. Specs become timeless documentation of what IS.
**Confidence**: Low | **Implements**: #9, #13

## H24: Ship Scripts, Don't Inline Python
**Statement**: When a skill needs Python, create a script that ships with it. Never inline Python in skill instructions.
**Confidence**: Low | **Implements**: #19, #7

## H25: User-Centric Acceptance Criteria
**Statement**: Acceptance criteria describe USER outcomes, not technical metrics. Never add performance criteria unless user requests.
**Confidence**: Low | **Implements**: #22

## H26: Semantic vs Episodic Storage
**Statement**: Classify content before creating: Semantic (current state) → `$ACA_DATA`. Episodic (observations) → GitHub Issues.
**Confidence**: Medium | **Implements**: #28, #9, #15

## H27: Debug, Don't Redesign
**Statement**: When debugging, propose fixes within current design. Don't pivot architectures without approval.
**Confidence**: Low | **Implements**: #23

## H28: Mandatory Acceptance Testing
**Statement**: Feature development MUST include acceptance testing as tracked TODO. /qa requires full e2e verification. Tests are contracts - fix the code, not the test.
**Confidence**: Medium | **Implements**: #22, #23, #17, #18 | **Evidence**: #217

## H29: TodoWrite vs Persistent Tasks
**Statement**: TodoWrite for tracking approved work steps only. Work requiring approval/rollback uses `/tasks` skill.
**Confidence**: Low | **Implements**: #22, #23

## H30: Design-First, Not Constraint-First
**Statement**: Start from "what do we need?" not "what do we have?" Current state is not a constraint.
**Confidence**: Low | **Implements**: #1

## H31: No LLM Calls in Hooks
**Statement**: Hooks never call LLM directly. Spawn background subagent for reasoning.
**Confidence**: High | **Implements**: #7

## H32: Delete, Don't Deprecate
**Statement**: When consolidating files, DELETE old ones. Don't mark "superseded". Git has history.
**Confidence**: High | **Implements**: #13, #28, #9

## H33: Real Data Fixtures Over Fabrication
**Statement**: Test fixtures use real captured data, not fabricated examples.
**Confidence**: Low | **Implements**: #19, #17 | **Evidence**: #247

## H34: Semantic Link Density
**Statement**: Files about same topic/project/event MUST link to each other in prose. Project hubs link to key content files.
**Confidence**: Low | **Implements**: #20, H7

## H35: Spec-First File Modification
**Statement**: When modifying any framework file, agents must: (1) check/update the SPEC governing what the file SHOULD contain, (2) if the file is generated/STATE, modify the skill that generates it instead, (3) check/update any index or documentation referencing the file.
**Confidence**: Medium | **Implements**: #1, #9, #20 | **Evidence**: #262 (2 occurrences)

## H36: File Category Classification
**Statement**: Every framework file belongs to exactly one category: SPEC (our design), REF (external knowledge), DOCS (implementation guides), SCRIPT (executable code), INSTRUCTION (agent workflows), TEMPLATE (fill-in patterns), or STATE (auto-generated). Category determines editing rules and is declared via `category:` in frontmatter.
**Confidence**: Medium | **Implements**: #9, #10, #11 | **Evidence**: [[specs/file-taxonomy]]

## H37: LLM Semantic Evaluation Over Keyword Matching
**Statement**: When verifying outcomes, use LLM semantic understanding to evaluate whether the INTENT was satisfied. NEVER use keyword/substring matching (`any(x in text for x in list)`) as this creates Volkswagen tests that pass on surface patterns without verifying actual behavior. A test that can be satisfied by wrong behavior is worse than no test.
**Confidence**: High | **Implements**: #17, #2, H12a | **Evidence**: #268

### H37a: Full Evidence for Human Validation
**Statement**: Demo tests and verification output must show FULL untruncated content so humans can visually validate. Truncating evidence defeats the purpose of verification.
**Confidence**: High | **Implements**: #17

### H37b: Real Fixtures Over Contrived Examples
**Statement**: E2E tests must use REAL framework prompts (actual skill invocations, actual workflows) not contrived examples ("What is the meaning of life?"). Testing fake scenarios proves nothing about real behavior.
**Confidence**: High | **Implements**: #13, #17 | **Evidence**: #268

---

## Revision Protocol

- **Strengthen**: Add observation to Issue, raise Confidence
- **Weaken**: Add counter-observation to Issue, lower Confidence
- **Propose new**: Create Issue with `learning` label, add entry with Low confidence
- **Retire**: Move to Retired section with reason

Use `/log adjust-heuristic H[n]: [observation]` to update.

---

## Retired Heuristics

(None yet)
