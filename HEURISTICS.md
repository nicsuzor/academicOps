# Heuristics

**Working hypotheses validated by evidence, subject to revision.**

These are empirically derived rules that implement AXIOMS in practice. Unlike axioms, heuristics can be adjusted as new evidence emerges. Each traces to one or more axioms it helps implement.

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

**Implements**: AXIOMS #1 (Categorical Imperative) - ensures actions flow through generalizable skills

---

## H2: Skill-First Action Principle

**Statement**: Almost all actions by agents should be undertaken only after invoking a relevant skill that provides repeatability and efficient certainty.

**Rationale**: Skills encode tested patterns. Ad-hoc action loses institutional knowledge and introduces variance.

**Evidence**:
- 2025-12-14: User observation - consistent pattern across framework development

**Confidence**: High

**Implements**: AXIOMS #1 (Categorical Imperative), #17 (Write for Long Term)

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

**Implements**: AXIOMS #23 (Just-In-Time Context)

---

## H3: Verification Before Assertion

**Statement**: Agents must run verification commands BEFORE claiming success, not after.

**Rationale**: Post-hoc verification catches errors but doesn't prevent false success claims. Verification-first ensures claims are grounded.

**Evidence**:
- learning/verification-skip.md - multiple logged failures of assertion-without-verification

**Confidence**: High

**Implements**: AXIOMS #15 (Verify First), #16 (No Excuses)

---

## H4: Explicit Instructions Override Inference

**Statement**: When a user provides explicit instructions, follow them literally. Do not interpret, soften, or "improve" them.

**Rationale**: Agents tend to infer intent and diverge from explicit requests. This causes scope creep and missed requirements.

**Evidence**:
- learning/instruction-ignore.md - documented pattern of ignoring explicit scope

**Confidence**: High

**Implements**: AXIOMS #4 (Do One Thing), #22 (Acceptance Criteria Own Success)

---

## H5: Error Messages Are Primary Evidence

**Statement**: When an error occurs, quote the error message exactly. Do not paraphrase, interpret, or summarize.

**Rationale**: Error messages contain diagnostic information that paraphrasing destroys. Exact quotes enable pattern matching and debugging.

**Evidence**:
- learning/verification-skip.md - errors misreported lead to wrong fixes

**Confidence**: Medium

**Implements**: AXIOMS #2 (Don't Make Shit Up), #15 (Verify First)

---

## H6: Context Uncertainty Favors Skills

**Statement**: When uncertain whether a task requires a skill, invoke the skill. The cost of unnecessary context is lower than the cost of missing it.

**Rationale**: Skills provide context, validation, and patterns. Over-invocation wastes tokens; under-invocation causes failures. Failures are more expensive.

**Evidence**:
- 2025-12-14: User observation - agents underestimate task complexity

**Confidence**: Medium

**Implements**: AXIOMS #1 (Categorical Imperative), #7 (Fail-Fast)

---

## H7: Link, Don't Repeat

**Statement**: When referencing information that exists elsewhere, link to it rather than restating it. Brief inline context is OK; multi-line summaries are not.

**Rationale**: Repeated information creates maintenance burden and drift. Links maintain single source of truth and reduce document bloat.

**Evidence**:
- 2025-12-14: User observation - documentation bloat from restated content

**Confidence**: High

**Implements**: AXIOMS #9 (DRY, Modular, Explicit), #20 (Maintain relational database integrity)

---

## H8: Avoid Namespace Collisions

**Statement**: Framework objects (skills, commands, hooks, agents) must have unique names across all namespaces. Do not reuse a name even if it's in a different category.

**Rationale**: When a skill and command share a name (e.g., "framework"), the system may invoke the wrong one. This causes silent failures where the agent receives unexpected content and proceeds as if the invocation succeeded.

**Evidence**:
- 2024-12-14: `Skill(skill="framework")` returned `/framework` command output (26-line diagnostic) instead of skill content (404-line SKILL.md). Agent proceeded without the categorical conventions it needed.

**Confidence**: Low (single observation, but failure mode is severe)

**Implements**: AXIOMS #7 (Fail-Fast) - namespace collisions cause silent failures instead of explicit errors

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
