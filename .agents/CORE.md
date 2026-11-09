# Working on academicOps

This repository contains the `academicOps` (`aops`) framework--an agentic workflow harness designed to support high-integrity academic and technical research.

## Where things are

[`specs/ARCHITECTURE.md`](../specs/ARCHITECTURE.md) is authoritative for the
repository layout, the plugin set, the hook set, the build stages, and the
binding constraints on all of them. Read it before scoping any change. Do not
restate it anywhere.

Design intent for anything else: [`specs/README.md`](../specs/README.md).

## Binding constraints

The axioms in [`plugins/rbg/skills/axioms/`](../plugins/rbg/skills/axioms/) apply here as they do everywhere.
On top of them:

- **Integration base branch**: Active development and PRs target `dev`. All workflows resolve the active base branch from this definition; PRs targeting alternative branches must be retargeted.
- **Pre-approval PR readiness and landing**: Under feature freeze, PRs requiring user approval must be green and independently reviewed, with review feedback addressed, before approval; mergeability is not required before approval. Do not rebase or resolve merge conflicts before approval. Bringing a PR up to date with its base branch and resolving conflicts happens after approval, just before merge.
- **No duplication.** Anything two plugins need lives in `lib/` and is injected
  at build time. A second copy is a build failure.
- **No defaults.** No endpoint, URL, host, path, token, or credential appears in
  a shipped artifact. Every such value comes from the environment or client
  `userConfig`.
- **A plugin never reads another plugin's files.** It may read `lib/`.
- **Installed runtime plugins are strictly read-only.** Never write to or edit `~/.gemini/config/plugins/` or `~/.claude/plugins/`. All modifications belong in the source repository.
- **Never edit a tracked file through a shell.** No heredoc, `python3 -c`,
  `sed -i`, or `awk`. Use Read/Write/Edit. If they cannot do it, stop and report.
- **Scratch files go in the repo's own `scratch/` directory, never in `/tmp` or the harness scratchpad.** The auto-mode classifier sends the user a permission prompt for every Bash call that reads or writes outside the working directory; that includes the premise-check recorder's `--reason-file` and any argdown file the parser validates. Write the file with the Write tool, then run the recorder or parser as one plain command on one file: no heredocs, `for` loops, `sed`, or `find -exec`, which the classifier cannot read and also sends to the user.
- **Commit immediately, and push.** After any change, commit with a short,
  descriptive message -- this container is ephemeral and uncommitted work
  disappears with it. Never write `.bak`/`.orig`/copy-suffixed files; git
  already keeps every version.
- **Fail fast.** A documented path that does not exist, a tool that does not
  behave as documented, an acceptance criterion you cannot meet as written -- stop
  and report. Do not substitute an adjacent action you can perform.
- **The user already knows.** They wrote this. Do not explain their own system
  back to them, restate what they just said, or re-justify a decision they have
  made. Report what they do not already have: what you found, what is false, what
  you changed.
- **Don't be so eager: answer what was asked, then stop.** In conversation
  or task execution, do not pre-empt the next question or task, propose
  next steps, offer unasked recommendations, or open a design fork they
  have not reached. They set the pace. One thing at a time, and hold.
- **Direct user instructions carried out as ordered**: Agents carry out direct user instructions without merit re-ruling or second-guessing, even when disagreeing with user reasoning or when approvals are weakened. Whether executed work adheres to user instructions is evaluated exclusively by `rbg` compliance review judged against what was asked, never by coordinating agents on the merits.
- **Intake contract.** On receiving a direction or work brief, the receiving agent must record its own summary stating deliverables as a frozen `## Acceptance` checklist before work starts. For autonomous tracked tasks, this checklist is recorded on the PKB task. In interactive sessions, strictly one outer task is created solely by Face Ida; internal subagents, downstream delegates, and pure lookup tasks/questions do NOT create additional tasks on the PKB graph.
- **Subagent brief verification on Turn 1**: When a subagent receives an incoming brief or direction, it must verify on Turn 1 that required inputs, target artifacts, task ID, and context are present. If required inputs or artifacts are absent, the subagent must immediately return `REVISE` via `send_message` to the caller naming the missing inputs, without invoking `verdict.py` (which is reserved for evidence-backed report checking).
- **No local transcript or hook log scraping**: Agents must never scrape or read local `.system_generated/logs/transcript*.jsonl` or `/tmp/aops_debug_hooks_*.jsonl` files when investigating session state, prompts, or tool execution. All session execution records and prompt histories must be queried from Arize Phoenix via `ida:session-trace`.
- **Substantial in-session tasks**: When an interactive session receives a substantial task directly in session without an existing minted task (anything more complex than a simple question or lookup), Face Ida creates strictly one outer task on the PKB graph: (a) searching the PKB for existing or overlapping tasks; (b) using `/q` to place the user's ask; (c) invoking `/workflow-library` to compose the task; and (d) running the outer `/dump` handover on completion. Internal subagents and delegates execute within this outer task without minting child tasks.
- **Coordinator session boundaries**: Coordinator and interactive agents are strictly prohibited from running expensive test suites (`uv run pytest`, `make test`, etc.) or large repository code greps/scans in-session. Any task requiring code inspection, repository search sweeps, build runs, or test execution must be delegated to isolated worker containers (`polecats`).
- **A fail from an expert reviewer is a fail.** When combining verdicts across expert review lenses (such as in `/strategic-review` or supervisor arbitration), any expert reviewer's `FAIL` makes the combined verdict `FAIL`. The consolidating agent must never downgrade, soften, or overrule an expert's `FAIL`. If an expert reviewer is judged too harsh, that is the user's job to address by reviewing the underlying review agent, not the consolidating agent's job to soften.

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

- NEVER create git worktrees or clones inside the repository or under `.agents/`. Use `$POLECAT_HOME/worktrees` instead.
