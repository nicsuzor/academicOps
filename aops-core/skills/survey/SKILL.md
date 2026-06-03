---
name: survey
type: skill
category: instruction
description: "Survey a corpus, classify, and dispatch outputs. Three modes: retro (transcript review → issues), trend (longitudinal performance analysis), sweep (GitHub issue triage → fix-epics). Delegates execution to junior/jr to keep main context clean."
triggers:
  - "survey"
  - "retro"
  - "transcript review"
  - "session review"
  - "trend review"
  - "performance trends"
  - "issue sweep"
  - "triage issues"
modifies_files: true
needs_task: false
mode: orchestration
domain:
  - framework
  - quality-assurance
  - operations
allowed-tools: Agent, Bash, Read, Grep, Glob, Edit, Write, Skill, AskUserQuestion, mcp__pkb__list_tasks, mcp__pkb__get_task, mcp__pkb__create_task, mcp__pkb__update_task, mcp__pkb__append, mcp__pkb__task_search
owner: junior
version: 1.0.0
tags:
  - retro
  - trend
  - sweep
  - quality
  - consolidation
---

# /survey — Unified Survey Skill

One abstract pattern, three modes: **survey a corpus, classify findings, dispatch outputs**.

| Mode    | Corpus                              | Primary output                 |
| ------- | ----------------------------------- | ------------------------------ |
| `retro` | Session transcripts (one at a time) | GitHub issues filed via `gh`   |
| `trend` | Many sessions / audit files         | Trend report + recommendations |
| `sweep` | Open GitHub issues                  | PKB tasks, fix-epics, closures |

**Privacy rule**: Anonymise all findings before filing. No real names, emails, student details, session dumps.

**See also**: [[../AXIOMS.md]] · [[../HEURISTICS.md]]

## Dispatch Model

This skill delegates execution to keep the main context window clean. The invoking agent dispatches, passes this skill as the execution spec, and exits.

```python
# retro or trend mode — junior has transcript/knowledge and execution access
Agent(
  subagent_type='junior',
  prompt='Read aops-core/skills/survey/SKILL.md. Execute in [retro|trend] mode. [user context]',
  tools=['Bash','Read','Grep','Glob','Edit','Write','Skill',
         'mcp__plugin_aops-core_pkb__search',
         'mcp__plugin_aops-core_pkb__task_search',
         'mcp__plugin_aops-core_pkb__get_document',
         'mcp__plugin_aops-core_pkb__pkb_context',
         'mcp__plugin_aops-core_pkb__append',
         'mcp__plugin_aops-core_pkb__create_task',
         'mcp__plugin_aops-core_pkb__update_task'],
)

# sweep mode — jr handles interactive confirmation gates
Agent(
  subagent_type='aops-core:jr',
  prompt='Read aops-core/skills/survey/SKILL.md. Execute in sweep mode. [user context]',
  tools=['Bash','Read','Grep','Glob','Skill','AskUserQuestion',
         'mcp__plugin_aops-core_pkb__get_task',
         'mcp__plugin_aops-core_pkb__create_task',
         'mcp__plugin_aops-core_pkb__update_task',
         'mcp__plugin_aops-core_pkb__append',
         'mcp__plugin_aops-core_pkb__task_search'],
)
```

---

## Mode: retro

**Purpose**: Read a recent transcript through a framework-development lens. Provide a brutal, concise critical review identifying problems. File every finding as a GitHub issue. We are aiming for EXCELLENCE, not "running code".

### 1. Select transcript

**Read the human-readable markdown transcript, not the raw session JSON/JSONL.** The
markdown is the mirrored, forensic-grade record (every line, tool calls and results
intact). The raw `.jsonl`/`.json` the harness writes under `~/.claude/projects/.../`
is a last resort only — it is harder to read and the markdown almost always exists.

**Corpus location.** The markdown corpus lives under the sessions repo, sharded by month:

```bash
# Canonical markdown corpus root (sharded into YYYY-MM/ subdirs):
#   $AOPS_SESSIONS/transcripts/YYYY-MM/
# Filename pattern:
#   YYYYMMDD-HHMM-<shortid>-<project>-claude-full.md      (preferred — complete record)
#   YYYYMMDD-HHMM-<shortid>-<project>-claude-abridged.md  (fallback — tool detail stripped)
# where <shortid> is the first 8 chars of the session UUID.
```

**Availability gate.** Before any path-dependent step, verify `$AOPS_SESSIONS` is set and
the transcripts directory exists on this host:

```bash
[ -n "$AOPS_SESSIONS" ] \
  || { echo "AOPS_SESSIONS is not set — cannot locate transcripts"; exit 1; }
[ -d "$AOPS_SESSIONS/transcripts" ] \
  || { echo "$AOPS_SESSIONS/transcripts does not exist on this host"; exit 1; }
```

If either check fails, **stop and ask the user** (via `AskUserQuestion`) — do not guess the
path and do not fall through to reviewing the raw JSONL as a workaround.

**Resolution order (do not skip a tier silently):**

1. **`-full.md`** — the complete forensic record. Always prefer this.
2. **`-abridged.md`** — thinner sibling with most tool calls/results stripped. Use only
   when no `-full.md` exists, and **say so** — abridged is weaker evidence for forensics.
3. **Raw `.jsonl`/`.json`** — last resort, AND only after you have told the user no
   markdown was found and they have confirmed (or directed) the fallback. Never fall back
   to JSONL silently.

**Auto-select the most recent unreviewed transcript** (retro auto-mode):

```bash
# Newest -full.md transcripts first, across all month shards:
find "$AOPS_SESSIONS/transcripts" -name '*-claude-full.md' -printf '%T@ %p\n' \
  | sort -rn | head -20 | cut -d' ' -f2-

# Of those, the unreviewed ones (no reviewed_by: in frontmatter):
for f in $(find "$AOPS_SESSIONS/transcripts" -name '*-claude-full.md' -printf '%T@ %p\n' \
            | sort -rn | head -20 | cut -d' ' -f2-); do
  grep -q "^reviewed_by:" "$f" || echo "$f"
done | head -10
```

**Resolve a user-supplied session ID to its markdown file.** The short id (first 8 chars
of the UUID) is embedded in the markdown filename, so glob on it — do NOT reach for the
raw `.jsonl` under `~/.claude/projects/`:

```bash
SID=04202ce6   # the short id (or first 8 chars of a full UUID the user pasted)
# Preferred -full.md, then -abridged.md fallback:
ls "$AOPS_SESSIONS/transcripts"/*/*-${SID}-*-claude-full.md 2>/dev/null \
  || ls "$AOPS_SESSIONS/transcripts"/*/*-${SID}-*-claude-abridged.md 2>/dev/null
```

If the user gave an explicit markdown path, use it. If they gave a session ID, resolve it
as above. If no unreviewed transcripts exist (auto-mode), report and stop. **Whichever way
you arrived at a file — auto-select, session-ID resolution, or an explicit path the user
handed you — it then passes the transcript-quality gate below. A path handed in by the user
is not exempt: a truncated or tool-stripped file is just as useless when named explicitly.**

**Before concluding a transcript is "absent," rule out looking in the wrong place.** A zero
-hit glob means one of two very different things, and the original bug was conflating them
(an agent reported "no mirrored markdown transcript exists" when the markdown was sitting in
`$AOPS_SESSIONS/transcripts/2026-06/` — it had simply checked a directory that does not
exist on this host). Distinguish them explicitly:

```bash
# 1a. Does the corpus root directory itself exist?
#     If not, the availability gate above should have caught this — re-check $AOPS_SESSIONS.
[ -d "$AOPS_SESSIONS/transcripts" ] && echo "Corpus root exists"

# 1b. Does the corpus root contain month shards?
#     An empty result here means the corpus is present but has no archived sessions yet —
#     do NOT report the transcript as absent; the path is correct, the session may be recent.
ls -d "$AOPS_SESSIONS/transcripts"/*/ 2>/dev/null | head

# 2. Only once the corpus root is confirmed present: a zero-hit glob for THIS session id
#    means the transcript for this session is genuinely absent (proceed to the gate).
```

Report "absent" only after step 1 confirms the corpus exists and step 2 returns nothing for
the session id. Never infer "no markdown exists anywhere" from a single failed `ls` in one
guessed directory.

**Transcript-quality gate — STOP rather than review a bad transcript.** Once you have a
candidate file, confirm it is good enough for a real forensic review. Do this by _reading_,
not glancing: open the head and the tail of the file, and where the raw `.jsonl` is also
present, use it as a cheap independent yardstick (count its lines — each is roughly one
event — against the markdown's turn count; a 1300-line raw session mirrored to a 50-line
markdown is stripped, not complete). The transcript is **not good enough** if any of these
hold:

- **Absent** — corpus root confirmed present (step 1 above), but no `-full.md` and no
  `-abridged.md` exists for the requested session (only the raw `.jsonl`).
- **Truncated** — the file does not end with a natural closing turn (it stops mid-message or
  mid-tool-call), OR it is drastically smaller than the raw `.jsonl` for the same session
  implies it should be (sanity-check the tail and the line-count ratio; don't assume).
- **Stripped** — tool calls and/or tool results are absent where the session used tools
  (read a sample of the body — if you see assistant turns referencing actions but no
  corresponding tool-call/tool-result blocks, it's stripped). Note: an `-abridged.md` used
  as the step-2 fallback deliberately drops tool detail and is acceptable — **disclose this
  to the user and continue**. "Stripped" in the gate sense applies to a `-full.md` that
  unexpectedly lacks tool blocks, or any file where the absence was not intentional.

When the transcript fails this gate, **stop and prompt the user to fix or regenerate it**
(via `AskUserQuestion`) — name which condition failed, cite the concrete evidence you
observed (the path you checked, the line counts you compared, the missing tool blocks), and
state what you need (e.g. "the markdown for session `<id>` is missing — corpus root
`$AOPS_SESSIONS/transcripts/` exists but holds no file matching `*/*-<id>-*-claude-*.md`;
please regenerate the mirror, or confirm you want me to proceed against the raw `.jsonl`
knowing tool results may be incomplete"). Do **not** silently proceed on the raw JSONL or a
degraded file; a forensic review built on a poor transcript produces false findings.

### 2. Read the full transcript

Read every line. Do not skim. For large files, read in chunks:

```
Read(file_path="<path>", offset=1, limit=500)
Read(file_path="<path>", offset=500, limit=500)
# continue until EOF
```

### 3. Critical review — structural over symptomatic

Evaluate the transcript critically. We are aiming for EXCELLENCE, not "running code".

You are trusted to find what matters. Read the transcript. Find what's worth fixing. Write it up however makes most sense. Flag your own biases.

- **Look for structural causes**: If you find yourself listing the same proximate cause across multiple findings, the deeper cause is upstream. Say so explicitly. Instead of listing four separate errors, articulate the structural mis-design that caused them.
- **Is the shape right?**: Instead of just asking "what went wrong against the framework as-is", ask "is the framework's shape correct?"
- **Pattern recognition**: Before filing issues, look for patterns across your findings. Are these discrete bugs, or symptoms of a single misaligned rule?
- **Instruction-quality failures**: When an agent underperformed — missed something visible in the logs, declared success prematurely, or optimised for the shallowest valid interpretation — ask whether the instruction itself was the root cause. Classify as root cause category "Instruction Gap" and note which of the seven /craft defects apply (compliance framing, missing artifact chain, no adversarial checks, summary-as-evidence, undefined boundary behavior, skimping on verification, no negative verification). The fix is an instruction rewrite via /craft audit, not an agent behavior change.

### 3b. Forensic scope (`recusal`)

**The retro is a forensic instrument. It does not legislate.** Per AXIOMS.md § recusal, the agent that just read the transcript is normatively recused from proposing framework change motivated by that transcript. Cross-incident judgment about adding/escalating/propagating rules happens in the detached `sweep` mode (a separate context, no prior exposure to this incident).

However, **what counts as forensic includes structural articulation.** You may articulate structural shape factually (e.g., "design X is impossible because Y", "the rule forces the agent into an impossible loop"). You may flag: "this looks structural; sweep should ask whether the rule shape is right, not just whether the rule fired".

For each finding, trust your judgment to provide a clear, forensic description that stops at the facts. Include what happened (quoted from the transcript), the structural context (how the framework's shape contributed), and the concrete impact.

**Crucially, do not propose what should be added, escalated, or propagated. That is the sweep agent's job, not yours.** You are trusted to identify the root cause category and causal chain naturally without adhering to a strict template.

You may flag the finding as severe; you may not author the legislation that severity might motivate. If you find yourself writing "we should add…", "the framework needs…", "an axiom against… would prevent this," strike it. The detached reviewer reading this report later, with the enforcement map and the incident register open, is the agent allowed to write that sentence.

### 4. Produce the review

```markdown
## Transcript Review: <filename>

**Session**: <session_id> **Date**: <date> **Project**: <project>
**Verdict**: [EXCELLENT | GOOD | ADEQUATE | POOR | FAILING]

### Findings

[Free-form description of what went wrong, what went well, and what could be improved. You may use lists, paragraphs, or whatever structure best articulates the issues. Group symptoms under structural causes if applicable.]

### Patterns (Optional)

[If you notice a pattern across findings, articulate the single upstream/structural cause here.]
```

### 5. File issues

For every **Finding** that requires action, file or update a GitHub issue.

**Group symptoms; split causes.** Findings that are symptoms of one structural cause — where one edit would resolve all of them — collapse into one issue. Findings that are **distinct fixable causes** — even when they share a meta-class — split into one issue per cause.

**Test for "distinct":** each cause must be independently fixable, meaning closable by a single PR scoped to one framework surface. Same meta-class is not the disqualifier; same fix is. If two seams collapse to the same edit, they are one issue; if they require coordinated edits across different surfaces (different skill files, different agent prose, different hook code), they are separate issues. The granularity of the issue tracker should match the granularity at which the framework actually gets fixed (one feature, one surface, one PR at a time) — so that `/issue-sweep` can rank seam-by-seam and each PR can close one issue cleanly.

**Cross-link pattern.** When a meta-class spans multiple seams, the meta-class itself still earns a record: preferably a parent issue (with the per-seam children listed by number in its body) or, for simpler cases, a "meta-class anchor" note inside one of the per-seam issues. Each per-seam child links back to the meta-class via `Refs #N`; the meta-class anchor links forward to each child. The children are individually rankable and individually closable; the meta-class record persists as the structural-shape memory.

**Search for existing issues and open PRs first** — add volume to existing ones rather than duplicating:

```bash
gh issue list --repo nicsuzor/academicOps --search "<failure keywords>"
gh pr list --search "<failure keywords>" --repo nicsuzor/academicOps
```

If an open PR addresses the issue, post your finding there (where it is most actionable). If both an issue and a PR exist, comment on both and cross-link them.

If an existing issue (and/or PR) matches:

- **New occurrence** (same problem, new incident): post a **delta comment** — new date, new incident facts, new impact angle only. Never restate the title, background, or anything already in the body or prior comments. One short paragraph maximum.
- **Structural correction** (wrong framing, wrong title, analysis needs updating): use `gh issue edit` — do not comment.

```bash
# Delta comment on PR — actionable feedback where the fix is happening:
gh pr comment <PR_N> --repo nicsuzor/academicOps \
  --body "New incident (<date>): [what happened]. Impact: [concrete cost]."

# Delta comment on issue — new incident facts only, no background recap:
gh issue comment <ISSUE_N> --repo nicsuzor/academicOps \
  --body "New incident (<date>): [what happened]. Impact: [concrete cost]."

# If both a PR and an issue exist, append the cross-link to each body:
#   PR body suffix:    " (Cross-posted to issue #<ISSUE_N>)"
#   Issue body suffix: " (Cross-posted to PR #<PR_N>)"

# Structural correction — edit title, body, or both:
gh issue edit <ISSUE_N> --repo nicsuzor/academicOps --title "<new-title>" --body-file /tmp/issue-<slug>.md
```

If no existing issue, perform root cause analysis and file:

```bash
# Write root-cause report to /tmp/issue-<slug>.md, then:
gh issue create --repo nicsuzor/academicOps \
  --title "Bug: <brief-slug>" \
  --body-file /tmp/issue-<slug>.md \
  --label "bug" --label "criticality:<level>"
```

**New issue body: forensic fields only, no narrative preamble. Lead with the failure; stop at impact.** Factual structural articulation is allowed; no remediation proposals (`recusal`):

Provide a clear, unstructured incident report containing:

1. **Incident facts**: What failed and why. Include any relevant logs or transcript excerpts.
2. **Structural shape**: How the framework's shape contributed (name any rules that fired or were missing).
3. **Impact**: The concrete cost of the failure (e.g. agent turns burned, downstream manual actions).

Do NOT propose what should change — only document what existed at the time of the incident and the structural realities of why it failed.

Issues that include a "suggested axiom," "proposed gate," or any remediation are out-of-scope under `recusal` and will be edited down to the forensic core by the sweep agent. Volume bumps on existing issues (`gh issue comment`) follow the same discipline — facts and impact only.

**Why this discipline:** the sweep agent (or a strategic review) reads many incident reports against the enforcement map and the axiom set, and decides what to add, propagate, escalate, or leave alone. That cross-incident judgment is undermined when each incident report ships pre-packaged with the legislation its author thought it implied. The detached reviewer needs facts; the framework needs coherence; the recused incident agent provides one and protects the other by withholding the second.

In batch mode: cap at **3 issues per session**.

### 6. Stamp the transcript as reviewed

```yaml
reviewed_by:
  - agent: "<model-name>"
    date: "<ISO 8601 datetime>"
    machine: "<hostname via bash>"
    verdict: "<EXCELLENT|GOOD|ADEQUATE|POOR|FAILING>"
    issues_filed: <count>
```

Append (do not replace) if `reviewed_by` already exists.

### 7. Framework reflection

```
## Framework Reflection
**Prompts**: /survey retro [transcript path]
**Outcome**: [success/partial/failure]
**Accomplishments**: Reviewed <transcript>, filed <N> issues, stamped as reviewed.
**Issues filed**: [GitHub Issue URLs]
```

### Retro anti-patterns

| Anti-pattern                                                                                     | What to do instead                                                                                    |
| ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| Skimming                                                                                         | Read every line                                                                                       |
| "Overall good with minor issues"                                                                 | Quote specifically                                                                                    |
| Filing four separate issues for symptoms of one structural flaw (where one edit fixes all)       | Identify the structural flaw and file one issue mapping the symptoms back to it                       |
| Bundling N distinct fixable causes into one issue because they share a meta-class                | File one issue per cause; cross-link each child to the meta-class parent (or anchor) via `Refs #N`    |
| Inventing praise                                                                                 | Only genuine strengths                                                                                |
| Reviewing your own session                                                                       | Review a DIFFERENT session                                                                            |
| Filing > 3 issues per session                                                                    | Triage first; group structural causes; cap at 3 issues                                                |
| New issue for known pattern                                                                      | Comment on existing issue                                                                             |
| Restating background or title in a bump comment                                                  | Post only the new delta: date, new incident facts, new impact angle. Reader already read the issue    |
| Verbose bump comment with narrative setup or recap                                               | One short paragraph max — lead with what happened this time; stop there                               |
| Verbose new issue body with narrative preamble or framing                                        | Lead with the failure facts; no throat-clearing; no framing preamble                                  |
| Including "suggested axiom", "add a gate", or any remediation proposal in the report (`recusal`) | Stop at facts + structural-context + impact. The sweep agent legislates from a detached context       |
| "We should change Y because I just hit X"                                                        | The agent that hit X is recused (`recusal`). Surface the incident; leave the change proposal to sweep |
| Citing a single session as justification for a new mechanism                                     | Recurrence is the evidence base for framework change, not the salience of one transcript              |

---

## Mode: trend

**Purpose**: Review many sessions to assess whether a SYSTEM (gate, agent, skill, workflow) is achieving its goals across the population. Produces an evidence-based trend report with recommendations.

**Distinction from retro**: retro reviews individual sessions for agent behavior. trend reviews MANY sessions to assess systemic effectiveness.

### 1. Define the review question

If vague, clarify: what component, what success criteria, what time window, what specific concern?

### 2. Identify data sources

| Source               | Contents                            | Location                        |
| -------------------- | ----------------------------------- | ------------------------------- |
| Markdown transcripts | Full conversations (primary source) | `~/.aops/sessions/transcripts/` |
| Session summaries    | High-level overviews                | `~/.aops/sessions/summaries/`   |
| PKB tasks            | Task lifecycle data                 | Via `mcp__pkb__task_search`     |

Read relevant framework workflows first. For hook/gate reviews, check `09-session-hook-forensics.md`.

### 3. Sample strategically

- **Min sample**: 8 files **Max sample**: 15 files
- At least 2 from earliest period, 2 from most recent
- Size diversity (1 large, 1 small), session hash diversity
- Platform diversity if applicable (platform-specific bugs contaminate general conclusions)
- Random fill after satisfying structural criteria

Record your sample with filenames and selection rationale.

### 4. Deep-read each sample

Read every line. Extract:

- **Context**: what was the agent doing, what triggered this?
- **Component behavior**: did it behave correctly and proportionately?
- **Accuracy**: TP / FP / FN classification with specifics
- **Impact**: did the component's action change the session's trajectory?

### 5. Synthesize

Before aggregating, define what observable success looks like. If it's not observable in the data, state that upfront.

- True positive rate, false positive rate, estimated false negative rate
- Temporal trends: early vs late comparison
- Coverage map: what categories reliably detected vs missed?
- Cost-benefit: overhead vs quality improvement; is the component self-undermining?
- Platform isolation: do findings hold per platform independently?

### 6. Produce the report

```markdown
# Trend Review: <Component Name>

**Question**: <review question> **Date**: <today>
**Corpus**: <N> files, <date range> **Sample**: <N> files (criteria: ...)

## Executive Summary

[3-5 sentences. Is it working? Trend? Biggest issue? If data can't answer, say so — that IS the finding.]

## Objectives Verdict

| Objective | Verdict                                      | Evidence |
| --------- | -------------------------------------------- | -------- |
| [obj 1]   | ANSWERED / PARTIALLY ANSWERED / UNANSWERABLE | [why]    |

## Individual Assessments

### <filename> (<date>)

- **Context**: ... **Component behavior**: ... **Accuracy**: [TP/FP/FN] **Impact**: ...

## Aggregate Analysis

### Signal Quality / Temporal Trends / Coverage Map / Cost-Benefit

## Recommendations

[Specific, actionable, prioritised. Each cites evidence.]

## Confidence and Limitations
```

### 7. Save the report

```bash
mkdir -p ~/.aops/sessions/reviews
# Save to: ~/.aops/sessions/reviews/<component>-trend-<date>.md
```

### Trend anti-patterns

| Anti-pattern                             | What to do instead                         |
| ---------------------------------------- | ------------------------------------------ |
| Reviewing all files                      | Sample strategically, read deeply          |
| Claims without citations                 | Every claim cites a specific file          |
| No temporal comparison                   | Always compare early vs late               |
| Treating absence as evidence             | Distinguish measurement gaps from findings |
| Platform-specific bugs as general claims | Isolate platform variables                 |
| Burying the primary finding              | Lead with structural limitations           |
| Substituting proxy findings              | Deliver explicit verdicts per objective    |

---

## Mode: sweep

**Purpose**: Run ONE cycle of the open-issue sweep on `nicsuzor/academicOps`. Classify ≤ 20 open issues, **proceed autonomously on the rational defaults** (apply each disposition as the rubric decides it), gate only on genuine judgment calls, log the cycle. **HALT after one cycle.** Fix-epics are left `queued` for `/supervisor` in a later session. The sweep actively shrinks the backlog — it consolidates and closes duplicates and aggregates related issues into fix-epics, it does not merely label them.

Sweep runs **undirected** (cursor-driven, the default) or **directed** — given a focus (a specific blocker, failure, or issue the user is fighting _right now_), it investigates and prioritises that focus first while still pulling and reviewing the general backlog. Direction is not a recency exemption — see "Directed vs undirected sweep" below.

**Detached judgment role (`recusal`)**: sweep is the framework's _legislative_ phase. The agents that diagnosed each incident are recused; the sweep agent reads their forensic reports together with the enforcement map and the axiom set, and is the one allowed to propose adding, propagating, escalating, or retiring rules. Recency exposure is what makes this work — sweep enters with no prior context on any individual incident, so the cross-incident pattern (not the salience of any one report) drives the call.

**Proceed autonomously on the rational defaults.** The sweep does NOT halt for per-bucket sign-off on every disposition. Apply the low-blast-radius defaults — evidence-bump, defer, consolidate-duplicate (consolidate + close), aggregate, single-task creation, and fix-epic creation that stays `queued` — without asking. Closing or consolidating a GitHub _issue_ is reversible (it reopens, the comment trail persists), so it is in-scope for autonomous action. Gate ONLY on:

- **Genuine judgment calls** — an ambiguous classification, or any issue the rubric sends to **Needs human triage** (decidable in < 30s by a fresh agent; if not, it gates).
- The two **HARD HALTS** that remain absolute:
  - **(a) The locked merge gate** — never auto-merge a PR, never mint, simulate, or stand in for an approval. Opening a visible PR / merging to `main` stays gated and is not a sweep action.
  - **(b) Destructive or externally-irreversible operations** — anything that cannot be reopened or reverted (force-pushes, history rewrites, deleting data, external side-effects beyond GitHub issue state).

**No improvised dispositions** beyond those in the rubric below (the rubric now sanctions consolidate-duplicate, aggregate, and the rest — an unsanctioned seventh bucket still goes to Needs human triage). No cursor in task body (labels ARE the cursor). No proposal to **add or escalate** enforcement (new gate, new axiom, tier-bump, new hook firing surface) without ≥3 cited recurrences (the CBA bar in ENFORCEMENT-MAP.md). Bug fixes within an existing enforcement surface at the same tier, and user-directed architectural changes, are NOT add-or-escalate proposals — a single forensic incident (or explicit user directive) is sufficient for `fix-epic` or `single-task`.

### Directed vs undirected sweep

Sweep accepts an optional **focus** — a specific blocker, failure, or issue the user is fighting _right now_ (passed as the invocation argument, e.g. `/issue-sweep 1573` or `/issue-sweep "agent infers rendered state instead of looking"`). With no focus, sweep runs undirected: cursor-driven over the oldest-untriaged batch.

A focus changes **what sweep attends to first, not how it judges.**

- **Attention / ordering** (a focus moves this): investigate the focal issue first — read it, its comments, and any linked forensic reports / transcripts — then pull every open issue that plausibly shares its root cause to the **front** of the batch so the cluster is triaged together.
- **Coverage** (a focus does NOT shrink this): after triaging the focal cluster, pull and classify the normal undirected batch. A directed sweep is _focus-first_, not _focus-only_. The cycle plan (step 3) MUST contain a general-batch section with the count of non-focal issues reviewed — an empty or absent general section is a failed directed sweep, not a fast one. If the focal cluster exhausts the batch budget, do not silently stop: name the exact cursor range left unreviewed (the oldest-untriaged issue numbers not reached) so the next cycle resumes there.
- **Judgment standard** (a focus does NOT relax this): the detached pyramid-position review (§2b) and the escalation evidence bar are unchanged. Being _directed to prioritise_ an issue is not the same as importing the recency bias `recusal` exists to defeat — that bias is about adopting an incident's _pre-authored legislation_ verbatim, not about which issue you look at first. Distinguish two different user inputs: a **focus** ("investigate this blocker first") only sets attention; a **directed change** ("change rule X this way") substitutes for the recurrence bar _for that specific change_ (per §2b). A focus is never, by itself, a directed change. So any add-or-escalate proposal arising from the focal issue MUST show its evidence inline in the cycle plan — the ≥3 recurrence links, or the explicit user directive quoted — and must NOT cite the user's focus, or the focal incident's salience, as that evidence. If you cannot show ≥3 recurrences or a directive, the disposition is `defer` with `needs-more-recurrences`, exactly as in an undirected sweep. A clear bug fix within an existing surface at the same tier still dispatches on a single incident.

The point: a user fighting a live blocker can aim the sweep at it without the sweep abandoning its backlog scan or lowering its bar for what counts as a justified framework change.

### Disposition rubric

| Disposition             | Criterion                                                                                                                | Action                                                                                                                                                                                                                                  | Label                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| `close-as-stale`        | > 90d + no recent comments + root cause fixed, OR describes behaviour framework no longer has (verifiable by cheap grep) | `gh issue close` with comment citing fix                                                                                                                                                                                                | `triaged-stale`         |
| `consolidate-duplicate` | Two+ issues are the same underlying problem                                                                              | Pick a canonical; merge any unique detail from the others into it FIRST; then close each duplicate with a comment cross-linking the canonical via `#N`. Apply autonomously.                                                             | `triaged-duplicate`     |
| `aggregate`             | Several related-but-distinct issues share one root cause / fix surface and are better solved together                    | Fold the related issues into ONE fix-epic (cap 5 sources); close each source with a pointer comment citing the epic / canonical via `#N` (merge any unique AC detail into the epic first); leave the epic `queued`. Apply autonomously. | `triaged-aggregate`     |
| `evidence-bump`         | Volume bump accumulating evidence on a related open issue (e.g. fix-epic)                                                | Leave open; MUST comment citing canonical via `#N`                                                                                                                                                                                      | `triaged-evidence-bump` |
| `single-task`           | Atomic: AC clear, ≤ 3 files, one obvious implementation, no cross-component coordination                                 | File polecat task with `Closes #N`. Apply autonomously.                                                                                                                                                                                 | `triaged-single`        |
| `fix-epic`              | Multi-step, multi-file, or design-required                                                                               | Create epic + decompose, leave `queued`. Apply autonomously.                                                                                                                                                                            | `triaged-epic`          |
| `defer`                 | Real but blocked or low-criticality                                                                                      | Apply `triaged-defer` + `revisit-by-YYYY-MM-DD` comment                                                                                                                                                                                 | `triaged-defer`         |

Every disposition must be decidable in < 30 seconds by a fresh agent. If longer: "Needs human triage."

### Cursor strategy

```bash
gh issue list --repo nicsuzor/academicOps --state open --limit 100 \
  --search 'sort:created-asc -label:triaged-stale -label:triaged-comment -label:triaged-duplicate -label:triaged-aggregate -label:triaged-evidence-bump -label:triaged-single -label:triaged-epic -label:triaged-defer' \
  --json number,title,labels,createdAt,updatedAt,comments,body \
  > /tmp/issue-sweep-batch.json
# Client-side sort: criticality-desc, age-asc. Take top 20.
```

**Directed focus (optional).** When the sweep is given a focus, additionally resolve the focal issue and its root-cause cluster and rank them ahead of the cursor batch:

```bash
# Focal issue(s) + same-root-cause siblings, pulled to the front:
gh issue list --repo nicsuzor/academicOps --state open --limit 30 \
  --search '<focus keywords, or the issue number>' \
  --json number,title,labels,createdAt,updatedAt,comments,body \
  > /tmp/issue-sweep-focus.json
# Triage the focal cluster first; then continue with the undirected batch above (dedup by issue number).
```

### 1. Pre-flight

```bash
gh issue list --repo nicsuzor/academicOps --state open --limit 1 --json totalCount
gh label list --repo nicsuzor/academicOps --limit 200 | grep -E '^(triaged-|criticality:)'
```

Create missing labels, then read the loop epic:

```
mcp__pkb__get_task(id="epic-a0523a25")  # halt if not in_progress
```

### 2. Pull batch (≤ 20 issues) and classify

For each issue: read body + ≤ 3 recent comments. Apply rubric. Group `fix-epic` and `aggregate` candidates by root cause (cap 5 issues per epic). Detect duplicates: two+ issues describing the same underlying problem collapse to one canonical (`consolidate-duplicate`); several distinct issues sharing one fix surface fold into one fix-epic (`aggregate` — e.g. the grounding/ratification meta-class folded into a single grounding fix-epic). Note one-line rationale per issue.

### 2b. Pyramid-position review for **enforcement-escalation** candidates (`recusal` — sweep's legislative role)

This step runs only for issues whose remediation would **add or escalate** a
rule — a new gate, a new axiom, a tier-bump (e.g. L1→L3), a new hook firing
surface. **Bug fixes** within an existing enforcement surface at the same
tier (correcting wrong logic or wrong prose in an existing skill, agent,
hook, or gate) follow the normal `fix-epic` / `single-task` path — they do
not require this section, and a single forensic incident is sufficient
evidence. **User-directed architectural changes** do NOT bypass this section —
pyramid-position reasoning still applies to establish where the fix lands on
the enforcement pyramid. Only the ≥3 recurrence requirement is waived;
the user's directive substitutes for that evidence.

For genuine add-or-escalate proposals, run this sequence before assigning a
disposition. This is the work that retro is forbidden to do; sweep is the
only mode allowed to author it.

1. **Read the forensic reports.** The issue body should be a clean incident report (per `recusal`). If it carries a "suggested axiom" or "proposed gate," strip that from your reasoning — the proposal was authored under prejudicial recency and is evidence of urgency, not of the right answer. Edit the issue to remove the stripped section and leave a comment explaining the `recusal` split.
2. **Generalise the failure.** Name the most general Root Cause Category from the documented vocabulary (Discovery Gap, Detection Failure, Instruction Gap, Instruction Weighting, Index Lag, Cross-workflow Gap, Enforcement Gap, Dropped Thread, Design Inversion, Wrong Layer of Abstraction, Rule Should Not Exist, Other) OR use a free-form framing if these do not fit. One per issue. _Instruction Gap_ means the agent's instructions were too shallow to produce excellent execution — the fix is an instruction rewrite via `/craft audit`, not a mechanism change.
3. **Map to existing mechanisms.** Read the enforcement map (repo-level) end-to-end (it is short by design). Grep AXIOMS.md and HEURISTICS.md for prior framing of the rule. List every existing mechanism that should plausibly have caught this failure, with its tier (L0–L7).
4. **Classify the failure shape**:
   - **Propagation failure** — rule exists at the right tier but didn't reach this surface. Fix is L1 propagation: edit the specific skill / agent / CORE.md text that needs to carry the rule. Same tier, more callsites.
   - **Escalation candidate** — rule exists but at a tier too cheap to beat the trained reflex. Apply the CBA from the enforcement map (repo-level) (≥3 recurrence links, named cheaper levels already tried with evidence, ongoing cost estimate, reversibility criterion). If you can't satisfy the CBA, the disposition is `defer` with a `needs-more-recurrences` comment, not an escalation.
   - **Rule absent** — name the rule before naming the mechanism. Phrase it as a sentence the user could quote. Then ask which tier it belongs at, defaulting to L0/L1 unless the CBA forces a higher placement.
5. **Default cheap, escalate reluctantly.** The enforcement map (repo-level) names the dominant failure mode: jumping to L3+ when the actual fix is L1 propagation. Most `exercise-authority` recurrences are L1 propagation failures; assume the same here unless evidence contradicts.
6. **Cite the row.** The disposition proposal must name either the row of the enforcement map (repo-level) the fix propagates from, or the new row it would add. "Add a gate" is not a disposition; "L1 propagation into agents/marsha.md lines XX–YY, citing existing axiom `halt-on-failure`" is.
7. **No-change is a valid outcome.** If the rule exists at the right tier and the failure was a single agent slip, the disposition is `close-as-stale` (or `consolidate-duplicate` to track volume) — not a framework change. Recurrence count is the evidence base; one slip is not.

The output of this step feeds the disposition decision in the rubric below (most often `fix-epic` for L1 propagation work, `defer` for "needs more recurrences," or `close-as-stale` for "no change warranted"). SAn **add-or-escalate proposal is a gate-stream item**: surface it to the user gate in step 3 with the pyramid-position reasoning visible. Bug-fix dispositions go through the normal user gate without this pyramid-position rationale — they require only the bug description and corrective scope. User-directed dispositions still include pyramid-position reasoning (citing the user's directive as the evidence base in place of recurrence links).


### 3. Apply the rational defaults; gate only judgment calls

Split the classified batch into two streams:

- **Default stream — apply autonomously, no sign-off.** Every issue whose disposition is a low-blast-radius default (consolidate-duplicate, aggregate, evidence-bump, close-as-stale, defer, single-task, fix-epic-left-`queued`). Execute these in step 4 directly, then report them as a done summary. Do NOT ask before applying.
- **Gate stream — surface and wait.** Only: issues the rubric sends to **Needs human triage** (ambiguous classification, not decidable in < 30s), add-or-escalate enforcement proposals that must show their evidence (per §2b), and anything brushing a HARD HALT (the locked merge gate, or a destructive/irreversible op). Use `AskUserQuestion` for the gate stream only; halt cleanly on decline and re-emit.

**Tie-breaker — when in doubt, gate.** The two streams are not symmetric: applying a default without sign-off is the autonomous behaviour Nic asked for, but applying something that should have gated is the failure this design must prevent. So if you cannot state, in one sentence, the rubric criterion that puts an issue in the default stream, it is NOT a rational default — route it to **Needs human triage** in the gate stream. "Rational default" means the disposition is one of the named rubric rows AND its criterion is met cleanly on the issue's own facts (no guessing at intent, no "probably a duplicate," no "close enough to stale"). A disposition you had to argue yourself into is a judgment call, not a default.

Report the cycle in this shape — the default-stream sections are an **applied/done log**, the gate section is the only one that waits:

```
## Cycle <N> — applied  (open before: <K>; batch: <M>)

### Applied autonomously (done)
- Consolidate-duplicate: #R → unique detail merged into #S, #R verified state:closed
- Aggregate: #A, #B, #C → folded into fix-epic <id> (queued), each source verified state:closed
- Evidence bump (left open): #T → bumped #U (both verified still open)
- Close (stale): #P → verified state:closed
- Defer: #Q (revisit-by YYYY-MM-DD)
- Single-task: #X → "<title>" (XS)
- Fix-epic (queued): <title> ← #D, #E

### Needs human triage / decision (waiting)
- #Z (rubric ambiguous: <reason>)
- <add-or-escalate proposal>: cost-ladder reasoning + ≥3 recurrence links or quoted directive (per §2b)
```

**Directed sweep:** lead the report with a **Focal cluster** section (the focus issue + its same-root-cause siblings), THEN the standard sections above for the general batch. The general-batch section is mandatory and must carry its reviewed-count; if it is empty because the focal cluster used the whole budget, say so explicitly and name the unreviewed cursor range (per "Directed vs undirected sweep" → Coverage). Any escalation inside the focal cluster still goes to the gate stream and shows its recurrence links or quoted user directive inline (per Judgment standard) — a focal escalation with no shown evidence is not applied, it gates.

### 4. Execute the default stream (low blast-radius first)

Order: consolidate-duplicate → aggregate → evidence-bump → close-as-stale → defer → single-task → fix-epic. Apply autonomously — these are not gated. (Gate-stream items wait at step 3 and are executed only after the user returns `y`.)

**All task-creation actions** MUST omit `severity` (or pass `severity=0`). Severity is a target-node-only signal — see skills/planner/SKILL.md (~lines 608-626). Setting it on a leaf inverts the focus queue.

- **consolidate-duplicate**: merge any unique detail from each duplicate into the canonical FIRST, then close each duplicate with a comment cross-linking the canonical via `#N`. MUST verify each closed duplicate is `state: closed` post-application, unless explicit carve-out. Workers verify before reporting `Done`.
- **aggregate**: create the fix-epic (intent + merged AC from all sources), then close each source issue with a pointer comment citing the epic / canonical via `#N`. MUST verify each source is `state: closed` post-application. Leave the epic `queued`; do NOT invoke `/supervisor`.
- **single-task**: `mcp__pkb__create_task` with issue body, AC, and `Closes #N` instruction. Apply the Trust the Worker doctrine ([[../aops/references/authoring-discipline]]).
- **fix-epic**: create epic + subtasks + `verify-parent` task. Apply the Trust the Worker doctrine ([[../aops/references/authoring-discipline]]) — intent+AC, no mid-stream approval theatre. Leave `queued`. Do NOT invoke `/supervisor`.
- Stamp the `triaged-*` label after each applied action.

### 5. Create per-cycle datestamped instance

```
# Read template for schema; create a fresh datestamped instance for this cycle
template = mcp__pkb__get_task(id="epic-a0523a25")
cycle_id = "epic-a0523a25-" + YYYYMMDD + "-" + HHMM  # e.g. epic-a0523a25-20260125-1430
instance = mcp__pkb__create_task(id=cycle_id, body=template.body)
mcp__pkb__append(id=cycle_id, content="<cycle entry per schema>")
```

Log must include: cursor=label-based; batch size; issues processed; per-disposition lists; open count after; triaged-* totals; stopping condition met (y/n with evidence).

### 6. Hand off to /qa

```
Skill(skill="qa", args="Verify cycle <N> of /issue-sweep on epic-a0523a25. Sample 20% (min 3). Reviewers: Pauli (cohesion) + RBG (axiom compliance). Add Marsha if single-tasks dispatched.")
```

### 7. HALT

Do not start the next cycle. Re-invoke `/survey sweep` (or `/issue-sweep`) for cycle N+1.

### Stopping condition

Loop stops only when ALL open issues are either: < 7 days old, stamped `triaged-defer` with revisit comment, linked to an in-progress fix-epic, or closed. PLUS: zero `criticality:critical` open without active fix-epic, zero `criticality:high` open > 14 days without active fix-epic.
