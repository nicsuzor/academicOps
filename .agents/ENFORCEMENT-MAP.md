# Enforcement Map

> **SSoT (state).** This file is the **canonical, operative** enforcement
> catalogue. The L0–L7 cost ladder below is the **only operative ladder**:
> `rbg` blocks on it via P#65, and all add/escalate/remove decisions cite a
> row of this file. Design rationale for the broader five-layer architecture
> lives in `specs/enforcement/enforcement.md` (spec); the per-mechanism
> reference catalogue is in `specs/enforcement/enforcement-mechanisms.md`
> (spec companion). The pipeline view (L0–L11) and pyramid view
> (base/middle/tip) in those spec files are **design narrative, not
> operative tiers** — no blocking decision uses them.
>
> **Adjacent state SSoT.** For the runtime catalogue of each session-time
> gate (what it is, where in source, how it's configured in `polecat.yaml`,
> how to verify it's firing, how to debug it when it isn't) — see
> [`aops-core/GATES.md`](../aops-core/GATES.md). The split: this file ranks
> mechanisms on the cost ladder + maps them to axioms (the operative
> decision register); `GATES.md` answers per-gate forensic-debug questions
> (the "is `ida` firing in this session?" register). Both are state.

Maps each mechanical enforcement mechanism to the rule(s) it enforces, its
execution context, its failure tier, and **what it costs to run**. Updated
whenever a check is added or retired (P#65).

## User story: how the framework gets better

Two flows, separated by design (AXIOMS § A17 — Recusal). The user is the
client of both, but each flow runs in its own context with its own job.

### Flow 1 — File a bug (incident phase, forensic)

> "Something just went wrong in this session."

When an agent hits friction (tool bug, missing instruction, dead end), it MUST invoke the `/learn` skill immediately at the point of discovery. One friction = one `/learn` call. Do NOT ask the user "want me to file this?" or "happy to file if you confirm" — filing friction is unilateral.

The dispatched agent reads the transcript and
files a GitHub issue containing only:

1. **What happened** — quoted from the transcript.
2. **Root cause category** — one of the documented categories.
3. **Rule already in place (if any)** — which axiom, gate, hook, or skill
   instruction was supposed to catch this, and at what tier.
4. **Impact** — concrete cost (turns burned, work to undo, trust hit).

That's it. **The /learn agent is forbidden from proposing a fix.** It is
the witness, not the legislator. The user doesn't have to think about
"what should the framework do about this" at file time — they just have to
report what happened. If they hit the same problem three times, that's
three forensic issues; the recurrence count is the evidence base later.

The user can file an issue by hand instead — same constraints. A bare
"please add a gate that does X" issue is in scope to be edited down to
forensic facts before it gets used.

### Flow 2 — Improve the framework (review phase, detached)

> "Let's look at what's piled up and decide what to actually change."

Periodically — when the issue queue feels heavy, or on a cadence the user
sets — the user runs `/issue-sweep`. The dispatched agent enters with no
prior exposure to any individual incident. It:

1. Pulls up to 20 open issues and classifies each (close-stale, comment-
   only, single-task, fix-epic, defer).
2. For any issue whose remediation would touch the framework (an axiom,
   gate, hook, skill instruction, or row of this map), runs the
   cost-ladder review: generalise the category → check existing
   mechanisms → classify the failure shape (propagation / escalation /
   rule absent) → default to the cheapest sufficient level → cite the
   specific row of this map the fix propagates from or would add.
3. Surfaces the proposed cycle to the user (`AskUserQuestion` gates on
   each disposition group). The user approves, edits, or defers.
4. On `y`: files fix-epics or single tasks, stamps labels, logs the
   cycle. Fix-epics stay `queued` until the user dispatches them via
   `/supervisor`.

The sweep agent will not propose **adding or escalating** a rule from one
incident — a new gate, a new axiom, a tier-bump (e.g. L1→L3), a new hook
firing surface. Add-or-escalate proposals need ≥3 cited recurrences plus
the CBA evidence below (named cheaper level tried, ongoing cost,
reversibility).

This bar does NOT apply to **fixes** within an existing enforcement
surface at the same tier — a skill that does the wrong thing, an agent
prompt that misroutes, a hook with broken logic, a gate whose verdict
table is incomplete. A clear forensic incident is sufficient evidence
for `fix-epic` or `single-task`; sweep dispatches the fix without
waiting for two more incidents. The same rule covers **directed
architectural changes** the user has explicitly authorised: one
incident plus user direction is sufficient — the user's authorisation
substitutes for the recurrence count, not for the cost-ladder
reasoning.

What gets deferred for pattern is the _add-or-escalate_ case: proposals
to grow the enforcement surface from a single witness report. Single
incidents that are bugs get fixed; single incidents that are
escalation proposals get logged and either closed or deferred.

### Why the split

Recency is bias. The agent that just lived through a failure proposes
fixes shaped by that failure — usually a new gate or axiom built around
one incident, which doesn't fit the seamless web of existing rules. By
separating the witness role from the judicial role, the framework's
volume and direction of change is governed by cross-incident patterns
visible from outside, not by the urgency a single failure feels from
inside. The user gets to be honest in flow 1 (no need to over-frame a
problem to justify a fix) and disciplined in flow 2 (no rule changes
without the evidence base).

### What the user does NOT need to do

- Propose remediations at /learn time. Just describe what happened.
- Worry about whether their issue duplicates an existing one. The sweep
  agent groups by root cause and bumps volume on duplicates.
- Choose a tier (L0–L7) for any rule. The sweep agent applies the cost
  ladder; the user gates the proposal.
- Maintain this document by hand. Approved fix-epics that add or move a
  row update this map as part of the change (per P#65).

## Cost ladder — escalate reluctantly

Every enforcement mechanism is paid for in tokens, latency, or attention,
every session, forever. The cheapest sufficient level wins. Costs in the
table below are **marginal** — the per-fire token / latency footprint of
that level alone. Combine with the firing frequency in the row's
Cost/Impact column to get the per-session total. Indicative numbers are
order-of-magnitude — measure when proposing.

| Level | Mechanism                               | Indicative marginal cost                                                 | When justified                                                 |
| ----- | --------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------- |
| L0    | PKB note / inline comment               | ~0                                                                       | Any time                                                       |
| L1    | Skill SKILL.md / CORE.md text           | ~50–500 tok/session × per-invoke (cached at SessionStart)                | Recurrent friction (≥3 instances) and a clear callsite         |
| L2    | Pre-commit hook                         | ~50ms–2s wall-clock per commit                                           | Mechanical, deterministic check; no judgement                  |
| L3    | Stop-hook injection (always-on)         | ~400–4,000 tok in-window per session (compounds on repeated Stop)        | Cross-cutting + agent demonstrably forgets between turns       |
| L4    | PreToolUse gate (`warn`)                | ~20–800 tok per fire (depends on injected template); no model dispatch   | Periodic compliance check without LLM dispatch                 |
| L5    | PreToolUse gate (`block`)               | ~100–500 tok per block fire + tool-call latency to evaluate every call   | Hard-block needed; destructive / legal / privacy               |
| L6    | LLM-gated hook (subagent call per fire) | ~1.5–3k tok + 5–30s latency × every fire (subagent dispatch)             | Last resort; structural fixes (L1–L3) have failed              |
| L7    | Numbered axiom (A-tier)                 | Permanent context burn (~100 lines, prompt-cached) + every surface cites | Rule must beat trained reflex; cross-cutting; primary contract |

> **Anti-pattern**: jumping to L3+ when the actual failure is recurrence at a
> single L1 callsite. Most over-deference recurrences (issue #195) were L1
> fixes that propagated incompletely, not failures of L1 as a tier.

> **One-ladder rule.** L0–L7 above is the only operative ranking. The
> L0–L11 pipeline view and the base/middle/tip pyramid in
> `specs/enforcement/enforcement.md` describe _when_ a mechanism fires and
> _how_ it sits architecturally; they do not score severity and no
> blocking rule cites them. Pipeline / pyramid references in the rest of
> this file are cross-reference annotations, not tier criteria.

## PR requirements for enforcement changes

This applies to PRs that **add, escalate, or remove** a row in the tables
below — a new gate, a tier change (e.g. L1→L3), a new axiom, an additional
hook firing surface, or removing one. Bug fixes within an existing
enforcement surface at the same tier (correcting wrong logic or wrong
prose in an existing skill, agent, hook, or gate) do NOT require CBA —
they need only a clear description of the bug and the corrective edit.
User-directed architectural changes skip the ≥3 recurrence requirement
but still require cost-ladder reasoning to document where the fix lands
on the enforcement ladder.

Any PR that adds, escalates, or removes enforcement MUST include a
**Cost-Benefit Analysis** block in the PR body:

1. **Friction evidence**: ≥3 concrete recurrences with links (transcript, PR,
   issue, /retro report) for add/escalate proposals. Fewer than 3 → close as
   premature unless explicitly directed by the user.
2. **Cheapest plausible level**: which row of the ladder above could
   reasonably address this?
3. **Why escalate above that level (if escalating)?**: what was tried at the
   cheaper level; specifically why it failed, with evidence.
4. **Ongoing cost**: token cost per fire × fire frequency, or latency
   estimate. Use the Cost/Impact column format below.
5. **Reversibility**: if this doesn't reduce recurrences in the next 5
   /retro reviews, how do we retire it?

Reviewers should WARN on missing CBA, BLOCK on missing items 1, 4, or 5.

## Worked example: A7

A7 ("Exercise Authority — Calibrate Capability", `aops-core/AXIOMS.md`) sits at **L7**, the highest tier. The placement is the result of an explicit cost-benefit decision, not a default.

- **Friction**: 9+ over-deference recurrences across 6 agent surfaces (issue #195 thread, issue #950, plus fresh /retro evidence from 2026-05-11 sessions).
- **Cheaper level attempted first**: L1 (skill instruction text in CORE.md / butler.md / planner). Tried 9 times across the #195 history. Each attempt reached one more surface; the next session hit a surface the patch hadn't reached.
- **Why escalation justified**: per-surface, permissively-framed L1 fixes did not beat the trained "seek confirmation" reflex. Reframing as an obligation-level axiom (L7) puts equal weight on the no-abdication direction as on the no-ultra-vires direction (the original A7).
- **Forward cost**: A7's text is ~100 lines in always-on AXIOMS.md, prompt-cached at SessionStart. Surface citations are L1 (≤10 lines each).
- **Future fixes** against any of A7's three edges should land at the cheapest sufficient level — usually L1 propagation into the specific failing surface, NOT additional axioms. Adding A18/A19 against the same root would repeat the failure mode this PR resolved.
- **Reversibility / acceptance criterion**: zero FM-1 through FM-7 recurrences across the next 5 /retro reviews. If the criterion fails, the documented contingency is L6 (pre-Stop LLM hook), per `note-23e58353`.

This serves as the template for any future L6/L7 escalation: the CBA must look like this, with named prior attempts and explicit reversibility.

## Runtime hooks (in-session)

Mechanisms that fire during a live Claude Code / Gemini session. Routed
through `aops-core/hooks/router.py`. Tier: `hint` = injected reminder,
`warn` = non-blocking warning, `block` = hard gate.

| Mechanism             | Hook event       | Source                                                  | Rule(s)                                           | Scope                                                                                                                                                        | Tier   | Cost / Impact                                               | Behaviour                                                                                      |
| --------------------- | ---------------- | ------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `hydration` gates     | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | (R: hydration discipline)                         | All sessions                                                                                                                                                 | `warn` | L4 · ~20 tok × 1/session                                    | Blocks tool calls until hydrator runs (mode-dependent)                                         |
| `enforcer` gate       | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | A1, A6, A8 (axiom compliance, scope, halt)        | All sessions                                                                                                                                                 | `warn` | L6 · ~820 tok + subagent dispatch × 1–3/session             | Periodic compliance checks via the enforcer subagent                                           |
| `qa` gate             | Stop             | `aops-core/lib/gates/definitions.py`                    | (R: QA before completion)                         | All sessions                                                                                                                                                 | `warn` | L3 · ~615 tok × 1/session                                   | Requires verification (marsha via /verify skill) before session can stop                       |
| `handover` gate       | Stop             | `aops-core/lib/gates/definitions.py`                    | (R: handover discipline)                          | Per `polecat.yaml` overlay — `run_defaults` / `crew_defaults` for polecat workers, `local_defaults` for local-host orchestrator (POLECAT_SESSION_TYPE unset) | `warn` | L3 · ~421 tok × 2–8/session (compounds → ~850–3,400 tok)    | Blocks Stop until commit + task update + framework reflection complete                         |
| `ida` gate            | Stop             | `aops-core/lib/gates/definitions.py`                    | A3, A4, A11 (proof, citation, observability)      | All sessions                                                                                                                                                 | `warn` | L3 · ~515 tok × 3–10/session (compounds → ~1,550–5,150 tok) | Non-blocking reminder to back assertions with proof and disclose skips                         |
| `custodiet` gate      | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | (R: workflow discipline — premature termination)  | All sessions                                                                                                                                                 | `warn` | L4 · ~500 tok × rare                                        | Detects scope explosion / plan-less execution                                                  |
| ~~`policy_enforcer`~~ | ~~PreToolUse~~   | ~~`aops-core/hooks/policy_enforcer.py`~~                | —                                                 | —                                                                                                                                                            | —      | —                                                           | **Retired 2026-05-15** — sandbox-supersedes-hook (aops-e0d015d9, D1 decision on aops-7dc1d899) |
| `aca_data_autocommit` | PostToolUse      | `aops-core/hooks/router.py` `_run_aca_data_autocommit`  | (procedural: keep PKB synced)                     | When `$ACA_DATA` set                                                                                                                                         | n/a    | L2 · ~100ms wall-clock × per write op                       | Auto-commits `$ACA_DATA` after state-modifying tool calls                                      |
| `context-map hints`   | UserPromptSubmit | `aops-core/hooks/router.py` `_inject_context_map_hints` | (procedural: discovery via `.agents/context-map`) | Repos with `.agents/context-map.json`                                                                                                                        | `hint` | L1 · ~50–200 tok × per prompt                               | Injects relevant doc pointers from the repo's context map                                      |

## Retired runtime hooks

Gates that were defined in config infrastructure but have since been removed.

| Mechanism     | Retired in | Notes                                                                                                                                                                   |
| ------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `commit` gate | PR #988    | Config key only — never implemented in `gates/definitions.py` and never registered here. Superseded by `handover` gate (Stop hook already mandates commit before Stop). |

## Pre-commit hooks

| Hook ID                     | Script                                 | Rule(s)                    | Tier   | Cost / Impact               | Behaviour                                                                                                                                                                                                                                                                                                                                               |
| --------------------------- | -------------------------------------- | -------------------------- | ------ | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `check-no-new-orphan-md`    | `scripts/check_no_new_orphan_md.py`    | R5.6                       | `warn` | L2 · ~200ms × per commit    | Exits 1 on new `.md` files outside canonical-location allowlist                                                                                                                                                                                                                                                                                         |
| `check-framework-integrity` | `scripts/check_framework_integrity.py` | (wikilink index integrity) | `warn` | L2 · ~500ms–2s × per commit | Exits 1 on broken wikilinks or missing SKILLS/WORKFLOWS index entries                                                                                                                                                                                                                                                                                   |
| `check-no-fallbacks`        | `scripts/check_no_fallbacks.py`        | A8 / P#8                   | `warn` | L2 · ~100ms × per commit    | Exits 1 on silent-fallback patterns in `aops-core/hooks/*.py`, `aops-core/agent-env-map.conf`, `scripts/repo-sync-cron.sh` (see issue #930 for context)                                                                                                                                                                                                 |
| `normalize-mcp-names`       | `scripts/normalize_mcp_names.py`       | (issue #1128)              | `warn` | L2 · ~100ms × per commit    | Auto-heals Gemini-form MCP names (`mcp_pkb_get_task`) back to canonical Claude form (`mcp__pkb__get_task`) in `aops-core/**/*.md` and `.github/agents/**/*.md`. Inverse of `scripts/build.py:698`; exits 1 on rewrite (same UX as `ruff --fix`). Also mirrored in `lint.yml` initial+autofix-push+final steps for CI-side commits that skip pre-commit. |

## CORE.md directives (always-on)

Static guidance embedded in `.agents/CORE.md` and loaded into every agent
session context for this repo. Unlike hooks, these are not event-triggered —
they are part of the agent's context window whenever it works in academicOps.
Prompt-cached at SessionStart, so marginal cost is ~$0 once cached; the
listed cost is the cold-start contribution.

| Directive   | Source                                                    | Rule(s)                           | Scope            | Tier   | Cost / Impact                           | Behaviour                                               |
| ----------- | --------------------------------------------------------- | --------------------------------- | ---------------- | ------ | --------------------------------------- | ------------------------------------------------------- |
| `pkb-first` | `.agents/CORE.md` — "Where to find documentation" section | (procedural: PKB-first discovery) | academicOps repo | `hint` | L1 · ~120 tok at session start (cached) | Instructs agents to use PKB before reading source code. |

## Bridge-level constraints

Synchronous validation in library/bridge code that fires at call time, not via the hook router. Not session hooks — fire whenever the underlying function is invoked (MCP call, direct import, or CLI).

| Mechanism                       | Source                  | Rule(s)                                                                                | Scope                                                                         | Tier    | Cost / Impact                                | Behaviour                                                                                                                                                                              |
| ------------------------------- | ----------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `create_task` prefix guard      | `polecat/pkb_bridge.py` | type-prefix-filename consistency (spec: `projects/aops/specs/pkb/consistency.md` AC#5) | All `create_task` calls via PKB bridge                                        | `block` | L2 · negligible (string match × each call)   | Raises `ValueError` when ID prefix mismatches the task type or project slug                                                                                                            |
| `claude OAUTH token pre-flight` | `polecat/cli.py`        | A8 (Halt rule — fail fast, no silent fallback). Task: aops-06ab3ee0                    | All `polecat run` / `crew` / `swarm` invocations where `cli_tool == "claude"` | `block` | L2 · negligible (env var check × per invoke) | Exits 4 with `claude setup-token` remediation message when `CLAUDE_CODE_OAUTH_TOKEN` is unset. Claude auth is OAuth-env-only; `.credentials.json` / `ANTHROPIC_API_KEY` paths removed. |

## Scheduled batch automation

Side-effects triggered by `aops-core/scripts/dump_pr_state.py` on a cron schedule.

| Mechanism             | Source                               | Rule(s)                             | Scope                     | Tier | Cost / Impact                                      | Behaviour                                                                                                                                                                                                     |
| --------------------- | ------------------------------------ | ----------------------------------- | ------------------------- | ---- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apply_triage` labels | `aops-core/scripts/dump_pr_state.py` | (procedural: PR routing visibility) | All open PRs per cron run | n/a  | L0 · negligible (subprocess × per open PR per run) | Applies `triage:escalate`, `triage:stale`, `triage:auto-mergeable`, or `triage:needs-judgment` based on CI status, staleness, and branch naming; creates a GitHub issue for escalate-class PRs if none exists |

## PR-pipeline agents (v2)

LLM agents that fire on PR events to enforce framework discipline at the
review surface. Each row maps a named framework agent to one named status
check (the contract — see `specs/workflows/pr-pipeline-v2.md` §3.2). Branch protection
AND-gates these statuses directly; there is no LLM judgment in the merge
gate. **Phase 1 operative (PR #1062). Remaining phases: 2 (pauli alignment surface), 3 (merge-prep mechanic strip-down), 5 (cross-repo rollout).**

| Agent (status name)                | Source (workflow + prompt)                                                                                                                                                                                                    | Rule(s)                                                                                             | Scope                                                           | Tier    | Cost / Impact                                                                                      | Behaviour                                                                                                                                                                                                                                          |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `enforcer-status` (rbg)            | Trigger: `.github/workflows/triggers/enforcer.yml`; Reusable: `.github/workflows/agent-enforcer.yml@enforcer-v1` (tag pending post-merge) + `.github/agents/enforcer.agent.md` (sources `aops-core/agents/rbg.md`)            | A1, A6, A8 (axiom compliance, scope, halt); P#65 (enforcement-map row required for new agents)      | Every PR with non-doc-only diff                                 | `block` | L6 · ~1.5–3k tok + 5–30s per fire × 1 per HEAD SHA (SHA-skip dedupe)                               | Reviews PR diff against axioms. Posts GitHub PR review (APPROVED / CHANGES_REQUESTED) + `enforcer-status` on HEAD SHA. SHA-skip prevents double-review of unchanged HEAD.                                                                          |
| `alignment-status` (pauli)         | `.github/workflows/agent-alignment.yml@alignment-v1` (GHA-side: pending+queue) + `aops-core/scripts/alignment-dispatcher.sh` (host-side: polecat) + `.github/agents/alignment.agent.md` (sources `aops-core/agents/pauli.md`) | (R: alignment to PKB-recorded design intent); A11 (observability — alignment verdict visible on PR) | Every PR (alignment is a strategic check, not diff-conditional) | `block` | L6 · ~3–5k tok + 3–10 min per fire × 1 per HEAD SHA. Off-GHA cost: polecat container time on host. | GHA workflow posts `alignment-status: pending` + work-queue entry. Host cron picks up, dispatches polecat with PKB-equipped pauli, pauli posts review + terminal status. Closes the v1 gap (#1034) where alignment was absent from the merge gate. |
| `mechanic-status` (was merge-prep) | `.github/workflows/agent-mechanic.yml@mechanic-v1` + `.github/agents/mechanic.agent.md` (trimmed from `merge-prep.agent.md`)                                                                                                  | (procedural: rebase + conflict resolution)                                                          | Every PR with `mergeable: CONFLICTING` or stale base            | n/a     | L4–L6 · ~500–2k tok per fire × bazaar-windowed cron                                                | Mechanical only: rebase / merge from base, resolve unambiguous conflicts, post `mechanic-status`. Does not approve, does not triage, does not substitute for missing agent verdicts.                                                               |

### Retired (v1 → v2)

| Mechanism                                                                                            | Retired in        | Notes                                                                                                                              |
| ---------------------------------------------------------------------------------------------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Author-trailer loop-skip (`Enforcer-By:` / `Merge-Prep-By:` grep on HEAD commit)                     | Phase 1, PR #1062 | Replaced by SHA-based loop-skip (`specs/workflows/pr-pipeline-v2.md` §3.6, §8). Closed PR #1037 black-hole bug.                    |
| Triage-substitution (merge-prep approves ⇒ implies all agent verdicts present)                       | Phase 1, PR #1062 | Branch protection now AND-gates each `<agent>-status` directly (`specs/workflows/pr-pipeline-v2.md` §5). No LLM in the merge gate. |
| Loose triggers on enforcer (`workflow_run` + `pull_request` + `workflow_dispatch` + `workflow_call`) | Phase 1, PR #1062 | v2 contract: `workflow_call` only (`specs/workflows/pr-pipeline-v2.md` §3.1). Closes ~130M cache_r/wk waste (`aops-638a351e`).     |

## Axiom × mechanism cross-reference

Folded forward from the older per-axiom registry that previously lived at
`specs/enforcement/enforcement-map.md` (now a redirect stub). This is a
secondary index over the mechanisms defined above — each row points at the
mechanism(s) that catch a given axiom, the action tier, and where in the
session lifecycle the catch fires. Two coexisting tier vocabularies are in
play here for historical reasons:

- The **L0–L7 cost ladder** (this file, above) — the operative ranking;
  used for add/escalate/remove decisions.
- The legacy **action ladder** (`inject` → `advisory` → `warn` → `block` →
  `hard-deny`) — descriptive: what the mechanism _does_ when it fires.
  Retained in the rows below because the per-axiom view is easier to scan
  with the action tier than with the cost tier; not used for blocking
  decisions.

| Action    | Definition         | Released when             |
| :-------- | :----------------- | :------------------------ |
| inject    | info into context  | n/a — non-blocking        |
| advisory  | verdict for caller | caller integrates verdict |
| warn      | gate warning       | n/a — agent proceeds      |
| block     | pauses progress    | gate condition met        |
| hard-deny | rejects call       | not released              |

The two vocabularies are not in conflict: the cost ladder ranks _how
expensive a mechanism is to maintain and run_, while the action vocabulary
describes _what the mechanism does in the moment it fires_. Most rows
below name an action; the cost-tier of the mechanism is recorded in the
tables above.

### Gate mode environment variables

| Variable              | Default | Values                 | Controls                  |
| :-------------------- | :------ | :--------------------- | :------------------------ |
| `ENFORCER_GATE_MODE`  | `block` | `warn`, `block`        | periodic compliance audit |
| `HYDRATION_GATE_MODE` | `off`   | `off`, `warn`, `block` | hydration before work     |
| `QA_GATE_MODE`        | `block` | `warn`, `block`        | QA verification           |
| `COMMIT_GATE_MODE`    | `warn`  | `warn`, `block`        | commit policy             |
| `HANDOVER_GATE_MODE`  | `warn`  | `warn`, `block`        | reflection before exit    |

### Axiom-keyed rule registry

| Rule         | Mechanism                            | Action     | Fires at       | Status                                                                                                     |
| :----------- | :----------------------------------- | :--------- | :------------- | :--------------------------------------------------------------------------------------------------------- |
| A1 Closure   | AXIOMS.md / CORE.md                  | inject     | always-on      | active                                                                                                     |
| A1 Closure   | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A2 Gen       | AXIOMS.md instruction                | inject     | always-on      | active                                                                                                     |
| A2 Gen       | `rbg` critic review                  | advisory   | review-time    | active                                                                                                     |
| A2 Gen       | aops-skill Phase 2 design            | advisory   | pre-impl       | active                                                                                                     |
| A3 Epistemic | AXIOMS.md / CORE.md                  | inject     | always-on      | active                                                                                                     |
| A3 Epistemic | Proof-of-compliance                  | block      | `release_task` | active                                                                                                     |
| A3 Epistemic | `marsha` verification                | advisory   | review-time    | active                                                                                                     |
| A3 Epistemic | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A4 Citations | AXIOMS.md instruction                | inject     | always-on      | active                                                                                                     |
| A4 Citations | auto-mode `Academic Integrity`       | warn       | PreToolUse     | active                                                                                                     |
| A4 Citations | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A4 Citations | `/learn` RCA schema                  | block      | invocation     | active                                                                                                     |
| A5 SSOT      | AXIOMS.md / aops-skill SSOT          | inject     | always-on      | active                                                                                                     |
| A5 SSOT      | auto-mode `Backup File Patterns`     | warn       | PreToolUse     | active                                                                                                     |
| A5 SSOT      | `find_duplicates` tool               | advisory   | on-demand      | active                                                                                                     |
| A5 SSOT      | `rbg` duplicate review               | advisory   | review-time    | active                                                                                                     |
| A6 Scope     | AXIOMS.md / Decision Frm             | inject     | always-on      | active                                                                                                     |
| A6 Scope     | TodoWrite reminder                   | inject     | TodoWrite      | active                                                                                                     |
| A6 Scope     | auto-mode `Scope Discipline`         | warn       | PreToolUse     | active                                                                                                     |
| A6 Scope     | auto-mode `Plan First`               | warn       | PreToolUse     | active                                                                                                     |
| A6 Scope     | auto-mode `Costly Operations`        | warn       | PreToolUse     | active — threshold: >50 calls or >$1                                                                       |
| A6 Scope     | `orchestrator_boundary`              | warn       | PostToolUse    | active                                                                                                     |
| A6 Scope     | enforcer gate (B)                    | warn/block | PreToolUse     | active                                                                                                     |
| A6 Scope     | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A6 Scope     | pr-reviewer GHA                      | warn       | PR push        | active                                                                                                     |
| A7 Authority | AXIOMS.md / task criteria            | inject     | always-on      | active                                                                                                     |
| A7 Authority | auto-mode `Classification`           | warn       | PreToolUse     | active                                                                                                     |
| A7 Authority | auto-mode `Acceptance Criteria`      | warn       | PreToolUse     | active                                                                                                     |
| A7 Authority | `marsha` criterion check             | advisory   | review-time    | active                                                                                                     |
| A7 Authority | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A7 Authority | pr-reviewer GHA                      | warn       | PR push        | active                                                                                                     |
| A7 Authority | QA gate                              | block      | Stop           | active — closes on `update_task in_progress` / write tool; reopens on `qa\|verify\|marsha` subagent        |
| A8 Halt      | AXIOMS.md / CORE.md                  | inject     | always-on      | active                                                                                                     |
| A8 Halt      | auto-mode `No Validation Bypass`     | block      | PreToolUse     | active — `--force` carve-out for benign cleanup                                                            |
| A8 Halt      | auto-mode `Silent Workaround`        | warn       | PreToolUse     | active                                                                                                     |
| A8 Halt      | auto-mode `Infra Workarounds`        | warn       | PreToolUse     | active                                                                                                     |
| A8 Halt      | `policy_enforcer` (git)              | hard-deny  | PreToolUse     | active                                                                                                     |
| A8 Halt      | `fail_fast_watchdog`                 | warn       | PostToolUse    | active                                                                                                     |
| A8 Halt      | commit gate                          | warn       | commit-time    | active                                                                                                     |
| A8 Halt      | branch protection                    | block      | merge          | active                                                                                                     |
| A8 Halt      | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A9 Boundary  | AXIOMS.md instruction                | inject     | always-on      | active                                                                                                     |
| A9 Boundary  | credential isolation                 | hard-deny  | SessionStart   | active                                                                                                     |
| A9 Boundary  | CC auto-mode rules                   | block      | PreToolUse     | active                                                                                                     |
| A9 Boundary  | `policy_enforcer` (env)              | hard-deny  | PreToolUse     | active                                                                                                     |
| A9 Boundary  | commit gate                          | warn       | commit-time    | active                                                                                                     |
| A9 Boundary  | branch protection                    | block      | merge          | active                                                                                                     |
| A10 Immut    | AXIOMS.md / CORE.md                  | inject     | always-on      | active                                                                                                     |
| A10 Immut    | auto-mode `Evidentiary Immutability` | block      | PreToolUse     | active — globs: `**/records/**`, `$ACA_DATA/records/**`, `~/brain/records/**`, `~/writing/data/records/**` |
| A10 Immut    | `policy_enforcer` paths              | hard-deny  | PreToolUse     | active                                                                                                     |
| A10 Immut    | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| Hydration    | hydrator / skills                    | inject     | UserPrompt     | active                                                                                                     |
| Hydration    | hydration gate                       | warn       | lifecycle      | active                                                                                                     |
| Handover     | /dump / reflection                   | inject     | invocation     | active                                                                                                     |
| Handover     | handover gate                        | warn/block | Stop           | active                                                                                                     |
| Audit        | countdown / subagent                 | warn/block | threshold      | active                                                                                                     |
| Audit        | compliance block flag                | hard-deny  | lifecycle      | active                                                                                                     |
| Pipeline     | pr-reviewer / enforcer               | warn       | PR push        | active                                                                                                     |
| Pipeline     | linter / branch prot                 | block      | merge          | active                                                                                                     |
| Pipeline     | loop detector                        | hard-deny  | merge-prep     | active                                                                                                     |
| Pipeline     | admin approval                       | block      | merge          | active                                                                                                     |
| Linting      | rules 6-9 (skill/agent)              | block      | Pre-commit/PR  | active — linter: aops-core/lib/lint_axiom_refs.py                                                          |
| Linting      | permissions-lint                     | block      | PR push        | planned                                                                                                    |
| Supervisor   | plan-review gate                     | block      | post-decomp    | active                                                                                                     |
| H91 Deadline | HEURISTICS.md                        | inject     | always-on      | active                                                                                                     |
| H91 Deadline | `rbg` review                         | advisory   | review-time    | active                                                                                                     |

### Known gaps (axiom-keyed view)

- **Hydration**: parent skip cascades to child; missing hydration/commit gate bodies.
- **Reactive**: PostToolUse on tool error is `planned` (Phase 2).
- **QA**: gate active (close-on-work-begin landed); requirements still freeform — verifier prompt reviews session narrative, no structured acceptance-criteria source yet.
- **Settings**: global/user rules unverifiable from this repo.
- **Evidence Loop**: Steps 4-5 (pattern detection) and Step 7 (auto-map update) partial/unbuilt.

### How to update

1. **Observe** failure (QA, /retro, /sleep, report).
2. **File evidence** via `/learn`.
3. **Locate rule** in registry above.
4. **Propose tier change** (escalate/demote) — cite the L0–L7 cost ladder row, not the action vocabulary.
5. **Update row** in the same PR (P#65).

## Related

- `specs/enforcement/enforcement.md` — design rationale for the five-layer
  architecture (spec; not operative).
- `specs/enforcement/enforcement-mechanisms.md` — per-mechanism reference
  catalogue keyed to the L0–L11 pipeline view (spec companion; not
  operative).
- `specs/enforcement/ultra-vires-enforcer.md` — enforcer agent + gate
  internal design (spec).
- `specs/enforcement/hook-router.md` — hook router architecture (spec).
- `aops-core/AXIOMS.md` — universal axioms.
- `.agents/rules/HEURISTICS.md` — advisory heuristics.
