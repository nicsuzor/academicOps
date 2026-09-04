# Specs Index

## Architecture

- [ARCHITECTURE.md](ARCHITECTURE.md) -- target repository layout, plugin boundaries, build stages.
- [build-and-install.md](build-and-install.md) -- local install and release pipeline.
- [meta/doc-taxonomy.md](meta/doc-taxonomy.md) -- the five document kinds and where each lives.
- [transcript-pipeline.md](transcript-pipeline.md) -- session-transcript ingestion, normalization, and output.

## Agents

- [agents/sara.md](agents/sara.md) -- delegate-and-verify orchestration process.
- [agents/ida-supervision-migration.md](agents/ida-supervision-migration.md) -- which supervision capabilities move to ida, the checkpoints that gate each increment of autonomy, and what never moves.

## Enforcement

- [ENFORCEMENT-MAP.md](ENFORCEMENT-MAP.md) -- current-state register: every mechanism, what it obliges, and whether it is on.
- [enforcement/enforcement.md](enforcement/enforcement.md) -- governing principle, the four levers, and the five bands.
- [enforcement/task-contract.md](enforcement/task-contract.md) -- the work-unit contract (claim → release).
- [enforcement/workflow.md](enforcement/workflow.md) -- the five-step workflow shape and review-depth call.
- [enforcement/sign-off.md](enforcement/sign-off.md) -- release-unit-scale sign-off.
- [enforcement/evidence-contract.md](enforcement/evidence-contract.md) -- the universal claim-evidence shape.
- [enforcement/auto-mode-classifier.md](enforcement/auto-mode-classifier.md) -- Claude Code auto-mode classifier design and cost model.

## Dispatch

- [dispatch/dispatch-system.md](dispatch/dispatch-system.md) -- one Docker Sandbox + one private clone per dispatched task, launched with raw `sbx`.

## Polecat

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

## Tools

- [tools/peer-review-probes.md](tools/peer-review-probes.md) -- why the peer-review skill's eleven analytical probes are held verbatim rather than condensed.

## Future

- [future/polecat-dispatch-from-container-via-ssh.md](future/polecat-dispatch-from-container-via-ssh.md) -- accepted design for dispatching polecats from a containerised orchestrator.
