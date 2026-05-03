# Agent Compliance Matrix — four-axes permissions audit

**Audit date:** 2026-05-03
**Branch:** `crew/michelle`
**Auditor:** michelle (read-only)
**Specs applied:**

- `agent-permissions` (PKB id `agents-f552b6c1`) — four-axes deny-by-default frontmatter schema (`tools`, `mcp_servers`, `bash_scopes`, `file_access`).
- `skill-delegation` (PKB id `skill-delegation`) — agent ↔ skill symmetry, optional `skills:`/`subagents:` lists on the agent side.

This document is a **point-in-time compliance matrix** for the eight agent files listed below. It is intended to drive the remediation commits the orchestrator schedules after this audit lands. It does NOT modify any agent files; it only diagnoses and prescribes.

The four-axes schema is **deny-by-default**:

1. `tools:` — explicit tool allowlist. Empty = no tool calls.
2. `mcp_servers:` — optional whole-server convenience grants.
3. `bash_scopes:` — REQUIRED when `Bash ∈ tools`. Named families (`git:read`, `git:write`, `gh:read`, `gh:write`, `pytest`, `ruff`, `fs:read`, `fs:write`, `net:http`, `pkg:install`, `docker`). Sentinel `unrestricted` is allowed for orchestrators but is **WARN-level**.
4. `file_access:` — REQUIRED when any of `Read | Write | Edit | NotebookEdit | Glob | Grep ∈ tools`. Has `read:` and `write:` glob lists; `!` prefix denies an override.

Lint rules:

- **ERROR** — `Bash ∈ tools` without `bash_scopes`.
- **ERROR** — any filesystem tool (`Read|Write|Edit|NotebookEdit|Glob|Grep`) without `file_access`.
- **WARN** — `bash_scopes: [unrestricted]`.
- **ERROR** — skill ↔ agent symmetry: any skill `S` with `S.callable-by` listing agent `A` requires `S ∈ A.skills`. Agents that lack a `skills:` list cannot satisfy this rule.

## Section 2: Compliance summary

| Agent       | Has `tools:` |  `Bash`?  | `bash_scopes:` | FS tools?                     | `file_access:` | `mcp_servers:` | `skills:` | `subagents:` |          Verdict          |
| ----------- | :----------: | :-------: | :------------: | ----------------------------- | :------------: | :------------: | :-------: | :----------: | :-----------------------: |
| james       |     yes      |    yes    |     **no**     | Read                          |     **no**     |       no       |  **no**   |    **no**    |           FAIL            |
| pauli       |     yes      |    no     |      n/a       | Read                          |     **no**     |       no       |  **no**   |    **no**    |           FAIL            |
| rbg         |     yes      |    no     |      n/a       | Read, Grep, Glob, Edit, Write |     **no**     |       no       |  **no**   |    **no**    |           FAIL            |
| marsha      |     yes      |    yes    |     **no**     | Read                          |     **no**     |       no       |  **no**   |    **no**    |           FAIL            |
| jr          |     yes      |    yes    |     **no**     | Read, Write, Edit, Glob, Grep |     **no**     |       no       |  **no**   |    **no**    |           FAIL            |
| merge-prep  |   no (n/a)   | n/a (GHA) |      n/a       | n/a (GHA)                     |      n/a       |      n/a       |    n/a    |     n/a      | EXEMPT (different format) |
| pr-reviewer |   no (n/a)   | n/a (GHA) |      n/a       | n/a (GHA)                     |      n/a       |      n/a       |    n/a    |     n/a      | EXEMPT (different format) |
| qa          |   no (n/a)   | n/a (GHA) |      n/a       | n/a (GHA)                     |      n/a       |      n/a       |    n/a    |     n/a      | EXEMPT (different format) |

Five of the eight files audited fail the four-axes schema. Three (`.github/agents/*.agent.md`) are GitHub Actions-runner agents that use a different frontmatter format and are excluded from strict compliance — see Section 4.

## Section 3: Per-agent findings

### james

- **File:** `/workspace/aops-core/agents/james.md`
- **Frontmatter fields present:** `name`, `description`, `model`, `color`, `tools`
- **Tools declared:** `Read`, `Bash`, `Agent`, `Skill`, plus 16 `mcp__plugin_aops-core_pkb__*` MCP tools.
- **Body claims that drive scope inference:** "Commission agents" via `Agent`; uses PKB MCP tools heavily; closes loop on merged PRs by searching task graph; references `mcp__pkb__complete_task`. Body does not call `git`, `gh`, `pytest`, `ruff`, or shell commands directly — Bash usage is implicit/orchestration-only (delegating to subagents that themselves shell out).

**Violations**

1. **ERROR — missing `bash_scopes`.** `Bash ∈ tools` requires `bash_scopes`. Currently absent.
2. **ERROR — missing `file_access`.** `Read ∈ tools` requires `file_access`. Currently absent.
3. **ADVISORY — missing `subagents:` declaration.** Body explicitly commissions `rbg`, `pauli`, `marsha`. The agent should declare `subagents: [rbg, pauli, marsha]` so the symmetry can be checked.
4. **ADVISORY — missing `skills:` declaration.** Body uses `Skill` tool implicitly via "load relevant context descriptor" but does not call out specific skills. If skills declare `callable-by: [james]` they cannot be reconciled.

**Recommended remediation** (concrete additions):

```yaml
bash_scopes: [unrestricted]   # WARN-level: james is the orchestrator and shells out only via subagents; unrestricted is the honest declaration. If the lint enforces tighter scopes, downgrade to [git:read, gh:read] — james itself does not write to the working tree.
file_access:
  read: ['**/*']              # orchestrator needs broad read to inspect any artifact under review
  write: []                   # james never writes — synthesis only; subagents fix
mcp_servers: [aops-core_pkb]   # convenience grant since 16 of its tools are this server
subagents: [rbg, pauli, marsha]
skills: []                    # populate as skills declare callable-by: [james]
```

Rationale: orchestrator role; body explicitly says "You synthesise. You do not implement either" → `write: []`. Read scope is broad because reviews can target any file in the repo.

### pauli

- **File:** `/workspace/aops-core/agents/pauli.md`
- **Frontmatter fields present:** `name`, `description`, `color`, `model`, `tools`
- **Tools declared:** `Read`, `Skill`, plus 16 `mcp__plugin_aops-core_pkb__*` MCP tools.
- **Body claims that drive scope inference:** Reads `.agents/CORE.md`, `.agents/context-map.json`, spec dirs; queries PKB; never edits files (PKB curation goes through MCP, not `Write`). Strategic Review output is text returned to caller. No `Bash`, no shell.

**Violations**

1. **ERROR — missing `file_access`.** `Read ∈ tools` requires `file_access`. Currently absent.
2. **ADVISORY — missing `skills:` declaration.** Body says "use `Skill`" but does not enumerate which skills pauli is permitted to invoke.

**Recommended remediation:**

```yaml
file_access:
  read: ['**/*']              # body reads .agents/, spec_dirs (variable), source artifacts under review
  write: []                   # pauli never writes to the filesystem; PKB writes go through MCP tools
mcp_servers: [aops-core_pkb]
skills: [remember, planner, strategic-review]   # body cites [[remember]] and the strategic-review pattern; planner is the skill the role is built around
```

Rationale: body explicitly references `remember`, `planner`, and the Strategic Review skill. No bash, no fs writes — PKB-only writes.

### rbg

- **File:** `/workspace/aops-core/agents/rbg.md`
- **Frontmatter fields present:** `name`, `description`, `color`, `model`, `tools`
- **Tools declared:** `Read`, `Grep`, `Glob`, `Edit`, `Write`, plus 6 PKB MCP tools.
- **Body claims that drive scope inference:** Reads PR diff and axioms; "Where the correction is clear, you MUST attempt the fix yourself" — actively edits files. No `Bash` declared (cannot run `git`/`gh`); cannot apply mechanical fixes that require shell. No `Agent` tool — cannot delegate.

**Violations**

1. **ERROR — missing `file_access`.** Five filesystem tools declared (`Read`, `Grep`, `Glob`, `Edit`, `Write`) but no `file_access`.
2. **CONSISTENCY — body/tool mismatch.** Body says "fix what you can" (mechanical edits) but lacks `Bash`. If the fix is "rename in 5 files", that's an `Edit`-only operation and is fine; but reordering imports / running formatters is not possible. Acceptable trade-off (rbg is intentionally non-shelling), document explicitly.
3. **ADVISORY — missing `skills:`/`subagents:`.** rbg is invoked by james and by marsha (per marsha's body). Cannot satisfy symmetry from the rbg side, but symmetry is bidirectional only on the agent side; the absence is just structural — note for downstream lint.

**Recommended remediation:**

```yaml
file_access:
  read: ['**/*']                              # rbg reads any file under review (axioms, source, configs)
  write:
    - '**/*.md'                               # axiom-driven mechanical fixes typically land in markdown agent/skill files
    - '**/*.py'                               # source-code fixes for clear violations
    - '**/*.yaml'
    - '**/*.yml'
    - '**/*.json'
    - '!**/.env*'                             # deny override on credentials
    - '!**/secrets/**'
mcp_servers: [aops-core_pkb]
skills: []
```

Rationale: rbg is empowered to fix; write list is broad over text/source. Deny-overrides on `.env` / `secrets` enforce the credential-isolation principle (P#51) at the schema layer.

### marsha

- **File:** `/workspace/aops-core/agents/marsha.md`
- **Frontmatter fields present:** `name`, `description`, `model`, `color`, `tools`
- **Tools declared:** `Read`, `Bash`, `Skill`, 19 `mcp__playwright__*` browser tools, 9 PKB MCP tools.
- **Body claims that drive scope inference:** Runs tests; "she is expected to USE [browser and shell] them"; runs shell to execute tests, run dev servers, exercise CLIs; explicitly says "Modify code yourself — report only" so writes are forbidden by role; delegates compliance to `rbg` via Agent tool — but **`Agent` is NOT in tools**, this is a body/tools mismatch.

**Violations**

1. **ERROR — missing `bash_scopes`.** `Bash ∈ tools` requires `bash_scopes`.
2. **ERROR — missing `file_access`.** `Read ∈ tools` requires `file_access`.
3. **CONSISTENCY — body says "delegate to rbg" via `Agent(subagent_type='aops-core:rbg', ...)` but `Agent` is not in tools.** Either add `Agent` to tools or remove the delegation paragraph. Flagged for orchestrator decision.
4. **ADVISORY — missing `subagents:` declaration.** Body invokes `rbg`.

**Recommended remediation:**

```yaml
tools:
  - Read
  - Bash
  - Skill
  - Agent                                      # required by body's delegation-to-rbg flow
  - ... (existing playwright + pkb tools)
bash_scopes:
  - pytest                                     # core: run test suite
  - ruff                                       # secondary lint runs in QA
  - fs:read                                    # ls/find/cat of artifacts under test
  - net:http                                   # spin up local servers, hit them with curl/httpie
  - pkg:install                                # uv run / npm install when the suite needs dependencies
  - git:read                                   # gh pr view / git log to scope the diff
  - gh:read
file_access:
  read: ['**/*']                              # QA can read anything the PR touches
  write: []                                   # body explicitly says "Modify code yourself — report only"
mcp_servers: [playwright, aops-core_pkb]
subagents: [rbg]                              # body delegates compliance to rbg
skills: [qa]
```

Rationale: marsha needs to run tests and dev servers but never writes source. Agent + subagents declaration closes the body/tools mismatch.

### jr

- **File:** `/workspace/aops-core/agents/jr.md`
- **Frontmatter fields present:** `name`, `description`, `model`, `color`, `tools`
- **Tools declared:** `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`, `Skill`, `Agent`, plus 30+ PKB MCP tools.
- **Body claims that drive scope inference:** General-purpose framework assistant. Reads `.agents/CORE.md`, `VISION.md`, PKB; updates `.agents/CAPABILITIES.md`; routes to specialist skills/agents; explicitly forbids "personal memory files outside [PKB]". Body explicitly carves out write access to `.agents/CAPABILITIES.md` and forbids editing other `.agents/*` instruction docs.

**Violations**

1. **ERROR — missing `bash_scopes`.** `Bash ∈ tools`, no scopes.
2. **ERROR — missing `file_access`.** Five FS tools declared.
3. **ADVISORY — missing `skills:` and `subagents:`.** Body's routing table enumerates them: skills `aops`, `planner`, `qa`, `research`, `dump`, `daily`; agents `james`, `rbg`, `marsha`, `pauli`. Should be declared.

**Recommended remediation:**

```yaml
bash_scopes:
  - git:read
  - gh:read                                    # body queries the framework state, doesn't push
  - fs:read
  - fs:write                                   # for the .agents/CAPABILITIES.md carve-out only — capped via file_access below
file_access:
  read: ['**/*']
  write:
    - '.agents/CAPABILITIES.md'                # body explicitly authorises this
    - '.agents/README.md'                      # body says "add a one-line pointer ... from .agents/README.md"
    - '!.agents/CORE.md'                       # body forbids: "Don't edit these yourself unless /learn directs you to"
    - '!.agents/BUTLER.md'
    - '!.agents/rules/**'
mcp_servers: [aops-core_pkb]
subagents: [james, rbg, marsha, pauli]
skills: [aops, planner, qa, research, dump, daily, remember]
```

Rationale: body carves out write narrowly to two inventory docs; everything else is read-only. The deny overrides codify the body's instruction. No `git:write` because jr explicitly delegates implementation to specialists.

### merge-prep, pr-reviewer, qa (`.github/agents/*.agent.md`)

- **Files:**
  - `/workspace/.github/agents/merge-prep.agent.md`
  - `/workspace/.github/agents/pr-reviewer.agent.md`
  - `/workspace/.github/agents/qa.agent.md`
- **Frontmatter fields present:** `name`, `description` only. No `model`, `color`, `tools`, `bash_scopes`, `file_access`, `mcp_servers`.
- **Body claims:** All three run inside GitHub Actions runners. They invoke `gh`, `git`, `git merge`, `gh pr review`, `pytest`, `ruff`, dev-server processes, browser tooling. They have direct shell access with whatever the GHA runner permits.

**Assessment:**

The `.github/agents/*.agent.md` files are a **different format** from the local Claude Code harness agent files. They are consumed by GitHub Actions workflows (e.g. `agent-merge-prep.yml`) which provide their own shell, runner, environment, and credentials (`GH_TOKEN`, `AOPS_BOT_GH_TOKEN`). Their permissions are governed by:

- The GHA workflow's `permissions:` block (statuses, contents, pull-requests, etc.)
- The runner's installed toolchain
- The bot PAT scopes

The four-axes schema in `agents-f552b6c1` is for the local Claude Code harness, where the harness itself enforces the allowlist. The GitHub Actions wrapper has no equivalent runtime hook to consume `tools:`/`bash_scopes:` — the workflow YAML is the enforcement surface there.

**Recommendation:** **Exclude these three files from strict four-axes compliance**, with two caveats worth flagging:

1. The current frontmatter is minimal (`name` + `description`). If a future lint rule extends the four-axes schema to GHA agents, these files will need an upgrade pass — but that should be coordinated with the workflows that invoke them (`agent-merge-prep.yml`, `agent-pr-review.yml`, `agent-qa.yml`).
2. The bodies of all three explicitly enforce **A13 (Rule Against Perpetuities)** — bounded polling, no `--watch`, reap backgrounded PIDs. This is a runtime convention not captured in the four axes; consider whether it should land in `bash_scopes` semantics (e.g., a `bash:bounded` constraint).

If/when the schema is extended to GHA agents, sketch frontmatter would be:

```yaml
# merge-prep
bash_scopes: [git:read, git:write, gh:read, gh:write, pytest, ruff, fs:read, fs:write]
file_access:
  read: ['**/*']
  write: ['**/*', '!.env*', '!secrets/**']

# pr-reviewer
bash_scopes: [git:read, git:write, gh:read, gh:write, pytest, ruff]
file_access:
  read: ['**/*']
  write: ['**/*', '!.env*', '!secrets/**']

# qa
bash_scopes: [git:read, gh:read, gh:write, pytest, net:http, pkg:install]
file_access:
  read: ['**/*']
  write: []                                     # body: "Never modify code"
```

But until the schema is extended to the GHA surface, these files **PASS by exemption** rather than by structural compliance.

## Section 4: Aggregate stats

- **Total agents audited:** 8
- **In-scope (local Claude Code harness):** 5 — `james`, `pauli`, `rbg`, `marsha`, `jr`
- **Out-of-scope / different format (GHA):** 3 — `merge-prep`, `pr-reviewer`, `qa`
- **In-scope verdict counts:**
  - PASS: 0
  - WARN: 0
  - FAIL: 5
- **GHA verdict:** EXEMPT (3)

### Most common missing field

**`file_access:`** — missing on every in-scope agent (5/5). All five declare at least one filesystem tool, and none declare a `file_access` block. This is the single biggest mechanical remediation pass: every in-scope agent needs the block, and the body of each agent unambiguously dictates the scope (broad read, narrow write — orchestrators write nothing; rbg writes broadly with credential deny-overrides; jr writes only to two inventory paths; pauli/marsha write nothing).

The next most common gap is **`bash_scopes:`** — missing on every agent that declares `Bash` (3/3 of `james`, `marsha`, `jr`).

### Notes on `.github/agents/` files

The three `.github/agents/*.agent.md` files use a **deliberately minimal frontmatter** (`name`, `description` only). They:

- Are consumed by GitHub Actions workflows (`agent-merge-prep.yml`, etc.), not the local Claude Code harness.
- Have their permissions governed by the workflow YAML's `permissions:` block and the runner's bot PAT, not by the four-axes schema.
- Do enforce a runtime convention (A13: bounded polling, reap PIDs) that the four-axes schema does not currently capture.

**Recommendation:** treat them as a separate compliance surface. Either (a) extend the four-axes schema with a `runtime: github-actions` flag that relaxes the `tools`/`bash_scopes` requirements in favour of the workflow YAML; or (b) leave them out of the lint scope entirely. This audit excludes them from strict compliance pending an explicit framework decision.

### Surprises / non-obvious findings

1. **marsha's body says "delegate to rbg via `Agent(...)`" but `Agent` is not in marsha's `tools`.** This is a latent bug — invocation will fail at runtime. The remediation must add `Agent` to tools, not just add the four-axes blocks.

2. **rbg is empowered by its body to fix mechanical violations but cannot run any shell commands** (no `Bash` in tools). This is by design (rbg is an Edit-only judge), but it bounds the kinds of "mechanical fix" rbg can apply — string-level edits only, no `ruff format`, no `git mv`. Worth surfacing to the framework owner: is this intended, or should rbg get `bash_scopes: [ruff, git:read]`?

3. **Every in-scope agent uses the same PKB MCP server** but none declare `mcp_servers: [aops-core_pkb]`. The convenience grant is consistently underused; remediation can collapse the per-tool allowlists where appropriate (or leave them explicit if fine-grained MCP allowlisting is preferred).

4. **No agent declares `skills:` or `subagents:`**, which means the symmetry rule from `skill-delegation` is unenforceable in either direction today. This is a structural gap, not a per-agent failure — the lint rule needs the agent-side lists to exist before it can check anything.

---

End of audit. Remediation commits should apply the per-agent `Recommended remediation` blocks above mechanically; the `.github/agents/*` decision (exempt vs extend) is a framework-level call that should be made before any work on those files.
