# Install academicOps

Quick pointers to get the framework running. This file is the entry point
doc-taxonomy.md expects at the repo root — design detail (what each install
path does and why) lives in [`specs/build-and-install.md`](specs/build-and-install.md)
and isn't restated here.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview)
- GitHub CLI (`gh`) for artifact retrieval
- Docker (optional — required only for polecat's sandboxed worker containers)

## Quick install

```bash
claude plugin marketplace add nicsuzor/academicOps@dist
claude plugin install aops@academicOps
```

Optional plugins (`aops-jr` for face discipline, `reflexes-cope` for advisory
policy checks, `aops-tools` for domain skills) install the same way — see
`specs/build-and-install.md` §2 for the full plugin list and what each one
ships, and §5.6 for the plugin → surface matrix.

## Polecat installation

Polecat is the containerized worker-dispatch CLI, shipped inside `aops` core
(`aops/polecat/cli.py`) rather than as a separate plugin. Beyond the base
install above, it needs Docker and a `polecat.yaml` project registry
(`$AOPS_SESSIONS/polecat.yaml`) — see the environment variables table in
[`README.md`](README.md#configuration). Dispatch invocation, build, and
configuration detail live in
[`specs/build-and-install.md`](specs/build-and-install.md); the canonical
dispatch flow is documented in
[`aops/skills/dispatch/SKILL.md`](aops/skills/dispatch/SKILL.md).

## Developer / local build

Building from source, the `make dev` / `make install` loop, and the full
release pipeline are covered in
[`specs/build-and-install.md`](specs/build-and-install.md). Contributing to
the framework itself starts at [`CONTRIBUTING.md`](CONTRIBUTING.md).
