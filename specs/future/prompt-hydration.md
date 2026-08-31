---
title: Prompt Hydration
type: spec
status: proposed
tier: core
depends_on: []
tags: [framework, routing, context]
---

# Prompt Hydration

Turn a terse user prompt into a durable, enriched task node carrying intent,
workflow, execution steps and guardrails — so any worker can pull it and execute
without gathering context again.

**Nothing in this document is built.** No hook, agent, workflow file or library
named below exists in the repository.

## Scope, against what already ships

`aops:hydrate` (`plugins/aops/skills/hydrate/SKILL.md`) already ships the
_disambiguation_ half: it searches the PKB for what the ambiguous words in an ask
point at and returns a shortlist of ids, writing nothing. That skill is the
retrieval primitive this design consumes; do not re-specify or re-implement its
search, shortlist or overlap-flagging behaviour.

What is unbuilt is the _enrichment_ half: selecting a workflow, interpreting it
into concrete steps, attaching guardrails, and **writing the result onto a task
node**. That durability is the whole point. Hydration is something done TO tasks,
not an ephemeral session artifact — an enriched task survives session loss,
is visible to other sessions, and carries its own audit trail.

## When it runs

Every `UserPromptSubmit`. This closes the control gap where freeform prompts get
baseline context only, unlike prompts that arrive through a skill or a claimed
task.

## Outputs

The hydrator emits four components, and the main agent executes them without
making further routing decisions:

| Component       | Content                                                                                                                                 |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Intent          | What the user actually wants, stated plainly                                                                                            |
| Workflow        | The selected template from the workflow catalog, plus its quality gate                                                                  |
| Execution steps | The workflow interpreted for _this_ request as concrete numbered steps, `CHECKPOINT:`-prefixed where the workflow mandates verification |
| Guardrails      | The constraints the selected workflow imposes                                                                                           |

The workflow catalog is `plugins/aops/workflows/INDEX.md` and its `wf-*.md`
templates. Selection is interpretive, not mechanical: the hydrator reads the
template and generates steps for the specific request. A plan that instructs the
main agent to go read a workflow file has failed — the whole cost saving is that
the reading already happened.

**`CHECKPOINT:` is behavioural guidance, not enforcement.** No code blocks
progress when verification is skipped. This is deliberate: enforcement here would
need a gate that can read evidence, which is a larger design than this one, and
the failure mode of a missed checkpoint is recoverable.

## Context gathering

| Tier | Source                     | Role                                                           |
| ---- | -------------------------- | -------------------------------------------------------------- |
| 1    | PKB, via `aops:hydrate`    | Primary — semantic search for related knowledge and open tasks |
| 2    | Framework specs and axioms | Secondary — the principles that bind this work                 |
| 3    | GitHub / web search        | Tertiary — only when internal sources are insufficient         |
| 4    | Session transcripts        | Last resort — very recent context not yet written anywhere     |

Tiers 1–2 run inside the hydrator against a budget of roughly 450 tokens of
retained context. Tiers 3–4 are never run by the hydrator; they are emitted as
execution steps for the main agent, because they are slow and usually
unnecessary.

### Principle selection, not principle injection

The hydrator receives the axioms in full and returns only the three to seven that
bear on this request, with a one-line justification each. The main agent receives
the selection, never the full files.

This is a cost decision that constrains the implementation: the hydrator is a
cheap model reading ~3000 tokens; the main agent is an expensive model reading
~150. Injecting the full set into every prompt inverts that and is what this
design exists to avoid.

### Repo-local context map

`.agents/context-map.json` maps topics and keywords to documentation files in the
current repository. It is designed to work at two levels, and the first must not
depend on the second:

1. **Platform-agnostic.** A plain JSON file any agent on any client can read
   directly. No hooks, no framework dependency.
2. **aops-integrated.** The `UserPromptSubmit` hook loads the map from the working
   directory only — no search up the tree, no fallback — and injects the **full**
   entry list as an "Available Documentation" section. Relevance is decided by the
   model, never by pre-filtering in Python: keyword matching in the hook throws
   away exactly the semantic judgement the model is there to make.

## Mechanism

```
UserPromptSubmit hook
  → extract session context, write the full context to a temp file
  → main agent receives a short instruction (~100 tokens) plus the file path
  → main agent spawns the hydrator subagent on a cheap model
  → hydrator reads the temp file, emits the execution plan
  → main agent follows the plan
```

The temp file exists so the main agent's context carries a path rather than the
several hundred tokens of prompt, session state and catalog the hydrator needs.
It is also inspectable, which is the only way to debug a bad plan after the fact.

Temp files live under a dedicated directory, are named with a collision-safe
prefix, and are cleaned up on a later hook invocation rather than by the writer —
a hydrator that cleans up its own input cannot be debugged.

## Failure modes

Infrastructure failures fail fast; content-gathering failures degrade gracefully.

| Failure                      | Behaviour                                                            |
| ---------------------------- | -------------------------------------------------------------------- |
| Temp file write fails        | Hook exits non-zero and logs. No silent fallback (`halt-on-failure`) |
| Temp file read fails         | Hydrator returns an error; main agent proceeds unhydrated            |
| PKB search fails             | Continue on codebase and session context alone                       |
| Workflow selection uncertain | Default to plan mode                                                 |
| Timeout                      | Return partial context, log a warning                                |

**Known unmitigated risk:** the main agent can simply ignore the injected
instruction and never spawn the hydrator. That failure is silent, and nothing in
this design detects it.

## Performance

Typical 5–10s, hard timeout 15s. Quality of the plan matters more than latency;
the budget exists to stop the hydrator from investigating rather than routing.

**It is cheaper to fail at execution time than to verify at planning time on
every request.** The hydrator therefore does not pre-flight checks such as "has
this already been implemented" — it plans that check as the first execution step
and lets the main agent discover the answer.

## Acceptance criteria

1. Hydration runs on every `UserPromptSubmit`.
2. The output carries all four components, and the enriched result is written to a
   task node rather than returned only in-turn.
3. The main agent can execute the plan without reading any workflow file.
4. The main agent receives selected principles, never full axiom files.
5. Latency meets the budget above.
6. Infrastructure failures halt; content failures degrade.
