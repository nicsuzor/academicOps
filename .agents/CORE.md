# Working on academicOps

You are working on the framework's own source. These rules bind.

## Where things are

[`specs/ARCHITECTURE.md`](../specs/ARCHITECTURE.md) is authoritative for the
repository layout, the plugin set, the hook set, the build stages, and the
binding constraints on all of them. Read it before scoping any change. Do not
restate it anywhere.

Design intent for anything else: [`specs/README.md`](../specs/README.md).

## Binding constraints

The axioms in [`lib/axioms/`](../lib/axioms/) apply here as they do everywhere.
On top of them:

- **No duplication.** Anything two plugins need lives in `lib/` and is injected
  at build time. A second copy is a build failure.
- **No defaults.** No endpoint, URL, host, path, token, or credential appears in
  a shipped artifact. Every such value comes from the environment or client
  `userConfig`.
- **Instructions are operative.** Agent, skill, and command files say what to do
  now — no history, rationale, changelogs, deprecation notices, backwards-compat
  notes, or decision logs. Explanation goes in `specs/`.
- **A plugin never reads another plugin's files.** It may read `lib/`.
- **Installed runtime plugins are strictly read-only.** Never write to or edit `~/.gemini/config/plugins/` or `~/.claude/plugins/`. All modifications belong in the source repository.
- **Never edit a tracked file through a shell.** No heredoc, `python3 -c`,
  `sed -i`, or `awk`. Use Read/Write/Edit. If they cannot do it, stop and report.
- **Commit immediately, and push.** After any change, commit with a short,
  descriptive message — this container is ephemeral and uncommitted work
  disappears with it. Never write `.bak`/`.orig`/copy-suffixed files; git
  already keeps every version.
- **Fail fast.** A documented path that does not exist, a tool that does not
  behave as documented, an acceptance criterion you cannot meet as written — stop
  and report. Do not substitute an adjacent action you can perform.
- **Nic already knows.** He wrote this. Do not explain his own system back to
  him, restate what he just said, or re-justify a decision he has made. Report
  what he does not already have: what you found, what is false, what you changed.
- **Answer the question asked, then stop.** In conversation, do not pre-empt the
  next question, propose the following three steps, or open a design fork he has
  not reached. He sets the pace. One thing at a time, and hold.

Project-local rules: [`rules/RULES.md`](rules/RULES.md).

## Build and test

```bash
make build          # assemble dist/ for every plugin, both clients
make install-dev    # build, then install dist/ as the local 'aops' marketplace
make uninstall-dev  # restore the released marketplace
make test           # uv run pytest tests/
make lint           # ruff check + documented-reference check + basedpyright
make format         # ruff format + dprint fmt
```

Run `make format` before committing. Pre-commit runs `dprint fmt` over markdown,
JSON, and TOML files; and `uv run ruff format` / `uv run ruff check --fix` for Python files.

## Workspaces and worktrees

- NEVER create git worktrees, clones, or scratch directories inside the repository or under `.agents/`. Use `$POLECAT_HOME/worktrees` instead.
