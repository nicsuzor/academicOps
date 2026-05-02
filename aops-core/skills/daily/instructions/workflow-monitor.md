# Daily Note: Workflow Monitoring

## Step 6: Monitor Workflows

Surface outstanding workflow signals in "What Needs Attention". This step runs after progress sync and before the task completion sweep (Step 7). Task auto-close logic lives in Step 7 — not here.

### Step 6.1: Discover Tracked Repos

Read `$AOPS_SESSIONS/projects.yaml` to get the project registry. For each project, resolve the on-disk path via convention (`$AOPS_SRC_DIR/<repo>`) or `$POLECAT_HOME/local.yaml` `paths.<slug>`. Skip repos that don't resolve locally.

This is the same repo discovery used by Step 4.2.5 (merged PR query). The repo list is configurable — repos are added/removed by editing `projects.yaml` in the sessions repo, not by changing skill code.

### Step 6.2: Fetch Open PRs Across Repos

**Run per-repo fetches in parallel.** Each repo query is independent — agent teams should dispatch a concurrent subagent per repo; single-agent environments should issue all `gh pr list` calls simultaneously rather than repo-by-repo. Merge results after all fetches complete.

For each tracked repo:

```bash
cd <repo_path> && gh pr list --state open --json number,title,isDraft,mergeable,createdAt,updatedAt,reviewDecision,headRefName,url,author,statusCheckRollup,additions,deletions,changedFiles,labels --limit 100 2>/dev/null
```

**Graceful degradation**: If `gh` CLI is unavailable or authentication fails for a repo, note it inline ("GitHub CLI unavailable for [repo] — skipped") and continue to the next repo. If all repos fail, skip the entire section and note "GitHub unavailable — skipped workflow monitoring" in natural language. Never produce empty tables or error codes.

### Step 6.3: Bucket PRs by Actionability

Classify each open PR into one of the following buckets, in order of prominence:

| Bucket                 | Criteria                                                                                                                 | Prominence                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| **Approve-ready**      | Has the `approve-ready` label (set by the user-side reviewer cron after the rebuilt RBG judge agent returned PASS)       | Top of section, grouped by epic    |
| **Ready to merge**     | `mergeable == "MERGEABLE"` AND `reviewDecision == "APPROVED"` AND CI passing (all checks in `statusCheckRollup` succeed) | Bold, direct URL, one-click action |
| **Needs review**       | `mergeable == "MERGEABLE"` AND `reviewDecision` is empty/pending AND not draft                                           | Brief context line with URL        |
| **Needs fixes**        | `mergeable == "CONFLICTING"` OR CI failing OR `reviewDecision == "CHANGES_REQUESTED"`                                    | Name the specific blocker          |
| **Stale**              | `createdAt` >7 days ago AND `updatedAt` >7 days ago AND not draft                                                        | Flag with age only                 |
| **Draft / autonomous** | `isDraft == true` OR author is a bot/polecat-worker                                                                      | Collapsed into count               |

**Approve-ready takes precedence.** A PR that carries `approve-ready` goes
into the Approve-ready bucket regardless of other state. This is the
single CTA list the supervisor's final summary points the user toward.

**CI status derivation**: Extract from `statusCheckRollup`. Classify as passing (all succeed), failing (any failure — name the failing checks), pending (any in progress, none failing), or no checks (empty rollup).

**A PR can appear in only one bucket.** Apply rules top-to-bottom — a stale PR that also needs fixes goes in "Needs fixes" (the more actionable bucket). A draft PR always goes in "Draft / autonomous" regardless of other signals.

### Step 6.4: Compose "Outstanding Workflows" Subsection

Write the subsection into "What Needs Attention" in the daily note. The
Approve-ready bucket renders first (it's the primary CTA per
task-212f1c82). Format proportionally:

```markdown
### Outstanding Workflows

**Approve-ready** (judge agent PASS — your call to merge):

- [ ] [#321](url) [[repo]] — PR title — _epic-abcd1234: one-line rationale_
- [ ] [#322](url) [[repo]] — PR title — _epic-abcd1234: one-line rationale_
- [ ] [#330](url) [[repo]] — PR title — _epic-efef5678: one-line rationale_

**Ready to merge:**

- [ ] [#123](url) [[repo]] — PR title (+N/-M, N files) — _merge now_
- [ ] [#456](url) [[repo]] — PR title (+N/-M, N files) — _merge now_

**Needs review:**

- [#789](url) [[repo]] — PR title — awaiting review (N days)

**Needs fixes:**

- [#101](url) [[repo]] — PR title — type check failing
- [#102](url) [[repo]] — PR title — merge conflicts

**Stale (>7d open):**

- [#200](url) [[repo]] — PR title — 12d open, no activity — close or rebase?

* N draft/autonomous PRs across M repos

_X open PRs total — Y ready to merge, Z need attention_
```

#### Approve-ready heartbeat distinction (mandatory)

The user-side reviewer cron writes a heartbeat file at
`dotfiles/cron/state/user-side-pr-review.last-run` on every run, regardless
of whether it found PRs to judge. The daily-sweep MUST read this file and
distinguish two empty-state cases with two different lines:

| Heartbeat state                                                         | Line to render                                                                                                                                       |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| File exists, `epoch` value within last 24 hours, no `approve-ready` PRs | `_No approve-ready PRs (reviewer cron last ran <ISO timestamp>)._`                                                                                   |
| File missing, OR `epoch` older than 24 hours                            | `_Approve-ready bucket unavailable: reviewer cron has not run in >24h (last <ISO timestamp or "never">). See dotfiles/cron/user-side-pr-review.sh._` |
| File exists, fresh, `approve-ready` PRs found                           | Render the bucket as shown above (no separate status line).                                                                                          |

Read the heartbeat file as `key=value` lines (`epoch=<seconds>`,
`timestamp=<ISO>`); fall back to "never" when missing. Compare `epoch`
against the daily-note generation time minus 86400 seconds. Treat any
parse failure as "missing" — the silent-failure mode (issue #890) MUST
remain visible.

**Formatting rules:**

- **Ready to merge** PRs render as `- [ ]` checkboxes with direct URLs. One-click decisions the user can tick off in their editor as they merge them. User ticks are preserved on regeneration (bidirectional contract — see `SKILL.md`).
- **Draft / autonomous** PRs: Collapse into a single count line.
- **Stale** PRs include age only. Do not recommend close/rebase/review — the user decides.
- Include size (`+additions/-deletions, N files`) for ready-to-merge PRs to help gauge merge confidence.
- Omit empty buckets entirely. If nothing is ready to merge, don't show the heading.

**Empty state**: If no open PRs across all repos: "No outstanding PRs." (single line, no subsection heading). When there are no `approve-ready` PRs but other buckets are populated, still render one of the two heartbeat-aware status lines from the table above so the cron's liveness is visible at a glance.

### Step 6.5: "Needs Your Call" — Ambiguous Completions

This step defines the format and location for ambiguous completion cases. The content is populated during Step 7 (Task Completion Sweep) — not here. Step 6.5 runs before Step 7, so this subsection is written into the note by Step 7 when it identifies ambiguous cases.

```markdown
### Needs Your Call

- **[task-abc123]** [[Task Title]] — PR [#456](url) was closed (not merged). Complete anyway? `/pull task-abc123 --complete`
- **[task-def456]** [[Email Reply Task]] — Sent email to [[Contact]] on similar subject but different thread. Mark done? `/pull task-def456 --complete`
```

**Rules:**

- Never auto-close items listed here — human judgment required
- Include the specific evidence and why it's ambiguous
- Include a one-click closure suggestion (task ID + action)
- Omit this subsection entirely if no ambiguous cases exist

### Step 6.6: Relationship to Work Log

The Outstanding Workflows subsection in "What Needs Attention" is the **single source** for open PRs in the daily note. The Work Log no longer carries a parallel "Open PRs" table — it was removed because it duplicated the same PR data in full-table form, padding the note without adding signal.

**What goes where:**

| Signal                                     | What Needs Attention                        | Work Log              |
| ------------------------------------------ | ------------------------------------------- | --------------------- |
| Open PRs (all buckets)                     | Yes — this is the canonical place           | No                    |
| Ready-to-merge PRs                         | `- [ ]` checkbox with URL + "merge now"     | No                    |
| PRs needing review / fixes / stale         | Listed under their bucket heading           | No                    |
| Merged PRs                                 | No                                          | Yes — merged PR table |
| PR action pipeline (agent recommendations) | Called out inline with the PR in its bucket | No (retired)          |
| Task completion sweep results              | "Needs your call" for ambiguous             | Sweep summary counts  |
