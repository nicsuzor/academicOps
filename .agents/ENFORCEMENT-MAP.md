# Enforcement Map

Maps each mechanical enforcement mechanism to the rule(s) it enforces, its
execution context, its failure tier, and **what it costs to run**. Updated
whenever a check is added or retired (P#65).

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

## PR requirements for enforcement changes

Any PR that adds, modifies, or removes a row in the tables below — or any
hook, gate, axiom, CORE.md directive, or skill instruction targeting agent
behaviour — MUST include a **Cost-Benefit Analysis** block in the PR body:

1. **Friction evidence**: ≥3 concrete recurrences with links (transcript, PR,
   issue, /retro report). Fewer than 3 → close as premature.
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

| Mechanism             | Hook event       | Source                                                  | Rule(s)                                           | Scope                                 | Tier    | Cost / Impact                                               | Behaviour                                                                |
| --------------------- | ---------------- | ------------------------------------------------------- | ------------------------------------------------- | ------------------------------------- | ------- | ----------------------------------------------------------- | ------------------------------------------------------------------------ |
| `hydration` gates     | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | (R: hydration discipline)                         | All sessions                          | `warn`  | L4 · ~20 tok × 1/session                                    | Blocks tool calls until hydrator runs (mode-dependent)                   |
| `enforcer` gate       | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | A1, A6, A8 (axiom compliance, scope, halt)        | All sessions                          | `warn`  | L6 · ~820 tok + subagent dispatch × 1–3/session             | Periodic compliance checks via the enforcer subagent                     |
| `qa` gate             | Stop             | `aops-core/lib/gates/definitions.py`                    | (R: QA before completion)                         | All sessions                          | `warn`  | L3 · ~615 tok × 1/session                                   | Requires verification (marsha via /verify skill) before session can stop |
| `handover` gate       | Stop             | `aops-core/lib/gates/definitions.py`                    | (R: handover discipline)                          | All sessions                          | `warn`  | L3 · ~421 tok × 2–8/session (compounds → ~850–3,400 tok)    | Blocks Stop until commit + task update + framework reflection complete   |
| `ida` gate            | Stop             | `aops-core/lib/gates/definitions.py`                    | A3, A4, A11 (proof, citation, observability)      | All sessions                          | `warn`  | L3 · ~515 tok × 3–10/session (compounds → ~1,550–5,150 tok) | Non-blocking reminder to back assertions with proof and disclose skips   |
| `custodiet` gate      | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | (R: workflow discipline — premature termination)  | All sessions                          | `warn`  | L4 · ~500 tok × rare                                        | Detects scope explosion / plan-less execution                            |
| `policy_enforcer`     | PreToolUse       | `aops-core/hooks/policy_enforcer.py`                    | (R: destructive-command guards)                   | All sessions                          | `block` | L5 · ~150 tok per block × rare                              | Hard-blocks dangerous Bash patterns (force-push to main, `rm -rf`, etc.) |
| `aca_data_autocommit` | PostToolUse      | `aops-core/hooks/router.py` `_run_aca_data_autocommit`  | (procedural: keep PKB synced)                     | When `$ACA_DATA` set                  | n/a     | L2 · ~100ms wall-clock × per write op                       | Auto-commits `$ACA_DATA` after state-modifying tool calls                |
| `context-map hints`   | UserPromptSubmit | `aops-core/hooks/router.py` `_inject_context_map_hints` | (procedural: discovery via `.agents/context-map`) | Repos with `.agents/context-map.json` | `hint`  | L1 · ~50–200 tok × per prompt                               | Injects relevant doc pointers from the repo's context map                |

## Pre-commit hooks

| Hook ID                     | Script                                 | Rule(s)                    | Tier   | Cost / Impact               | Behaviour                                                                                                                                               |
| --------------------------- | -------------------------------------- | -------------------------- | ------ | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `check-no-new-orphan-md`    | `scripts/check_no_new_orphan_md.py`    | R5.6                       | `warn` | L2 · ~200ms × per commit    | Exits 1 on new `.md` files outside canonical-location allowlist                                                                                         |
| `check-framework-integrity` | `scripts/check_framework_integrity.py` | (wikilink index integrity) | `warn` | L2 · ~500ms–2s × per commit | Exits 1 on broken wikilinks or missing SKILLS/WORKFLOWS index entries                                                                                   |
| `check-no-fallbacks`        | `scripts/check_no_fallbacks.py`        | A8 / P#8                   | `warn` | L2 · ~100ms × per commit    | Exits 1 on silent-fallback patterns in `aops-core/hooks/*.py`, `aops-core/agent-env-map.conf`, `scripts/repo-sync-cron.sh` (see issue #930 for context) |

## CORE.md directives (always-on)

Static guidance embedded in `.agents/CORE.md` and loaded into every agent
session context for this repo. Unlike hooks, these are not event-triggered —
they are part of the agent's context window whenever it works in academicOps.
Prompt-cached at SessionStart, so marginal cost is ~$0 once cached; the
listed cost is the cold-start contribution.

| Directive   | Source                                                    | Rule(s)                           | Scope            | Tier   | Cost / Impact                           | Behaviour                                               |
| ----------- | --------------------------------------------------------- | --------------------------------- | ---------------- | ------ | --------------------------------------- | ------------------------------------------------------- |
| `pkb-first` | `.agents/CORE.md` — "Where to find documentation" section | (procedural: PKB-first discovery) | academicOps repo | `hint` | L1 · ~120 tok at session start (cached) | Instructs agents to use PKB before reading source code. |
