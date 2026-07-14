# tests/harness — polecat probe artifact dropbox

This directory is the artifact dropbox for agent-driven probes of `polecat
run`. There is no wrapper harness (see #1110 — replaced by inline `tmux`).

**Mechanics moved out.** The tmux-driving pattern, log/artifact locations,
gotchas, and the dev-loop workflow now live in
[`specs/polecat/tmux-interactive-driving.md`](../../specs/polecat/tmux-interactive-driving.md)
— read that first. For the operational `aops:debug` skill wrapping this
pattern, see `aops/skills/debug/SKILL.md`.

For the **validation workflow** (what to verify, what signals indicate
hooks/plugins/skills are actually loaded vs. just file-present), see
[`11-self-test.md`](../../.agents/skills/aops/workflows/11-self-test.md) § 2.

`dev-polecat.yaml` here is the static config `scripts/dev-crew.sh` targets
for the dev-loop (see the spec above). `artifacts/` is where a driving
session may choose to save probe output (`pane.log`, session-state copies)
— nothing writes there automatically.
