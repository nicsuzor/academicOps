# PR Triage Dashboard Procedure

This procedure generates a traffic-light decision dashboard for batch PR triage. It is triggered when the `repo-sync-cron` artefact reports **≥ 10** open PRs across tracked repositories.

**Note:** This is an editorial triage surface (producing approve/hold decisions). It complements, but does not replace, the factual `Outstanding Workflows` state bucketing.

## Procedure

1. **Check Threshold**: Use the PR state already loaded in Step 6.2. If the total open PR count is `< 10`, abort this procedure and do not render the dashboard subsection.
2. **Cluster**: Group the open PRs by theme based on PR titles and commit message excerpts. Aim for 4–7 clusters of 2–7 PRs each.
   _Heuristic: If a PR doesn't share a theme with at least one other, give it its own cluster rather than forcing a batch._
3. **Dispatch Subagents**: For each cluster, dispatch one subagent in parallel. Provide the subagent with the PRs in its cluster and the specific brief template below.
4. **Render Dashboard**: Roll up the cluster cards into the daily note under `## What Needs Attention` -> `### PR Triage Dashboard` (sibling to `Outstanding Workflows`).

## The Artefact (Decision-Card Format)

Each cluster card contains three buckets (omit empty sections) and a concluding verdict:

- **🟢 GREEN — approve.** Table with PR / Title / What it does (1 sentence) / My read (1 sentence). Ensure it works, is honest, not a bad idea/implementation, no duplication.
- **🔴 RED — your call.** Table with PR / What / Why / Approach (each cell 1 sentence), THEN a "Concerns:" prose block under it with 1–3 sentences per PR naming the alignment/scope/architecture question requiring human judgment.
- **🟡 IN PROGRESS — pipeline handling.** Table with PR / Title / Why revising. For PRs with CI failures or mechanical reviewer flags that the pipeline will catch. Nic doesn't act on these.
- _(Optional)_ **📝 DRAFT — for awareness.** For draft PRs worth flagging direction now.

**Cluster Verdict**: 1–2 sentences naming the theme and what Nic actually has to decide.

## Triage Discipline (Bake into Dispatch)

These discipline rules must be applied by the reviewing subagent. The SSoT for these rules is task `aops-f4bd7368`.

1. **Override mechanical reviewer flags**: Gemini-reviewer can be wrong. Override and re-classify if a flag is mechanical (typecheck, trivial doc deduplication) or factually wrong.
2. **Flag what reviewers missed**: Look for scope creep, duplication, naming-against-reality bugs, and broken tool references.
3. **Don't flag incidental tech-debt bundling as scope creep**: Pyright pragmas, type suppressions, and config bumps bundled with a feature change are incremental debt repayment, NOT RED scope creep.
4. **CI red ≠ RED**: A mechanical failure the pipeline will catch is IN PROGRESS. RED is reserved for semantic/architectural/alignment concerns requiring human judgment.
5. **Surface pipeline gaps explicitly**: If a PR has reviewer concerns unaddressed for hours, diagnose the gap (which loop should have caught it; why it didn't).

## Subagent Dispatch Brief Template

Use this template when invoking the subagent for each cluster.

```text
You are a PR triage subagent evaluating a cluster of PRs around the theme: <THEME>.
Your goal is to produce a decision card for this cluster. Read the PRs using `gh pr view -R <repo> <number>` and `gh pr diff -R <repo> <number> | head -400` (sample more only if load-bearing).

Discipline Rules:
1. Override reviewer flags when they're noise (mechanical or factually wrong).
2. Flag what reviewers missed (scope creep, duplication, etc.).
3. INCIDENTAL DEBT REPAYMENT IS NOT SCOPE CREEP. Do not flag pyright pragmas, type suppressions, or config bumps as scope creep. They are incremental burndowns.
4. CI red ≠ RED. Mechanical pipeline issues are IN PROGRESS. RED is for human judgment only.
5. Surface pipeline gaps explicitly if reviewer concerns sit unaddressed for hours.

Format your output using these buckets (omit empty):
🟢 GREEN — approve. (Table: PR / Title / What it does / My read)
🔴 RED — your call. (Table: PR / What / Why / Approach) followed by "Concerns:" prose.
🟡 IN PROGRESS — pipeline handling. (Table: PR / Title / Why revising)
📝 DRAFT — for awareness.

Finish with a 1-2 sentence Cluster Verdict naming the theme and what the human must decide.
```
