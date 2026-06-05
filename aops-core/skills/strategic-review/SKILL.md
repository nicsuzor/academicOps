---
name: strategic-review
type: skill
category: instruction
description: Multi-agent strategic review of documents, plans, and proposals. Commissions review agents and iterates until the review meets quality standards. Use --critic for a fast pauli-only pre-hoc critique.
triggers:
  - "strategic review"
  - "pre-hoc plan evaluation"
  - "adversarial review"
  - "plan review"
  - "review this document"
  - "review this proposal"
  - "/strategic-review --critic"
  - "critic review"
  - "critic mode"
modifies_files: false
needs_task: false
mode: conversational
domain:
  - framework
  - quality-assurance
allowed-tools: Task,Read
version: 2.5.0
permalink: skills-strategic-review
---

# /strategic-review — Strategic Review

Perform strategic reviews of documents, plans, and proposals. Use the appropriate mode based on parameters or user intent:

## Mode Selection

- **Default (Multi-agent loop)**: Call the orchestrator agent `james` to run the multi-agent review loop (RBG, Pauli, Marsha).
- **`--critic` (Solo Pauli)**: Invoke `pauli` to run a solo adversarial critique of a plan or proposal using the 10 cognitive moves.
- **`--arch-fit` (Solo Pauli)**: Invoke `pauli` to assess if a green/merge-ready PR is architecturally in the right place rather than a workaround.

---

## Architectural-Fit Lens (`--arch-fit`) Prompt

You are the ARCHITECTURAL-FIT reviewer (Pauli). Correctness, tests, and basic axiom compliance are handled upstream. Your focus is strictly: _Is this change in the right place, or is it a workaround for a problem whose root cause belongs elsewhere or requires redesign?_

### Analysis Checklist

1. **Reconstruct, Don't Accept**: Investigate the task, diff, call sites, specs (`specs/INDEX.md`), and vision (`[[vision]]` / permanent ID `aops-vision`) to locate the true root cause.
2. **Spec Grounding**: Verify if the change aligns with the canonical spec in `specs/`. If it is a taxonomy/SSoT change, verify internal coherence and complete propagation.
3. **Cross-Repo & External Impact**: Search the PKB to identify if this change implies concurrent changes in other repositories (e.g. `nicsuzor/mem`, `nicsuzor/overwhelm-dashboard`). Enumerate them and check if tasks are already scheduled.
4. **Hunt Failure Patterns**:
   - _Symptom vs Cause_: Fixing a symptom instead of the upstream cause.
   - _Wrong Abstraction_: Branching instead of unifying/refactoring abstractions.
   - _Reimplementing Platform_: Building in-framework what is native to Git, GitHub, OS, etc.
   - _Coordination/Gate Creep_: Unnecessary new gates, hooks, or control mechanisms.
   - _Complexity without Demonstrated Benefit_: New fields/enums/code surfaces without an active, deterministic, downstream consumer.
   - _Unregistered/Under-integrated Mechanism_: Adding a step, gate, or lifecycle hook without documenting it in its canonical spec, `specs/ENFORCEMENT-MAP.md`, `.agents/INDEX.md`, or README.
   - _Unjustified Removal_: Dropping existing checks/gates without replacing their safety invariants.
5. **Propagation Completeness**: Enumerate all sites implementing the old pattern/schema across the entire repository (using PR diff, not just local branch status) and confirm they are migrated.
6. **Persistence Trace**: Trace the full write path to a durable resting place (explicit filename/path) for any new/altered persistence mechanisms.
7. **Axiom Backstop**: Perform a trust-but-verify scan against `.agents/rules/AXIOMS.md` and `.agents/rules/AXIOMS-REVIEW.md` to catch any missed violations.
   - _Mechanical Check_: If a mechanism is added/modified, verify `specs/ENFORCEMENT-MAP.md` is updated in the same PR. If missing, flag as `GAP - ENFORCEMENT-MAP row missing`.

### Output Format

Lead with **exactly one** verdict emoji and text, followed by one scannable line per applicable section below (omit inapplicable sections). Keep output extremely concise.

**Verdict Options**:

- ✅ MERGE — Right place and shape.
- ✅ MERGE (tension noted) — Genuinely separable watchpoint noted but not blocking.
- ⚠️ HOLD — Sound in principle, but requires specific resolution before merge.
- 🔁 REDESIGN — Right goal, wrong approach/location; needs redesign.
- 🔴 REJECT — The change adds complexity without benefit or targets a non-problem; close the PR.

**Output Fields**:

1. **Core Action**: One sentence in root-cause terms summarizing the change.
2. **Strategic Call**: If merging, state why the location is correct. If hold/redesign, state the exact chain: change -> root cause -> correct redesign target -> vision principle. If reject, name the unjustified cost and missing consumer.
3. **External Impact**: Concomitant changes needed in other repos and if tasks are scheduled.
4. **Persistence**: The concrete durable destination path (if write path changed).
5. **Axiom Backstop**: `rbg coverage OK` or the specific gap (e.g. `GAP - axiom <name> missed`).
6. **Issue-Completeness**: completeness check (e.g. `discharges N of M items from #X; remaining: <list>`).
7. **Spot-Check**: 1-2 file:line pointers for manual verification.
8. **Confidence + Counter-Argument**: High/Medium/Low confidence with the strongest counter-argument to your recommendation.
9. **Out-of-Scope Routing**: Any correctness/test concerns routed to QA.

### Post-Review Actions

1. **Post PR Comment**: Post the output to the PR (`gh pr comment`), scrubbed of all personal info (names, private paths, etc.).
2. **Set Commit Status**: Set the commit status `strategic-review/arch-fit` on the PR head SHA: success for ✅ MERGE / MERGE (tension noted), failure for others.
   - Run: `gh api -X POST repos/{owner}/{repo}/statuses/<sha> -f context=strategic-review/arch-fit -f state=<success|failure> -f description=<short>`
3. **Route Concerns**: If correctness issues were found, route them by filing a task or @-mentioning `marsha`.

---

## Orchestrator: James (Default Mode)

When running the default mode, commission James to coordinate the multi-agent review loop:

```
Agent(subagent_type="aops-core:james", prompt="[artifact + context]")
```

### Review Context Descriptors

Descriptors in `review-contexts/` guide the review based on target type:

- `pr-code.md`: Code PRs.
- `pr-framework.md`: Framework PRs (skills, agents, hooks, etc.).

### Agent Roster

- **rbg**: Axiom compliance and workflow discipline (Always runs).
- **pauli**: Strategic critique via 10 cognitive moves (As needed).
- **marsha**: Runtime and verification testing (Runs when code is changed).
