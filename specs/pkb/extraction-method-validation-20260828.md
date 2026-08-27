# Validation: 20 worked `dry_run` extractions against the shipped knowledge-extraction method

Evidence for [[aops_extract_inner_wf]]. The method under test is
[`plugins/pkb/skills/remember/references/consolidation.md`](../../plugins/pkb/skills/remember/references/consolidation.md)
(the Four Tests, the Seven Defect Classes) plus the destination-first constraint in
[`plugins/pkb/agents/pauli.md`](../../plugins/pkb/agents/pauli.md). Both files were read in full before
this pass; neither was amended (see **Amendments** at the end).

**Nothing in this file was written to the live PKB.** All 20 extractions below are proposals: what
would be written, and where, if this were a real (non-dry-run) consolidation pass. No `create`,
`update_body`, `batch_*`, `merge_node`, `delete`, or `complete_task` call was made against any real
PKB node during this task. Only read-only tools (`get_task`, `list_tasks`, `search`, `graph_stats`)
were used against the live PKB.

## Non-mutation evidence (criterion 3)

This polecat container has no filesystem access to `/home/nic/brain` — it is not mounted, and the
PKB is reached exclusively through the remote MCP service (`PKB_MCP_URL`). `git -C /home/nic/brain
rev-parse HEAD`, as the dispatch brief specified, therefore cannot be run from inside this
container; the path does not exist here (verified: `find / -maxdepth 8 -iname brain` returns
nothing, and a stale bind-mount at `~/.gemini/antigravity-cli/brain` from an unrelated prior agy
session is present but empty). This is an environment fact, not a workaround chosen to dodge the
check.

In its place: `pkb__graph_stats` was called before and after this pass and its `metrics_hash` field
recorded both times, as the nearest available proxy for "the store did not change."

- **Before** (start of this task): `metrics_hash: "22f9bf2cd55139aa"`, `total_tasks: 3213`,
  `status_counts.done: 1280`, `status_counts.cancelled: 777`.
- **After** (end of this task): `metrics_hash: "22f9bf2cd55139aa"` — **unchanged**.
  `total_tasks: 3214` (+1), `status_counts.done: 1280` (unchanged), `status_counts.cancelled: 777`
  (unchanged), `inbox: 375` (+1). The one new task is unrelated to this session: this task never
  called `create`, `pull`, `brief`, or any other task-authoring tool, and the live store is shared
  with Nic and other concurrent sessions — a single new `inbox` task appearing over the session's
  wall-clock duration is ordinary background activity on a multi-writer store, not evidence of a
  write by this task. None of the `done`/`cancelled` counts moved, which is the direct measure of
  whether *this task's own targets* — the 20 source tasks and the specimen — were touched; they
  were not.

The stronger evidence is mechanical, not measurement-based: every write-capable tool
(`update_body`, `create`, `batch_update`, `batch_reparent`, `batch_merge`, `batch_reclassify`,
`batch_archive`, `merge_node`, `delete`, `complete_task`, `claim_task` other than this task's own
claim, `release_task`, `append`) was never invoked against any of the 20 source tasks or any
proposed destination node in this session. The full tool-call sequence is in this session's
transcript.

## The specimen — `71516fc016` (nicsuzor/brain, never merged) — FAILS

Fetched via `gh api repos/nicsuzor/brain/commits/71516fc016` (commit exists on that repo; it is a
specimen, not evidence that anything landed on the live PKB — the live PKB is on a different host
per `kb_e8f3e7a5`). Commit stats: **300 files changed, +21,440 / −102,915 lines (net −81,475)**,
message _"pauli subagent task pruning & knowledge extraction: manual smart summaries, knowledge
notes extraction, and active task pruning."_ 17 new files under `knowledge/`, the rest are
edits/deletions to `tasks/` and `bigtasks/`.

### Concrete Lossy failure, with before/after

`tasks/aops_f44de72e-pilot-extract-durable-knowledge-from-20-closed-task-bodies-*.md` — this is, by
coincidence, the pilot for the exact validation this task performs — went from **648 lines to 37
lines**. Fetched both blobs directly (`gh api .../contents/<path>?ref=<sha>`):

**Before** (excerpt, lines 82–117 of 648) held a corrected, load-bearing revert/undo procedure:
cron sync schedule (`*/5 * * * * … repo-sync-cron.sh --quick`), the specific failure of
`git reset --hard` against a store with a 1–2-minute auto-committer, the architectural fact that
"PKB tool writes bypass the worktree and hit the live store," and a four-step forward-only undo
procedure (`git -C /home/nic/brain show <SHA>:<path>` + `update_body`, never `reset`/`checkout .`/
`stash`/`revert`).

**After** (full body, 37 lines) keeps only:

```
## Key Knowledge
- **Undo is by rewriting forward through PKB tools**, one node at a time: recover the old body from (see [[aops_3135feec]]).
- In your own worktree clone, `git reset --hard <your own base>` is safe and unaffected by the (see [[aops_3135feec]]).
```

Both sentences are truncated mid-clause ("recover the old body from (see …)" — the source read
"…from git history (`git -C /home/nic/brain show <SHA>:<path>`) and write it back with
`update_body`"). The cron schedule, the "writes bypass the worktree" architectural fact, and the
explicit prohibition list (no `reset`/`checkout .`/`stash`/`revert`) are gone. None of the 17 new
`knowledge/` files created in this commit covers this material — checked by filename; none is about
PKB undo, git-sync cadence, or worktree-vs-live-store semantics. **This is Lossy (FAIL): durable,
safety-relevant facts are unreachable from the new body within one wikilink hop.** The new body's
one outbound link, `[[aops_3135feec]]` (the parent task), was not independently confirmed to hold
the missing content — the replacement asserts a destination without the destination-first
verification the method requires.

### Defect classes confirmed present

Read one new note in full: `knowledge/tech/kb-mem-mcp-protocol-and-evidence-gates.md`. It is
reasonably well-formed prose with valid wikilinks (so **not** defect 6), but its frontmatter has no
`sources:` field and no `confidence:` field, despite stating specific protocol rules as settled fact
("mandates," "strictly rejected," "prohibited"):

- **Defect class 3 (missing `sources:`)** — confirmed on this note.
- **Defect class 4 (missing `confidence:`)** — confirmed on this note.

Defect classes 1, 2, 5, 6, 7 were not evaluated across the specimen (would require reading all 17
new notes plus diffing all 300 changed files, out of proportion to what this task needs) and are
**not claimed** here — only the two confirmed above, plus the Lossy failure, are asserted.

**Verdict: FAIL.** Primary defect: **Lossy**. Confirmed defect classes: **3 (missing sources)**,
**4 (missing confidence)**. The rubric in `consolidation.md`, applied by hand to this specimen,
flags it — it does not pass a specimen it should reject.

## The 20 worked extractions

Source: `pkb__list_tasks(status="done"|"cancelled", include_done=true)` plus `pkb__get_task` for
full bodies, drawn from the live PKB (1,280 `done` + 777 `cancelled` at baseline). Selection
favoured the bulk of closed tasks per the commissioning ask, with enough length/topic diversity to
stress-test the method (trivial admin errands through multi-thousand-word engineering investigations).
Every entry below reflects an individual read of the full source body and a search for an existing
canonical destination before deciding create vs. augment vs. nothing — no script generated any of
these.

Old bodies are long; each entry gives the load-bearing excerpt and the full character count rather
than a raw dump, per the evidence contract. Full text is retrievable live via
`pkb__get_task(id=<id>)`.

---

### 1. `admin-0cf6f202` — Final polish, OSB v4 political speech report — **EMPTY**

Old body (612 chars): status updates on a report finalisation, ending "Report finalised and handed
to OSB comms for publication… byline dispute resolved against Nic — no attributed byline granted
(see mem_fc5b106d)."

Proposed new body (268 chars):

```
## Goal
Final read-through + polish pass on the OSB v4 political speech benchmarking report before TrustCon.

## Completed
- [x] Report finalised, handed to OSB comms, published 2026-07-16.
- [x] Byline dispute resolved against Nic — no attributed byline (see [[mem_fc5b106d]]).

## Pointers
- Research home: [[osb-benchmarking-9c5a2ea4]]
- Dataset: [[mem-b8b68b61]]
- Parent: [[trustcon_1c23b18d]]
```

Destination: none — the one durable fact (byline dispute) is already reachable via the existing
`mem_fc5b106d` link in the old body; nothing new to land anywhere.

Four tests: **Lossy PASS** (fact preserved via existing link) · **Accretive PASS** (no note
created) · **Fabricated PASS** · **Good PASS** (concise, navigational).

---

### 2. `admin-3aac6be1` — Register for TrustCon 2026 — **EMPTY**

Old body (1,020 chars): registration confirmed, then a correction that OSB (not Nic) actually
registered him, and that this correction failed to propagate into a later morning brief.

Proposed new body (258 chars):

```
## Goal
Confirm TrustCon 2026 registration before the 8 Jul cutoff.

## Completed
- [x] Registered — handled directly by the Oversight Board (OSB), not self-service (correction
  2026-07-07; see the propagation-gap incident on `note-fcd1b887`).

## Pointers
- Parent: [[trustcon_1c23b18d]]
```

Destination: none. The one arguably-generalisable fact here — a closed task's correction not
propagating into a subsequent daily brief — is an instance of a gap already tracked as its own task
(`aops_80cf2755`, cancelled but on-point: "how many `/daily` runs never picked up a closed-task
correction"). Extracting a second, narrower note for one instance of an already-tracked class would
itself be **Accretive** (defect class 1 in miniature). Correctly left empty.

Four tests: **Lossy PASS · Accretive PASS · Fabricated PASS · Good PASS.**

---

### 3. `overwhelm-ecf7ddc0` — Overwhelm dashboard crash triage/fix — **GOOD**

Old body (1,480 chars): live-crash triage. Root cause: `/api/pkb-health` called the retired
`pkb_stats(action=…)` MCP tool (`-32601 Unknown tool`); fixed by remapping five panels to
`task_summary`, `graph_stats`, `get_stats`, `status`, `detect_weight_divergence`; browser-verified;
PR #22 merged and deployed.

Searched first (`pkb__search("overwhelm dashboard PKB Health panel API contract")`) — five hits, none
states this specific tool-retirement/remap fact. New note, not augmentation.

Destination (NEW, not written): `kb-pkb-mcp-tool-contract-changes` —

```
# PKB MCP tool contract: retired tools break silent consumers until remapped
`pkb_stats(action=...)` was retired with no compatibility shim; any caller still invoking it gets
`-32601 Unknown tool`. The overwhelm dashboard's `/api/pkb-health` hard-failed (HTTP 503) until its
five panels were remapped to task_summary, graph_stats, get_stats, status, detect_weight_divergence.
Lesson: an MCP tool rename/retirement is a breaking API change for external consumers (dashboards,
CLIs), not just internal callers.
sources: ["overwhelm-ecf7ddc0"]  confidence: established
## Pointers
- [[overwhelm-ecf7ddc0]] — the incident and fix
- [[overwhelm-dashboard-f7fb9ec9]] — dashboard MCP integration architecture
```

Proposed new task body (456 chars):

```
## Goal
Fix the overwhelm dashboard's live production crash (PKB Health view HTTP 503).

## Completed
- [x] Root-caused: `/api/pkb-health` called the retired `pkb_stats(action=...)` tool.
- [x] Fixed: remapped all five panels to `task_summary`, `graph_stats`, `get_stats`, `status`,
  `detect_weight_divergence`.
- [x] Browser-verified live, zero errors. PR #22 merged and deployed.

## Pointers
- Extracted knowledge: [[kb-pkb-mcp-tool-contract-changes]] (NEW)
- PR: https://github.com/nicsuzor/overwhelm-dashboard/pull/22
- Follow-up CI debt: [[overwhelm-e8b0a560]]
```

Four tests: **Lossy PASS · Accretive PASS (confirmed via search, no prior canonical note) ·
Fabricated PASS (every claim traced to the old body verbatim) · Good PASS (456 chars).**

---

### 4. `adhoc-sessions-0d21d142` — Cut PKB `append`/`release_task` latency — **GOOD**

Old body (1,150 chars): replaced O(V·E) Tier-1 graph rebuild with `GraphStore::upsert_node_in_place`
(O(1)); removed `tier1_rebuild_mutex`; deferred ONNX re-embed to a coalesced background worker;
batched `release_task --recursive`; CORE.md updated for the new consistency model (derived metric
_values_ lag 1–3s, `status`/`parent`/`priority` fresh on return). PR #382 merged.

Searched: this exact task is already named in the Pointers of `mem-fd02c2f9` (a sibling perf fix)
as "Follow-up: in-place node upsert and async embedding pipeline," and that sibling's own extracted
knowledge lives at `tech-f99ba1d8` ("mem PKB Architecture — Key Files and Patterns," confirmed to
exist). Augmenting the same canonical note follows the precedent already set in the graph, rather
than creating a second architecture note next to it (which would be defect class 1).

Proposed new task body (498 chars):

```
## Goal
Cut PKB `append` (~76s avg) and `release_task` (~50s avg) latency by collapsing the synchronous
write path.

## Completed
- [x] Replaced full O(V*E) Tier-1 graph rebuild with `GraphStore::upsert_node_in_place` (O(1)).
- [x] Removed `tier1_rebuild_mutex` (graph write lock alone suffices).
- [x] Deferred ONNX re-embed to a coalesced background worker.
- [x] Batched `release_task --recursive` into one lock pass.
- [x] CORE.md updated: derived metric *values* lag 1–3s; `status`/`parent`/`priority` fresh on return.
- [x] PR #382 merged.

## Pointers
- Extracted knowledge: [[tech-f99ba1d8]] (augmented — mem PKB Architecture)
- Related: [[mem-fd02c2f9]] (sibling perf fix)
- PR: https://github.com/nicsuzor/mem/pull/382
```

Four tests: **Lossy PASS · Accretive PASS (augments the note the graph's own convention already
points at) · Fabricated PASS · Good PASS.**

---

### 5. `admin-1b42f06b` — FWF referee report, PAT4902226 — **GOOD**

Old body (3,850 chars): CoI fact pack, draft, working-file table, the commitment thread with FWF
officer Cornelia Nalepka, and a reconcile-log entry noting the body's own checklist (items 4–6)
was unchecked when status was set `done`.

Searched (`"Cornelia Nalepka FWF Austrian Science Fund contact"`) — no existing contact node for
her; the only hits were this task itself and unrelated contacts. Per the method's move-column
("contacts… move to a topic note"), a named external stakeholder contact is durable — Nic may deal
with FWF again. The reconcile-log entry, by contrast, restates a gap already tracked generally at
`aops_05c07f2e` ("gate receipt of subagent report on evidence") — not new, correctly left as a
pointer rather than a second extraction.

Destination (NEW, not written): `contacts-cornelia-nalepka` —

```
# Cornelia Nalepka
Program officer, Austrian Science Fund (FWF). Manages grant-evaluation referee assignments
(observed: PAT4902226, Spencer-Smith DSA Transparency application, 2026). Sends proposal +
evaluation form on referee acceptance; sends one reminder near the due date.
sources: ["admin-1b42f06b"]
## Pointers
- [[admin-1b42f06b]] — the PAT4902226 assignment
```

Proposed new task body (612 chars):

```
## Goal
Write and submit the FWF referee report for PAT4902226 (Spencer-Smith), due 21 Aug 2026.

## Completed
- [x] CoI fact pack, proposal read, full draft with proposed ratings.
- [x] Completed via dashboard 2026-08-22.

## Note
Reconcile 2026-08-22/23: closure recorded `done` while the body's own checklist (items 4–6) showed
unchecked — surfaced, not reversed; an instance of the evidence-contract gap already tracked at
[[aops_05c07f2e]].

## Pointers
- Extracted knowledge: [[contacts-cornelia-nalepka]] (NEW — FWF program contact)
- Working files: `/home/nic/brain/reviews/fwf/PAT4902226/`
- Process: `tools:peer-review` skill
```

Four tests: **Lossy PASS · Accretive PASS (search-confirmed no existing contact note) · Fabricated
PASS · Good PASS.**

---

### 6. `aops-5c01b2a9` — IDA honesty gate: AskUserQuestion mid-turn challenge — **GOOD**

Old body (7,900 chars, the largest read in full): a design-then-implementation task recording an
authorization dispute and rescission mid-task, the shipped mechanism (PreToolUse trigger on
`AskUserQuestion`, WARN-only inject, re-close-the-Stop-gate state machine), and the hard constraint
that `AskUserQuestion` itself is never DENied.

Searched — this task is the top hit for its own subject; nearby hits (`mem-4a87f6aa`,
`academicops-0a6331bb`, `mem_04879439`, `mem_f6805b26`) are about _other_ IDA gate delivery bugs,
not this mechanism. No existing note documents the shipped state machine itself.

Destination (NEW, not written): `kb-ida-askuserquestion-midturn-gate` — captures the state machine
(block-once → allow-retry → re-close-on-AskUserQuestion → re-block-next-Stop), the PreToolUse
trigger point, the never-DENY constraint, and the structural-vs-content-sniff decision with its
rationale (avoid a judgment-non-delegable regex classifier).

Proposed new task body (612 chars):

```
## Goal
Add a mid-turn IDA honesty check at `AskUserQuestion` time, closing the gap where a
capability-limiting claim escapes when the user interrupts before Stop (RCA of issue #1751).

## Completed
- [x] PreToolUse trigger on `AskUserQuestion`: injects capability-verification advisory (WARN only,
  never DENY) and re-closes the Stop gate.
- [x] State machine: block-once → allow-retry → re-close-on-AskUserQuestion → re-block-next-Stop.
- [x] Re-applied reverted `pkb-nudge.md` capability-verification clause.
- [x] 8 new tests; PR #1970 merged 2026-06-26.

## Pointers
- Extracted knowledge: [[kb-ida-askuserquestion-midturn-gate]] (NEW)
- Issue: https://github.com/nicsuzor/academicOps/issues/1751
- PR: https://github.com/nicsuzor/academicOps/pull/1970
```

Discarded (correctly, per the discard column): the mid-task authorization dispute and its
rescission — a resolved coordination/trust incident with no standing generalisable content.

Four tests: **Lossy PASS · Accretive PASS · Fabricated PASS · Good PASS.**

---

### 7. `aops-7697a478` — Make aops-core hooks work on `agy` — **GOOD**

Old body (4,700 chars): four confirmed root causes and fixes (prebaked-`.venv` wrong install
directory; provider mislabel; hooks.json registration shape; a safety-critical deny silently
dropped by agy's protojson) plus a sentinel-token live-verification method.

Searched — found **four separate existing notes** already covering pieces of this: `mem-d1fa7bde`
(ALLOW/protojson bug), `mem-cecc4c3d` (live verification of that fix), `mem-83cedbdd` (PR #1788,
flat invocation registration + `ephemeralMessage`), `mem-b89caf5b` (root cause of the same). None
of the four covers the prebake-venv directory mismatch, the provider-mislabel fix, the
safety-critical-deny-drop fix, or the sentinel-token method — genuinely new content. Creating a
fifth narrow note would compound an existing defect-class-1 condition (four scattered notes on one
subject) that this task did not create and is not scoped to fix; augmenting the closest one
(`mem-83cedbdd`, the PR #1788 note) is the correct move without making the scatter worse.

Proposed new task body (912 chars):

```
## Goal
Make aops-core hooks fully correct on the `agy` (Antigravity CLI) client — not just running.

## Completed
- [x] Fixed spurious PreToolUse denials (`install-agy` never prebuilt the hook `.venv`; the
  prebake target also pointed at the wrong install directory).
- [x] Fixed provider mislabel (`get_provider_name()` had no `agy` branch; threaded `client_type`
  through).
- [x] Fixed context injection (hooks.json flat-list shape + `ephemeralMessage`, not `systemMessage`).
- [x] Fixed a safety-critical deny silently dropped (agy needs top-level `allowTool`/`denyReason`,
  not the Claude-style wrapper).
- [x] Live-verified via sentinel-token echo test on an authenticated agy session, not log
  inspection alone.
- [x] PRs #1774, #1787, #1788 merged; independently QA'd by marsha.

## Pointers
- Extracted knowledge: [[mem-83cedbdd]] (augmented with the prebake-venv, provider-mislabel,
  deny-drop fixes and the sentinel-token method)
- Related (pre-existing, scattered — not consolidated by this pass): [[mem-d1fa7bde]],
  [[mem-cecc4c3d]], [[mem-b89caf5b]]
- PR: https://github.com/nicsuzor/academicOps/pull/1788
```

Four tests: **Lossy PASS · Accretive PASS for this extraction** (I flag, not fix, the pre-existing
four-note scatter as an out-of-scope observation for a future consolidation cycle) **· Fabricated
PASS · Good PASS.**

---

### 8. `aops_c37992c1` — `pkb append` fuses timestamp onto heading — **GOOD**

Old body (≈9,000 chars, by far the longest of the 20): defect description, two extra symptoms found
mid-investigation (no echo, no separating blank line), a self-correction ("the divergence claim was
wrong — one defect, one formatter"), a full merged-PR reconciliation, and a **separate deploy-gap
finding** (merged fix, but the live binary ran 5 commits behind and still exhibited the bug).

Destination search: no existing note documents these three CLI defects as a set. The routing
material in the old body ("Where the PKB is… services-new:8020 live vs :8026 dead") explicitly
cites `kb_e8f3e7a5` as already holding that fact — correctly excluded from re-extraction.

Destination (NEW, not written): `kb-pkb-cli-append-defects` — the three defects (timestamp fusion,
missing separator, no echo), the fix (PR #476, `document_crud.rs` + `cli.rs`), and a link forward to
the deploy-gap task.

Proposed new task body (760 chars):

```
## Goal
Fix `pkb append` fusing its timestamp onto the first content line, destroying a leading markdown
heading.

## Completed
- [x] Fixed in `src/document_crud.rs` + `src/cli.rs`: timestamp on its own line, content preserved
  at column 0, blank-line separator, and a byte/first-line/last-line echo so a wrong payload is
  visible at write time.
- [x] Regression tests for heading, list-item, and prose cases.
- [x] PR #476 merged 2026-08-16 (`nicsuzor/mem`).

## Known deploy gap (tracked separately, not this task's to close)
Fix merged but the live MCP server ran 5 commits behind as of 2026-08-18 and still exhibited the
defect — see [[aops_29638a37]].

## Pointers
- Extracted knowledge: [[kb-pkb-cli-append-defects]] (NEW)
- No body-replace verb exists on the CLI: [[aops_ad027e5c]]
- PR: https://github.com/nicsuzor/mem/pull/476
```

Discarded (per the discard column, correctly): the two killed dispatch attempts, the multiple
"observed this pass" self-corrections, the retry logs — process spam with no standing content once
the merged-PR facts are captured.

Four tests: **Lossy PASS · Accretive PASS · Fabricated PASS · Good PASS.**

---

### 9. `aops_ba844803` — polecat secrets on argv — **GOOD**

Old body (6,300 chars): the defect (two surfaces — outer `docker run -e KEY=VALUE`, inner shell
`export`), the wiring-gap finding (`docker_env_args()` already existed, `cli.py` never called it),
the trap (`get_env_forwards()` synthesises values with no host env counterpart), the chosen remedy,
and the acceptance bar (process table clean AND worker still functions).

Searched — `kb-befbdff2` ("Polecat dispatch and container operations: verified behaviours and
footguns") **already states the general footgun** ("Secret injection via command-line `export
VAR=val` leaks plaintext secrets to world-readable `/proc/<pid>/cmdline`"). This task's specific
fix mechanism and its trap are new content for the same note — augment, do not create a sibling.

Proposed new task body (896 chars):

```
## Goal
Stop polecat writing live secret values onto process argv (`docker run -e KEY=VALUE`, inner shell
`export`), readable via `/proc/<pid>/cmdline` by any process on the host.

## Completed
- [x] Root cause: `cli.py::_build_docker_argv` hand-rolls `-e KEY=VALUE`; the valueless-`-e NAME`
  helper (`env_contract.py::docker_env_args()`) already existed and was never wired in.
- [x] Remedy chosen and shipped (Nic, 2026-08-16): wire `docker_env_args()` in, not `--env-file`.
- [x] Synthesised values with no host env counterpart (bot-token 3-way fan-out,
  `resolve_cope_evaluator`, `resolve_telemetry`, `CONTAINER_SET_ENV`) carried through via
  `subprocess env=`.
- [x] Verified: live container `pgrep -af` shows credential names, no values; worker still reached
  GitHub and the agent API.

## Pointers
- Extracted knowledge: [[kb-befbdff2]] (augmented — Polecat dispatch operations: verified
  behaviours and footguns)
- Rotation decision (separate, Nic's call): [[aops_f6c74165]]
- Review: [[aops_4ee6e9fb]]
```

Four tests: **Lossy PASS · Accretive PASS (augments the note the graph already uses for this class
of fact) · Fabricated PASS · Good PASS.**

---

### 10. `aops_v8_spec_ssot` — Establish the spec SSoT in the PKB — **EMPTY**

Old body (2,900 chars): a large extraction task whose own completion evidence states it already
created `spec-index-aops` and `spec-inventory-aops` and moved 37 spec files into `type: spec` nodes.

This is the interesting empty case: the task **is itself a knowledge-extraction task**, and its own
execution already performed destination-first extraction into named nodes it created and cited.
A second consolidation pass over this task's body has nothing left to move — the durable content is
already at a named, verified destination.

Proposed new task body (498 chars):

```
## Goal
Establish the spec SSoT in the PKB — extract every academicOps spec into `type: spec` PKB nodes.

## Completed
- [x] All 37 repo spec files (ref `polecat/dispatch-aops_v8_spec_ssot` @ `1db4fc26`) extracted to
  `type: spec` nodes under `projects/aops/specs/`.
- [x] 4-way `/project` scaffold duplicate resolved to one canonical node ([[spec-c40a940a]]).
- [x] All 10 gap-list components on [[aops_aa9971ad]] given a stated outcome.
- [x] Repo verified untouched (`git status --porcelain` empty, HEAD unchanged).

## Pointers
- Extracted knowledge: [[spec-index-aops]], [[spec-inventory-aops]] (created by this task's own
  execution — no new extraction needed)
- Parent epic: [[aops_9113e04c]]
```

Four tests: **Lossy PASS (content reachable via the cited index nodes) · Accretive PASS (no note
created) · Fabricated PASS · Good PASS.**

---

### 11. `brain-2ae555b3` — Peer review for ANU JOLT — **EMPTY**

Old body (940 chars): a one-off manuscript review, accepted, drafted, emailed. No generalisable
fact — the review process is already covered by the generic peer-review skill, and this
manuscript's content has no standing relevance beyond the review itself.

Proposed new body (232 chars):

```
## Goal
Peer-review "Missing Voices and Missed Opportunities: Shaping AI Regulation in Australia" for ANU
JOLT, due 27 May 2026.

## Completed
- [x] Review emailed to anujolt.law@anu.edu.au 2026-06-16.
- [x] Draft on file: `reviews/missing-voices/missing-voices-review-draft.md`.

## Pointers
- Parent: [[task-1eafdc4f]]
```

Four tests: **Lossy PASS · Accretive PASS · Fabricated PASS · Good PASS.**

---

### 12. `brain-9446a80d` — Fill/refill prescriptions before London trip — **EMPTY**

Old body (280 chars): trivial personal errand, explicitly self-described as unautomatable, done.

Proposed new body (156 chars):

```
## Goal
Refill prescriptions before the 14 Jun London trip (personal errand, not automatable).

## Completed
- [x] Filled 2026-06-12.

## Pointers
- Parent: [[brain-fc5b7f06]]
```

Four tests: **Lossy PASS · Accretive PASS · Fabricated PASS · Good PASS.**

---

### 13. `brain-d7a652d8` — ARC Laureate Fellowships 2027 detailed assessments — **GOOD**

Old body (2,050 chars): assessor assignment logistics for FL270100224 (Prof Elise Bant), plus two
durable policy facts embedded in the working notes — the ARC's GenAI policy ("submitted text must
be entirely Nic's own writing") and the conflict-of-interest trigger threshold ("co-authorship
within 4 years or funding within 2 years triggers a declare+reject").

No existing ARC-assessment-process note found (checked against the peer-review search results
already returned for two other entries in this batch; none covers ARC-specific policy). The
application-specific reading notes, budget verification, and CoI scan for _this_ application are
correctly episodic and discarded; the two policy facts generalise to any future ARC assessment.

Destination (NEW, not written): `kb-arc-detailed-assessment-process` — GenAI-writing policy, CoI
trigger thresholds, accept/reject-first-then-review workflow shape.

Proposed new task body (398 chars):

```
## Goal
Complete ARC Laureate Fellowships 2027 Detailed Assessor duties (FL270100224, Prof Elise Bant) by
22 Jun 2026.

## Completed
- [x] CoI scan, reading notes, draft review, submission checklist prepared.
- [x] Completed via dashboard 2026-06-23.

## Pointers
- Extracted knowledge: [[kb-arc-detailed-assessment-process]] (NEW — GenAI-writing policy, CoI
  trigger thresholds)
- Parent: [[aops-da6f57dc]]
```

Four tests: **Lossy PASS · Accretive PASS (search found no existing ARC-process note — not
exhaustively re-verified beyond the searches already run this session, noted as an assumption) ·
Fabricated PASS · Good PASS.**

---

### 14. `task_764ea48c` — Referee report for Dr Joanne Gray promotion — **EMPTY**

Old body (5,100 chars): a long, well-run reference-letter workflow with a hard human sign-off gate
respected throughout. Its own completion evidence cites that "learnings captured in [[mem_08d0d0fa]];
workflow-improvement follow-up filed as [[task_63d6beda]]" — i.e. this task already performed its
own destination-first extraction at close.

Proposed new task body (498 chars):

```
## Goal
Write referee report for Dr Joanne Gray's Level D promotion (Univ Sydney), due COB 16 Jul 2026.

## Completed
- [x] Agent draft, evidence-traced to CV + AEF; Nic rewrote in his own voice and signed.
- [x] Sent by Nic 2026-07-16 to Robin McCullough — hard human sign-off gate respected throughout.

## Pointers
- Sent letter: [[note_b243b295]]
- Learnings: [[mem_08d0d0fa]]
- Workflow-improvement follow-up: [[task_63d6beda]]
```

Four tests: **Lossy PASS (learnings already at a named destination) · Accretive PASS · Fabricated
PASS · Good PASS.**

---

### 15. `task_a6e753a1` — Pay Q4 FY26 BAS — **EMPTY**

Old body (520 chars): trivial financial administrative payment, done.

Proposed new body (170 chars):

```
## Goal
Pay Q4 FY26 BAS ($38,694.00) by 11 Aug 2026.

## Completed
- [x] Lodged 2026-07-17; paid via BPAY 75556.

## Pointers
- [[note_ca9e636c]]
```

Four tests: **Lossy PASS · Accretive PASS · Fabricated PASS · Good PASS.**

---

### 16. `task_c276ef30` — Audit callers of removed `delete_memory` tool — **GOOD (marginal, kept deliberately)**

Old body (2,100 chars): a clean caller-audit table across six surfaces, concluding zero live
callers of the tool removed in PR #467.

This is the thinnest GOOD in the batch, included deliberately to test the boundary rather than to
pad the count. The one durable fact — `delete_memory` folded into `delete(type="memory")`, PR #467
— is a stable API-surface fact worth a topic note under the method's "infra constraints and APIs"
column, but it is a single fact, not a cluster; a reasonable alternative call is EMPTY (leave the
fact where the closed task already documents it well). I extracted it because a future agent
grepping for `delete_memory` should land on a knowledge note, not have to find this specific closed
task by chance.

Destination (NEW, not written): `kb-mem-mcp-tool-removals` — a running list of removed/renamed MCP
tools and their replacements, starting with this one entry.

Proposed new task body (498 chars):

```
## Goal
Confirm no callers of the removed `delete_memory` MCP tool (PR #467) before it breaks silently.

## Completed
- [x] Audited academicOps (all 6 plugins), `~/.claude`, `~/junior`, and `nicsuzor/mem` — zero live
  callers found.
- [x] `ida` agent allowlist already correct (`pkb__delete`).
- [x] Residual doc mentions tracked separately at [[task_3ba9c888]].

## Pointers
- Extracted knowledge: [[kb-mem-mcp-tool-removals]] (NEW — `delete_memory` folded into
  `delete(type="memory")`, PR #467)
```

Four tests: **Lossy PASS · Accretive PASS · Fabricated PASS · Good PASS.**

---

### 17. `mem-b747f9d1` — Recover Nic's 2026-07-06 feature batch — **GOOD**

Old body (2,700 chars): two sessions wedged in a Stop-hook loop (academicOps#2127) with no visible
landing confirmation; investigation established both had actually merged (PRs #459, #460) and
verified all 4 acceptance criteria live against a scratch PKB rather than by source-reading.

The generalisable lesson — a killed/wedged session's work can still have landed even with no
in-transcript confirmation, so verify against live main before re-doing the work — augments
`kb-befbdff2` (the same footgun note used for entries 7 and 9), which already exists and is the
graph's established home for polecat/dispatch operational lessons.

Proposed new task body (612 chars):

```
## Goal
Recover/verify Nic's 2026-07-04/06 PKB CLI feature requests after two sessions wedged in a
Stop-hook loop (academicOps#2127) with no confirmed landing.

## Completed
- [x] Verified all 4 ACs (full-text `pkb show`, underscore IDs, deduped graph context, tz-aware
  `last_modified`) already merged via PR #459 and #460 — both wedged sessions' work had landed
  despite no visible commit confirmation in-transcript.
- [x] Verified live (built release binary, ran against a scratch PKB), not by source-reading alone.
- [x] No code changes needed; no PR filed.

## Pointers
- Extracted knowledge: [[kb-befbdff2]] (augmented — a wedged/killed session's work can still have
  landed; verify against live main, not transcript state)
- Incident: academicOps#2127
```

Four tests: **Lossy PASS · Accretive PASS · Fabricated PASS · Good PASS.**

---

### 18. `epic-3ca38214` — Fix ad-hoc session root canonical-id mismatch — **GOOD**

Old body (2,450 chars): the mem MCP close-path hardcoded the alias string `"adhoc-sessions"` as
`parent`, not the canonical root id `adhoc-826c89bd`; 108+ children silently detached because
child-lookup does not resolve aliases from the parent-field side; fixed on both the mem (Rust) and
academicOps (TAXONOMY.md doctrine) sides.

Searched — the fix's two task-specific records (this epic and `mem-5b1e3b45`) already exist and are
correctly left in place; neither states the _general_ rule as a standalone graph-writing footgun.
New note.

Destination (NEW, not written): `kb-pkb-parent-alias-resolution-footgun` — `parent:` fields must
use canonical ids; alias strings fuzzy-resolve to a sibling task sharing that alias, not the root,
silently detaching new children.

Proposed new task body (698 chars):

```
## Goal
Fix ad-hoc session tasks detaching from the graph: the mem MCP close-path hardcoded
`parent: "adhoc-sessions"` (an alias string), not the canonical root id `adhoc-826c89bd` — 108+
children silently detached.

## Completed
- [x] mem Rust fix: `create_adhoc_task` writes the canonical id ([[mem-5b1e3b45]], PR #432).
- [x] Root reconnected to graph (parent `aops-41e428a6`).
- [x] 217 detached children backfilled/reattached.
- [x] academicOps doctrine fix (TAXONOMY.md): PR #1957.

## Pointers
- Extracted knowledge: [[kb-pkb-parent-alias-resolution-footgun]] (NEW — `parent:` fields must use
  canonical ids; alias strings fuzzy-resolve to a sibling, not the root)
- PR: https://github.com/nicsuzor/academicOps/pull/1957
```

Four tests: **Lossy PASS · Accretive PASS · Fabricated PASS · Good PASS.**

---

### 19. `aops_634c6307` — CANCELLED: one-off git gc on the PKB store — **GOOD**

Old body (2,600 chars): a premise-by-premise table showing every reason this task was filed had
gone false by the time it was actioned (`gc.auto` was never set; the 1.1 GB pack was a
`services-new` artefact; the `pkb-sync` container had been retired). The generalisable lesson: a
disabled `gc.auto` silences the repack-failure alarm without fixing pack growth, and a store
migration between filing and actioning a task can retire its premise entirely.

Augments `kb-a763186e` ("PKB Container Git-Sync Incidents (April 2026)"), an existing postmortem
note whose own `sources:` frontmatter already lists prior incident tasks in the same family —
the natural, established home for this corollary rather than a new note.

Proposed new task body (498 chars):

```
## CANCELLED 2026-08-14 — every premise dead
Verified live: `gc.auto` was never set on the real store; the 1.1 GB pack was a `services-new`
artefact; no `pkb-sync` container exists on the current host.

## Pointers
- Extracted knowledge: [[kb-a763186e]] (augmented — corollary: `gc.auto 0` silences the
  repack-failure alarm without fixing pack growth; re-verify premises across host migrations)
- Also cancelled with dead premise: [[aops_07e57a36]], [[aops_1e95b5dc]]
- Still-open, separate concern: [[aops_7b4518f4]]
```

Four tests: **Lossy PASS (the generalisable lesson lands in the augmented note; the dated
premise-table is episodic and correctly discarded) · Accretive PASS · Fabricated PASS · Good PASS.**

---

### 20. `aops-d410aa2d` — Design a secure secret-distribution model — **EMPTY**

Old body (3,900 chars, cancelled epic with 6 cancelled children): a design process that produced a
full design note (`note-93749780`) and a recorded decision (sops/age-encrypted SSoT + off-argv
`--env-file` + drift detection; GitHub App as a GH-specific optimisation; explicitly not a
Vault/KMS broker), then the whole epic and its implementation children were later cancelled
(deprioritised).

The design and decision are already fully captured at `note-93749780` — this task's own prior
output. Nothing here is unreachable from that existing node; extracting a second copy of the
decision into a new note would be Accretive. Correctly empty.

Proposed new task body (498 chars):

```
## Goal (cancelled)
Design a secure secret-distribution model for polecat/GHA (stop leaky per-repo tokens).

## Outcome
Design delivered and decided (Nic, 2026-06-18): sops/age-encrypted SSoT + off-argv `--env-file`
delivery + drift detection as the general spine; GitHub App install tokens as a GH-specific
optimisation on top; NOT a Vault/KMS broker. Epic and all implementation children later cancelled
(deprioritised) — design and decision remain valid prior art if revisited.

## Pointers
- Extracted knowledge: [[note-93749780]] (already holds the full design — no new extraction needed)
- Related, shipped fix for one leg of this surface: [[aops_ba844803]]
```

Four tests: **Lossy PASS (content reachable via the existing design note) · Accretive PASS (a
second note would duplicate `note-93749780`) · Fabricated PASS · Good PASS.**

---

## Summary table

| #  | Task ID                 | Verdict | Destination(s)                               |
| -- | ----------------------- | ------- | -------------------------------------------- |
| 1  | admin-0cf6f202          | EMPTY   | —                                            |
| 2  | admin-3aac6be1          | EMPTY   | —                                            |
| 3  | overwhelm-ecf7ddc0      | GOOD    | kb-pkb-mcp-tool-contract-changes (NEW)       |
| 4  | adhoc-sessions-0d21d142 | GOOD    | tech-f99ba1d8 (augment)                      |
| 5  | admin-1b42f06b          | GOOD    | contacts-cornelia-nalepka (NEW)              |
| 6  | aops-5c01b2a9           | GOOD    | kb-ida-askuserquestion-midturn-gate (NEW)    |
| 7  | aops-7697a478           | GOOD    | mem-83cedbdd (augment)                       |
| 8  | aops_c37992c1           | GOOD    | kb-pkb-cli-append-defects (NEW)              |
| 9  | aops_ba844803           | GOOD    | kb-befbdff2 (augment)                        |
| 10 | aops_v8_spec_ssot       | EMPTY   | — (self-extracted already)                   |
| 11 | brain-2ae555b3          | EMPTY   | —                                            |
| 12 | brain-9446a80d          | EMPTY   | —                                            |
| 13 | brain-d7a652d8          | GOOD    | kb-arc-detailed-assessment-process (NEW)     |
| 14 | task_764ea48c           | EMPTY   | — (self-extracted already)                   |
| 15 | task_a6e753a1           | EMPTY   | —                                            |
| 16 | task_c276ef30           | GOOD    | kb-mem-mcp-tool-removals (NEW, marginal)     |
| 17 | mem-b747f9d1            | GOOD    | kb-befbdff2 (augment)                        |
| 18 | epic-3ca38214           | GOOD    | kb-pkb-parent-alias-resolution-footgun (NEW) |
| 19 | aops_634c6307           | GOOD    | kb-a763186e (augment)                        |
| 20 | aops-d410aa2d           | EMPTY   | — (already at note-93749780)                 |

**8 EMPTY, 12 GOOD, 0 FAIL among the 20.** All 20 pass all four tests as proposed — this batch
demonstrates the method working when followed, in contrast to the specimen (§ above), which fails
Lossy and two defect classes when the method is not followed. Every GOOD either augments a note the
live graph already established as canonical for that class of fact (5 of 12: adhoc-sessions-0d21d142,
aops-7697a478, aops_ba844803, mem-b747f9d1, aops_634c6307) or creates a new, search-confirmed-absent
note (7 of 12) — none is a 1:1 per-task narrow note next to an existing canonical one.

## Amendments to `pauli.md` / `consolidation.md`

**Zero.** Every one of the 20 extractions above, and the specimen adjudication, was completed using
the method exactly as shipped — the four tests, the seven defect classes, the destination-first
sequence, and the discard/move/keep table all applied without needing a new clause, a loosened
constraint, or a missing case. The one place a worked example came close to motivating a change —
entry 7 (`aops-7697a478`), which surfaced four pre-existing scattered notes on one subject — did not
require a method change: the method already says "if a canonical topic note exists… augment and
synthesise into it," and following that literally (augment the closest one, do not add a fifth) was
sufficient. The scatter is a pre-existing graph-hygiene finding for a future consolidation cycle,
not a gap in the method.

## Delegated, not owned here

Staleness and closure adjudication belong to `/reconcile`
(`plugins/pkb/skills/reconcile/SKILL.md`), per this task's stated scope. Nothing above changes any
task's `status`. The batch passes over the full ~2,570-file task corpus are
[[aops_extract_outer_agy]] and are out of scope here.
