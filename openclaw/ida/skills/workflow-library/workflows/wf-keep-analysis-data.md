---
alias:
  - wf-keep-analysis-data
description: For long-running analyses whose data is somewhat difficult, slow or expensive to collect, save the intermediate data temporarily so it can be queried again; skip when collection is trivial.
id: wf-keep-analysis-data
tags:
  - wf-template
  - analysis
title: wf-keep-analysis-data
type: template
---

## What this step does

Keeps the intermediate data a long-running analysis collects, for a while, so a follow-up question or a changed assumption can be answered by querying the saved data instead of collecting it again.

## Procedure

1. **Judge the collection.** If the data was trivial to collect, skip this step. If it was somewhat difficult, slow or expensive to collect, continue.
2. **Save the intermediate data** temporarily, somewhere the analysis can query it again.
3. **Record where it is** in the task's result.

## Output contract

When the step applies: the intermediate data saved temporarily, and its location recorded in the task's result. When collection was trivial: nothing.

## When to include

Long-running analyses only.
