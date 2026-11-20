# Working on academicOps

This repository holds the `academicOps` (`aops`) framework.

## Orientation

- Architecture, plugin layout, hooks, and build stages: [`specs/ARCHITECTURE.md`](../specs/ARCHITECTURE.md) (read before scoping changes; never restate it)
- Design specifications: [`specs/README.md`](../specs/README.md)
- Project-local rules: [`.agents/rules/`](rules/) (applied on top of [`plugins/rbg/skills/axioms/`](../plugins/rbg/skills/axioms/))

## Repository Constraints

- **Integration base branch**: Active development and pull requests target `dev`; retarget PRs pointing elsewhere.
- **Pre-approval PR readiness**: Under feature freeze, PRs must pass checks and independent review with feedback addressed before approval; rebase and resolve merge conflicts after approval, just before merge.
- **Shared plugin code**: Code used by more than one plugin lives in `lib/` and is injected at build time; duplicate copies fail the build.
- **Plugin isolation**: A plugin never reads another plugin's files (only `lib/`).
- **No hardcoded defaults**: Endpoints, URLs, hosts, paths, tokens, and credentials come from the environment or client `userConfig`, never hardcoded in shipped artifacts.
- **Installed runtime plugins are read-only**: Never modify `~/.gemini/config/plugins/` or `~/.claude/plugins/`; edit only the source repository.
- **Scratch files**: Write scratch and temporary validation files inside `scratch/`, never `/tmp` or external scratchpads.
- **Workspaces and worktrees**: Create git worktrees and clones under `$POLECAT_HOME/worktrees`, never inside the repository or `.agents/`.

## Build and Test

```bash
make build          # assemble dist/ for every plugin, both clients
make install-dev    # build and install dist/ as local development marketplace
make uninstall-dev  # restore the released marketplace
make test           # run pytest suite
make lint           # ruff check, documented-reference check, basedpyright
make format         # ruff format and dprint fmt
```

Run `make format` before committing.
