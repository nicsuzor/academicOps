# Contributing

How academicOps itself is developed — repo setup, tests, and the release path. Researchers installing the plugin for their own work want [`README.md`](README.md) (repo root); this doc is for people developing academicOps.

## Development setup

```bash
git clone git@github.com:nicsuzor/academicOps.git && cd academicOps
uv sync                    # install dependencies
make install-hooks         # activate pre-commit hooks
```

Or use `make install-dev` to build, install the plugin locally, and activate hooks in one step.

Run `./scripts/format.sh` manually before committing if pre-commit hooks aren't firing.

## Testing and release

```bash
uv run pytest                              # fast unit tests (default, CI)
make build                                 # build Docker image
uv run pytest -m slow -n 0 --timeout=300   # container e2e + live session tests
```

Before releasing, build the image and run slow tests on a Docker-capable host. Releases are cut via release-please PRs on `dev`.

For how plugin artifacts are built, packaged per platform, and what goes where, see [`aops-core/BUILD.md`](aops-core/BUILD.md). For the full release/publish pipeline, see [`RELEASING.md`](RELEASING.md).

## Pull requests

A PR that touches an enforcement mechanism must include a Cost-Benefit Analysis in the PR body — see [`specs/enforcement/enforcement.md`](specs/enforcement/enforcement.md) §4.1 for the CBA template and [`aops-core/skills/strategic-review/review-contexts/pr-framework.md`](aops-core/skills/strategic-review/review-contexts/pr-framework.md) for what counts and how it's checked.
