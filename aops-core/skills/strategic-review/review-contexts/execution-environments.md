# Execution Environments for Review Agents

Two environments are available for running review agents: GitHub Actions runners and local
polecats. Each has distinct capabilities and constraints. James decides which to use per
agent commission.

## GitHub Actions Runners

Agents run via `anthropics/claude-code-action@v1` on a transient Ubuntu runner.

**Have:**

- Git (full repo checkout, `fetch-depth: 0`)
- `gh` CLI (read PR diffs, post reviews, set commit statuses, push commits)
- File read/write/edit on the checked-out repo
- Bash
- `uv`, Python (if installed in the workflow)

**Don't have:**

- PKB MCP tools (no `pkb-search`, no task graph)
- Zotero, email, or calendar access
- Brain repo access
- aops framework hooks and skills
- Session transcript history
- Access to services on Tailscale

**Constraints:**

- GHA job timeout: typically 10–30 min per job (configurable, hard cap at 6 h)
- No persistent state between runs — each job starts clean
- Agent prompt loaded from a repo file (`.github/agents/`) or fetched via sparse-checkout
- Secrets available: `CLAUDE_CODE_OAUTH_TOKEN`, `AOPS_BOT_GH_TOKEN`

**Can:**

- Push fix commits directly to the PR branch
- Submit PR reviews (`gh pr review --approve` / `--request-changes`)
- Set commit statuses (`gh api repos/.../statuses/...`)
- Run repo test suites (`uv run pytest`)
- Read any file in the checked-out repo

## Local Polecats (Claude Code Sessions)

Agents run via `polecat run` or `start_code_task` dispatch, in a full Claude Code session.

**Have:**

- Full MCP tool access: PKB (`pkb-search`), task graph, memories, semantic search
- Zotero, email, calendar access
- Brain repo (`$ACA_DATA`) and all locally-cloned repos
- aops framework skills and hooks (full session context)
- Session transcript history and knowledge graph
- Git worktree isolation (each task gets a clean branch)
- Can run `cargo`, `npm`, `make`, `docker`, arbitrary local tooling
- Access to services on Tailscale (dev servers, databases, internal APIs)

**Constraints:**

- No hard timeout (but cost-per-token still applies)
- Requires the agent host machine to be running
- Slower dispatch than GHA (polecat startup overhead)

**Can do everything a GHA runner can, plus:**

- Spin up a local dev server and verify runtime behaviour (Marsha pattern)
- Query the PKB for strategic context before reviewing
- Access memories and learnings from prior sessions
- Search the knowledge graph for related decisions and prior art

## When to Use Which

| Need                                              | Use           |
| ------------------------------------------------- | ------------- |
| Lint, type check, pytest                          | GHA runner    |
| Axiom compliance review (rbg / enforcer)          | GHA runner    |
| Code review — diff only (pauli / pr-reviewer)     | GHA runner    |
| Runtime verification (spin up server, click test) | Local polecat |
| Strategic review requiring PKB context            | Local polecat |
| Work that needs framework skills (`/plan`, `/qa`) | Local polecat |
| Anything requiring MCP tools                      | Local polecat |
| Long-running tasks (>30 min)                      | Local polecat |

**Rule of thumb:** If the task only needs the repo diff, use GHA. If it needs context
beyond the repo — runtime, PKB, memory, external services — use a local polecat.
