# Specs Index

## Architecture

- [ARCHITECTURE.md](ARCHITECTURE.md) -- repository layout, plugin boundaries, hook set, build stages.
- [build-and-install.md](build-and-install.md) -- local install and release pipeline.
- [transcript-pipeline.md](transcript-pipeline.md) -- session-transcript ingestion, normalization, and output.
- [observability/observability.md](observability/observability.md) -- cross-surface observability and correlation across the task graph, trace store, container runtime, and session log archive.
- [observability/telemetry-failure-surfacing.md](observability/telemetry-failure-surfacing.md) -- surfacing telemetry configuration failures, export refusals, and network errors across all emitters with session gating policy options.
- [meta/doc-taxonomy.md](meta/doc-taxonomy.md) -- the five document kinds and where each lives.
- [meta/writing-specs.md](meta/writing-specs.md) -- the spec template and the rules every spec follows.
- [meta/naming-and-decisions.md](meta/naming-and-decisions.md) -- task naming, filename standards, and graph-relationship decision representation.

## Agents

- [agents/sara.md](agents/sara.md) -- the supervisor: delegate-and-verify orchestration process.
- [agents/reify.md](agents/reify.md) -- binding a node to an executor and composed three-tier workflow inside container supervision or planning.
- [agents/prompt-hydration.md](agents/prompt-hydration.md) -- prompt hydration.
- [agents/sleep-cycle.md](agents/sleep-cycle.md) -- the periodic consolidation agent.
- [agents/ida-interaction-rules.md](agents/ida-interaction-rules.md) -- presentation standards, conversational pacing, subagent delegation boundaries, and channel hygiene for Ida.
- [agents/face-ida-triage-and-tracked-requests.md](agents/face-ida-triage-and-tracked-requests.md) -- face-Ida triage decision, subagent twin verification, /q placement, container dispatch, and tracked-request closed-loop delivery.
- [agents/compliance-consequences-removal.md](agents/compliance-consequences-removal.md) -- removal of volunteered compliance and conflict-of-interest consequences in decision conversations.
- [agents/authoritative-user-task-reports.md](agents/authoritative-user-task-reports.md) -- authoritative user task reports deciding task state and ministerial lifecycle execution in Pauli.
- [agents/decision-queue-boundaries.md](agents/decision-queue-boundaries.md) -- decision-queue boundaries, informational query list-routing, conversational pacing, and preservation of collaborative design exploration.
- [agents/external-state-recheck.md](agents/external-state-recheck.md) -- targeted external-state verification and read-only GitHub query authority for the knowledge base custodian.
- [agents/dump-session-wrapup.md](agents/dump-session-wrapup.md) -- dump skill invocation modes: user-run emergency handover vs. agent-run routine wrap-up, consolidated daily note project pointers, retroactive tasks, durable facts, and handover traceability.
- [agents/dump-faults-and-finds.md](agents/dump-faults-and-finds.md) -- dump skill triggers for significant operational fault recoveries and major diagnostic findings without code changes.

## Enforcement

- [ENFORCEMENT-MAP.md](ENFORCEMENT-MAP.md) -- concise cross-reference table mapping rules to their live enforcement mechanisms.
- [enforcement/enforcement-map.md](enforcement/enforcement-map.md) -- specification governing the enforcement map schema, inclusion boundaries, and concision invariants.
- [enforcement/enforcement.md](enforcement/enforcement.md) -- governing principle, regulatory tools, mechanism categories, and proportional intervention.
- [enforcement/task-contract.md](enforcement/task-contract.md) -- the work-unit contract (claim → release).
- [enforcement/workflow.md](enforcement/workflow.md) -- the four-step workflow shape and review-depth call.
- [enforcement/evidence-contract.md](enforcement/evidence-contract.md) -- the universal claim-evidence shape.
- [enforcement/evidence-contract-enforcement.md](enforcement/evidence-contract-enforcement.md) -- the reminders, gate, and proportional interventions that hold agents to the evidence contract.
- [enforcement/reviewer-class-standard-check.md](enforcement/reviewer-class-standard-check.md) -- reviewer class-standard verification across changed files in candidate changes.
- [enforcement/coordinator-failure-enforcement.md](enforcement/coordinator-failure-enforcement.md) -- design enforcement moves and observable build criteria for five coordinator failure classes.
- [enforcement/auto-mode-classifier.md](enforcement/auto-mode-classifier.md) -- Claude Code auto-mode classifier design and cost model.
- [enforcement/handback-format-design.md](enforcement/handback-format-design.md) -- premise-check handback format design review: empirical sample, Toulmin structure preservation, and migration plan.
- [enforcement/premise-check-rejection-load-instruction.md](enforcement/premise-check-rejection-load-instruction.md) -- premise-check load instructions in argument rejections and refusals across hearsay gate, verdict recorder, and checker surfaces.
- [enforcement/premise-check-instruction-tuning.md](enforcement/premise-check-instruction-tuning.md) -- instruction and refusal message tuning to eliminate format errors across report sender and checker surfaces.

## Polecat

- [polecat/polecat-system.md](polecat/polecat-system.md) -- one isolated container + isolated clone per invocation, running /supervise for epic tasks or /pull for leaf tasks.
- [polecat/tmux-interactive-driving.md](polecat/tmux-interactive-driving.md) -- driving a polecat container interactively via tmux.
- [polecat/spec-partial-work-tight-loop-delivery.md](polecat/spec-partial-work-tight-loop-delivery.md) -- the `partial` terminal state and partial-work doctrine.
- [polecat/spec-base-ref-resolution.md](polecat/spec-base-ref-resolution.md) -- how `resolve_isolated_workspace()` picks the commit a worker's isolated clone diverges from.
- [polecat/spec-image-staleness-detection.md](polecat/spec-image-staleness-detection.md) -- detecting and surfacing a stale baked plugin payload against a bind-mounted workspace.
- [polecat/spec-observability.md](polecat/spec-observability.md) -- real-time monitoring across MCP and host-launcher dispatch surfaces.
- [polecat/spec-silent-failure-detection.md](polecat/spec-silent-failure-detection.md) -- launch preflight, exit-time task guard, durable `run.json` harvest, and immediate orphan detection for polecat workers.

## Telegram

- [telegram/command-menus.md](telegram/command-menus.md) -- native Telegram bot command menu: registration of the configured `TELEGRAM_BOT_COMMANDS` list and delivery of command taps to the agent.
- [telegram/message-actions.md](telegram/message-actions.md) -- inline message action buttons (`Check logic`, `Explain`, `Reasons`), callback tap events, and multi-level argument chain response contract.
- [telegram/mini-app-dashboard-integration.md](telegram/mini-app-dashboard-integration.md) -- operator experience and agent bridge contract for supervising and steering conversational agents via the Telegram Mini App.
- [telegram/question-delivery.md](telegram/question-delivery.md) -- delivery guarantee for structured questions over Telegram, confirmed button rendering, dynamic bot resolution, and fast failure surfacing.
- [telegram/reactions.md](telegram/reactions.md) -- Telegram reaction handling contract, platform-authoritative validation, and unified shared reaction legend across bot personas.
- [telegram/reply-button-layout.md](telegram/reply-button-layout.md) -- reply button layout customization, consolidated predefined row, and tap acknowledgement specification.
- [telegram/shunt-handover.md](telegram/shunt-handover.md) -- single-command conversation handover from any session to Telegram across local, remote-control, and cloud environments.
- [telegram/threaded-conversations.md](telegram/threaded-conversations.md) -- threaded Telegram conversations and topic message routing by default without configuration.

## Tools

- [tools/diagram-pkb-graphs.md](tools/diagram-pkb-graphs.md) -- how an agent using `tools:diagram` draws a PKB graph selection as a layered Excalidraw map: procedure, layout, kind and state encoding, weight-to-width scale, gap badges.

## Workflows

- [workflows/workflow.md](workflows/workflow.md) -- the four-stage planning and execution pipeline (capture, expand, reify, dispatch) and three-tier template resolution.
- [workflows/default-planning.md](workflows/default-planning.md) -- repository specs for academicOps design changes and PKB task plans for general work.
- [workflows/plan-view.md](workflows/plan-view.md) -- formal plan view generation and redrawing on decomposed objectives.
- [workflows/conceptual-review-workflow.md](workflows/conceptual-review-workflow.md) -- composable-lens multi-agent review of intellectual artifacts.
- [workflows/default-dialectic-review.md](workflows/default-dialectic-review.md) -- dialectical multi-agent evaluation as the workflow library's default independent review stage.
- [workflows/pr-lifecycle.md](workflows/pr-lifecycle.md) -- PR lifecycle workflows: sweep task queuing and move-along fan-out.
- [workflows/research-decomposition.md](workflows/research-decomposition.md) -- research-specific decomposition primitives and sequencing.
- [workflows/reconcile.md](workflows/reconcile.md) -- GitHub ↔ PKB task-graph reconciliation.
- [workflows/strategic-review.md](workflows/strategic-review.md) -- design intent for the parallel-review-and-reconcile quality gate.
- [workflows/graph-valuation.md](workflows/graph-valuation.md) -- how agents capture, value and maintain the graph under the flow rule: placement, densify batches, pricing, deadline classes, ripeness, and the budget for asking the user.

## Future

Unbuilt designs -- see each file for what would need to exist before it ships.

- [future/session-insights-prompt.md](future/session-insights-prompt.md) -- the session-insights extraction contract.
- [future/session-insights-metrics-schema.md](future/session-insights-metrics-schema.md) -- the session-insights pipeline metrics definition.
