---
id: enforcement-318d578e
title: Enforcement Architecture
type: spec
status: ready
tier: core
depends_on: []
tags: [enforcement, compliance, framework-architecture, verification]
---

# Enforcement Architecture

> **Spec, not state.** This file is the **design statement** for how the
> aops framework enforces its rules: the regulatory pyramid that frames
> all enforcement choices, the escalation discipline, the PR
> cost-benefit requirements, the worked A7 example, the user-facing
> witness → judge separation, and the evidence loop that drives all
> enforcement change. The **operative state register** — every
> mechanism currently in play, its pyramid position, and the axiom-keyed
> rule registry — lives in
> [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md).
> `rbg` blocks on the map's currency via P#65.

**Purpose.** Enforcement is **responsive, proportionate, and evidence-driven**: most work happens cheaply and constantly at the base of the pyramid; heavier measures escalate only when lower layers produce evidence they are insufficient.

**Sibling documents.**

- **`specs/ENFORCEMENT-MAP.md`** — **operative state register** (canonical SSoT). Pyramid-position assignments, every runtime hook / pre-commit hook / gate / PR-pipeline agent, plus the axiom-keyed cross-reference. When to reach for it: "what is currently catching X" or "what does it cost."
- **`specs/enforcement/enforcement.md`** (this file) — design statement. When to reach for it: deciding where a new rule, gate, or check should live; understanding why enforcement is shaped the way it is; PR cost-benefit framing.
- **`specs/enforcement/enforcement-mechanisms.md`** — per-mechanism reference catalogue keyed to the L0–L11 pipeline view (companion design-narrative spec). When to reach for it: schema-shaped details for a single mechanism.
- **`specs/enforcement/ultra-vires-enforcer.md`** — design doc for the `enforcer` agent + PreToolUse gate.
- **`specs/enforcement/enforcement-map.md`** — redirect stub pointing at `specs/ENFORCEMENT-MAP.md` (superseded 2026-05-20).
- **`specs/GATES.md`** — **state SSoT** for the runtime gate catalogue (where each lives in source, how it's configured, how to verify firing, how to debug). When to reach for it: a forensic-debug question about a specific gate.

## Two views of the same mechanisms

The framework has ~40 distinct enforcement mechanisms. Two organising principles are useful for thinking about them.

1. **The pipeline (temporal view).** When in the flow of work does a mechanism fire? Capture → hydration → decomposition → execution → handover → review → merge → follow-up → evidence loop. The mermaid graph in §3 shows this. Labels are `L0`–`L11`, one per pipeline layer. This view answers _when_ a mechanism fires; it is not a severity tier.
2. **The pyramid (escalation view).** Where does a mechanism sit in the regulatory pyramid (§4)? How frequently does it fire, and how invasive is it when it does? Base (high-volume, cheap, non-blocking) → middle (moderate, triggered, warns or opens gates) → tip (rare, heavy, blocks or requires human). The pyramid is the **operative framing** for add/escalate/remove decisions; positions L0–L7 in [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md) are the register-of-record.

These views are **orthogonal**. The same mechanism appears in both. A pipeline-L4 mechanism (soft gate) may sit at the base of the pyramid (runs every tool call, cheap) or in the middle (triggered on threshold). The pipeline L-number is cross-reference; the pyramid position is the cost-benefit assignment.

When reasoning about a framework change, use the pipeline to decide _when_ the intervention fires and the pyramid to decide _how invasive_ it should be — then record the decision as a row in the operative state register.

## §3 Pipeline view (temporal)

```mermaid
flowchart TD
  subgraph L0[L0 Capture]
    Q["/q, PKB MCP, inbox default, complexity eval"]
  end
  subgraph L1[L1 Context injection]
    HYD["session_env_setup, hydrator, skills routing, CLAUDE.md, status strip"]
  end
  subgraph L2[L2 Decomposition]
    DEC["/planner, task templates, proof-of-compliance fields"]
  end
  subgraph L3[L3 Workflow composition]
    WF["Phase 3 — not yet formalised"]
  end
  subgraph L4[L4 Soft gates]
    GATES["hydration gate, enforcer gate, QA gate (planned), unified logger"]
  end
  subgraph L5[L5 Hard blocks]
    HARD["policy_enforcer.py, deny rules, credential isolation"]
  end
  subgraph L6[L6 Observability]
    LOGS["session logs, task-file append, STATUS.md"]
  end
  subgraph L7[L7 Agent review]
    AGENTS["rbg, enforcer, qa/marsha, pauli"]
  end
  subgraph L8[L8 Handover]
    HAND["/dump, framework reflection, handover gate, commit gate"]
  end
  subgraph L9[L9 Review pipeline]
    REV["james, review-pr, GHA pr-review, agent-enforcer, linters"]
  end
  subgraph L10[L10 Merge gates]
    MERGE["agent-merge-prep, branch protection, loop detector, project-owner"]
  end
  subgraph L11[L11 Follow-up]
    FUP["task closure, unblocked downstream, cross-reference"]
  end
  subgraph EV[Evidence loop]
    LEARN["/learn → GH issues → /aops → spec/axiom/hook change"]
  end
  L0 --> L1 --> L2 --> L3 --> L4 --> L5 --> L6 --> L7 --> L8 --> L9 --> L10 --> L11
  L4 -. fail .-> LEARN
  L7 -. fail .-> LEARN
  L9 -. fail .-> LEARN
  L11 --> LEARN
  LEARN -. spec/axiom/hook change .-> L0
```

Edges show control-flow in the common path (top to bottom) and the three most common failure-to-evidence arcs (dotted). The evidence loop closes back to L0 because the _output_ of the loop is spec/axiom/template changes, which propagate forward through the whole pipeline from its start.

Full catalogue of mechanisms per layer: **see [`specs/enforcement/enforcement-mechanisms.md`](enforcement-mechanisms.md)** (companion). For the operative register, see [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md).

## §4 Pyramid view (escalation)

**Responsive regulation theory.** The pyramid is borrowed directly from Ian Ayres & John Braithwaite, _Responsive Regulation: Transcending the Deregulation Debate_ (Oxford University Press, 1992). The framework cannot force any agent to do anything — we can only create _encouragement with detection_. Given that, the choice of _where to intervene_ should follow the principle of least invasion: use the lightest mechanism that catches the failure, and escalate only when evidence shows the lighter mechanism is insufficient. The width of the pyramid at each level represents the **volume × frequency** of enforcement there: a wide base of high-volume soft mechanisms (always-on context injection, voluntary skill invocation, lifecycle hints) tapering to a sharp apex of rare severe responses (LLM-mediated review, branch protection, recusal-grounded recourse). The narrower the level, the more reluctantly invoked.

**Executive vs legislative.** The pyramid is **executive only** — it lists the mechanisms that act on agent behaviour. Axioms (the numbered A-rules in [`.agents/rules/AXIOMS.md`](../../.agents/rules/AXIOMS.md)) and heuristics are **legislative**: they declare what the rules are. The rules don't enforce themselves; they are *enforced by* mechanisms across multiple pyramid tiers. Numbering an axiom raises the *weight* of a rule in the L1 always-on injection mechanism — the numbering is content-weighting, not pyramid placement. Looking up "what enforces A7?" means scanning the axiom × mechanism table in [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md), not the pyramid table.

**Operative use.** The pyramid is **not** a decorative metaphor — it is the structure that organises every add/escalate/remove decision. Each mechanism in [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md) carries an explicit pyramid position (L0–L7); PRs that propose enforcement changes cite that position and justify it against §4.1. The L0–L11 pipeline numbering above and the base/middle/tip tier labels below are different lenses on the same set of mechanisms — the pipeline answers _when_, the pyramid answers _how invasive_.

Mechanisms are placed in tiers based on **frequency of activation × invasiveness when active** — not on where they sit in the pipeline.

| Tier       | Definition                                                             | Mechanisms (with pipeline layer cross-reference)                                                                                                                                                                                                                                                                                                                                                                                                |
| ---------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Base**   | High-volume, low-invasiveness, non-blocking, runs constantly           | lightweight hydrator (L1), skills routing table (L1), CLAUDE.md / AGENTS.md load (L1), gate status strip (L1), session_env_setup (L1), unified logger (L6), task-file append (L6), session logs (L6), task template conventions (L2)                                                                                                                                                                                                            |
| **Middle** | Moderate volume, triggered by threshold or event, warns or opens gates | hydration gate (L4), enforcer gate (L4), enforcer subagent invocation (L7), QA gate — planned (L4), /planner decomposition checks (L2), proof-of-compliance tool fields (L2), rbg subagent invocation (L7), qa / marsha subagent invocation (L7), james orchestration (L9), pr-reviewer GHA (L9), agent-enforcer GHA (L9), linter workflows (L9), commit gate (L8), CC auto-mode classifier `soft_deny` rules (L4 — surfaces permission prompt) |
| **Tip**    | Rare, heavy — hard-blocks or requires human judgment                   | policy_enforcer.py hard blocks (L5), settings.json deny rules (L5), credential isolation (L5), handover gate (L8), agent-merge-prep auto-merge (L10), branch protection (L10), loop detector (L10), project-owner / admin approval (L10), CC auto-mode classifier `block` rules (L4 — pre-execution hard-deny)                                                                                                                                  |

**Escalation rules.**

- **Escalate up** when the evidence loop (§5) shows a base-tier mechanism is being bypassed or ignored with reproducible consequences.
- **De-escalate down** when evidence shows a tip-tier measure has been unnecessary for a full feedback cycle — a middle-tier warn or base-tier reminder may be sufficient.
- **Never guess.** If there is no evidence one way or the other, the current placement holds. Changes are made from §5 evidence, not from authorial intuition.

### §4.1 PR requirements for enforcement changes

This applies to PRs that **add, escalate, or remove** a row in [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md) — a new gate, a position change (e.g. L1→L3), a new axiom, an additional hook firing surface, or removing one. Bug fixes within an existing enforcement surface at the same position (correcting wrong logic or wrong prose in an existing skill, agent, hook, or gate) do NOT require CBA — they need only a clear description of the bug and the corrective edit. User-directed architectural changes skip the ≥3 recurrence requirement but still require pyramid-position reasoning to document where the fix lands.

Any PR that adds, escalates, or removes enforcement MUST include a **Cost-Benefit Analysis** block in the PR body:

1. **Friction evidence**: ≥3 concrete recurrences with links (transcript, PR, issue, /retro report) for add/escalate proposals. Fewer than 3 → close as premature unless explicitly directed by the user.
2. **Cheapest plausible position**: which row of the pyramid could reasonably address this?
3. **Why escalate above that position (if escalating)?**: what was tried at the cheaper position; specifically why it failed, with evidence.
4. **Ongoing cost**: token cost per fire × fire frequency, or latency estimate. Use the Cost/Impact column format from the operative register.
5. **Reversibility**: if this doesn't reduce recurrences in the next 5 /retro reviews, how do we retire it?

Reviewers should WARN on missing CBA, BLOCK on missing items 1, 4, or 5.

### §4.2 Worked example: A7

A7 ("Exercise Authority — Calibrate Capability", `.agents/rules/AXIOMS.md`) is an axiom — a rule, not a pyramid position. Its **enforcement footprint** spans multiple tiers of the executive pyramid:

| Tier | Mechanism enforcing A7 | What it does                                                              |
| :--- | :--------------------- | :------------------------------------------------------------------------ |
| L1   | AXIOMS.md inject       | Always-on prompt-cached load at SessionStart; ~100 lines per session.     |
| L6   | `rbg` PR-time review   | Reads diff against A7; advisory verdict for the orchestrator.             |
| L6   | `marsha` QA verifier   | Checks task-completion claims for over-deference.                         |
| L7   | `enforcer-status` GHA  | LLM review fed into branch-protection AND-gate at merge.                  |

The decision to **number** A7 (vs leaving the rule as scattered surface-text instructions) was an explicit cost-benefit decision. Numbering raises the rule's **weight inside the L1 always-on inject mechanism**; it does not move the enforcement to a different tier.

- **Friction**: 9+ over-deference recurrences across 6 agent surfaces (issue #195 thread, issue #950, plus fresh /retro evidence from 2026-05-11 sessions).
- **Cheaper position attempted first**: surface-text L1 fixes (per-skill CORE.md / butler.md / planner). Tried 9 times across the #195 history. Each attempt reached one more surface; the next session hit a surface the patch hadn't reached.
- **Why numbering justified**: per-surface L1 surface-text fixes did not beat the trained "seek confirmation" reflex. Moving the rule into always-on AXIOMS.md (still L1 — same mechanism class) makes it cross-cutting in a way no per-surface edit could match. Numbering is the weight-raising act.
- **Forward cost**: ~100 lines permanent in always-on AXIOMS.md, prompt-cached. Surface citations remain L1 (≤10 lines each).
- **Future fixes** against any of A7's three edges should land at the cheapest sufficient position — usually L1 surface-text propagation, not new axioms. Adding A18/A19 against the same root would repeat the failure mode this PR resolved.
- **Reversibility / acceptance criterion**: zero FM-1 through FM-7 recurrences across the next 5 /retro reviews. If the criterion fails, the documented contingency is L6 (pre-Stop LLM hook), per `note-23e58353`.

This serves as the template for axiom-weight escalation: the CBA must look like this, with named prior attempts and explicit reversibility. The axiom is the rule; the pyramid tiers are the mechanisms enforcing it — confusing the two leads to inflating the axiom count rather than thickening the enforcement footprint.

### §4.3 How to update the operative register

1. **Observe** failure (QA, /retro, /sleep, report).
2. **File evidence** via `/learn`.
3. **Locate rule** in the axiom-keyed registry in [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md).
4. **Propose position change** (escalate/demote) — cite the L0–L7 pyramid position, not the action vocabulary.
5. **Update the row** in the same PR (P#65).

## §5 Evidence loop

The pyramid _learns_ by an evidence loop: incidents become anonymised reports become patterns become recommendations become rule changes. The loop is split deliberately by recusal (A17) into a witness phase and a judge phase — the agent that lived through the failure files facts only; a separate, detached agent later reads accumulated reports and proposes change.

### §5.1 User story: how the framework gets better

Two flows, separated by design. The user is the client of both, but each flow runs in its own context with its own job.

#### Flow 1 — File a bug (incident phase, forensic)

> "Something just went wrong in this session."

When an agent hits friction (tool bug, missing instruction, dead end), it MUST invoke the `/learn` skill immediately at the point of discovery. One friction = one `/learn` call. Do NOT ask the user "want me to file this?" or "happy to file if you confirm" — filing friction is unilateral.

The dispatched agent reads the transcript and files a GitHub issue containing only:

1. **What happened** — quoted from the transcript.
2. **Root cause category** — one of the documented categories.
3. **Rule already in place (if any)** — which axiom, gate, hook, or skill instruction was supposed to catch this, and at what position.
4. **Impact** — concrete cost (turns burned, work to undo, trust hit).

That's it. **The /learn agent is forbidden from proposing a fix.** It is the witness, not the legislator. The user doesn't have to think about "what should the framework do about this" at file time — they just have to report what happened. If they hit the same problem three times, that's three forensic issues; the recurrence count is the evidence base later.

The user can file an issue by hand instead — same constraints. A bare "please add a gate that does X" issue is in scope to be edited down to forensic facts before it gets used.

#### Flow 2 — Improve the framework (review phase, detached)

> "Let's look at what's piled up and decide what to actually change."

Periodically — when the issue queue feels heavy, or on a cadence the user sets — the user runs `/issue-sweep`. The dispatched agent enters with no prior exposure to any individual incident. It:

1. Pulls up to 20 open issues and classifies each (close-stale, comment-only, single-task, fix-epic, defer).
2. For any issue whose remediation would touch the framework (an axiom, gate, hook, skill instruction, or row of the operative register), runs the pyramid review: generalise the category → check existing mechanisms → classify the failure shape (propagation / escalation / rule absent) → default to the cheapest sufficient position → cite the specific row of the register the fix propagates from or would add.
3. Surfaces the proposed cycle to the user (`AskUserQuestion` gates on each disposition group). The user approves, edits, or defers.
4. On `y`: files fix-epics or single tasks, stamps labels, logs the cycle. Fix-epics stay `queued` until the user dispatches them via `/supervisor`.

The sweep agent will not propose **adding or escalating** a rule from one incident — a new gate, a new axiom, a position-bump (e.g. L1→L3), a new hook firing surface. Add-or-escalate proposals need ≥3 cited recurrences plus the CBA evidence in §4.1 (named cheaper position tried, ongoing cost, reversibility).

This bar does NOT apply to **fixes** within an existing enforcement surface at the same position — a skill that does the wrong thing, an agent prompt that misroutes, a hook with broken logic, a gate whose verdict table is incomplete. A clear forensic incident is sufficient evidence for `fix-epic` or `single-task`; sweep dispatches the fix without waiting for two more incidents. The same rule covers **directed architectural changes** the user has explicitly authorised: one incident plus user direction is sufficient — the user's authorisation substitutes for the recurrence count, not for the pyramid reasoning.

What gets deferred for pattern is the _add-or-escalate_ case: proposals to grow the enforcement surface from a single witness report. Single incidents that are bugs get fixed; single incidents that are escalation proposals get logged and either closed or deferred.

#### Why the split

Recency is bias. The agent that just lived through a failure proposes fixes shaped by that failure — usually a new gate or axiom built around one incident, which doesn't fit the seamless web of existing rules. By separating the witness role from the judicial role, the framework's volume and direction of change is governed by cross-incident patterns visible from outside, not by the urgency a single failure feels from inside. The user gets to be honest in flow 1 (no need to over-frame a problem to justify a fix) and disciplined in flow 2 (no rule changes without the evidence base).

#### What the user does NOT need to do

- Propose remediations at /learn time. Just describe what happened.
- Worry about whether their issue duplicates an existing one. The sweep agent groups by root cause and bumps volume on duplicates.
- Choose a position (L0–L7) for any rule. The sweep agent applies the pyramid; the user gates the proposal.
- Maintain the operative register by hand. Approved fix-epics that add or move a row update [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md) as part of the change (P#65).

### §5.2 Implementation status

Each step names its inputs, outputs, implementation status, and location.

**Step 1 — Failure detection.** _(Implemented at sources; aggregation partial.)_ Signals originate at any pipeline layer: RBG findings, QA / marsha fails, /retro observations, user-reported problems, post-merge regressions, /sleep staleness findings, hook log patterns. Currently aggregated through ad-hoc agent invocation, not a single pipeline.

**Step 2 — `/learn` files anonymised GitHub issue.** _(Implemented.)_ Skill at `aops-core/commands/learn.md`. Anonymisation is mandatory; root-cause-analysis schema is enforced in issue body; deduplication by search-first. Repo is the framework repo. Labels: `bug`, `criticality:<level>`, plus layer-specific tags (e.g. `framework`, `enforcement`, `axiom`).

**Step 3 — Evidence accumulation.** _(Implemented via GitHub issues as durable store.)_ Issues cluster around patterns; volume × criticality informs priority. No separate database — the issue list is the evidence base.

**Step 4 — `/aops` pattern detection.** _(Aspirational — principal known gap.)_ Intended behaviour: periodic read of issue labels / bodies / close-status, detection of recurring failure modes, mapping to pyramid layers where intervention needs to change. Not yet mechanically implemented.

**Step 5 — Recommendation generation.** _(Aspirational.)_ Intended behaviour: `/aops` produces a proposed enforcement adjustment — which layer, which mechanism, escalate or de-escalate, what spec/axiom/hook change. Not yet implemented.

**Step 6 — Human decision + implementation.** _(Implemented as the normal task flow.)_ User approves the change; an agent implements it via the usual `/q` → decomposition → execution route; spec / code / axiom is updated through PR pipeline.

**Step 7 — Closing the loop.** _(Partially implemented.)_ Issues referenced by the implementing PR close automatically; [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md) (operative state) updates to reflect the new intervention. The _automatic_ row update is not yet wired — done manually in the PR.

**Principal gap.** Steps 4–5 are the unbuilt piece. Failure evidence is captured reliably (Step 2) and implementation flow exists (Step 6), but the _recommendation_ connecting them is aspirational. A follow-up task should scope what `/aops` needs to do.

## §6 Per-mechanism reference

See **[`specs/enforcement/enforcement-mechanisms.md`](enforcement-mechanisms.md)** for the per-mechanism design-narrative catalogue (keyed to the L0–L11 pipeline view). For the operative register, see [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md). Each mechanism is documented with a fixed schema:

```
### <Mechanism name>
- **Pipeline layer**: L<n>
- **Pyramid tier**: base | middle | tip
- **Trigger**: <event or condition>
- **Purpose**: <one sentence>
- **Location**: <file:line or module path>
- **Scope**: polecat | crew | interactive | GHA | all
- **Status**: active | warn-only | planned | disabled
```

Tier-spanning mechanisms (e.g. `/dump` handover: middle when the handover gate is open, tip when it blocks Stop) carry both tiers in the **Pyramid tier** field with a conditional clause.

## §7 Scope limits

### §7.1 Known-clients only

The framework's agent-based enforcement (rbg, enforcer, qa / marsha, pauli, james) applies **only to known clients**: polecat, crew, and interactive sessions invoked through the aops plugin. GHA agents inherit via prompt inlining at build time (see `scripts/build.py` — intentionally out of scope this cycle).

**Unknown third-party agents** running on arbitrary platforms are out of scope. The framework cannot reach them, and no gate mechanism assumes they exist. The only mechanism for third-party alignment is prompt-level: by shaping the specs / axioms / templates that any agent reads, the framework influences what third-party agents do. The pipeline is _not_ a perimeter around a trust boundary.

### §7.2 Per-client coverage table

| Client                  | Hooks?               | Gates? | rbg/enforcer?      | /dump? | PR pipeline? |
| ----------------------- | -------------------- | ------ | ------------------ | ------ | ------------ |
| Polecat                 | Yes                  | Yes    | Yes                | Yes    | Yes          |
| Crew (Claude Code)      | Yes                  | Yes    | Yes                | Yes    | Yes          |
| Interactive (local CLI) | Yes                  | Yes    | Yes                | Yes    | Yes          |
| GHA review agents       | No (inlined prompts) | No     | Yes (prompt-level) | No     | N/A          |
| Third-party agents      | No                   | No     | No                 | No     | No           |

## §8 Operator impact — env var rename

The `custodiet` agent and gate have been renamed to `enforcer`. Operators with values set in shell profiles or `~/.env.local`:

| Old                             | New                            |
| ------------------------------- | ------------------------------ |
| `CUSTODIET_GATE_MODE`           | `ENFORCER_GATE_MODE`           |
| `CUSTODIET_TOOL_CALL_THRESHOLD` | `ENFORCER_TOOL_CALL_THRESHOLD` |

Migration is a breaking change unless a backward-compat alias is added at load time — decision deferred to the rename commit.

## §9 Workflow composition (Phase 3 placeholder)

Task-creating agents compose compliant workflows by combining axioms, heuristics, and procedures at task-creation time. The agent enumerates which axioms apply to the task, which heuristics flag likely hazards, and which procedures are the current recommended sequence — then assembles them into a workflow the executing agent runs.

**This layer is not yet formalised.** It is named here as pipeline L3 so the pyramid/map/mechanism specs have a consistent reference point. Phase 3 of `task-e64e29c5` and parent-epic `task-b5fec0b5` Thread 4 (workflows-as-logical-statements) carry the design work.

## §10 Design principles

1. **Layer defences** — no single mechanism is reliable. Combine base, middle, and tip tiers for any failure mode worth catching.
2. **Prefer observable over invisible** — TodoWrite, task bodies, STATUS.md, gate icons. If a mechanism fires and the user cannot see it, the mechanism has not enforced.
3. **Accept imperfection** — enforcement is encouragement with detection, not coercion. Design for drift, not for prevention.
4. **Measure before changing** — the §5 evidence loop is the authority for tier changes. Authorial intuition is not evidence.
5. **Least invasion first** — conventions before templates; templates before gates; soft gates before hard blocks; hard blocks before human approval. Escalate only on §5 evidence.
6. **Show, don't tell** — where compliance is claimed, require information that demonstrates it. Tool signatures and task templates should carry the proof into the schema rather than accept reassurance.

## §11 Component responsibilities

Enforcement failures fall into five root-cause categories:

| Category          | Definition                                                 |
| ----------------- | ---------------------------------------------------------- |
| Clarity Failure   | Instruction ambiguous or insufficiently emphasised         |
| Context Failure   | Component did not provide relevant information when needed |
| Blocking Failure  | Component did not block what it promised to block          |
| Detection Failure | Component did not catch a violation it promised to catch   |
| Gap               | No component existed for this case — create one            |

Multiple categories can apply; defence-in-depth can fail at multiple layers.

### Root-cause analysis protocol

1. Was there a rule? Check AXIOMS / HEURISTICS.
2. Did the hydrator suggest the correct workflow?
3. Did the agent follow the workflow? If yes, was output correct?
4. Should a PreToolUse hook have blocked? Check hook rules.
5. Should a PostToolUse hook have detected? Check detection hooks.
6. Should a deny rule have blocked? Check `settings.json` / `policy_enforcer.py`.
7. Should a pre-commit hook have caught? Check `.pre-commit-config.yaml`.

If all components met their responsibilities and the failure still occurred: **Gap** — create a new mechanism at the appropriate position.

## §12 Verification — "Can it" ≠ "Does it"

The top failure pattern in this framework is conflating capability with actual state. An agent that checks whether code _could_ work, or what defaults _would_ be, has not verified that anything _is_ working.

| Agent checked              | Should have checked |
| -------------------------- | ------------------- |
| Framework default value    | Actual config file  |
| Code capability exists     | Feature is enabled  |
| Tool exists                | Tool is configured  |
| "Should work" / "probably" | Observed output     |

Evidence types, in decreasing order of trust:

| Type              | Definition                                 |
| ----------------- | ------------------------------------------ |
| `actual_state`    | Config files read, runtime output captured |
| `default_only`    | Only defaults checked                      |
| `capability_only` | Only documented capabilities               |
| `none`            | No evidence gathered                       |

Conclusions require `actual_state`. Anything less is a claim, not a finding.

---

**Related**

- **Operative state register (SSoT)**: [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md) — pyramid-position assignments + every mechanism row. `rbg` blocks on it (P#65).
- [`specs/enforcement/enforcement-mechanisms.md`](enforcement-mechanisms.md) — per-mechanism design-narrative catalogue (companion to this file).
- [`specs/enforcement/ultra-vires-enforcer.md`](ultra-vires-enforcer.md) — enforcer agent + gate internal design.
- [`specs/enforcement/enforcement-map.md`](enforcement-map.md) — redirect stub (superseded 2026-05-20 by `specs/ENFORCEMENT-MAP.md`).
- [`.agents/rules/AXIOMS.md`](../../.agents/rules/AXIOMS.md) — universal axioms (read only by `rbg`).
- [`.agents/rules/HEURISTICS.md`](../../.agents/rules/HEURISTICS.md) — advisory heuristics.
