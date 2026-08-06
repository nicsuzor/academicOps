# Original User Request

## Initial Request — 2026-08-06T12:26:46Z

# Teamwork Project Prompt — Draft

Resolve a batch of 5 pending tasks spanning workflow component creation, plugin maintenance, and bug fixes in the codebase.

Working directory: /workspace
Integrity mode: development

## Requirements

### R1. Email Triage Workflow Component (aops_7ea0f95f)

Build the email triage workflow as a reusable `wf-*` component. The user has noted this is a blocker for other tasks, but the team may decide the optimal execution order (parallel vs sequential) for the entire batch.

### R2. Fix Dangling Plugin References (aops_4bc0dfea)

Resolve the divergence between source and distribution by fixing or removing dangling `/email` references in the shipped plugin set.

### R3. Fix list_tasks Timestamps (mem_dbaa694a)

Fix the bug where `list_tasks` returns bogus modified timestamps, ensuring staleness sweeps can be trusted.

### R4. Fix Due-date Bucketing (aops_05f34cb0)

Correct the due-date bucketing logic, which currently uses UTC and mis-buckets in a 10-hour Brisbane window. It should correctly account for Brisbane local time (UTC+10:00).

### R5. Clarify /daily Skill Status (aops_30f41ae4)

Fix the misdiagnosis where the system reports the `/daily` skill is missing due to an install failure. It was deliberately removed and this state needs to be accurately reflected.

## Acceptance Criteria

### Workflow & Plugin Maintenance

- [ ] The email triage workflow is available as a reusable `wf-*` component, and an independent test script verifies its functionality.
- [ ] A search (e.g., `grep`) confirms there are no longer any dangling `/email` references in the shipped plugin set.
- [ ] A test script or verification step confirms that the misdiagnosis regarding the `/daily` skill has been corrected.

### Bug Fixes

- [ ] A newly created test script objectively demonstrates that `list_tasks` returns correct, accurate modified timestamps.
- [ ] A newly created test script objectively demonstrates that due-date bucketing correctly handles dates within the Brisbane timezone context (UTC+10:00).

## Final Authorization

The user has provided authority for you to make changes, commit, push and file a PR. The acceptance gates are all on the PR side, and you are running in an isolated container. You do NOT need to ask for any further permissions. The user is unavailable (asleep) — do NOT pause to ask questions; make reasonable judgments and proceed all the way to completion (filing the PR).
