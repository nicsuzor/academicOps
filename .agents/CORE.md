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
- **Never edit a tracked file through a shell.** No heredoc, `python3 -c`,
  `sed -i`, or `awk`. Use Read/Write/Edit. If they cannot do it, stop and report.
- **Never modify files outside this repository.** Found a bug upstream? Report it.
- **Commit immediately, and push.** After any change, commit with a short,
  descriptive message — this container is ephemeral and uncommitted work
  disappears with it. Never write `.bak`/`.orig`/copy-suffixed files; git
  already keeps every version.
- **Fail fast.** A documented path that does not exist, a tool that does not
  behave as documented, an acceptance criterion you cannot meet as written — stop
  and report. Do not substitute an adjacent action you can perform.
- **A defect is never a rule.** Do not write "avoid X" into any instruction,
  comment, contract or test because X is currently broken. Guidance outlives the
  bug it was written for: the next reader takes the detour as the design, stops
  asking why, and the capability is gone without anyone deciding to drop it.
  Broken things get an issue, a dated note that names it, and a mitigation
  labelled as temporary at the point of the mitigation. Parity between clients is
  owed until it is met — a surface that works on one client and not the other is
  an open defect, never the shape of the system.
- **Verify before asserting.** Every factual claim in a doc or instruction must be
  true of the tree as it is. A doc that lies is worse than no doc.
- **Verbatim proof.** Any claim of success, state change, test pass, or task
  completion must be accompanied by a verbatim extract of the output (stdout/stderr,
  log snippet, or state query) that proves the claim. Do not assert success
  without falsifiable evidence.
- **Proof comes from a channel the subject cannot author.** A verbatim quote of
  an agent saying it did something proves only that it said so. Asked for a
  server's output, an agent will find that output in a file — the logs your own
  probing wrote are the likeliest source — and report it as its own. The
  contamination compounds: each run leaves the expected answer on disk, so later
  runs pass more readily than earlier ones and a surface that never worked reads
  as fixed. Score the instrumented record instead: the tool-call entry, the
  request the server logged, the state that changed. Where you must ask the
  subject, ask what it cannot fabricate consistently — its own capability list,
  not a value.
- **Outcome-oriented delegation.** When delegating tasks to subagents, specify
  _what_ needs to be done and the constraints, not _how_ to do it. Trust
  specialized agents to use their tools and domain knowledge appropriately. Do
  not micro-manage tool selection or execution paths.
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

Headless agy runs use `agy --output-format stream-json -p "<prompt>"`.

**Open defect, 2026-08-07 — no agent parity on agy ([#2387]).** Every agent
_this repo builds_ — james, rbg and pauli were tested — comes up under
`--agent <name>` with a fixed toolset (`find_by_name`, `generate_image`,
`grep_search`, `list_dir`, `read_url_content`, `schedule`, `search_web`,
`send_message`, `view_file`): no `call_mcp_tool`, no write, no shell. An
unnamed agy run gets the full set. So the personas that carry this framework's
doctrine cannot currently run work on agy.

**The cause is not isolated.** It has not been shown to be agy's `--agent`
mechanism: no agy-native or hand-written agent definition was tested, so our
own build adapter is an equally live suspect — in particular the
`includeSections` whitelist injected at `build/clients/agy.py`. That
hypothesis was dismissed earlier on evidence since shown worthless and has
**not** been re-tested. Until the cause is isolated, an agy run that drops
`--agent` is a **temporary mitigation** and the persona it should have had is
still owed. A worker that reads and greps and then dies with
`trajectory converted to zero chat messages` at exit 0 had no write tool — read
that as this defect, not as a crash to retry verbatim.

A worker that has to change anything also wants
`--dangerously-skip-permissions`.

[#2387]: https://github.com/nicsuzor/academicOps/issues/2387

Give a worker its brief in a file and pass a one-line pointer. Long `-p`
prompts are also a way to lose a run, and a brief on disk is the one the next
attempt can re-read unchanged.

Run `make format` before committing. Pre-commit runs `dprint fmt` over markdown,
JSON, and TOML files; and `uv run ruff format` / `uv run ruff check --fix` for Python files.

## Pull requests

Open against `dev`. Bundle an unrelated fix only when it blocks your PR from
merging and it is one sentence to describe; otherwise file it separately.
