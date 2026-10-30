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

| Component | Content |
| - | - |
| Intent | What the user actually wants, stated plainly |
| Workflow | The selected template from the workflow catalog, plus its quality gate |
| Execution steps | The workflow interpreted for _this_ request as concrete numbered steps, `CHECKPOINT:`-prefixed where the workflow mandates verification |
| Guardrails | The constraints the selected workflow imposes |

The workflow catalog is `plugins/ida/skills/workflow-library/workflows/` and its `wf-*.md`
templates. Selection is interpretive, not mechanical: the hydrator reads the
template and generates steps for the specific request. A plan that instructs the
main agent to go read a workflow file has failed -- the whole cost saving is that
the reading already happened.

**`CHECKPOINT:` is behavioural guidance, not enforcement.** No code blocks
progress when verification is skipped. This is deliberate: enforcement here would
need a gate that can read evidence, which is a larger design than this one, and
the failure mode of a missed checkpoint is recoverable.

## Task body length and step inlining

Task bodies are strictly concise: 50–150 words for atomic tasks, and up to 300 words for multi-stage composite workflows.

Step inlining is interpretive, not mechanical transcription:

- Workflow templates (`wf-*`) cannot be invoked by workers. Each composed template stage, obligation, and quality gate is interpreted into a concise numbered imperative step in Instructions.
- Inlining distills the required outcome or verification checkpoint for each stage; it omits narrative prose, rationale, background explanations, and implementation methods the worker can determine for itself.
- Every composed template stage and finish obligation is represented as a concrete step so no required process or gate is lost, while staying strictly within the 300-word ceiling for composite workflows (or 150 words for atomic tasks).
- Outcome-oriented criteria: Reified tasks define observable end-state conditions and verification criteria rather than implementation mechanisms. Line numbers, line ranges, and narrow code slice prescriptions are strictly forbidden in `Goal`, `Acceptance criteria`, and `Execution steps` / `Instructions`.
- Preserving design and build staging: When multi-file modifications or architectural choices are required, separate tasks are reified for Stage 1 (Design) and Stage 2 (Build) under `wf-code-task-base`. Stage 1 is never collapsed into Stage 2, even when the brief includes an implementation proposal.

## QA follow-up tasks

For pull request deliverables, `/reify` mints an independent downstream `QA: <task>` child task that verifies the delivered artifact and evaluates PR risk.

For non-PR tasks (such as empirical analyses, documentation updates, research tasks, and operational maintenance), `/reify` mints a separate `QA: <task>` child task only where the composed workflow warrants an independent verification check (e.g. empirical analysis with replication requirements, high-impact specification or policy changes, or multi-step qualitative audits). Workflows that do not warrant a separate verification pass mint no QA child.

Worker self-release to `done` is preserved across all non-PR tasks: workers self-release to `done` upon satisfying the frozen acceptance checklist with concrete evidence, without being held in `review`.

## Context gathering

| Tier | Source | Role |
| - | - | - |
| 1 | PKB, via `aops:hydrate` | Primary -- semantic search for related knowledge and open tasks |
| 2 | Framework specs and axioms | Secondary -- the principles that bind this work |
| 3 | GitHub / web search | Tertiary -- only when internal sources are insufficient |
| 4 | Session transcripts | Last resort -- very recent context not yet written anywhere |

Tiers 1–2 run inside the hydrator against a budget of roughly 450 tokens of
retained context. Tiers 3–4 are never run by the hydrator; they are emitted as
execution steps for the main agent, because they are slow and usually
unnecessary.
