# Specs Index

## Architecture

- [ARCHITECTURE.md](ARCHITECTURE.md) -- repository layout, plugin boundaries, hook set, build stages.
- [build-and-install.md](build-and-install.md) -- local install and release pipeline.
- [transcript-pipeline.md](transcript-pipeline.md) -- session-transcript ingestion, normalization, and output.
- [observability/observability.md](observability/observability.md) -- cross-surface observability and correlation across the task graph, trace store, container runtime, and session log archive.
- [meta/doc-taxonomy.md](meta/doc-taxonomy.md) -- the five document kinds and where each lives.
- [meta/writing-specs.md](meta/writing-specs.md) -- the spec template and the rules every spec follows.
- [meta/naming-and-decisions.md](meta/naming-and-decisions.md) -- task naming, filename standards, and graph-relationship decision representation.

## Agents

- [agents/sara.md](agents/sara.md) -- the supervisor: delegate-and-verify orchestration process.
- [agents/reify.md](agents/reify.md) -- hydrating a task node with intent, workflow, execution steps, and guardrails.
- [agents/prompt-hydration.md](agents/prompt-hydration.md) -- prompt hydration.
- [agents/sleep-cycle.md](agents/sleep-cycle.md) -- the periodic consolidation agent.
- [agents/ida-supervision-migration.md](agents/ida-supervision-migration.md) -- which supervision capabilities move to ida, the checkpoints that gate each increment of autonomy, and what never moves.
- [agents/face-ida-triage-and-tracked-requests.md](agents/face-ida-triage-and-tracked-requests.md) -- face-Ida triage decision, subagent twin verification, tracked-request closed-loop delivery, and retirement of legacy /mine tracking.

## Enforcement

- [ENFORCEMENT-MAP.md](ENFORCEMENT-MAP.md) -- concise cross-reference table mapping rules to their live enforcement mechanisms.
- [enforcement/enforcement-map.md](enforcement/enforcement-map.md) -- specification governing the enforcement map schema, inclusion boundaries, and concision invariants.
- [enforcement/enforcement.md](enforcement/enforcement.md) -- governing principle, regulatory tools, mechanism categories, and proportional intervention.
- [enforcement/task-contract.md](enforcement/task-contract.md) -- the work-unit contract (claim → release).
- [enforcement/escalated-delivery-contract.md](enforcement/escalated-delivery-contract.md) -- in-session escalated delivery contract (`ida_held`, `/mine` surfacing pass, and the Workers-Append rule).
- [enforcement/workflow.md](enforcement/workflow.md) -- the four-step workflow shape and review-depth call.
- [enforcement/decision-steps-and-followup-placement.md](enforcement/decision-steps-and-followup-placement.md) -- decision steps on design research and task follow-up structural placement invariants.
- [enforcement/human-readability-first.md](enforcement/human-readability-first.md) -- design for the human-readability-first universal axiom and tripartite no-shitty-NLP clarification.
- [enforcement/release-as-done-lifecycle.md](enforcement/release-as-done-lifecycle.md) -- release-as-done task lifecycle, autonomous QA dispatch unblocking, and retirement of agent review status.
- [enforcement/rule-handling-and-escalation.md](enforcement/rule-handling-and-escalation.md) -- rule handling, waivers, one-way PKB linking, and mandatory upward escalation.
- [enforcement/evidence-contract.md](enforcement/evidence-contract.md) -- the universal claim-evidence shape.
- [enforcement/evidence-contract-enforcement.md](enforcement/evidence-contract-enforcement.md) -- the reminders, gate, and proportional interventions that hold agents to the evidence contract.
- [enforcement/preventing-over-engineering.md](enforcement/preventing-over-engineering.md) -- eliminating over-engineered mechanical software builds and enforcing agentic-first workflows.
- [enforcement/auto-mode-classifier.md](enforcement/auto-mode-classifier.md) -- Claude Code auto-mode classifier design and cost model.

## Polecat

- [polecat/polecat-system.md](polecat/polecat-system.md) -- one isolated container + isolated clone per `polecat run` invocation.
- [polecat/tmux-interactive-driving.md](polecat/tmux-interactive-driving.md) -- driving a polecat container interactively via tmux.
- [polecat/spec-partial-work-tight-loop-delivery.md](polecat/spec-partial-work-tight-loop-delivery.md) -- the `partial` terminal state and partial-work doctrine.
- [polecat/spec-base-ref-resolution.md](polecat/spec-base-ref-resolution.md) -- how `resolve_isolated_workspace()` picks the commit a worker's isolated clone diverges from.
- [polecat/spec-image-staleness-detection.md](polecat/spec-image-staleness-detection.md) -- detecting and surfacing a stale baked plugin payload against a bind-mounted workspace.
- [polecat/spec-observability.md](polecat/spec-observability.md) -- real-time monitoring across MCP and host-launcher dispatch surfaces.
- [polecat/spec-silent-failure-detection.md](polecat/spec-silent-failure-detection.md) -- launch preflight, exit-time task guard, durable `run.json` harvest, and immediate orphan detection for polecat workers.

## Telegram

- [telegram/command-menus.md](telegram/command-menus.md) -- native Telegram bot command menu registration and routing contract across conversational agent personas.
- [telegram/message-actions.md](telegram/message-actions.md) -- inline message action buttons (`Check logic`, `Explain`, `Reasons`), callback tap events, and multi-level argument chain response contract.
- [telegram/mini-app-dashboard-integration.md](telegram/mini-app-dashboard-integration.md) -- integration plan and interface specification for serving the Telegram Mini App from the overwhelm dashboard with dynamic state and bi-directional communication.
- [telegram/reactions.md](telegram/reactions.md) -- Telegram reaction handling contract, platform-authoritative validation, and unified shared reaction legend across bot personas.
- [telegram/reply-button-layout.md](telegram/reply-button-layout.md) -- reply button layout customization and consolidated predefined row specification.
- [telegram/threaded-conversations.md](telegram/threaded-conversations.md) -- threaded Telegram conversations and topic message routing by default without configuration.

## Tools

- [tools/diagram-pkb-graphs.md](tools/diagram-pkb-graphs.md) -- how an agent using `tools:diagram` draws a PKB graph selection as a layered Excalidraw map: procedure, layout, kind and state encoding, weight-to-width scale, gap badges.

## Workflows

- [workflows/workflow.md](workflows/workflow.md) -- the four-stage pipeline and where workflow components come from.
- [workflows/conceptual-review-workflow.md](workflows/conceptual-review-workflow.md) -- composable-lens multi-agent review of intellectual artifacts.
- [workflows/research-decomposition.md](workflows/research-decomposition.md) -- research-specific decomposition primitives and sequencing.
- [workflows/reconcile.md](workflows/reconcile.md) -- GitHub ↔ PKB task-graph reconciliation.
- [workflows/strategic-review.md](workflows/strategic-review.md) -- design intent for the parallel-review-and-reconcile quality gate.
- [workflows/graph-valuation.md](workflows/graph-valuation.md) -- how agents capture, value and maintain the graph under the flow rule: placement, densify batches, pricing, deadline classes, ripeness, and the budget for asking the user.

## Future

Unbuilt designs -- see each file for what would need to exist before it ships.

- [future/session-insights-prompt.md](future/session-insights-prompt.md) -- the session-insights extraction contract.
- [future/session-insights-metrics-schema.md](future/session-insights-metrics-schema.md) -- the session-insights pipeline metrics definition.
