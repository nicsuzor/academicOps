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

This is the PENULTIMATE step before human approval. The lens reads deeply (diff + call sites + originating task + vision note + specs + PKB cross-repo links) but returns a thin surface — leading with a verdict glyph, then ONE scannable line per applicable field plus a spot-check pointer, so Nic can make the call without re-reading the diff himself. The thin surface is one-line-per-field, NOT a fixed line count: an honest MERGE that owns its external-impact, persistence, and axiom-backstop lines runs ~7 lines and that is correct. The cap is on what NIC READS per line; the lens still does the full analysis and records its full output on the PR (see the post + check actions in the prompt block).

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
what elsewhere is. Strategic context lives in: the PKB vision note `[[vision]]`
(permalink `aops-vision`; fetch with get_document) for framework intent and design
philosophy, and the relevant doc in the repo-root `specs/` tree (map: `specs/INDEX.md`)
for the canonical spec, plus the linked task. NOT STATUS.md or any operational snapshot.

SPEC GROUNDING. Ground the change against the canonical spec — normally the relevant
doc in the repo-root `specs/` tree. But for a taxonomy / SSoT edit, the edited file may itself BE
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
  • Component that doesn't earn its keep — new skill/script/flag/config/structure surface
    for something an existing component should carry, or that won't survive neglect. The
    burden is on the PR to name a consumer that genuinely NEEDS the new complexity; "a
    counter / rollup / analytics pass COULD consume it" is NOT justification — a
    hypothetical consumer whose need was never established earns nothing. NOR does a consumer
    that already EXISTS and runs establish need by merely existing: a rollup that COUNTS or
    DISPLAYS the signal, with nothing downstream DETERMINISTICALLY ACTING on it (no gate,
    branch, brake, or depended-upon workflow keyed off the value), is observability for its
    own sake — "it's live, tested, and wired to a dashboard" describes the CODE, not the need.
    And the burden SCALES with the cost the PR imposes: obligating many producer surfaces to
    emit a new structured signal is a high, spreading cost (coordination-creep-adjacent) that
    a count-and-display consumer does not justify — and that one surface ALREADY emits the
    token is not licence to extend the obligation to others; propagating an unjustified
    pattern compounds it, never blesses it. Complexity or structure added without a
    demonstrated benefit is ITSELF a defect, sufficient grounds to 🔴 REJECT on its own,
    independent of correctness. Of every new field/token/enum ask: who actually reads it, what
    do they DO differently because of it, and would a smart agent reading the prose have sufficed?
  • Unregistered mechanism / under-integrated component — the PR ADDS a skill / step / surface /
    gate / lifecycle-transition behaviour that lives ONLY in skill-instruction prose (plus thin
    pointers) and is INVISIBLE to the framework's self-description layer. This is DISTINCT from
    "doesn't earn its keep" (that is about NEED; this is about REGISTRATION & DISCOVERABILITY of a
    mechanism that may be perfectly justified). For any ADDED mechanism, check four homes and name
    each that is missing: (1) its OWNING canonical spec — is the mechanism described where the
    framework documents that workflow/transition (e.g. `specs/workflows/*.md` for a close/reconcile
    step), not only inside a `references/` file? (2) `specs/ENFORCEMENT-MAP.md` — does it have a row?
    This is MECHANICAL and rbg-BLOCKING: ENFORCEMENT-MAP's own header states "Any PR that adds,
    escalates, or retires a mechanism updates a row here in the same change (P#65); rbg blocks on
    currency." A "surface, not block" / non-gating mechanism is NOT exempt — that table already
    carries advisory, manual, non-blocking surfaces (e.g. marsha `/verify`, james `/review-pr`).
    (3) discoverability — `.agents/context-map.json` / README / any enforcement flowchart. (4) WHO
    RUNS IT WHEN, stated canonically — not reconstructable only by reading N skills. A mechanism
    integrated nowhere but skill prose + pointers is UNDER-INTEGRATED → ⚠️ HOLD / 🔁 REDESIGN
    (resolve the registration before merge); the ENFORCEMENT-MAP omission alone is an rbg pipeline
    gap to surface on the axiom-backstop line. BEWARE the anaesthetic: "it's only a surface, not a
    gate" reads as "not a mechanism" and silences this hunt — treat ANY added surface/step as a
    registrable mechanism regardless of whether it blocks.
  • Entrenches what should shrink / fights the trajectory.
  • Procedure where philosophy belongs (skill/agent edits) — rigid mechanics/mode-routers
    where the principle is to state the goal and trust the agent.
  • Removal / de-enforcement — the PR DROPS or RELAXES a guard/lock/gate/mechanism. Don't
    assume removal is wrong (the framework should shrink) — but name what the removed
    mechanism protected, decide whether dropping it leaves a real safety gap or is correctly
    removing dead weight, and say where (if anywhere) that protected property now lives.

CONSUMER MIGRATION / PROPAGATION COMPLETENESS. If the PR redefines or renames a status,
field, schema, or shared concept — OR changes a shared RULE, TEMPLATE, or RENDERING that more
than one site implements (e.g. a daily-note bar format, a worked example, a documented procedure
duplicated across surfaces) — ENUMERATE every site that implements the OLD form and confirm each
was migrated. Do NOT scope this to the files the PR happened to touch: grep the WHOLE repo for the
pattern the PR claims to fix and check the matches the diff did NOT change. The defect the PR's own
text says it removes must not survive in a sibling (a second template, a parallel SSoT doc, another
skill's copy) — that is a single-source-of-truth break and a class-instance miss (the fix applied to
one of N members). "All call sites reconciled" asserted is not enough — show the enumeration.
WARNING: verify against the PR DIFF (`gh pr diff`), NOT the local working tree / branch
state. Local-state checks produce false positives — a consumer can look migrated locally
while the diff doesn't carry the change. (This exact error happened in dogfooding.)

PERSISTENCE-TO-DURABLE-DESTINATION TRACE (standing requirement). For any PR that writes or
persists data, TRACE the full write path to a CONCRETE final resting place. Label each hop —
container-local / host-temp-not-backed-up / durable — and STATE the final durable destination
explicitly, or state plainly there isn't one. "Lands in the existing JSONL" is an automatic
FAIL of this requirement: name the EXACT file, resolve any path helper to a real path, and
check it against the backup/push policy. A non-backed-up intermediate is not automatically a
blocker, but it MUST be surfaced and accepted, never assumed away. CARVE-OUT: this fires for
PRs that introduce or change a WRITE PATH or destination. A PR that only changes a VALUE
flowing through an already-existing, already-traced path — no new persistence, no new file,
no new destination (e.g. dropping a runtime fallback so a value is derived differently but
lands in the same place) — does NOT owe a full trace: say "no new write path; existing
persistence unchanged" in one line and move on. Don't manufacture a persistence concern
where the PR creates none.

AXIOM BACKSTOP (trust-but-verify of rbg). You are the penultimate gate before the human,
so you backstop — not duplicate — the axiom stage. LOAD the canonical axiom set rbg
applies: `.agents/rules/AXIOMS.md` and its review checklist `.agents/rules/AXIOMS-REVIEW.md`
(the same files referenced from the rbg agent definition). Then ask ONE question: did any
axiom violation that rbg should have flagged slip past her? This is verification of her
coverage of the CLASS, not a from-scratch re-review that re-litigates everything she
already cleared — read the diff against the axioms looking for a missed violation, not for
agreement on calls she made. MECHANICAL CURRENCY CHECK (do NOT delegate this to rbg — she
demonstrably whiffs it): if the PR ADDS, ESCALATES, or RETIRES a mechanism (a gate, hook, skill,
step, surface, or lifecycle-transition behaviour — INCLUDING a non-blocking "surface"), open
`specs/ENFORCEMENT-MAP.md` and confirm the PR adds/updates a row IN THE SAME CHANGE. Its header
makes this rbg-blocking (P#65: "Any PR that adds, escalates, or retires a mechanism updates a row
here in the same change; rbg blocks on currency"). A missing row is a CONCRETE pipeline gap —
report it on the axiom-backstop line as "GAP — ENFORCEMENT-MAP row missing (P#65, rbg-blocking)",
treat it as HOLD/REDESIGN-class, and cross-reference the unregistered-mechanism failure pattern
above. This is mechanical, not a judgment call: do not rationalise it away because the mechanism
"only surfaces" or "isn't a gate." HUNT WHAT THE PR GETS WRONG; never shop for an axiom it
"satisfies" and cite that to bless the merge. Axiom COMPLIANCE is the absence of one kind of
problem, never a positive reason to merge — "the PR correctly applies axiom X" is not a
finding this backstop produces. Anti-rationalisation cuts BOTH ways: the backstop can talk
itself INTO a merge (shopping for a blessing axiom) as easily as out of a hold.
If you find one: name the axiom (e.g. `categorical-imperative`,
an instance-specific carve-out where a general rule was required), treat it as a
REDESIGN/HOLD/REJECT-class signal in your verdict, AND flag it as a merge-prep/rbg PIPELINE GAP —
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
That axiom has a COROLLARY that cuts the OTHER way, and missing it is how this lens has
already failed: we have smart agents — TRUST them for qualitative work, don't mechanise it.
A verdict, a recommendation, any conclusion inseparable from its reasoning is QUALITATIVE;
its real consumers read the prose and must. It stays qualitative even when its HEADLINE is a
closed-set label (APPROVE / REVISE / PASS / FAIL): the label is a lossy handle on the
conclusion, not the signal itself, and "it's one-of-N, so structuring it is fine" confuses
the value's SHAPE with whether it is a judgment. What makes a value legitimately MECHANICAL is
that a consumer DETERMINISTICALLY ACTS on it (branches, gates, brakes) — not that it happens
to be one-of-N; a label nothing acts on, fed to a count-and-display rollup, is a qualitative
judgment dressed as a metric. Adding a machine-countable token / enum / marker
to a qualitative signal is the anti-pattern this axiom PROHIBITS — it is NOT an application
of "don't dress prose as structure." When a PR mechanises a qualitative signal, do not bless
it as "correctly structured"; fire the doesn't-earn-its-keep pattern instead — name the
consumer that genuinely needs the enum, and if the only candidate is a hypothetical
analytics rollup, that is complexity without demonstrated benefit → 🔴 REJECT. This routes to
REJECT, not REDESIGN: the correct alternative to mechanising a qualitative signal is to leave
it as prose the agent reads — i.e. BUILD NOTHING, keep the status quo — so the PR's own
deliverable should not exist. Do NOT let a separable good edit bundled into the same PR
launder this into REDESIGN. (A grep false-positive that "justifies" such a token is itself the
argument for using an agent that reads context, not for the token.)

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
    value → may MERGE, with the tension named — see "✅ MERGE (tension noted)") from an
    anti-pattern that IS the PR's CORE MECHANISM (→ 🔁 REDESIGN, ⚠️ HOLD, or 🔴 REJECT).
    Sharp test: if you removed the smell, would the PR still have a DELIVERABLE a consumer
    needs? Ask it of the PR, NOT the system — the system keeps working without the PR (that's
    the status quo it adds to); the question is whether the PR still has a REASON TO EXIST. If
    the smell IS the mechanism but the goal still needs something built a different way or
    elsewhere → call 🔁 REDESIGN (the well-engineered-workaround case this lens exists to
    catch). But if removing the smell leaves the PR with NOTHING to deliver — the correct
    alternative is to BUILD NOTHING (keep the prose, the existing field, the status quo a
    smart agent already handles), the mechanism served a consumer that doesn't need it, or the
    problem isn't real — there is no redesign to salvage; call 🔴 REJECT. Beware the BUNDLED
    RESCUE: a separable, independently correct edit riding along in the same PR is NOT the
    PR's deliverable — re-land it standalone, and judge the core by what the PR is actually
    FOR. "Separable redesign, not a hold" must NEVER be used to wave through a
    fundamentally-wrong approach. Do NOT anchor on "the code is clean and passing" —
    clean+passing is exactly what hides this.
  • STEELMAN THE SECOND-BEST SITE. The alternative you name (in DISCIPLINE above and in
    OUTPUT step 2) must be the STRONGEST REAL place the logic could have lived — e.g. an
    existing processor that already handles the corpus and already persists durably — not a
    weak strawman picked to be easy to dismiss. Steelman it with a concrete "what each site
    has that the other lacks" comparison. "Here is better" only earns its place by naming
    the perishable/better info the alternative would actually lose.
  • DON'T REDESIGN TOWARD A FORECLOSED ALTERNATIVE. Before issuing 🔁 REDESIGN because the fix
    "should be a stronger mechanism elsewhere," confirm that stronger mechanism is not one the
    originating issue/task EXPLICITLY RULED OUT. If the issue says (e.g.) "without adding a new
    blocking gate where doctrine forbids it" and your redesign target IS a gate / forced dispatch /
    the very thing it foreclosed, REDESIGN is the wrong glyph: the PR took the constrained path on
    purpose. When the residual concern is a real-but-deferred enhancement that the issue's own
    constraints push OUT of this PR's scope, the call is ✅ MERGE (tension noted) + a named
    follow-up — not REDESIGN. Beware the over-fire twin of the rationalisation trap: "surfacing
    only defers, it doesn't drive resolution" proves too much — it convicts EVERY surface-not-block
    mechanism in the framework, since none force resolution. Distinguish "defers SILENTLY" (a real
    defect) from "surfaces VISIBLY but doesn't drive" (doctrine-compliant detection); only the
    former is a verdict-moving concern.

OUTPUT — exactly what a final pre-merge human gate needs, no more.
Lead with ONE verdict:
  ✅ MERGE — right place, right shape; approve.
  ✅ MERGE (tension noted) — right place, but a genuinely SEPARABLE watch-point worth
     recording (a dual-writer to retire later, a latent asymmetry) — not load-bearing enough
     to block. Use this instead of a silent MERGE when there's an X to keep an eye on; still
     merge-class. Name the X in the strategic-call line.
  ⚠️ HOLD — sound in principle, but one thing must be resolved or confirmed before merge.
  🔁 REDESIGN — right GOAL, wrong APPROACH: don't merge as-shaped; rework it (often
     elsewhere) and resubmit. The well-engineered-workaround case.
  🔴 REJECT — the change SHOULDN'T EXIST: close the PR. Either the goal isn't real, OR the
     complexity earns nothing — no consumer genuinely needs it (complexity without
     demonstrated benefit, a defect in itself). Deciding line vs REDESIGN: ask what the
     CORRECT alternative is. If it is to BUILD the thing differently or elsewhere → REDESIGN.
     If it is to BUILD NOTHING — keep the prose, the existing field, the status quo a smart
     agent already handles — the PR's own deliverable should not exist → REJECT. "Rework as
     prose / let the agent read it / the existing field already carries this" is REJECT
     (nothing to build), not REDESIGN. And a separable, independently-correct edit BUNDLED in
     the same PR does NOT rescue a reject-worthy core — re-land it standalone; judge the PR by
     its PRIMARY deliverable, not by what rides alongside.
Then only as much as the decision needs:
  1. What it actually does — one sentence, root-cause terms, not the PR's framing.
  2. The strategic call — if MERGE: one line on why this location/shape is right, naming the
     alternative you rejected; if a consumer/parser FAILS OPEN (degrades to a safe default
     rather than crashing or corrupting), name it — that property often bounds the risk and
     earns the merge. If HOLD/REDESIGN: THE one load-bearing concern as a chain — what the
     PR does → the real root cause → where the fix should live / the redesign → which vision
     principle is at stake. If REJECT: name the unjustified cost — what complexity it adds
     across how many surfaces and the consumer whose need is missing (or the non-problem it
     targets) → say plainly it should be closed. One concern; name any others in a single
     trailing line.
  3. External impact — one line: does merging imply concomitant changes in other
     repos/projects (name them), and are tasks already scheduled in the PKB for them
     (task-IDs) or not (flag it)? "None" if nothing connects outward.
  3b. Persistence (only if the PR introduces/changes a write path — see the carve-out) — one
     line naming the final durable destination as a concrete resolved path, or stating
     plainly there is none, with any non-backed-up intermediate hop surfaced.
  3c. Axiom backstop — one line: "rbg coverage OK" or "GAP — axiom <name> missed (pipeline
     gap, REDESIGN/HOLD/REJECT-class)".
  3d. Issue-completeness (only if the PR claims to close/address a tracked issue) —
     VERDICT-INDEPENDENT, one line: "discharges N of M fix-items from #X; remaining: <list>
     (task scheduled? id / not)". Orthogonal to placement: a perfectly-placed change can
     still close only part of its issue. Do NOT fold it into the counter-argument and do NOT
     let it move the verdict — it's a completeness FYI, not a defect.
  4. Spot-check — the 1-2 file:line refs Nic can open to confirm the call in under a minute.
  5. Confidence + counter-argument — high/medium/low with the reason (NOT a fake %), and the
     strongest case AGAINST your own recommendation.
  6. Out-of-scope routing (only if you surfaced a correctness/test concern you can't judge) —
     one line: name it and where it's been carried (marsha / a filed task), so a green
     arch-fit + green CI can't let it slip. See the routing action below.
HARD LIMITS: no correctness/test findings of your own (out of scope) — but a correctness
wrinkle you CAN'T judge gets ROUTED (field 6), not buried. Axiom findings ONLY via the
axiom-backstop line — a single missed-violation flag, not a re-review dump. No multi-point
critique dumps WITHIN a field. The thin surface is ONE LINE PER FIELD, not a fixed total:
omit fields that don't apply, but never amputate a mandatory field (external-impact,
axiom-backstop) to hit an arbitrary "~4 lines" — an honest MERGE runs ~7 lines and that is
correct. The cap is Nic's READING EFFORT per line (one scannable line, lead with the verdict,
spot-check pointer for anything he wants to open himself), not total honesty.

AFTER the verdict — this lens is the penultimate step before human approval, so record it
on the PR itself:
  • POST the lens output as a PR comment (`gh pr comment`), SCRUBBED of personal info —
    real names, emails, private filesystem paths, stakeholder identities. Keep it about the
    architecture, not the people.
  • COMPLETE the named check `strategic-review/arch-fit` on the PR head SHA, conclusion
    matching the verdict: ✅ MERGE → success; ⚠️ HOLD / 🔁 REDESIGN / 🔴 REJECT → failure
    (or neutral). PRIMARY mechanism = a COMMIT STATUS, which works under the bot token:
    `gh api -X POST repos/{owner}/{repo}/statuses/<sha> -f context=strategic-review/arch-fit -f state=<success|failure> -f description=<short>`
    Do NOT lead with the Checks API (`/check-runs`): under the bot PAT it 403s EVERY run
    ("must authenticate via a GitHub App"), so reaching for it first just burns a guaranteed
    failure. The check-run form becomes available only once this lens is promoted behind a
    GitHub App at pipeline-wiring time — upgrade then, use commit status now.
  • ROUTE any out-of-scope concern you surfaced. If reconstructing the change surfaced a
    CORRECTNESS or test-coverage wrinkle you can't judge (out of this lens's lane), your
    green arch-fit status + green CI must NOT be allowed to imply it's clear — CI may not
    cover it. Carry it: state it (output field 6) AND hand it to a correctness reviewer —
    file a follow-up task or @-mention marsha in the PR comment — so a real concern can't
    slip between "arch-fit OK" and "CI green."
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
