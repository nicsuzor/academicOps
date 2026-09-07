---
description: Every material action leaves a persisted record a third party can audit and re-trace.
trigger: off
---

## Full Observability: commit and push your work often, with informative messages

Each discrete set of changes must be accompanied by a git commit with adequate explanatory reasons.

You should commit and push immediately after making a set of changes.
Committing and pushing frequently allows you to:

- guarantee that your reasoning travels with the specific changes you make
- provide reasons that are both more informative and more concise because they are scoped smaller
- be resilient to unexpected outages, failures, and pre-emption
- ensure your reasons are judged as more trustworthy because they are recorded contemporaneously, not backfilled
- avoid polluting your outputs with meta-commentary

The branches you are provided are yours for writing to, and the remote is your only backup. Push often; we can always squash later to clean up.
