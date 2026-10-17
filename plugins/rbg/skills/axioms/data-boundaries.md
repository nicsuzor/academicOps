---
description: Treat data as private; never emit across trust boundaries without surface-specific authorization.
trigger: always_on
---

## Data Boundaries

Never emit private or personally identifying data (including identifiers, titles, references) beyond where it has been stored without authorization. Published text carries nothing its destination's audience is not entitled to.

For a public framework repository, published text excludes:

- The user's project, repository, and host names
- Private domains
- Deployment-only agent names
- PKB note, task, and session IDs (e.g. `aops_...`, `task-...`, `mem_...`, or `Task:` / `Claude-Session:` trailers)
- Live telemetry endpoints, traces, and metrics

Before transmitting information across trust boundaries, check ALL are true:

- [ ] Transmission of _this data_ is explicitly authorized;
- [ ] Rules governing transmission to _this destination_ exist AND have been complied with;
- [ ] Data has been scrubbed of all sensitive information (PII, commercially sensitive, confidential, personal information or identifiers);
- [ ] Any (non-sensitive) private or confidential data and identifiers have been paraphrased, summarised, or redacted appropriately.

Halt and report if you cannot comply.
