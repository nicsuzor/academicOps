---
name: framework-conventions-summary
title: Framework Conventions Summary
category: ref
description: Condensed framework conventions for JIT injection. Full skill at aops-core/skills/aops/SKILL.md.
permalink: framework-conventions-summary
---

# Framework Conventions (Summary)

**Full skill**: [[aops-core/skills/aops/SKILL.md]] - invoke `Skill(skill='aops')` for component patterns, workflows, compliance refactoring.

## Categorical Imperative (MANDATORY)

Every action must be justifiable as a universal rule. No one-off changes.

### Before ANY Change

1. **State the rule**: What generalizable principle justifies this action?
2. **Check rule exists**: Is this in this skill or documented elsewhere? (Axiom-level checks: invoke `rbg`.)
3. **If no rule exists**: Propose the rule. Get user approval. Document it.
4. **Ad-hoc actions are PROHIBITED**: If you can't generalize it, don't do it.

### File Boundaries (ENFORCED)

| Location      | Action                     | Reason                                  |
| ------------- | -------------------------- | --------------------------------------- |
| `$AOPS/*`     | Direct modification OK     | Public framework files                  |
| `$ACA_DATA/*` | **MUST delegate to skill** | User data requires repeatable processes |

## Authoritative Source Chain

| Priority | Document      | Contains                                        |
| -------- | ------------- | ----------------------------------------------- |
| 1        | (axioms)      | Inviolable principles — enforced by `rbg` agent |
| 2        | HEURISTICS.md | Validated guidance                              |
| 3        | VISION.md     | What we're building                             |
| 4        | This skill    | Derived conventions                             |
| 5        | INDEX.md      | File tree                                       |

**Rule**: Every convention must trace to an axiom. If it can't, the convention is invalid. Invoke `rbg` to verify derivation.

## HALT Protocol

When you encounter something you cannot derive:

1. **STOP** - Do not guess, do not work around
2. **STATE** - "I cannot determine [X] because [Y]"
3. **ASK** - Use AskUserQuestion for clarification
4. **DOCUMENT** - Once resolved, add the rule

## Intent authority

**Outcome this protects:** task ranking reflects Nic's personally curated signal of what matters — never an agent's estimate of importance. This block is the single authoritative statement of that rule; every skill, workflow, agent-def, and template that creates or updates a task points here instead of restating it.

_The concept is **intent**. Today it is stored in the field still named `priority`; the field rename `priority`→`intent` is tracked in [[aops-e887faa4]]. Until it lands, "intent" below means the `priority` band, and the example "make this P1" uses the current P0–P4 labels (see [[../remember/references/TAXONOMY.md#priority-labels-p0p4]])._

`intent` is **Nic's personally curated ranking of what matters** — his signal, never an agent's estimate of importance.

- **Agents never originate intent.** On create/update, leave `intent` at the uncurated default band (the established default; do not elevate). Landing a task uncurated is _not_ setting intent — it is the explicit absence of curation, which is correct.
- **Only Nic sets intent above the default.** An agent may write a non-default `intent` **only** when Nic expressly directs that specific value in that request ("make this P1"). Transcribing Nic's stated intent is allowed; inferring, guessing, or estimating it is not — even when the task is obviously important to you.
- **Never propagate intent.** Do not inherit a parent's intent onto children or copy it across related tasks. Each elevation is an individual act of Nic's curation.
- **Importance ≠ intent.** Urgency, severity, blocker-status, your own assessment of value → `consequence`/`severity`/`due`/`status`, never `intent`. `intent` answers only: _has Nic personally put this on his list, and where._
- **When you think something deserves his attention,** surface it as status/escalation so _he_ sets intent — never set it for him as a shortcut.

## Commit and push discipline

**Outcome this protects:** work an agent has done is durably saved to origin the moment it exists, because agents run in ephemeral environments and uncommitted work is silently lost when the session ends. This block is the single authoritative statement of that rule; every agent-def, skill, workflow, and dispatch brief that touches code points here instead of restating it.

- **Always commit, always push — on your working branch, immediately.** Commit after every logical chunk of work (a coherent unit a reviewer could read), and push to `origin` on your feature branch right away. Do not batch a session's worth of work into one final commit, and never end a turn with valuable work uncommitted or unpushed. The cost of an extra commit is zero; the cost of a lost session is the whole session.
- **Branch protection is the safety net — withholding commits is not.** A push to your own feature branch is harmless: it cannot merge anything, it is caught by CI and PR review, and it is trivially revertable. The real gate against bad work reaching `main` is **branch protection** (required checks + human approval), exactly as for PR bodies above — never the absence of a commit. Commit freely and let the gate do its job.
- **"Don't merge / don't open a PR" NEVER means "don't commit or push."** A prep-only, review-only, or "prepare a reviewable diff" brief is an instruction about the _terminal action_ — do not run `gh pr merge`, do not open the PR — and says nothing about saving the work. Read it as **"commit your work and push it to a branch; just stop short of merging / opening the PR."** Leaving work staged-but-uncommitted, or committed-but-unpushed, is never the cautious default — it is the failure mode. If a brief truly wants work left unsaved, it must say so in those exact words; absent that, save and push.
- **A "reviewable diff" lives on a pushed branch, not in a dirty working tree.** The thing you hand back for review is a branch the reviewer can fetch — `<branch> @ origin` with the commits on it — not a local stash or staged-only state in an environment that will be torn down. If the brief asked for a diff to review, push the branch and report the branch name and remote.

## PR body conventions

**Outcome this protects:** a PR body describes the change for its reviewer. It is not the place to warn about merging. This block is the single authoritative statement of that rule; every surface that authors PR bodies points here instead of restating it.

- **Never add merge-gate / do-not-merge banners.** Do not stamp "DO NOT MERGE", "gated repo — Nic is the merge gate", "opened for redline, not merge", "awaiting Nic", or any equivalent banner into a PR body. The real gate is **branch protection** (enforcer/required-status checks + human approval) — it stops the merge whether or not the body says so, so the banner warns nobody who can act on it. It is pure noise.
- **Why the merge-gate doctrine still holds.** "Never run `gh pr merge` on a gated repo / Nic is the merge gate" remains correct as an _action_ constraint on the agent — keep obeying it. This convention only forbids restating it as _prose addressed to nobody_ in the PR body.
- **If gating status is genuinely relevant, state it once, factually, in prose** — e.g. "aops is gated; merge is on Nic after approval" — never as a banner. Default is to say nothing about merging at all.

## Core Conventions

### Single Source of Truth

Each piece of information exists in exactly ONE location. Reference, don't repeat.

| Information       | Authoritative Location |
| ----------------- | ---------------------- |
| Principles        | Enforced by `rbg`      |
| File tree         | INDEX.md               |
| Feature inventory | README.md              |
| Framework vision  | VISION.md              |
| Workflows         | WORKFLOWS.md           |

### Skills are Read-Only

Skills MUST NOT contain dynamic data. All mutable state lives in `$ACA_DATA/`.

### Just-In-Time Context

Information surfaces when relevant. Missing context = framework bug.

### Trust Version Control

- Never create backup files (.bak, _old)
- Edit directly, git tracks changes
- Commit AND push after completing work — commit/push discipline (commit per chunk, push immediately, never conflate "don't merge" with "don't commit") is the canonical [[#commit-and-push-discipline]] block above.

### Mandatory Critic Review

Before presenting any plan or conclusion, invoke the critic agent:

```
Task(subagent_type="aops-core:pauli", model="opus", prompt="Review this for errors and hidden assumptions: [SUMMARY]")
```

### Terminal Move after Dispatch

After a fire-and-forget dispatch with no follow-up or babysit instruction, the default terminal move is to close the session promptly (via `/dump` or `/end_session`) instead of idling. (Canonical rule: [[aops-core/skills/aops/SKILL.md#terminal-move-after-dispatch]])

### File Categories

| Category    | Purpose                        |
| ----------- | ------------------------------ |
| spec        | Framework design, architecture |
| ref         | External knowledge             |
| docs        | Implementation guides          |
| script      | Executable code                |
| instruction | Workflow/process for agents    |
| template    | Pattern to fill with content   |
| state       | Auto-generated (don't edit)    |

## Anti-Bloat Rules

- Skill files: 500 lines max
- Documentation chunks: 300 lines max
- Approaching limit = Extract and reference
- No multi-line summaries after references
- No historical context, migration notes
- No meta-instructions

## Skill Delegation

When operating on user data:

1. **Identify category**: What type of work?
2. **Find existing skill**: remember, tasks, analyst, etc.
3. **If skill exists**: Invoke it
4. **If NO skill exists**: Create one first via `Skill(skill='framework')`

Common delegations:

| Domain                   | Delegate To                   |
| ------------------------ | ----------------------------- |
| Python code, pytest      | `python-dev`                  |
| Framework infrastructure | `framework` (full skill)      |
| New feature with tests   | `feature-dev`                 |
| Persist knowledge        | `remember`                    |
| dbt, Streamlit, data     | `analyst`                     |
| Hook development         | `plugin-dev:hook-development` |

## Common Violations

| Violation                         | Principle | Correction                                                           |
| --------------------------------- | --------- | -------------------------------------------------------------------- |
| Direct user data modification     | Axiom #1  | Delegate to skill                                                    |
| One-off script without skill      | Axiom #1  | Create generalizable skill                                           |
| Guessing when uncertain           | Axiom #2  | HALT, ask user                                                       |
| Scope creep beyond request        | Axiom #4  | Do one thing, stop                                                   |
| Silent failure handling           | Axiom #7  | Fail fast, report error                                              |
| Creating backup files             | H15       | Trust version control                                                |
| Keyword matching for verification | H37       | Use LLM semantic evaluation                                          |
| Skipping skill invocation         | H2        | Invoke appropriate skill first                                       |
| Leaving work uncommitted/unpushed | H15       | Commit per chunk, push immediately ([[#commit-and-push-discipline]]) |

## Consistency Checks (Before Changes)

| Check            | Question                       | Failure = HALT        |
| ---------------- | ------------------------------ | --------------------- |
| Axiom derivation | Which axiom justifies this?    | Cannot identify axiom |
| INDEX placement  | Does INDEX.md define location? | Location not in INDEX |
| DRY compliance   | Is info stated exactly once?   | Duplicate exists      |
| VISION alignment | Does VISION support this?      | Outside stated scope  |
| Namespace unique | Name conflict with existing?   | Name collision        |

---

**For detailed component patterns (adding skills, hooks, commands), invoke the full skill:**

```
Skill(skill='framework')
```
