# Specs Index

## Architecture

- [ARCHITECTURE.md](ARCHITECTURE.md) -- repository layout, plugin boundaries, hook set, build stages.
- [build-and-install.md](build-and-install.md) -- local install and release pipeline.
- [transcript-pipeline.md](transcript-pipeline.md) -- session-transcript ingestion, normalization, and output.
- [meta/doc-taxonomy.md](meta/doc-taxonomy.md) -- the five document kinds and where each lives.
- [meta/naming-and-decisions.md](meta/naming-and-decisions.md) -- task naming, filename standards, and graph-relationship decision representation.

## Agents

- [agents/sara.md](agents/sara.md) -- the supervisor: delegate-and-verify orchestration process.
- [agents/reify.md](agents/reify.md) -- hydrating a task node with intent, workflow, execution steps, and guardrails.
- [agents/prompt-hydration.md](agents/prompt-hydration.md) -- prompt hydration.
- [agents/sleep-cycle.md](agents/sleep-cycle.md) -- the periodic consolidation agent.
- [agents/ida-supervision-migration.md](agents/ida-supervision-migration.md) -- which supervision capabilities move to ida, the checkpoints that gate each increment of autonomy, and what never moves.

## Enforcement

- [enforcement/enforcement.md](enforcement/enforcement.md) -- governing principle, the four levers, and the escalation ladder.
- [enforcement/task-contract.md](enforcement/task-contract.md) -- the work-unit contract (claim → release).
- [enforcement/workflow.md](enforcement/workflow.md) -- the five-step workflow shape and review-depth call.
- [enforcement/sign-off.md](enforcement/sign-off.md) -- release-unit-scale sign-off.
- [enforcement/evidence-contract.md](enforcement/evidence-contract.md) -- the universal claim-evidence shape.
- [enforcement/auto-mode-classifier.md](enforcement/auto-mode-classifier.md) -- Claude Code auto-mode classifier design and cost model.

## Polecat

- [polecat/polecat-system.md](polecat/polecat-system.md) -- one isolated container + isolated clone per `polecat run` invocation.
- [polecat/tmux-interactive-driving.md](polecat/tmux-interactive-driving.md) -- driving a polecat container interactively via tmux.
- [polecat/spec-partial-work-tight-loop-delivery.md](polecat/spec-partial-work-tight-loop-delivery.md) -- the `partial` terminal state and partial-work doctrine.
- [polecat/spec-base-ref-resolution.md](polecat/spec-base-ref-resolution.md) -- how `resolve_isolated_workspace()` picks the commit a worker's isolated clone diverges from.
- [polecat/spec-image-staleness-detection.md](polecat/spec-image-staleness-detection.md) -- detecting and surfacing a stale baked plugin payload against a bind-mounted workspace.

## Workflows

- [workflows/workflow.md](workflows/workflow.md) -- the three-stage pipeline and where workflow components come from.
- [workflows/conceptual-review-workflow.md](workflows/conceptual-review-workflow.md) -- composable-lens multi-agent review of intellectual artifacts.
- [workflows/research-decomposition.md](workflows/research-decomposition.md) -- research-specific decomposition primitives and sequencing.
- [workflows/reconcile.md](workflows/reconcile.md) -- GitHub ↔ PKB task-graph reconciliation.
- [workflows/strategic-review.md](workflows/strategic-review.md) -- design intent for the parallel-review-and-reconcile quality gate.

## Future

Unbuilt designs -- see each file for what would need to exist before it ships.

- [future/session-insights-prompt.md](future/session-insights-prompt.md) -- the session-insights extraction contract.
- [future/session-insights-metrics-schema.md](future/session-insights-metrics-schema.md) -- the session-insights pipeline metrics definition.
