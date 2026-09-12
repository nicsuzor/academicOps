Turn a terse user prompt into a durable, enriched task node carrying intent,
workflow, execution steps and guardrails -- so any worker can pull it and execute
without gathering context again.

This skill does _enrichment_: selecting a workflow, interpreting it
into concrete steps, attaching guardrails, and **writing the result onto a task
node**. That durability is the whole point: an enriched task survives session loss,
is visible to other sessions, and carries its own audit trail.

## Outputs

The hydrator emits four components, and the main agent executes them without
making further routing decisions:

| Component       | Content                                                                                                                                 |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Intent          | What the user actually wants, stated plainly                                                                                            |
| Workflow        | The selected template from the workflow catalog, plus its quality gate                                                                  |
| Execution steps | The workflow interpreted for _this_ request as concrete numbered steps, `CHECKPOINT:`-prefixed where the workflow mandates verification |
| Guardrails      | The constraints the selected workflow imposes                                                                                           |

The workflow catalog is `plugins/pkb/workflows/` and its `wf-*.md`
templates. Selection is interpretive, not mechanical: the hydrator reads the
template and generates steps for the specific request. A plan that instructs the
main agent to go read a workflow file has failed -- the whole cost saving is that
the reading already happened.

**`CHECKPOINT:` is behavioural guidance, not enforcement.** No code blocks
progress when verification is skipped. This is deliberate: enforcement here would
need a gate that can read evidence, which is a larger design than this one, and
the failure mode of a missed checkpoint is recoverable.

## Context gathering

| Tier | Source                     | Role                                                            |
| ---- | -------------------------- | --------------------------------------------------------------- |
| 1    | PKB, via `aops:hydrate`    | Primary -- semantic search for related knowledge and open tasks |
| 2    | Framework specs and axioms | Secondary -- the principles that bind this work                 |
| 3    | GitHub / web search        | Tertiary -- only when internal sources are insufficient         |
| 4    | Session transcripts        | Last resort -- very recent context not yet written anywhere     |

Tiers 1–2 run inside the hydrator against a budget of roughly 450 tokens of
retained context. Tiers 3–4 are never run by the hydrator; they are emitted as
execution steps for the main agent, because they are slow and usually
unnecessary.
