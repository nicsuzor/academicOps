---
title: Experiment Archival
type: reference
category: instruction
permalink: skills-analyst-experiment-archival
description: Patterns for archiving intermediate analyses and experiments when data pipelines change
tags: [experiments, archival, jupyter, research-methods, reference]
---

# Draft: Experiment Archival and Research Journaling

Notes on archiving intermediate analysis and experiments before data changes.

## 2025-10-29 - Archiving Analysis Before Data Removal

**Context**: TJA project, scorer template quality improvement experiment

**User request:**

> /analyst we just proved a major increase in quality with the scorer template change. From now on, that's the new standard. We will only use scorer results in the new format from this point forwards. Before we clean our dashboard and dbt models, I want you to move all our analysis of scorer reliability relevant to this experiment (including our diagnosis of the issue and our proof of success) to a single streamlit page or jupyter notebook or something filed with today's date. I want to see all the charts created and saved in a way that they can serve as an archive of our experiment. my plan is that after today, we will NO LONGER be able to run these queries, because I intend to excise ALL OLD SCORER DATA from the DBT staging tables. I don't yet know what the best way of archiving all our analysis is, but I want it in one single place, I want the charts and the explanation and the tables all there, and I want it stable so that we will be able to look at it in future without re-running anything. Ultrathink about what's best -- I trust you to come up with a solution based in best practices for academic research. This won't form part of our ultimate analysis in the paper, so it doesn't have to be reproducible, but it has to be journaled.

**Situation**:

- Proved major quality increase with new scorer template
- New format becomes the standard going forward
- About to remove ALL old scorer data from dbt staging tables
- Need to archive all analysis of old vs new format comparison
- This analysis won't be in final paper but must be journaled

**Requirements identified**:

- Single location for all experiment analysis (charts, explanations, tables)
- Stable format that can be viewed in future without re-running
- Not reproducible (since data will be removed) but must be journaled
- Should follow academic research best practices for process documentation

**RESOLUTION: Jupyter notebook with HTML export**

- Created comprehensive Jupyter notebook with all analysis
- Saved all chart outputs in notebook
- Exported to static HTML for long-term viewing
- Filed in `experiments/20251029_scorer_validation_experiment.ipynb`
- HTML export ensures viewability without re-running code

**Key insight**: Need distinction between:

- **Reproducible research** (final analysis, dbt models, goes in paper)
- **Process documentation** (intermediate experiments, decisions, diagnosis)

Process documentation characteristics:

- Won't be reproduced (data might be removed)
- Still needs to be stable/viewable
- Archives research decisions and experiments
- Shows the journey, not just final destination

**VALIDATED PATTERN**: When making major data pipeline changes:

1. Archive all related analysis BEFORE the change
2. Create comprehensive Jupyter notebook with all outputs saved
3. Export to static HTML for long-term viewing
4. Timestamp and link to the change that made it necessary
5. File in experiments/YYYYMMDD-archive-description/
6. Clean up working files after archive is committed

**PROMOTE TO FORMAL PATTERN:** This pattern worked extremely well. Should be formalized into a reusable skill.

**ACTION TAKEN:** Created "archiver" skill to automate this workflow for future use.

## Patterns to Watch For

Track whether this becomes a recurring pattern:

- [ ] Do we often need to archive before removing/changing data?
- [ ] What format works best for these archives?
- [ ] Should this be integrated into standard workflow?

If this happens 3+ times, promote to formal guidance in experiment-logging.md.
