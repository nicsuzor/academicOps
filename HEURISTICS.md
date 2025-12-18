---
name: heuristics
title: Heuristics
type: reference
description: Empirically validated rules that implement axioms. Subject to revision based on evidence.
permalink: heuristics
tags: [framework, principles, empirical]
---

# Heuristics

**Working hypotheses validated by evidence, subject to revision.**

These are empirically derived rules that implement [[AXIOMS]] in practice. Unlike axioms, heuristics can be adjusted as new evidence emerges. Each traces to one or more axioms it helps implement.

**Confidence levels:**
- **High** - Consistent success across many observations
- **Medium** - Works reliably but limited data or known edge cases
- **Low** - Promising but needs more validation

---

## H1: Skill Invocation Framing

**Statement**: When directing an agent to use a skill, (a) explain that the skill provides needed context even if the task seems simple, and (b) use Claude's explicit tool syntax: `call Skill(name) to...`

**Rationale**: Agents often skip skill invocation when they believe a task is simple. Framing skills as context-providers (not just capability-providers) and using explicit syntax reduces bypass behavior.

**Evidence**:
- 2025-12-14: User observation - explicit syntax significantly more effective than prose instructions

**Confidence**: Medium

**Implements**: [[AXIOMS]] #1 (Categorical Imperative) - ensures actions flow through generalizable skills

---

## H2: Skill-First Action Principle

**Statement**: Almost all actions by agents should be undertaken only after invoking a relevant skill that provides repeatability and efficient certainty. **This includes investigation/research tasks about framework infrastructure, not just implementation tasks.**

**Rationale**: Skills encode tested patterns. Ad-hoc action loses institutional knowledge and introduces variance.

**Evidence**:
- 2025-12-14: User observation - consistent pattern across framework development
- 2025-12-18: Agent classified git hook investigation as "research" and skipped framework skill. Had to reinvestigate from scratch instead of using institutional knowledge about autocommit hook and related experiment.

**Confidence**: High

**Clarification**: The distinction between "research" and "implementation" does NOT gate skill invocation. Questions ABOUT framework infrastructure ARE framework work.

**Implements**: [[AXIOMS]] #1 (Categorical Imperative), #17 (Write for Long Term)

### H2a: Skill Design Enablement (Corollary)

**Statement**: Well-designed skills should enable and underpin all action on user requests.

**Rationale**: If agents need to act without skills, the skill system has gaps. Missing skills are framework bugs.

**Confidence**: High

### H2b: Just-In-Time Skill Reminders (Corollary)

**Statement**: Agents should be reminded to invoke relevant skills just-in-time before they are required.

**Rationale**: Upfront context is forgotten; reactive reminders arrive too late. JIT reminders balance cognitive load with compliance.

**Evidence**:
- prompt_router hook implementation - suggests skills on every prompt
- UserPromptSubmit hook - injects skill invocation reminders

**Confidence**: High

**Implements**: [[AXIOMS]] #23 (Just-In-Time Context)

---

## H3: Verification Before Assertion

**Statement**: Agents must run verification commands BEFORE claiming success, not after.

**Rationale**: Post-hoc verification catches errors but doesn't prevent false success claims. Verification-first ensures claims are grounded.

**Evidence**:
- learning/verification-skip.md - multiple logged failures of assertion-without-verification

**Confidence**: High

**Implements**: [[AXIOMS]] #15 (Verify First), #16 (No Excuses)

---

## H4: Explicit Instructions Override Inference

**Statement**: When a user provides explicit instructions, follow them literally. Do not interpret, soften, or "improve" them.

**Rationale**: Agents tend to infer intent and diverge from explicit requests. This causes scope creep and missed requirements.

**Evidence**:
- learning/instruction-ignore.md - documented pattern of ignoring explicit scope

**Confidence**: High

**Implements**: [[AXIOMS]] #4 (Do One Thing), #22 (Acceptance Criteria Own Success)

---

## H5: Error Messages Are Primary Evidence

**Statement**: When an error occurs, quote the error message exactly. Do not paraphrase, interpret, or summarize.

**Rationale**: Error messages contain diagnostic information that paraphrasing destroys. Exact quotes enable pattern matching and debugging.

**Evidence**:
- learning/verification-skip.md - errors misreported lead to wrong fixes

**Confidence**: Medium

**Implements**: [[AXIOMS]] #2 (Don't Make Shit Up), #15 (Verify First)

---

## H6: Context Uncertainty Favors Skills

**Statement**: When uncertain whether a task requires a skill, invoke the skill. The cost of unnecessary context is lower than the cost of missing it.

**Rationale**: Skills provide context, validation, and patterns. Over-invocation wastes tokens; under-invocation causes failures. Failures are more expensive.

**Evidence**:
- 2025-12-14: User observation - agents underestimate task complexity

**Confidence**: Medium

**Implements**: [[AXIOMS]] #1 (Categorical Imperative), #7 (Fail-Fast)

---

## H7: Link, Don't Repeat

**Statement**: When referencing information that exists elsewhere, link to it rather than restating it. Brief inline context is OK; multi-line summaries are not.

**Rationale**: Repeated information creates maintenance burden and drift. Links maintain single source of truth and reduce document bloat.

**Evidence**:
- 2025-12-14: User observation - documentation bloat from restated content

**Confidence**: High

**Implements**: [[AXIOMS]] #9 (DRY, Modular, Explicit), #20 (Maintain relational database integrity)

---

## H8: Avoid Namespace Collisions

**Statement**: Framework objects (skills, commands, hooks, agents) must have unique names across all namespaces. Do not reuse a name even if it's in a different category.

**Rationale**: When a skill and command share a name (e.g., "framework"), the system may invoke the wrong one. This causes silent failures where the agent receives unexpected content and proceeds as if the invocation succeeded.

**Evidence**:
- 2024-12-14: `Skill(skill="framework")` returned `/framework` command output (26-line diagnostic) instead of skill content (404-line SKILL.md). Agent proceeded without the categorical conventions it needed.

**Confidence**: Low (single observation, but failure mode is severe)

**Implements**: [[AXIOMS]] #7 (Fail-Fast) - namespace collisions cause silent failures instead of explicit errors

---

## H9: Skills Contain No Dynamic Content

**Statement**: Skill files must contain only static instructions and patterns. Current state, configuration snapshots, or data that changes must live in `$ACA_DATA/`.

**Rationale**: Skills are distributed as read-only files. Dynamic content in skills (a) violates AXIOMS #14, (b) drifts from actual state, (c) requires manual sync processes. The authoritative source for "what is configured" is the configuration itself, not a skill's description of it.

**Evidence**:
- 2025-12-15: Skill documentation listed example deny rules that didn't match actual settings.json. Agent proceeded with outdated understanding of what was blocked.

**Confidence**: High

**Implements**: [[AXIOMS]] #14 (Skills are Read-Only), #9 (DRY)

**Corollary**: When agents need current enforcement state, they must read the actual sources (`settings.json`, `policy_enforcer.py`, `.pre-commit-config.yaml`), not skill documentation about them.

---

## H10: Light Instructions via Reference

**Statement**: Framework instructions should be brief and reference authoritative sources rather than duplicating or hardcoding content that lives elsewhere.

**Rationale**: Hardcoded lists (enforcement levels, filing locations, intervention ladders) become stale when the authoritative source changes. Brief instructions that delegate to reference docs stay current automatically.

**Evidence**:
- 2025-12-16: `/learn` command hardcoded a 4-level intervention ladder that ignored git hooks, deny rules, and other mechanisms defined in ENFORCEMENT.md

**Confidence**: Medium

**Implements**: [[AXIOMS]] #9 (DRY, Modular, Explicit)

---

## H11: No Promises Without Instructions

**Statement**: Agents must not promise to "do better" or change future behavior without creating persistent instructions. Intentions without implementation are worthless.

**Rationale**: Agents have no memory between sessions. Promising to improve without encoding the improvement in framework instructions (ACCOMMODATIONS.md, HEURISTICS.md, hooks, etc.) is a false commitment that cannot be kept.

**Evidence**:
- 2025-11-16: Documented as lesson in experiment file but not promoted to instructions (experiment: minimal-documentation-enforcement)
- 2025-12-17: Agent said "I just need to do this better" about cognitive load support without creating any instructions

**Confidence**: High

**Implements**: [[AXIOMS]] #2 (Don't Make Shit Up) - promising what you can't deliver is fabrication

---

## H12: Semantic Extraction Over Keyword Matching

**Statement**: When extracting information from user messages (accomplishments, action items, decisions, etc.), use semantic understanding rather than keyword matching. Read each message, identify action verbs and their objects, and extract meaning regardless of phrasing.

**Rationale**: Keyword matching (e.g., grep for "done", "completed", "mark") misses most content. User messages use varied language: "do it", "delete X", "run Y", "update Z" - all indicate completed actions but don't match completion keywords. Semantic extraction requires reading each message and understanding what was requested or accomplished.

**Evidence**:
- 2025-12-17: Agent extracted 232 user messages but identified only ~10 accomplishments using keyword matching. Re-extraction with semantic analysis found ~43 discrete action items. Missed: "do it and delete bmdev", "update our flow", "pull latest version", etc.

**Confidence**: Medium (strong single observation)

**Implements**: [[AXIOMS]] #15 (Verify First) - actually understand content; [[AXIOMS]] #2 (Don't Make Shit Up) - don't fabricate understanding from keyword presence

**Application**: When asked to summarize, extract, or categorize user messages:
1. Read each message fully
2. Identify action verbs: do, delete, update, run, create, fix, add, remove, pull, push, commit, etc.
3. Extract what the verb applies to
4. Group by project/context
5. Don't filter based on keyword presence

---

## H13: Edit Source, Run Setup

**Statement**: Never directly modify runtime/deployed config files (`~/.claude.json`, `~/.config/*`, symlinked files). Always edit the authoritative source in the appropriate repo (academicOps, dotfiles) and run the setup script to deploy.

**Rationale**: Direct edits bypass version control, break reproducibility, and violate the Categorical Imperative (treating config management as a special case instead of following the general rule). Setup scripts exist to transform source configs into deployed configs with proper path expansion, merging, and validation.

**Evidence**:
- 2025-12-18: Agent edited `~/.claude.json` directly to change MCP server config instead of editing `$AOPS/config/claude/mcp.json` and running `setup.sh`

**Confidence**: Low (first occurrence)

**Implements**: [[AXIOMS]] #1 (Categorical Imperative), #13 (Trust Version Control)

---

## H14: Mandatory Second Opinion

**Statement**: Plans and conclusions must be reviewed by an independent perspective (critic agent) before presenting to user.

**Rationale**: Agents exhibit confirmation bias and overconfidence. A skeptical second pass catches errors that the planning agent misses. The cost of a quick review is lower than the cost of presenting flawed plans.

**Evidence**:
- 2025-12-18: User observation - agents confidently present flawed plans without self-checking

**Confidence**: Low (new)

**Implements**: [[AXIOMS]] #15 (Verify First), #16 (No Excuses)

**Application**:
```
Task(subagent_type="critic", model="haiku", prompt="
Review this plan/conclusion for errors and hidden assumptions:
[SUMMARY]
Check for: logical errors, unstated assumptions, missing verification, overconfident claims.
")
```

If critic returns REVISE or HALT, address issues before proceeding.

---

## Revision Protocol

To adjust heuristics based on new evidence:

1. **Strengthen**: Add dated observation to Evidence section, consider raising Confidence
2. **Weaken**: Add dated counter-observation, consider lowering Confidence
3. **Propose new**: Create entry with Low confidence, gather evidence
4. **Retire**: If consistently contradicted, move to "Retired Heuristics" section below with reason

Use `/log adjust-heuristic H[n]: [observation]` to trigger the learning-log skill with heuristic context.

---

## Retired Heuristics

(None yet - heuristics that are consistently contradicted by evidence move here with retirement rationale)
