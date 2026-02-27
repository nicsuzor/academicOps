# GitHub Agent Templates

Templates for configuring GitHub Copilot coding agent in project repos.

## Files

| File | Destination | Purpose |
| --- | --- | --- |
| `copilot-instructions.md.template` | `.github/copilot-instructions.md` | Project-specific build/test/conventions |
| `copilot-setup-steps.yml.template` | `.github/workflows/copilot-setup-steps.yml` | Environment setup |
| `worker.agent.md` | `.github/agents/worker.agent.md` | Worker persona (copy as-is) |

## Setup for a new repo

1. Copy `worker.agent.md` to `.github/agents/worker.agent.md` (no changes needed).
2. Copy `copilot-setup-steps.yml.template` to `.github/workflows/copilot-setup-steps.yml`.
   Edit the `python-version` if the project uses a different version.
   For repos outside `nicsuzor/academicOps`, the composite action isn't available
   via local path — inline the steps or publish the action to a shared repo.
3. Copy `copilot-instructions.md.template` to `.github/copilot-instructions.md`.
   Fill in the `{{ placeholders }}` with project-specific details.
4. Merge to default branch. Assign `@copilot-swe-agent` to an issue to dispatch.
