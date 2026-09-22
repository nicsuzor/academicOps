---
title: Reconcile Task Graph
type: template
description: Truth maintenance over the task graph -- mark merged PRs done, route aged work, and cancel moot claims based on world-facts.
tags: [reconcile, workflow]
---

## What this pass does

Maintains truth across the task graph. It is the sole writer of the `done` status. The pass applies world-facts without evaluating acceptance criteria or re-planning.

## Obligations & Exit Criteria

1. **Merged PRs**: Mark tasks `done` *only* on observing a merged gating PR. No acceptance-criteria judgment after merge.
2. **Rot and Mootness**:
   - Cancel tasks when a premise is falsified, referent destroyed, or superseded by merge.
   - You must write the evidence to the node body before cancelling.
   - Demote tasks to `inbox` when a fact they rely on is absent but cannot be proven destroyed.
3. **Staleness**: Route aged tasks to `review` for Sara. Do not reset abandoned claims.
4. **Completed-but-uncertified**: Do not judge uncertified work or forward it.
5. **Two-step mutation**: Every demotion/cancellation must append evidence to the body, then explicitly set the frontmatter status.
6. **Return affected**: When a node is completed, demoted, or cancelled, return its newly unblocked dependents or invalidated siblings to `inbox`.
7. **Hygiene**: No pruning unless mandated by a ratified graph-hygiene rule set. No re-planning or arbitrary closure.

## Daily Note Ownership

This workflow appends its daily findings to the **"Left over from today"** section of the daily note (`[[tpl_daily]]`), and is that section's single owning mechanism. The "**Asks filed**" section belongs to the capture mechanism; never merge or write to it here.

## Output

Emit exactly one synthesized result:
1. Cancellations, each stating: id, trigger (person's decision, referent destroyed, superseded, premise falsified), and written evidence.
2. Tasks that need a person's decision.
3. What you changed, what you found and left alone, and demotions to `inbox`.
4. The remaining single item the next sweep should pick up, and the sweep window.
