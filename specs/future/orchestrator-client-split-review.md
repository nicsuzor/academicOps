---
status: draft
tier: 2
type: spec
title: Reconciled review verdict — orchestrator client split
tags: [agents, review, rbg, pauli, polecat, mcp]
created: 2026-08-15
---

# Reconciled review verdict — orchestrator-client-split.md

**Overall: REVISE.** Sections C, D and G survive. Section A (the split) is sent
back for a design decision it does not contain. Section E (the `ida` lockdown) is
blocked on two independently-verified findings. Reviewers: rbg (rule compliance),
pauli (strategic). marsha returned nothing.

**This document supersedes the plan where they conflict.** Item numbers refer to
`plan-james-split.md`.

## Synthesis table

| Agent       | Issue                                                                                         | Feedback                                                                                                                                                                                                                                                                                                                                                                                                                                             | Severity   |
| ----------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| rbg         | **Item 2 — commented `allowedTools` is stripped by the build**                                | Both adapters `yaml.safe_load` → `yaml.safe_dump` (`build/clients/claude.py:129-132`, `agy.py:296-300`). Comments cannot survive; "ready to enable" ships as nothing. Also violates instructions-are-operative (`ARCHITECTURE.md:51-53`).                                                                                                                                                                                                            | **REJECT** |
| rbg         | **`allowedTools` is not in the agent schema at all**                                          | `agent-authority.md:53-79` never lists it; the canonical formula `:190` is `effective = (tools ∪ expand(mcpServers)) ∖ disallowedTools`. The designed field is `subagents` (`:73`, `:229-231`). Affects items 2 and 10 — and `ida.md:6-9` and `pc.md:6-8` are _already_ using a field with no semantics.                                                                                                                                             | **REJECT** |
| rbg + pauli | **Item 3 — sweep list materially incomplete**                                                 | Both found the same gap independently. rbg names 8 further surfaces, pauli names 10; union includes `specs/agents/supervision-split.md:103-104`, `plugins/ida/skills/strategize/SKILL.md:79`, `plugins/ida/README.md` (9 sites), `plugins/orchestrate/README.md` (5), `ENFORCEMENT-MAP.md` (8 rows), `pyproject.template.toml:2`, `plugin.template.json:7`, `tests/test_build.py:429,433`, `build/marketplace.toml`, `lib/polecat/cli.py`.           | **REVISE** |
| rbg         | **Item 3 — `strategic-review` has no correct single answer**                                  | `SKILL.md:10` says "James runs this skill end to end". The skill ships identically to both clients (F5). `james` fans out natively; `jim` shells out. Re-pointing at either is wrong on the other. **Needs a design decision the plan does not contain.**                                                                                                                                                                                            | **REJECT** |
| rbg         | **Item 7 — `--agent none` is a magic value**                                                  | `categorical-imperative.md:10` (a carve-out over a namespace we do not own) and `governing-rules.md:12` (the distinction already exists — `_agent_args` returns `[]` when agent is falsy). Use a paired `--agent/--no-agent` boolean, or set defaults at the call sites.                                                                                                                                                                             | **REJECT** |
| rbg         | **Item 13 — cannot withhold playwright from agy-marsha without a build change**               | The `clients.claude`/`clients.agy` split scopes _server config_; the _grant_ is `marsha.md` frontmatter, and every `agents/*.md` ships to both clients (F5). `build/tools.py:105-111` reads `mcpServers` unconditionally. Plan line 37's "No build change required" is false for item 13, and item 14 has the mirror problem for `james` on claude.                                                                                                  | **REJECT** |
| pauli       | **Item 10 — the gate does not bind**                                                          | `agent-authority.md:163-176`: _"despite `ida.md` declaring `tools: [...]`, the spawned ida's actual top-level set was `Agent, Artifact, Bash, Edit, Read, Skill, ToolSearch, Write` plus the full MCP namespace… no agent's declared allowlist is trustworthy ground truth."_ Item 10 pays R1 in full and buys nothing.                                                                                                                              | **REJECT** |
| pauli       | **Item 10 — `Agent(pc)` is not a resolvable address**                                         | `aops_ba33ec32` (status `ready`, tag `measured`, 100% reproducible across 3 runs): bare `pc`/`pauli` → "Agent type not found"; working forms are plugin-namespaced. Today a wrong guess costs 12–20s and she retries; item 10 leaves nothing to retry onto. **`aops_ba33ec32` must land before item 10.**                                                                                                                                            | **REJECT** |
| rbg + pauli | **Items 9+11 — `pc.md`'s prohibition blocks the rewrite**                                     | `pc.md:17-19`: _"Your ONLY job… You are PROHIBITED from taking any other action… HALT immediately."_ Item 11 routes hydrate/q/brief/enqueue to `pc`; item 9 never touches the prohibition. And the narrowness is a _recorded decision_ — `supervision-split.md:36-38`.                                                                                                                                                                               | **REVISE** |
| pauli       | **Item 5 (`dispatch.sh`) is self-defeating — CUT**                                            | Its rationale is "an instruction to pass a flag is droppable". An instruction to call `dispatch.sh` is exactly as droppable. Item 6 closes the class properly, because no instruction is involved. Also has no shipping path: `lib/polecat/` reaches plugins via explicit `[[shared]]` blocks in `plugin.toml`; no equivalent for `lib/agy/`.                                                                                                        | **REVISE** |
| rbg         | **Items 4+5 violate single-source-of-truth**                                                  | `single-source-of-truth.md:14`: "A principle stated in full in two files… is a violation even while the two copies agree." Moot once item 5 is cut, but item 4 must then be the sole authority for the flag set.                                                                                                                                                                                                                                     | **FIX**    |
| pauli       | **Correction to F2 / `aops_267a459a` — item 6 is NEW work, not an unverified prior decision** | `lib/polecat/cli.py:1331-1335` has **no `default=`**; `_agent_args` returns `[]` when agent is falsy (`:910-913`); the only two `james` strings in the file are error prose (`:848`, `:858`). A dispatched worker today boots as **no agent at all**. Corroborated by `debug/SKILL.md:122`: "agy currently defaults to its base agent". **This strengthens item 6** and makes item 8 harder: it must prove the default both _exists_ and _resolves_. | **FIX**    |
| pauli       | **Correction to F10 — `agy.md` runs nowhere**                                                 | `ls dist/ida-claude/agents/` → `agy.md.disable`, `ida.md`. It ships with the suffix intact; no client loads it. "Already correct" overstates it.                                                                                                                                                                                                                                                                                                     | **FIX**    |
| rbg         | **Item 14 — context7 spec is incomplete**                                                     | Needs the exact shape pkb already ships: `${user_config.*}` for claude, env for agy, a `userConfig` entry with no default, **plus `"mcpServers": "./.mcp.json"` under `clients.claude` in `plugin.template.json`** (orchestrate's is `{}` — config nothing reads), plus `manifestVersion` + `clients` or the build fails. **And context7 is a keyed service — the plan says nothing about the credential, which "no defaults" names verbatim.**      | **REVISE** |
| rbg         | **Item 15 freezes an agy-scoped mitigation as a framework-wide invariant**                    | `rbg/hooks/handlers.py:335-336`: _"This is a mitigation, not the design. The stop gate is owed on both clients."_ Measured harm was agy-specific. Defensible rule: **no handler blocks on agy.** Also must route through `tests/policy.toml` per `.agents/rules/RULES.md:36-39`, not hardcoded Python literals.                                                                                                                                      | **REVISE** |
| rbg         | **Three sources disagree about hook registration — item 15 tests over exactly that surface**  | Code registers `PostToolBatch` + `SubagentStart` (`handlers.py:203-204`); `ARCHITECTURE.md:195,200` says not registered; `tests/policy.toml:29-31` says something third; `lib/hooks/dispatch.py:104-117` `CANONICAL_EVENTS` lacks `SubagentStart` — yet it demonstrably fires. **Reconcile before codifying.**                                                                                                                                       | **REVISE** |
| pauli       | **M1 — `pc`'s tool grant does not cover the command it runs**                                 | `pc.md:6-8` grants `Bash(pc *)`, `Bash(ssh *)`; its documented commands are `uv run python3 …/polecat/cli.py` and `tmux new-session`. No `pc` executable exists anywhere. Invisible today only because allowlists don't bind. Fix inside item 9.                                                                                                                                                                                                     | **REVISE** |
| pauli       | **M5 — stale `dist/` will corrupt the sweep**                                                 | `dist/` is gitignored but on disk with 11 `james`-bearing files. A grep-driven item 3 without a `dist/` exclusion edits files the next `make build` overwrites.                                                                                                                                                                                                                                                                                      | **FIX**    |
| rbg         | **Q1 ruling — cross-plugin MCP naming is ALLOWED**                                            | Naming ≠ reading; `ARCHITECTURE.md:129-130` blesses cross-boundary namespace references. Two conditions: declare the runtime dep in orchestrate's README; **never re-configure `services`** — `plugins/aops/manifest/mcp.template.json` stays sole authority.                                                                                                                                                                                        | **FIX**    |
| pauli       | **M4 — the deciding fact for item 12 is unrecorded**                                          | `build/clients/agy.py:63-67` writes `mcp_config.json` **per plugin**. Whether agy merges plugin MCP configs into one namespace decides item 12, and nothing is recorded. Settle by live call.                                                                                                                                                                                                                                                        | **REVISE** |
| rbg         | **`.agents/rules/RULES.md:15-22` obligation missing from Verification**                       | Items 1,2,4,9,10,11,15 are persona edits / enforcement changes; each requires `specs/enforcement/enforcement.md` updated **in the same PR**.                                                                                                                                                                                                                                                                                                         | **FIX**    |
| pauli       | **Contradicts a `done` node**                                                                 | `aops_e39b6b9d` explicitly excludes from ida: _"Spawning and adjudicating workers… properties of the role, not of the confidence placed in it"_ and _"Writing to the graph — single-writer is what makes it correctable."_ Plan moves in a third direction (neither james nor pauli) that **no recorded decision supports**. Reconcile against it and PR #2446 first.                                                                                | **REJECT** |
| pauli       | **M2 — `ida.md` has drifted since that node**                                                 | It now grants `Agent(pauli)` (`:7`) and instructs "Call `pauli` to hydrate" (`:81`), contradicting `supervision-split.md:105-109` and the node's own recorded observation B1. The plan treats this as a live design choice to revoke rather than **an undocumented regression**.                                                                                                                                                                     | **REVISE** |

## Where the reviewers were working from stale information

Both flagged **F17 / #2387** (`agy --agent` strips MCP) as blocking items 1/6/12/14.
rbg called it "two independent sources on the same defect". **Nic has ruled: this
was proved end to end in the immediately preceding session** — headless
`agy --agent <name> --prompt` confirmed working for filesystem, network and PKB
(commit `250921f8d`).

Direct observation beats a stale doc, so the blocker does not stand. But both
reviewers reaching it independently is itself the evidence for **item 17**: the
stale records are actively misdirecting competent readers. The doc line
(`.agents/skills/debug/SKILL.md:122`) and the four PKB nodes are now the highest-
value part of item 17, not a tidy-up.

Retained from their finding: **item 8's verification must be a tool count plus a
live PKB call from inside the container under `--agent james`, compared against
the same container with no `--agent`.** A resolving agent name is not sufficient
evidence. That was right regardless of #2387.

## Amended plan

**CUT:** item 5 (`dispatch.sh`) — self-defeating and has no shipping path.

**RESOLVED by Nic, 2026-08-15 — items 1–3 are replaced, not sent back.**

**There is no split.** One agent file, `plugins/orchestrate/agents/james.md`, with
client-conditional prose — the shape `plugins/ida/agents/agy.md.disable:11-13`
already uses:

> "## Instructions ONLY for antigravity ('agy') cli or ide agent harnesses
> If you are ALREADY running antigravity / `agy`, just do the work using your
> normal tools. **Ignore the rest of the instructions below.**"

This is pauli's recommendation (§4b) adopted. Consequences:

- **`jim.md` is not created.** Delete it from the design.
- **Item 3's reference sweep is CANCELLED.** Every `james` reference stays
  correct, because there is still exactly one `james`. This dissolves rbg's
  BLOCKING finding on `strategic-review/SKILL.md:10` and pauli's M2 sweep
  finding — both existed only because of the split.
- **The duplicated honesty/hearsay body is avoided**, so `.agents/CORE.md`'s
  no-duplication rule is satisfied by construction rather than by discipline.
- **No build change is needed** for this, which restores the plan's original
  line-37 claim for section A (it remains false for item 13 — see that row).
- **Item 6's per-client default becomes simpler:** both clients default to
  `james`; the one file tells the occupant which half of its instructions apply.

### Superseded again, same day — per-client agent FILES, not conditional prose

Nic's final call: **stop translating difficult frontmatter.** Author the agent as
two files, `plugins/orchestrate/agents/james.agy.md` and `james.claude.md`,
accepting slight body duplication because the launch syntax genuinely differs.
`@ref`-style inclusion of common chunks is acceptable later if wanted.

**Why the split was never really about prose.** The two bodies differ in exactly
one section — how to dispatch. Roughly 55 of `james.md`'s 66 lines are common
(fail-fast, the hearsay rule, the logical-integrity check, the output standard,
PKB discipline). Every recurring failure on this surface has been a _frontmatter
translation_ failure, never a prose failure:

| Key                | agy                | claude       | Failure mode                                                                                                                                                                              |
| ------------------ | ------------------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools:`           | 54-name vocabulary | Claude names | The no-`tools:` fallback emitted `tools: ["*"]`; agy has no converter for `*`, crashing every custom agent (fixed `250921f8d`).                                                           |
| `call_mcp_tool`    | must never appear  | n/a          | Fails executor construction before the model runs, exit 1 (#2422).                                                                                                                        |
| `model:`           | must be dropped    | honoured     | Unrecognised value silently unregisters the agent; `--agent` then falls back to a 56-tool unnamed session — `build/clients/agy.py:271-275`: "a privilege escalation, not a cosmetic bug". |
| `enable_mcp_tools` | agy-only           | meaningless  | Not in the schema either way.                                                                                                                                                             |
| `allowedTools`     | —                  | —            | Not in the schema at all; already shipping in `ida.md`, `pc.md`.                                                                                                                          |

#### This needs a build change, and today it fails silently

Verified: both adapters glob `*.md` only — `build/clients/claude.py:62` and
`build/clients/agy.py:223`, both `agents_dir.rglob("*.md")`. Anything else is
copied through unadapted. Proof it ships as dead weight rather than erroring:

```
dist/ida-claude/agents/  →  agy.md.disable (2.5K), ida.md
dist/ida-agy/agents/     →  agy.md.disable (2.5K), ida.md
```

So `james.agy.md` today would be adapted by neither client and shipped to **both**
as a stray file, with no error.

**Required change (~10 lines per adapter):**

1. Glob `*.md` **plus** this client's suffix (`*.claude.md` / `*.agy.md`).
2. Strip the suffix when writing, so both land as `agents/james.md`.
3. **Delete the other client's suffixed file from the build dir** — without this
   the convention "works" while leaking the other client's agent definition into
   every artifact, exactly as `agy.md.disable` does today.
4. Build error if one name resolves from two sources (`james.md` _and_
   `james.agy.md` both present) — otherwise precedence is undefined.
5. Tests for all four.

#### `@ref` will not work as a build feature

`inject_shared` is `shutil.copy2` / `copytree` (`build/shared.py:105-108`) — whole
files from `lib/` at declared paths. There is **no content-level include anywhere
in the build**. `@path` in `CLAUDE.md` is Claude Code's own runtime import syntax,
not ours, so a shared chunk written that way would resolve on claude and sit as
literal text on agy — a silent divergence in the one file whose purpose is to
differ cleanly between clients. The mechanism that does work on both is a
`[[shared]]` block injecting from `lib/`.

**BLOCKED pending prerequisites:** items 10–11 (the `ida` lockdown). Requires, in
order: `aops_ba33ec32` lands (namespaced agent addresses); reconciliation against
`aops_e39b6b9d` / PR #2446; a decision on `pc.md:19`; and a route that does not
rest on `tools`/`allowedTools`, which `agent-authority.md:163-176` records as
non-binding at runtime.

**PROCEED — wave 1:**

- **6, 7, 8** — per-client polecat default. Item 7 uses `--no-agent`, not
  `--agent none`. Item 8 verifies by live in-container PKB call, not by build.
  Item 6 is new work (pauli's correction); `shell`/`sleep`/passthrough exclusion
  is already structural (`_build_inner_command`), so claim it rather than build it.
- **9** — `pc`'s two modes, **plus** fixing its Bash grant (M1) and the stale
  `plugins/orchestrate/manifest/plugin.toml` path (M6).
- **4** — re-enable `agy.md` (drop `.disable`), sole authority for the flag set.
- **15** — scoped to **"no handler blocks on agy"**, routed through
  `tests/policy.toml`, **after** reconciling the three-way registration drift and
  correcting `ARCHITECTURE.md:195/196/200`.
- **17** — reconcile the stale record. Now high-value, not housekeeping.
- **18** — record the deferred per-branch-container design.

**PROCEED with a probe first — wave 1b:** items 12–14 (MCP). Settle M4 (does agy
merge per-plugin MCP configs?) by live call before writing any grant. Item 13
needs a build change or a different mechanism. Item 14 needs the full template
shape and a credential story.

**Every wave-1 item additionally requires** `specs/enforcement/enforcement.md`
updated in the same PR (`.agents/rules/RULES.md:15-22`).
