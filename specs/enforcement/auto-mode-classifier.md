---
id: auto-mode-classifier
title: Auto-Mode Classifier — the framework's judgment gate at the per-action boundary
type: spec
status: draft
tier: core
depends_on: [enforcement]
tags: [enforcement, automode, classifier, judgment, framework-architecture]
---

# Auto-Mode Classifier — the framework's judgment gate at the per-action boundary

> **Spec, not state.** This file is the **design statement** for what the
> Claude Code auto-mode classifier is _for_ in this framework: the policy that
> decides which rules belong in it, the cost model that shapes how those rules
> must be written, and how it relates to the rest of the enforcement pyramid.
> The **operative register** — which rules are actually installed, at which
> tier — lives in [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md). The
> per-mechanism runtime catalogue entry lives in
> [`enforcement-mechanisms.md`](enforcement-mechanisms.md). The enforcer
> subagent's relationship to this classifier is in
> [`ultra-vires-enforcer.md`](ultra-vires-enforcer.md) §"Relationship to Claude
> Code auto mode". This spec is the single canonical source for the _design
> intent_; those siblings point here.

## What it is

Claude Code's [auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode) delegates tool-call approvals to a **model-based classifier** (Sonnet 4.6) that runs **before every tool call**. For each proposed call it reads:

- a **stripped transcript** — the user's messages in full, plus the bare tool-call names and parameters, but **not** the agent's prose, tool-call descriptions, or prior tool outputs ("we strip assistant text so the agent can't talk the classifier into making a bad call… judge what the agent _did_, not what it _said_"); and
- a fixed evaluation template plus the framework's **prose rules** (`environment` / `allow` / `soft_deny` / `hard_deny`).

It returns a verdict: **allow** the call, or **deny** it. There is **no "ask" verdict** — auto mode exists precisely to remove the approval-prompt friction. When it denies, the denial and its reason come back **to the agent as a tool result**, with an instruction to treat the boundary in good faith and find a safer path rather than route around it.

In framework terms: the classifier is **`rbg`-class judgment running at the per-action gate** — transcript-aware, prose-reasoning, fast, already in the execution path. It is the **only** enforcement mechanism that applies _qualitative judgment to every tool call before it runs_. That is its unique value, and it is the reason this spec exists: the framework has long needed somewhere to put the rules it "wishes it could encode as a deterministic gate but can't, without really bad pattern-matching heuristics." This is that place.

## What we want it to do in this framework

The classifier is the home for the **small, deliberately-bounded** set of behavioural guardrails that satisfy all three of:

1. they **genuinely require judgment** to apply — a deterministic check would be brittle, false-positive-prone "shitty NLP"; and
2. they are **best caught pre-execution, at the specific action**; and
3. they are **not** already handled reliably by a cheaper mechanism or by the agent's own competence.

This is, by design, the framework's mechanised answer to its own `judgment-non-delegable` and `exercise-authority` (Edge 3) axioms: those axioms forbid substituting a regex for a comprehension call and tell us to _invoke a judging agent instead_. The classifier **is** that judging agent, sitting at the one place no subagent can affordably sit — in front of every action. A rule like "search the PKB instead of grepping for a concept" cannot be a hook (you cannot cleanly distinguish "grep for a literal symbol" from "grep for an idea" with a pattern), but it is exactly the kind of call a judging model makes well from the grep pattern plus the user's request.

**What it is explicitly NOT for:**

- **Things already mechanically enforced.** Path/binary/flag denials, pre-commit checks, `policy_enforcer` hard-denies, settings `deny` rules. Duplicating them here violates `single-source-of-truth` and wastes per-call budget.
- **Things agents are already reliably good at.** The budget is for _recurring_ failures with evidence, not for restating good behaviour the models already exhibit.
- **Session-level or reasoning-level concerns the classifier cannot observe.** It sees the action and the user's words, not the agent's reasoning or tool outputs. "Don't assert without verifying," "stay in scope across the whole session," "don't over-narrow the acceptance criteria" are real rules, but they are _not_ judgeable from a single stripped action — they belong to the IDA/QA gates, the enforcer subagent, or PR review.
- **Anything better caught downstream.** If an integration test, a pre-commit hook, or a review agent catches it more cheaply or more reliably, it goes there.

## Admission criteria — a rule belongs in the classifier iff _all_ hold

| # | Criterion                             | The question to ask                                                                                                                               | If it fails                                                                                                 |
| - | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 1 | **Judgment-requiring**                | Would a deterministic check need brittle heuristics / regex-for-meaning and false-positive?                                                       | A clean path/AST/flag check works → use `policy_enforcer` or a pre-commit hook, not the classifier.         |
| 2 | **Per-action observable**             | Is the violation visible in {user messages + the proposed tool call + its parameters} alone, without the agent's reasoning or prior tool outputs? | Only observable across the session or in the agent's prose → enforcer subagent / IDA / review.              |
| 3 | **Pre-execution is the right moment** | Does catching it _before_ the call beats warning _after_?                                                                                         | Post-hoc is fine or better → PostToolUse / enforcer / review.                                               |
| 4 | **Not already covered**               | Is it un-caught by any cheaper, reliable mechanism today?                                                                                         | Already caught → don't duplicate (`single-source-of-truth`).                                                |
| 5 | **Evidence of recurrence**            | Are agents demonstrably _not_ already good at this (≥3 cited recurrences, or explicit user direction)?                                            | No evidence → premature; log it, don't add it (`enforcement.md` §4.1, `recusal`).                           |
| 6 | **Survives the denial-cost test**     | Will it fire _rarely and precisely_, and hand the agent a clear safer path on the first denial?                                                   | Fires often / no clean alternative → it will kill autonomous sessions (see Cost model). Redesign or reject. |

## Cost model — the constraints that shape every rule

These are not style notes; they are hard properties of the mechanism that determine whether a rule is even viable.

- **There is no nudge channel — only deny.** The classifier's only agent-visible output is a **denial with a reason returned as a tool result**. To "nudge" the agent toward better behaviour, you must _deny the worse action_ and write the reason as the redirect you want it to read. A rule that wants to "gently remind" without ever blocking has no mechanism here — it belongs in the L1/L2 instruction tiers.
- **The denial reason is the whole interface.** Write each rule so the reason a denied agent receives names _what to do instead_. "Use `search` against the PKB; grep is for locating a known literal, not for understanding a concept" is a usable redirect; "violates judgment-non-delegable" is not.
- **The classifier cannot see the agent's intent — only its action.** Rules must be judgeable from the action + user context. Do **not** write a rule that depends on the agent's stated reasoning (it is stripped). Lean on the _cue in the parameters_ (e.g. the grep pattern, the file path, the command flags) and the user's request.
- **Death-by-denial is the dominant risk.** In headless / autonomous operation (`claude -p`, polecats) there is no human to approve a blocked action. Claude Code **terminates the process after 3 consecutive or 20 total denials**. A well-meaning behavioural rule that fires on, say, 10% of an agent's tool calls will _kill long autonomous runs_. Therefore classifier rules MUST be calibrated to **fire rarely and only on clear violations**, and MUST give a **one-shot safer path** so the agent corrects on the first denial instead of retrying into termination. **This is why the initial set is 1–3 rules, not a behavioural rulebook.**
- **The denial budget is shared across all rules.** The 3-consecutive / 20-total termination count is _aggregate_, not per-rule. The seed set must be calibrated against the _sum_ of every rule's fire rate, not each rule in isolation — two individually-safe rules can jointly cross the ceiling. Add a rule only once the existing rules' aggregate fire rate is known to leave headroom.
- **You cannot calibrate a rule you cannot watch fire.** Observability (auto-mode decisions surfaced into transcripts — acceptance criterion #4) is a _precondition_ for seeding any rule, not a follow-up. Without a fire-rate baseline, "fires rarely" is a hope, not a measurement, and the shared-budget calibration above is impossible.
- **Interactive vs headless surfaces differ.** In an interactive session a `soft_deny` surfaces as a permission prompt the user can approve; in headless it is a recorded denial counted toward termination. Same rule, two surfaces — design for the headless case, which is the unforgiving one.

## Rule-writing form

Write each rule as **prose stating principle + reasoning + cue + carve-outs**, never as a rule-ID lookup or keyword pattern (the classifier reads natural language and applies judgment; a rule that just names an axiom wastes its capability). Each rule states:

1. **The principle** and, in one clause, **why it matters** — cite the **axiom slug** it serves (e.g. `judgment-non-delegable`). `RULES.md` is no longer a populated layer; rules cite axioms in [`AXIOMS.md`](../../.agents/rules/AXIOMS.md) directly.
2. **The cue** the classifier should look for in the action + user context — the observable signal, since it cannot see reasoning.
3. **What counts as a violation**, and the **safer path** to name in the denial.
4. **Explicit carve-outs** — when the same action is fine. The classifier handles disjunctions ("deny X when bypassing tests; allow X when validating") as prose.

Keep each rule tight: every rule is permanent surface area, a per-call token cost, and one more thing that can fire wrongly.

### Slots and merge semantics

| Slot          | Meaning                                                                                                      | aops vs CC defaults                                                                                                                                                                                                                                                                                                                     |
| ------------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `environment` | Trust boundary — which repos / domains / buckets / paths count as "inside".                                  | aops **replaces** CC defaults (our context is more specific).                                                                                                                                                                                                                                                                           |
| `allow`       | Carve-out where a deny rule technically matches but the action is benign.                                    | aops **appends** to CC defaults (dedup).                                                                                                                                                                                                                                                                                                |
| `soft_deny`   | Context-overridable block: deny **unless** the transcript clearly justifies it; reason returns to the agent. | aops **appends**. **Default tier for every new behavioural rule.**                                                                                                                                                                                                                                                                      |
| `hard_deny`   | Absolute block (CC reserves it for data exfiltration and classifier-bypass).                                 | aops **does not currently write `hard_deny`** — `automode.py` merges only `environment`/`allow`/`soft_deny`; CC's `hard_deny` defaults still apply at read time. Adding an aops `hard_deny` rule requires extending `_merge_rules`, and should be reserved for evidence that a `soft_deny` was bypassed with reproducible consequences. |

## Relationship to other mechanisms (do not duplicate)

| Mechanism                            | Determinism                      | Position                              | Verdict goes to                                           | Platforms            |
| ------------------------------------ | -------------------------------- | ------------------------------------- | --------------------------------------------------------- | -------------------- |
| **Auto-mode classifier** (this spec) | **Judgment** (LLM)               | Every tool call, pre-execution        | User (permission UI) / agent (denial-as-tool-result)      | Claude Code only     |
| `policy_enforcer` / settings `deny`  | Deterministic (path/binary/flag) | Every tool call, pre-execution        | Hard block                                                | Claude Code          |
| `enforcer` subagent                  | Judgment (LLM)                   | Threshold (~25–50 writes) or explicit | Agent's working context + session-state file + icon strip | Claude Code + Gemini |
| `ida` / `qa` gates                   | Judgment-prompted                | Stop event                            | Agent (inject)                                            | Claude Code + Gemini |
| `rbg` / `marsha` / `alignment`       | Judgment (LLM)                   | PR / `/review-pr` / threshold         | Reviewer / change-author                                  | all                  |

The two failure modes to avoid:

- **Classifier vs `policy_enforcer`.** If a reliable deterministic match exists (a forbidden path, a destructive flag), it goes to `policy_enforcer` — cheaper, no LLM, no false positives. The classifier is for the cases where _only judgment_ distinguishes the violation from the benign twin.
- **Classifier vs `enforcer` subagent.** Same prose-judgment capability, different place in the loop. The classifier gates a _single action pre-execution_; its verdict surfaces to the user or as a denial. The enforcer reviews _the whole session at a threshold_ and writes its verdict **back into the agent's working context** (and runs on Gemini too, where the classifier does not). Pick by where the intervention needs to land — not by which feels stricter. Rules the framework itself needs to _read and act on_ belong to the enforcer; rules that should stop a bad action before it runs belong here.

## Pyramid placement

The classifier is **L5 — the judgment per-action gate** in the [`ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md) pyramid: a distinct level between **L4** (deterministic mechanical checks, including `policy_enforcer`'s hard-denies — _no LLM_) and **L6** (LLM-mediated session/PR review subagents). It earns its own level because it is the framework's _only_ judgment mechanism that fires per-action and pre-execution; folding it in with deterministic hard-deny (its prior placement) was a category error — one is pattern-matching, the other is reasoning. By **frequency × invasiveness** it is a middle-tier mechanism: it fires on every call (high frequency) but is overwhelmingly _allow_ (low invasiveness), tightening to a real block only on the rare clear violation. Within L5, `soft_deny` is the default (middle-weight: a context-overridable block) and `hard_deny` the rare escalation (tip-weight: absolute) — which is why [`enforcement.md`](enforcement.md) §4's base/middle/tip table lists the classifier in _both_ the middle and tip rows: one L5 level, two invasiveness points.

## SSoT, install, and sync

- **Canonical source:** [`templates/aops-core.plugin.json`](../../templates/aops-core.plugin.json), `autoMode` key (`environment` / `allow` / `soft_deny`).
- **Loader/merger:** [`aops-core/lib/automode.py`](../../aops-core/lib/automode.py) reads the template, fetches CC defaults (`claude auto-mode defaults`), merges (`environment` replace; `allow`/`soft_deny` append + dedup), and installs to `~/.claude/settings.json`. `update_polecat_defaults()` mirrors the merged result into [`polecat/defaults/claude-settings.json`](../../polecat/defaults/claude-settings.json).
- **Install trigger:** [`scripts/install.py`](../../scripts/install.py) runs both at install time.
- **Verify:** `claude auto-mode config` (effective merged rules), `claude auto-mode critique` (model feedback on the rule set — must return no "dangerous" / "disables the classifier" findings).

**Current state (2026-06): the rule set is empty.** The template has no `autoMode` key and `polecat/defaults/claude-settings.json` carries empty arrays — the aops rules added in [PR #729](https://github.com/nicsuzor/academicOps/pull/729) were stripped from source (the installed config is effectively CC defaults). This deployment therefore genuinely **seeds the first rules** — subject to the escalation discipline below: an empty rule set is a green field for the _mechanism_, but not every classifier-shaped behaviour is a green-field _candidate_ (see "Relationship to the v0.4 retrieval-gap epic"). Known SSoT fragilities to fix alongside (per PKB `kb-15ddad1c`): the duplicated polecat copy must be **regenerated via `update_polecat_defaults()`**, never hand-edited; and the stale `aops-core/config/automode-rules.json` fallback references in `automode.py` / `setup-automode.sh` should be removed (that file does not exist — `plugin.json` is the only source).

## Governance and lifecycle

- **Adding a rule** follows the evidence loop: ≥3 cited recurrences + the §4.1 cost-benefit block, **or** explicit user direction (which substitutes for the recurrence count, not for the pyramid reasoning). Per `recusal`, the agent that hit the failure files forensic facts; a _detached_ context decides whether a rule is warranted.
- **Start in `soft_deny`.** Escalate to `hard_deny` only on evidence that a `soft_deny` was bypassed with reproducible consequences (and only after extending the merge to carry aops `hard_deny`).
- **Reversibility / retirement.** A rule is retired when it (a) causes death-by-denial — terminating autonomous runs, (b) false-positives often enough that its denial reason becomes noise the agent learns to route around, or (c) the behaviour is now reliably handled by a cheaper mechanism. Re-run `claude auto-mode critique` after every change.
- **Observability is a prerequisite, not an afterthought.** The evidence loop can only tune the rule set if auto-mode decisions are _measurable_ — fire rate and false-positive rate per rule. The transcript tooling MUST surface auto-mode verdicts into the markdown/insights so `/retro` and `/trend-review` can see them (see [`aops-core/scripts/transcript.py`](../../aops-core/scripts/transcript.py)).
- **Deployment sequence.** (1) Land observability (criterion #4) so decisions are measurable; (2) seed the minimum viable rule(s) that clear _both_ the admission criteria and the §4 escalation bar; (3) escalate further (more rules, or `soft_deny`→`hard_deny`) only on measured evidence. A behaviour already owned by an instruction-tier workstream is **not** seeded here until that workstream's own measurement shows the instruction insufficient.

## Relationship to the v0.4 retrieval-gap epic

The single most-evidenced classifier-shaped behaviour — _"search the PKB / read, don't grep for understanding"_ — is **already owned by an in-flight workstream** and is therefore **not** a green-field seed candidate. Epic [[aops-34155220]] ("Close the agent↔PKB retrieval gap") and its deliverable D2 [[aops-1e16725d]] hold this problem. The history is dispositive: a deterministic tiered hook for it was **rejected by Nic** ("scrap this… NO SHITTY NLP axiom violation… a fucking stupid idea"; "remove tier 1 too. it's also dumb"), who then specified the doctrine-correct sequence himself — **ship a static instruction (T0), measure (D5), escalate to anything heavier ONLY if T0 is proven insufficient.** T0 shipped ([[aops-960cff4f]], done, PR #1513); the measurement gate D5 [[aops-217ba56d]] is **inbox — not done**.

Consequence for this spec: a grep→PKB classifier rule is the **documented escalation contingency** for the retrieval gap — to be evaluated _only if_ D5 shows T0 insufficient, and _only after_ auto-mode observability (acceptance criterion #4) gives a fire-rate baseline. It is **not** a seed rule. This matters as precedent: the classifier's _own first deployment_ must demonstrate the §4 escalation discipline (instruction-tier first → measure → escalate on evidence), not violate it. Note the meta-lesson: this collision was found only by searching the PKB — three transcript/issue/PR research streams missed it — which is itself a data point _for_ the retrieval-gap epic, and _against_ short-circuiting its measured sequence.

## Initial deployment decision (2026-06-04)

After the candidate analysis was presented, **Nic chose to seed zero classifier rules** and walk the cheaper instruction rung first — the pure "default to instructions, bias hard against new L5+ gates" path ([`enforcement.md`](enforcement.md) §4). Concretely:

- **No `soft_deny` / `hard_deny` behavioural rules are added in this deployment.** The mechanism, its spec, its pyramid placement, and its observability ship; the rule set stays empty.
- **Lead candidate — scope-pivot** (a mutation aimed at an _unrelated_ target when the user asked a question / bounded read; `do-one-thing`, `exercise-authority`) — **is routed to the instruction tier first.** `do-one-thing` is not yet delivered always-on to worker sessions (ENFORCEMENT-MAP "Known gaps"; the always-on axiom-delivery gap is tracked as `aops-98c7ce49`). That cheaper rung — deliver scope-discipline to worker sessions and **measure** — must be walked and shown insufficient before a classifier rule is reconsidered.
- **grep→PKB is gated on D5** (`aops-217ba56d`) per the retrieval-gap epic above.
- The classifier's first rule is therefore **evidence-gated, not authored now** — making the mechanism's debut a demonstration of the escalation doctrine rather than a violation of it.

The SSoT **path** is documented here (canonical source `templates/aops-core.plugin.json` `autoMode` key → `automode.py` merge → install + polecat mirror). The drift _fix_ itself — restoring the key, refreshing the stale `is_installed()` fingerprint (it still matches a removed `P#42`-era string), regenerating the polecat mirror — lands **with the first seeded rule**, so it is done once against real content. Installing an empty key now would only reinstall CC defaults and churn the fingerprint every session for no behavioural gain; that is deliberately not done. (Tracked.)

## Acceptance criteria for the initial deployment

1. The canonical SSoT **path** for auto-mode rules is documented: `templates/aops-core.plugin.json` (`autoMode` key) → `automode.py` merge → install + polecat mirror. The `autoMode` key restoration, `is_installed()` fingerprint refresh, and polecat regen are **not performed this cycle** (zero rules seeded; doing so now would churn the fingerprint with no behavioural gain — see deployment decision above) — these land with the first seeded rule (AC #2). When a rule is later seeded it follows the form above (principle + reasoning + cue + carve-outs + safer path + axiom slug).
2. The SSoT path is canonical and documented; because zero rules are seeded, no install/mirror change is made this cycle — the key restoration + `is_installed()` fingerprint refresh + polecat regen are tracked to land with the first seeded rule.
3. `ENFORCEMENT-MAP.md` (pyramid + axiom×mechanism rows), `enforcement-mechanisms.md`, and `enforcement.md` are updated so the classifier is the L5 judgment per-action gate, distinct from deterministic L4.
4. Transcript tooling extracts auto-mode decisions — session `permission_mode`, plus structured `permission_denials` (`tool_name`/`tool_use_id`/`tool_input`) and `terminal_reason` from the result envelope — into the transcript frontmatter and timeline events (fixture-tested). The _upstream capture_ of the headless result envelope (currently stdout-only, not persisted to a transcript-readable file) is tracked and lands with the first seeded rule, when there are real denials to capture.
5. A test plan exists that is satisfied by **demonstrated success in live transcripts** and/or **deliberate, agent-led boundary-probing sessions** — not a prescriptive mechanical script.
6. When a rule is eventually seeded, `claude auto-mode critique` returns no "dangerous" / "disables the classifier" findings (no rules this cycle, so nothing to critique).

## Test & validation approach

The classifier deals in judgment, so its validation is judgment-based, not a mechanical pass/fail rig — doing otherwise would re-commit the `judgment-non-delegable` error the mechanism exists to avoid. Two complementary modes; a seeded rule must satisfy at least one before it is trusted, and the observability above is what makes either possible.

1. **Demonstrated success in live transcripts (primary).** Once a rule is seeded, mine real sessions (via the auto-mode-decision extraction) for its fires. For each fire a reviewer judges: a _true catch_ (the action really was the violation) or a _false positive_ (a legitimate action denied)? The rule earns trust when real fires are predominantly true catches **and** no session shows a `terminal_reason` death-by-denial. This uses work that was happening anyway, and the first real denial to appear in a transcript also confirms the extraction pipeline end-to-end (and is the trigger to wire the upstream capture if still pending).

2. **Deliberate, agent-led boundary sessions.** Where live fires are too rare to judge, commission an agent to _explore_ the rule's boundary — construct actions near the carve-out edge (for a read-vs-grep rule: a literal-symbol grep that should pass, a concept grep that should be redirected, and the ambiguous middle) and report where the classifier actually draws the line versus where we want it. This is exploratory and adversarial, **not** a fixed script: the agent uses judgment to find the interesting edges; a reviewer judges whether the line is right. The output is a characterisation of real behaviour, not a checkbox.

**Bar to keep a rule:** true-catch-dominant fires, zero death-by-denial, and a denial reason that observably redirects the agent (the next action in the transcript is the safer path, not a retry). A rule that cannot show this on real or probed evidence is retired per the lifecycle section — the same evidence discipline that gated its admission.

## References

- [CC Auto Mode engineering post](https://www.anthropic.com/engineering/claude-code-auto-mode) — canonical external description.
- [`specs/enforcement/enforcement.md`](enforcement.md) — enforcement design statement (pyramid, escalation discipline, §4.1 CBA).
- [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md) — operative register (where this classifier's rules are recorded).
- [`specs/enforcement/ultra-vires-enforcer.md`](ultra-vires-enforcer.md) §"Relationship to Claude Code auto mode" — classifier vs enforcer subagent.
- [`specs/enforcement/enforcement-mechanisms.md`](enforcement-mechanisms.md) — per-mechanism runtime catalogue entry.
- [`.agents/rules/AXIOMS.md`](../../.agents/rules/AXIOMS.md) — the axioms rules cite (esp. `judgment-non-delegable`, `exercise-authority`).
- PKB `kb-15ddad1c` (Auto-mode classifier — adding a rule), `task-06db60dc` (prior prose rewrite), `task-5079886a` (classifier-as-matcher misframing audit).
