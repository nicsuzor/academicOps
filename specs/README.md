# Specs Index

## Architecture

- [ARCHITECTURE.md](ARCHITECTURE.md) — target repository layout, plugin boundaries, build stages.
- [build-and-install.md](build-and-install.md) — local install and release pipeline.
- [meta/doc-taxonomy.md](meta/doc-taxonomy.md) — the five document kinds and where each lives.
- [transcript-pipeline.md](transcript-pipeline.md) — session-transcript ingestion, normalization, and output.

## Agents

- [agents/agent-authority.md](agents/agent-authority.md) — permissions schema, tool naming, skill/sub-agent delegation.

## Interactive experience

- [adhd/surface-contract.md](adhd/surface-contract.md) — attention-surface contract for the daily note / morning brief.

## Enforcement

- [enforcement/enforcement.md](enforcement/enforcement.md) — governing principle and the seven enforcement mechanisms.
- [enforcement/task-contract.md](enforcement/task-contract.md) — the work-unit contract (claim → release).
- [enforcement/workflow.md](enforcement/workflow.md) — the five-step workflow shape and review-depth call.
- [enforcement/sign-off.md](enforcement/sign-off.md) — release-unit-scale sign-off.
- [enforcement/evidence-contract.md](enforcement/evidence-contract.md) — the universal claim-evidence shape.
- [enforcement/auto-mode-classifier.md](enforcement/auto-mode-classifier.md) — Claude Code auto-mode classifier design and cost model.

## Polecat

- [polecat/polecat-system.md](polecat/polecat-system.md) — one isolated container + isolated clone per `polecat run` invocation.
- [polecat/supervisor.md](polecat/supervisor.md) — delegate-and-verify orchestration process.
- [polecat/tmux-interactive-driving.md](polecat/tmux-interactive-driving.md) — driving a polecat container interactively via tmux.
- [polecat/spec-partial-work-tight-loop-delivery.md](polecat/spec-partial-work-tight-loop-delivery.md) — the `partial` terminal state and partial-work doctrine.

## Workflows

- [workflows/conceptual-review-workflow.md](workflows/conceptual-review-workflow.md) — composable-lens multi-agent review of intellectual artifacts.
- [workflows/research-decomposition.md](workflows/research-decomposition.md) — research-specific decomposition primitives and sequencing.
- [workflows/reconcile.md](workflows/reconcile.md) — GitHub ↔ PKB task-graph reconciliation.

## Future

- [future/polecat-dispatch-from-container-via-ssh.md](future/polecat-dispatch-from-container-via-ssh.md) — accepted design for dispatching polecats from a containerised orchestrator.
