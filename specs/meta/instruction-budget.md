---
title: Instruction budget — right-sizing what goes in each injection tier
type: spec
status: draft
created: 2026-06-01
---

# Instruction budget — right-sizing what goes in each injection tier

**The problem this answers.** On 2026-06-01 a live session was observed loading the
_full_ text of `AXIOMS.md` on the first/second turn — ~3–5k tokens of inviolable-rule
prose paid by **every agent on every session**. Some of that text earns its slot
(behaviour-shaping rules an agent cannot reactively look up). Much of it does not (the
reviewer checklists, already split to `AXIOMS-REVIEW.md`; multi-sentence elaborations a
working agent never consults). This doc gives the rule for deciding which is which.

It is the companion to two existing docs and overlaps neither:

- [`doc-taxonomy.md`](doc-taxonomy.md) answers **which file** content goes in, by
  _audience_ (agent / dev / both / script / human).
- [`CONSTRAINTS.md`](../CONSTRAINTS.md) gives **enforced hard caps** (e.g. `SKILL.md ≤ 500
  lines`).
- **This doc** answers a third, orthogonal axis: given a piece of instruction, **which
  injection tier does it earn, and how much of it**, by its _type_ and its _every-turn
  cost_. It is the rubric [[aops-510a795b]] (subtask 3) applies file-by-file.

---

## 1. The principle: every-turn cost is paid by every agent, every turn

Instruction context is not free real estate. Its cost is:

> **cost ≈ size × audience-breadth × load-frequency**

A 500-token block in a skill body that one agent reads once when it invokes the skill is
cheap. The _same_ 500 tokens in an every-turn injection is paid by every agent on every
turn and, for in-window injections, **compounds** — eight Stop-hook `ida` injections at
515 tokens each leave 4,120 tokens sitting in the window by session end ([[note-108883d4]]
§1a). The higher the tier, the more an instruction must _earn_ its slot.

**The altitude rule.** To occupy a high (push) tier, an instruction must pass **all three**:

1. **It changes behaviour on most loads** — not "is occasionally relevant" but "shapes what
   the agent does this turn / this session."
2. **It cannot be reliably pulled when needed** — the agent can't look up a rule it doesn't
   know exists. (This is the one honest reason to push: to make the agent _reach_ for the
   detail.)
3. **It is compact** — every line is load-bearing _at that frequency_. Ceremony, rationale,
   and history are not.

Fail any one → **demote** it to a lower tier. The default direction is always **down**:
prefer pull (paid on use) over push (paid whether used or not). Push only what the agent
must have _before it knows it needs it_.

---

## 2. Injection tiers, ranked by push-cost

| # | Tier                          | Mechanism                                                                           | Audience × frequency                          | Cost character                                                                                                                                            |
| - | ----------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | **Every-turn injection**      | `UserPromptSubmit` hook                                                             | every agent × every turn                      | Highest. Compounds in-window. The most expensive real estate in the system.                                                                               |
| 2 | **Per-event gate cue**        | `Stop` / `PreToolUse` / `PostToolUse` templates (`ida`, `enforcer`, `qa`, handover) | every agent that trips the gate × each firing | High. Also compounds in-window (the 8×515 `ida` case).                                                                                                    |
| 3 | **Always-on session context** | `.agents/CORE.md` + `.agents/rules/*.md` loaded at `SessionStart`                   | every agent × once per session                | High nominal, but **prompt-cached** (~5-min window) → marginal ~0 after first turn. Full cost on every cold start, long gap, and fresh subagent dispatch. |
| 4 | **Agent-def system prompt**   | `agents/<name>.md`                                                                  | only the dispatched agent × once per dispatch | Scoped by role.                                                                                                                                           |
| 5 | **Skill body**                | `skills/<name>/SKILL.md`                                                            | only sessions that invoke × once per invoke   | Scoped + pulled.                                                                                                                                          |
| 6 | **Task body**                 | PKB task, pulled on claim                                                           | one task × once                               | Scoped to the unit of work.                                                                                                                               |
| 7 | **On-demand / referenced**    | `Read` tool, `[[wikilink]]`, `ToolSearch`                                           | only when the agent reaches for it            | Lowest. Pure pull.                                                                                                                                        |

Tiers 1–3 are **push** (paid whether or not the content is used this turn). Tiers 4–7 are
**pull** (paid only on use). The split at tier 3↔4 is the line between "every agent pays"
and "only the relevant agent pays."

---

## 3. Instruction-type taxonomy and placement rule

For each _type_ of content, its default tier and the test it must pass to sit higher.

| Instruction type                      | Example                                                                                        | Default tier    | Rule                                                                                                                                                                                                            |
| ------------------------------------- | ---------------------------------------------------------------------------------------------- | --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Honesty floor**                     | "don't claim inferred as observed; flag unverified/substituted/skipped; don't launder a relay" | 2/3 (compact)   | Always on, every register — fires every turn, cannot be reactively looked up. Keep to the **floor** (the cue); the evidence _manifest_ is agent-applied by judgment, not pushed (§4, [[note-36c15a69]] v0.5.3). |
| **Axiom rule statements**             | the A1–A13 MUST/MUST-NOT one-liners                                                            | 3 (compact)     | Behaviour-governing and unlookuppable → earns always-on, but as **compact rule statements**, not full prose. Corollaries/elaboration → pull.                                                                    |
| **Axiom review checklists**           | "On review, ask: …"                                                                            | 7 (rbg only)    | Only the _reviewer_ role needs them. → `AXIOMS-REVIEW.md`, `@include`d by `rbg.md`, **not auto-loaded**. (Already done — the canonical worked example, §5.)                                                     |
| **Role identity**                     | "you are junior, the router; delegate by default"                                              | 4               | Useless to other agents → agent-def system prompt, not always-on.                                                                                                                                               |
| **Routing table (live)**              | the ~20-token Skills Routing Table                                                             | 1               | Earns every-turn **only because it is tiny and state-dependent**. The full skill _catalogue_ does not — it's pulled via `Skill`/`ToolSearch`.                                                                   |
| **Procedures / how-to-do-X**          | `end_session` steps, skill workflows                                                           | 5               | Needed only when doing X → skill body, pulled on invoke.                                                                                                                                                        |
| **Task context / AC**                 | this task's acceptance criteria                                                                | 6               | Scoped to one unit of work → task body.                                                                                                                                                                         |
| **Tool / MCP catalogues**             | "Tool Capabilities in dispatched sessions"                                                     | 7               | Doesn't change behaviour; agents query `ToolSearch` anyway → referenced.                                                                                                                                        |
| **Derivations / history / rationale** | "emerged from the 2026-03-17 session"                                                          | 7 (PKB note)    | Documentation, not working context → PKB note, linked.                                                                                                                                                          |
| **Reference / state tables**          | enforcement-map, gates catalogue, surfaces                                                     | 7               | Looked up when relevant → state doc, referenced.                                                                                                                                                                |
| **Gate decision prose**               | "use `/end-session` vs `/dump` because…"                                                       | 2 (compact) + 5 | The _cue_ fires at the event; the _explanation_ lives in the skill it points to. Don't restate the skill in the gate.                                                                                           |

**Register exception (locked, [[note-36c15a69]] v0.5.3).** Two types are always-on in **every**
register including casual/personal — honesty floor and axiom compliance ("agents lie all
the time"; "axiom violations are prohibited anywhere and everywhere"). Only **verification
(qa)** is task-scoped. Register scales _what qa asks for_, never whether honesty/axioms fire.

---

## 4. The floor-vs-elaboration split (the reusable move)

Most over-injection is one mistake repeated: **a principle and its full elaboration sit in
the same high tier.** The fix is almost always to split them:

- **Floor** — the compact cue that _triggers_ the behaviour and _points_ at the detail.
  Earns the high (push) tier, because the agent can't reach for what it doesn't know exists.
- **Elaboration** — the rationale, worked checklist, edge cases, examples. Demoted to pull
  (referenced doc, role-specific file, or PKB note).

This is not theoretical — it is the shape of every fix the framework has already shipped:

- `AXIOMS.md` rule statements (floor, always-on) ← review checklists (elaboration) →
  `AXIOMS-REVIEW.md`, loaded only by rbg.
- `ida` honesty **floor** (always-on cue) ← evidence **manifest** (per-claim certainty,
  next-best hypotheses) the agent adds **by judgment** when work is shippable
  ([[note-36c15a69]], 2026-05-30 resolution). Note the tiering is **instruction-led, not
  mechanical** — the agent is given both tiers and chooses the register; no hook-side
  detection.

When you find a fat block in a push tier, the first question is not "can I cut words?" but
"**what is the floor here, and where does the elaboration go?**"

---

## 5. Decision procedure (what subtask 3 runs per file/section)

For each instruction file — or each _section_ of a large one — answer in order. The first
"demote" answer wins.

1. **Who reads it, how often?** Map to a tier (§2): all-agents-every-turn → all-agents-per-
   session → one-role → one-task → on-demand. Place it no higher than its real audience.
2. **Does it change behaviour on most loads, or is it reference consulted _sometimes_?**
   Reference → pull (tier 7). Push tiers are for behaviour, not lookup.
3. **Can the agent pull it when needed — does a higher cue point to it?** If yes, demote the
   detail to pull and leave a one-line cue. If the content is unlookuppable _and_ needed
   every load, it may stay (this is the only justification for tiers 1–3).
4. **Is it compact enough for its tier?** In a push tier, is every line load-bearing _at
   that frequency_? Strip preamble, restatements of rules the agent already has, etymology,
   and "this is a reminder not a block" disclaimers ([[note-108883d4]] §2).
5. **Apply the floor/elaboration split (§4).** Is there a compact floor that triggers the
   behaviour plus an elaboration that can be referenced? If so, split and demote the
   elaboration.

Record, per file, the verdict (`keep` / `trim` / `split` / `demote`) and the target tier.

### Size guidance (judgment, not hard caps)

Caps are enforced elsewhere ([`CONSTRAINTS.md`](../CONSTRAINTS.md)); these are altitude
expectations, applied with judgment per [doc-taxonomy](doc-taxonomy.md)'s "judgement... not a
mechanical contract" rule:

- **Tier 1 (every-turn):** aim for ~tens of tokens of injected text. The ~20-token routing
  table is the model. If it's bigger, it almost certainly belongs in tier 3 or lower.
- **Tier 2 (gate cue):** a cue, not a lecture — target a few sentences. `ida` at 515 tokens
  was ~61% ceremony ([[note-108883d4]]).
- **Tier 3 (always-on context):** load-bearing rule statements only. The audit found ~29% of
  `AXIOMS.md` was reviewer prose (now split) and most of `HEURISTICS.md`'s "Derivation:"
  sections are pull-tier history.
- **Tiers 4–7:** bounded by relevance, not a token budget — but still subject to the
  enforced `SKILL.md ≤ 500-line` cap and the same floor/elaboration discipline.

---

## 6. Worked examples (grounded in the audit)

| Content                                                 | Was                                     | Verdict                                          | Now / recommended                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------------- | --------------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AXIOMS "On review, ask:" checklists                     | always-on in `AXIOMS.md`                | **split**                                        | `AXIOMS-REVIEW.md`, rbg-only, not auto-loaded ✅ done                                                                                                                                                                                                                                                                      |
| `ida` honesty reminder                                  | 515-tok every-Stop block, ~61% ceremony | **split + trim**                                 | floor cue always-on; evidence manifest agent-applied ✅ done                                                                                                                                                                                                                                                               |
| `HEURISTICS.md` "Derivation:" sections                  | always-on                               | **demote**                                       | PKB notes, linked (backlog, [[note-108883d4]] rank 5)                                                                                                                                                                                                                                                                      |
| `CORE.md` "Tool Capabilities" list                      | always-on                               | **demote**                                       | referenced; agents use `ToolSearch` (backlog, rank 6)                                                                                                                                                                                                                                                                      |
| **`AXIOMS.md` full rule text** (the 2026-06-01 trigger) | full prose always-on, every agent       | **split — flagged for subtask 3 + human review** | Apply §4: keep the **compact rule statements** always-on (unlookuppable, behaviour-governing); demote multi-sentence corollaries/justifications to a pulled `AXIOMS` detail/reference. Touches the most load-bearing file in the framework → subtask 3 should propose, not unilaterally rewrite, and route through review. |

The last row is the headline item the parent epic ([[aops-4e6057b7]]) opened this work for:
the rule says axiom _statements_ earn their always-on slot, their _elaboration_ does not.

---

## 7. Provenance

- **Driving observation:** [[aops-4e6057b7]] (Full QA of hook context injection) — full
  `AXIOMS.md` injected on a live session, 2026-06-01.
- **Cost catalogue:** [[note-108883d4]] (Instruction-Conciseness Audit, 2026-05-11) — the
  char-by-char tally of every injection source, frequencies, and ranked compression
  candidates this rubric formalises.
- **Register model:** [[note-36c15a69]] (Supervision architecture spec) — honesty + axioms
  always-on, qa task-scoped, and the instruction-led (not mechanical) tiering of `ida`.
- **Sibling axes:** [doc-taxonomy](doc-taxonomy.md) (which file, by audience),
  [CONSTRAINTS](../CONSTRAINTS.md) (enforced caps).
