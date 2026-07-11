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

## Pull requests

Open PRs against `dev`. Structure the PR body as a reviewer-decision aid so the maintainer can decide to approve in ~60s — the required sections (Summary, Posture, Why now / alignment, Change, Risk & blast radius, Sequencing, Verification) live in [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md), which GitHub pre-fills on hand-opened PRs. Polecat workers file their own PR from within their session and are instructed to use the same structure (`polecat/prompt_template.py`), so bot and human PRs read the same way — polecat itself never creates or edits a PR. This is contributor practice, not pipeline semantics — for how a PR is driven to merge, see [`specs/workflows/pr-pipeline.md`](specs/workflows/pr-pipeline.md).

## Testing and release

```bash
uv run pytest                              # fast unit tests (default, CI)
make build                                 # build Docker image
uv run pytest -m slow -n 0 --timeout=300   # container e2e + live session tests
```

Before releasing, build the image and run slow tests on a Docker-capable host. Releases are cut via release-please PRs on `dev`.

For how plugin artifacts are built, packaged per platform, installed (including the `make dev`/`make install` local dev loop), and cleaned up, see [`specs/build-and-install.md`](specs/build-and-install.md). For the full release/publish pipeline, see [`specs/workflows/releasing.md`](specs/workflows/releasing.md).
