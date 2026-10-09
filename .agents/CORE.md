# Working on academicOps

This repository contains the `academicOps` (`aops`) framework—an agentic workflow harness designed to support high-integrity academic and technical research.

## Where things are

[`specs/ARCHITECTURE.md`](../specs/ARCHITECTURE.md) is authoritative for the
repository layout, the plugin set, the hook set, the build stages, and the
binding constraints on all of them. Read it before scoping any change. Do not
restate it anywhere.

Design intent for anything else: [`specs/README.md`](../specs/README.md).

## Binding constraints

The axioms in [`plugins/rbg/axioms/`](../plugins/rbg/axioms/) apply here as they do everywhere.
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
- **The user already knows.** They wrote this. Do not explain their own system
  back to them, restate what they just said, or re-justify a decision they have
  made. Report what they do not already have: what you found, what is false, what
  you changed.
- **Don't be so eager: answer what was asked, then stop.** In conversation
  or task execution, do not pre-empt the next question or task, propose
  next steps, offer unasked recommendations, or open a design fork they
  have not reached. They set the pace. One thing at a time, and hold.

Project-local rules: [`rules/RULES.md`](rules/RULES.md) and [`rules/*.md`](rules/).

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

## Dispatching workers

Dispatch a queued task to an agy polecat through the `polecat` tools on the
`services` MCP portal:

- Call `polecat_run_container` with image `polecat:latest`, a name
  `polecat-<task-id>-<yyyymmdd><letter>`, and labels `aops.dispatched_by` and
  `aops.task`.
- Pass the whole agy command as `command`: the
  [`agy` skill](../plugins/ida/skills/agy/SKILL.md)'s invocation without the
  `tmux` wrapper, with `--add-dir` naming a writable directory for the worker's
  clone and `--print "/ida:pull <task-id>"` last. Leave `POLECAT_TARGET_TASK`
  unset.
- Pass no credential values and mount no workspace. The server supplies the bot
  credentials; the worker clones the repository itself.
- Confirm the start with `polecat_list_containers` and
  `polecat_fetch_container_logs`. A container that exits within seconds with
  empty logs never started: halt and report.
