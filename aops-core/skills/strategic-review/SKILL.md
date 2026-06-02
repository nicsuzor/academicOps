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
version: 2.3.0
permalink: skills-strategic-review
---

# /strategic-review — Strategic Review

Multi-agent strategic review of documents, plans, and proposals. Supports two modes:

| Mode         | Agent                    | Use when                                                                                                             |
| ------------ | ------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| default      | James (multi-agent loop) | Full strategic review — architecture, compliance, runtime verification                                               |
| `--critic`   | Pauli (solo)             | Fast pre-hoc critique using 10 cognitive moves — plans, proposals                                                    |
| `--arch-fit` | Pauli (solo)             | Is this PR in the right place, or a well-engineered workaround? Run on a green, merge-ready PR before human approval |

## When to invoke

Use this when a document needs strategic review, not proofreading:

- Plans and implementation proposals
- Research proposals and grant applications
- PR reviews where architectural or epistemological problems may exist
- Design decisions and specs
- Any time the question "is this actually good, or just coherent?" matters

## Critic mode (`/strategic-review --critic`)

For a focused, solo pre-hoc critique — invoke Pauli directly, bypassing the full James loop:

```
Agent(subagent_type="aops-core:pauli", prompt="[document or file path]")
```

Pauli applies 10 cognitive moves and returns a structured strategic critique. Use this before implementation when you want adversarial plan review without the overhead of full multi-agent orchestration. Equivalent to the former `/critic` command.

## Architectural-fit lens (`/strategic-review --arch-fit`)

A manually-invoked, principle-driven lens — run by Pauli — for the one strategic question the merge pipeline (rbg + marsha) structurally cannot ask: _is this change in the right place, or a well-engineered workaround for a problem whose real fix lives elsewhere — or that calls for a redesign?_ It assumes correctness and tests already passed and never re-litigates them; it treats the upstream axiom review as trust-but-verify, backstopping rbg's coverage as the penultimate gate before the human. This is the human-judgment gap Nic checks manually today by reading each PR's changed files before merge.

Invoke on a green, merge-ready PR before human approval:

```
Agent(subagent_type="aops-core:pauli", prompt="[the lens text below + PR ref / diff + originating task]")
```

This is the PENULTIMATE step before human approval. The lens reads deeply (diff + call sites + originating task + VISION + specs + PKB cross-repo links) but returns a thin surface — ~4 lines on a MERGE verdict, leading with a verdict glyph and a spot-check pointer, so Nic can make the call without re-reading the diff himself. The thin-surface cap is on what NIC READS; the lens still does the full analysis and records its full output on the PR (see the post + check actions in the prompt block).

**Not yet auto-wired into merge-prep — this is graduated enforcement (VISION).** It earns promotion to an always-on pipeline stage only after dogfooding proves it catches real wrong-place fixes without crying wolf. Promotion path (follow-up, not taken here): add it as a Pauli commission in `review-contexts/pr-code.md` / `pr-framework.md` so James runs it automatically on merge-ready PRs, and register `strategic-review/arch-fit` as an expected/required CI check so the PR cannot go green without it. **Do not take those steps until dogfooding earns it.** (Completing the check when the skill runs — below — is part of the skill now; _requiring_ the check is the promotion step.)

This is a working draft we iterate via dogfooding — keep the prompt block below easy to locate and revise.

```
You are the ARCHITECTURAL-FIT reviewer — one strategic-review lens, run by pauli.

This PR has ALREADY passed correctness, test, and axiom review. Do NOT re-run
correctness or tests — assume the code works and is clean, and restating that is a
failure. AXIOMS are different: treat rbg's upstream axiom review as TRUST-BUT-VERIFY,
not settled. rbg is fallible and this lens is the penultimate gate before the human, so
you BACKSTOP her coverage (see the Axiom backstop step below) rather than assume it.

Your only job: is this change in the RIGHT PLACE, or a well-engineered workaround for
a problem whose real fix lives elsewhere — or that calls for a redesign? A good
engineer can make almost any local change clean and passing; that is exactly what
hides this failure mode. Reconstruct, from the code itself, what this PR actually
solves, where that problem originates, and whether here is where it should be solved.

RECONSTRUCT, DON'T ACCEPT. Do not take the PR description's account of the problem.
Read the originating task/issue, the changed files, AND their call sites and the
abstraction they belong to — you cannot judge "should be elsewhere" without reading
what elsewhere is. Strategic context lives in: projects/aops/vision (VISION) and the
relevant projects/aops/specs/ doc, plus the linked task. NOT STATUS.md or any
operational snapshot.

SPEC GROUNDING. Ground the change against the canonical spec — normally the relevant
projects/aops/specs/ doc. But for a taxonomy / SSoT edit, the edited file may itself BE
the canonical spec: there is no external doc to match against. In that case the grounding
check becomes "is the SSoT edit internally coherent, and fully propagated to every
consumer?" — not "does it match a specs/ doc."

CROSS-REPO / EXTERNAL IMPACT. After placing the change, query the PKB (search /
pkb_context / get_document) for what connects to the surfaces and abstractions this PR
touches — especially in OTHER repositories/projects (e.g. `nicsuzor/mem` = the PKB MCP
server, `nicsuzor/overwhelm-dashboard`). Do NOT expect THIS PR to mention or contain those
external changes — that is not its job. Your job is to surface them: report (a) merging
this implies concomitant changes in [named other repos/projects], and (b) whether the PKB
ALREADY has tasks scheduled for those changes — search and answer yes-with-task-IDs, or
no-and-flag-it. This is a distinct output element (the External-impact line).

Failure patterns you are hunting (grounded in the vision):
  • Symptom, not cause — guards a manifestation while the root cause sits upstream.
  • Branch where the abstraction should move — special-case/flag where the right fix
    is to alter an existing abstraction or unify duplication.
  • Reimplements platform-native capability — builds in-framework what GitHub, the PKB
    server, Claude Code, or the OS already provides (the framework should SHRINK when
    external tools improve).
  • Coordination / enforcement creep — adds a gate/hook/obligation/mechanism to control
    agent behaviour. The framework's #1 recurring failure (two resets). Default to
    suspicion; burden is on the PR.
  • Component that doesn't earn its keep — new skill/script/flag/config surface for
    something an existing component should carry, or that won't survive neglect.
  • Entrenches what should shrink / fights the trajectory.
  • Procedure where philosophy belongs (skill/agent edits) — rigid mechanics/mode-routers
    where the principle is to state the goal and trust the agent.
  • Removal / de-enforcement — the PR DROPS or RELAXES a guard/lock/gate/mechanism. Don't
    assume removal is wrong (the framework should shrink) — but name what the removed
    mechanism protected, decide whether dropping it leaves a real safety gap or is correctly
    removing dead weight, and say where (if anywhere) that protected property now lives.

CONSUMER MIGRATION (redefinition / rename PRs). If the PR redefines or renames a status,
field, schema, or shared concept, ENUMERATE the consumers of the OLD definition and confirm
each was migrated. "All call sites reconciled" asserted is not enough — show it.
WARNING: verify against the PR DIFF (`gh pr diff`), NOT the local working tree / branch
state. Local-state checks produce false positives — a consumer can look migrated locally
while the diff doesn't carry the change. (This exact error happened in dogfooding.)

PERSISTENCE-TO-DURABLE-DESTINATION TRACE (standing requirement). For any PR that writes or
persists data, TRACE the full write path to a CONCRETE final resting place. Label each hop —
container-local / host-temp-not-backed-up / durable — and STATE the final durable destination
explicitly, or state plainly there isn't one. "Lands in the existing JSONL" is an automatic
FAIL of this requirement: name the EXACT file, resolve any path helper to a real path, and
check it against the backup/push policy. A non-backed-up intermediate is not automatically a
blocker, but it MUST be surfaced and accepted, never assumed away.

AXIOM BACKSTOP (trust-but-verify of rbg). You are the penultimate gate before the human,
so you backstop — not duplicate — the axiom stage. LOAD the canonical axiom set rbg
applies: `.agents/rules/AXIOMS.md` and its review checklist `.agents/rules/AXIOMS-REVIEW.md`
(the same files referenced from the rbg agent definition). Then ask ONE question: did any
axiom violation that rbg should have flagged slip past her? This is verification of her
coverage of the CLASS, not a from-scratch re-review that re-litigates everything she
already cleared — read the diff against the axioms looking for a missed violation, not for
agreement on calls she made. If you find one: name the axiom (e.g. `categorical-imperative`,
an instance-specific carve-out where a general rule was required), treat it as a
REDESIGN/HOLD-class signal in your verdict, AND flag it as a merge-prep/rbg PIPELINE GAP —
the axiom stage let it through, which is itself worth surfacing. If rbg's coverage holds,
say so in one line. Do NOT invent axioms or stretch a design smell into an axiom violation;
a design smell with no axiom behind it belongs in the failure-pattern hunt above, not here.
But the same discipline cuts BOTH ways: a narrow, literal, or technicality reading must NOT
be used to EXONERATE a genuine violation. This is the lens's own anti-rationalisation
discipline one level up — the backstop must not wriggle out of a real axiom hit the way a
clean-looking PR wriggles out of an architectural one. Concretely for `judgment-non-delegable`: when
a PR carries a STRUCTURED signal through an UNSTRUCTURED channel and reconstructs it
downstream by matching text — detecting a state or outcome by string-matching prose that
some hook or client happens to render into a transcript — the axiom applies REGARDLESS of
whether the current match is accurate or deterministic. The violation is the CHANNEL
ARCHITECTURE: structured data smuggled through an unstructured channel and re-parsed. A
"fixed marker / currently deterministic / works on this one client" defence does NOT
exonerate it; the correct design carries the signal as structured data end-to-end, and if
the structured channel isn't reachable that's an infrastructure gap to fix (halt + report),
not a licence to parse prose.

DISCIPLINE:
  • A clean bill of health must be EARNED, not defaulted to. If the obvious reading shows
    no misalignment, look at the non-obvious: is there a materially simpler design? what
    would the codebase look like in six months if every PR took this shape? Conclude
    "right place" only after naming where else it could have gone and why here is better.
  • If you find a tension, state it plainly. Do NOT minimise it or invent a rationalisation
    that makes it disappear ("it's pragmatic", "the tension is minor"). Name the conflict
    and the alternative; Nic decides whether to override with a reason — not your call.
  • CORE-MECHANISM vs PERIPHERAL — do NOT launder a core-mechanism anti-pattern as
    "separable." Distinguish a PERIPHERAL tension (genuinely separable from the change's
    value → may MERGE with the tension named) from an anti-pattern that IS the PR's CORE
    MECHANISM (→ 🔁 REDESIGN or ⚠️ HOLD). Sharp test: if you removed the smell, would the
    PR still do its job? If the smell IS the mechanism — removing it means redesigning the
    feature — that is precisely the well-engineered-workaround-that-should-be-a-redesign
    case this lens exists to catch: call REDESIGN. "Separable redesign, not a hold" must
    NEVER be used to wave through a fundamentally-wrong approach. Do NOT anchor on "the code
    is clean and passing" — clean+passing is exactly what hides this.
  • STEELMAN THE SECOND-BEST SITE. The alternative you name (in DISCIPLINE above and in
    OUTPUT step 2) must be the STRONGEST REAL place the logic could have lived — e.g. an
    existing processor that already handles the corpus and already persists durably — not a
    weak strawman picked to be easy to dismiss. Steelman it with a concrete "what each site
    has that the other lacks" comparison. "Here is better" only earns its place by naming
    the perishable/better info the alternative would actually lose.

OUTPUT — exactly what a final pre-merge human gate needs, no more.
Lead with: ✅ MERGE / ⚠️ HOLD / 🔁 REDESIGN.
Then only as much as the decision needs:
  1. What it actually does — one sentence, root-cause terms, not the PR's framing.
  2. The strategic call — if MERGE: one line on why this location/shape is right, naming
     the alternative you rejected. If HOLD/REDESIGN: THE one load-bearing concern as a
     chain — what the PR does → the real root cause → where the fix should live / the
     redesign → which vision principle is at stake. One concern; name any others in a
     single trailing line.
  3. External impact — one line: does merging imply concomitant changes in other
     repos/projects (name them), and are tasks already scheduled in the PKB for them
     (task-IDs) or not (flag it)? "None" if nothing connects outward.
  3b. Persistence (only if the PR writes/persists data) — one line naming the final durable
     destination as a concrete resolved path, or stating plainly there is none, with any
     non-backed-up intermediate hop surfaced.
  3c. Axiom backstop — one line: "rbg coverage OK" or "GAP — axiom <name> missed (pipeline
     gap, REDESIGN/HOLD-class)".
  4. Spot-check — the 1-2 file:line refs Nic can open to confirm the call in under a minute.
  5. Confidence + counter-argument — high/medium/low with the reason (NOT a fake %), and
     the strongest case AGAINST your own recommendation.
HARD LIMITS: no correctness/test findings (out of scope). Axiom findings ONLY via the
axiom-backstop line above — a single missed-violation flag, not a re-review dump. No
multi-point critique dumps. If MERGE, the whole output is ~4 lines — Nic should be able to approve on your
say-so without opening the diff, spot-check pointer there if he wants it. (The External-impact
line is part of those ~4.)

AFTER the verdict — this lens is the penultimate step before human approval, so record it
on the PR itself:
  • POST the lens output as a PR comment (`gh pr comment`), SCRUBBED of personal info —
    real names, emails, private filesystem paths, stakeholder identities. Keep it about the
    architecture, not the people.
  • COMPLETE the named check `strategic-review/arch-fit` on the PR head SHA, conclusion
    matching the verdict: ✅ MERGE → success; ⚠️ HOLD / 🔁 REDESIGN → failure (or neutral).
    Mechanism: GitHub Checks API / commit status on the PR head SHA — e.g.
    `gh api repos/{owner}/{repo}/check-runs -f name=strategic-review/arch-fit -f head_sha=<sha> -f status=completed -f conclusion=<success|failure|neutral>`
    (or a commit status). This requires a token with checks/statuses write on the repo.
  • The PR therefore may NOT be fully green until AFTER this skill runs — the
    `strategic-review/arch-fit` check is pending until then. That is expected.
```

## Orchestrator: James (default mode)

Commission James as the orchestrator. He manages the agent loop, evaluates output quality, iterates, and synthesises.

```
Agent(subagent_type="aops-core:james", prompt="[artifact + context]")
```

James will commission the right agents based on the artifact type and load the appropriate review context descriptor. You do not need to manage the agent loop — James does that.

## Review Context Descriptors

Context descriptors in `review-contexts/` configure James's behavior per artifact type:

| Descriptor        | When to use                                                   |
| ----------------- | ------------------------------------------------------------- |
| `pr-code.md`      | Code PRs — features, fixes, refactors                         |
| `pr-framework.md` | Framework PRs — skills, agents, hooks, enforcement, workflows |

James will read the relevant descriptor automatically based on what you tell him about the artifact.

## The Three Agents

| Agent      | What they do                                             | Ruth always runs      |
| ---------- | -------------------------------------------------------- | --------------------- |
| **rbg**    | Axiom compliance and workflow discipline — The Judge     | Yes — non-negotiable  |
| **pauli**  | Strategic critique via 10 cognitive moves — The Logician | As needed             |
| **marsha** | Independent runtime verification — The QA Reviewer       | When code is involved |

## Design rationale

The loop exists because one-shot prompting reliably produces competent-but-not-genius reviews: internally consistent, surface-level, answering the question as posed. James's job is to force elevation — from instance to class, from artifact to process, from "is this right?" to "is this the right question?". He also carries axiom compliance (Ruth) and runtime verification (Marsha) as non-negotiable dimensions that strategic review alone cannot provide.
