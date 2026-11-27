---
name: dogfood
description: Standing experiment protocol for the academicOps project -- every piece of real work is also evidence about the framework. Use when starting framework work of any type, testing instructions blind, trialling a runtime mechanism, or reviewing how well the framework served a task just completed.
---

# Dogfood -- Learn How the Framework Performs by Using It

## Orientation

`academicOps` lets the user **delegate execution without delegating judgment** across three goals: academic quality, strategic planning, and cognitive-load and working-memory support for users. As harnesses grow more capable, the framework must get _simpler_: evolve _processes_ (when skills fire, what contracts bind handoffs) and delete crutches for transient model limits. **Every real task is an experiment on the framework.**

## The Loop

`work -> observe friction -> record evidence (never fix inline) -> detached review checks recurrence -> change with the most proportional intervention -> re-test blind.`

## Modes (Pick One)

1. **`live-trial`** (default): Work normally. File an evidence record when the framework helps or hurts (misleading instruction, unhelpful check or guard, helpful contract, missing context) without fixing inline. Propose fixes after finishing; apply only with express user approval.
2. **`instruction-test`** (blind delegated execution): Give a contextless agent only the instruction and a real task (an ask recorded in the trace store, never one written for the test; no coaching; redirect rather than restart). Record a failure hypothesis before reading output, score against acceptance criteria, and have an independent agent score blind. After edits, run >=2 blind runs per condition.
3. **`mechanism-trial`** (new runtime boundary guard, hook, evaluator, or classifier): Pre-register hypothesis, promote criteria, kill criteria, and review date on the task record before enabling; remove once past review date without evidence.
4. **`planning-eval`**: Read [references/decomposition-eval.md](references/decomposition-eval.md) before scoring decomposition/planning quality; gold-standard pairs are single-use.

## Supervising a Trial (Modes 2-4)

- **Do none of the work yourself**: Pass only brief facts; never supply framework method, doctrine, or stopping rules in the brief.
- **A subject halt is a result**: Record `instruction-gap` evidence and leave the run blocked rather than solving it for the subject.
- **A blocked route for you is repair work**: Fix your own sanctioned launch path via the least invasive intervention (inputs before instruction text), recorded first and approved before editing.
- **Keep the bar intact**: Never drop surfaces or scope to pass; judge qualitatively against world-class outcomes, not binary "done".
- Drive runs and tracking records via [`debug`](../debug/SKILL.md).

## Invariants

- **Hypothesis before observation**: Write expectations down before inspecting outputs.
- **Real inputs, traced runs**: Trials run on real recorded asks and are judged from their own traces; a claim about how the framework performs beyond those runs comes only from the observed-trace store, never from synthetic, constructed or simulated runs.
- **No verdict from absence**: Name the discriminating observation before scoring pass/fail; otherwise file `undetermined`.
- **Named surface binds**: Run on the specified client, container, agent, or tier; verify blockers before halting, and never swap surfaces silently.
- **Record before remedy**: File unedited evidence first; three cited recurrences justify a runtime mechanism (fewer justify at most a text edit).
- **Approval boundary on remedies**: Any edit changing future agent directives requires express user approval (undoing session-local damage or deleting dead pointers is repair, not a remedy).

## Evidence Record and Turning Evidence Into Change

File one GitHub issue per incident: **What happened vs what was promised** (cite rule/skill path or `"no rule existed"`), **Classification** (`instruction-gap | process-gap | harness-limit | genuine-bug | framework-win`), **Impact**, and **Separate proposed remedy** (never applied without approval).

Match approved intervention force proportionally: `instruction text -> skill/process step -> workflow contract -> runtime mechanism` (>=3 recurrences + pre-registration). Pass `/craft`, re-test blind (mode 2), promote tested edits before session end, and note residual friction in handback rather than filing speculative tasks.
