---
id: monitor-prevent-bloat
kind: process
category: meta
description: Regular maintenance pass to detect and remove framework documentation/skill bloat and duplication
requires: []
pairs-with: [verification]
conflicts: []
version: 1.0.0
permalink: workflows-process-monitor-prevent-bloat
---

# Process: Monitor & Prevent Bloat

**When**: regular maintenance, before major commits, or when file sizes are
visibly growing.

## Steps

1. **Check file sizes** — scan for markdown files by line count, descending.
2. **Flag approaching limits** — skills >80% of their line budget, docs >80%
   of theirs, or any file growing rapidly session over session.
3. **Analyze for duplication** — repeated content across files; summaries that
   duplicate the thing they summarize; information that should be referenced
   rather than repeated.
4. **Extract and reference** — move duplicated content to a single
   authoritative source, replace the rest with references, verify every
   reference resolves.
5. **Validate** — compose [[verification]]: run integration tests, confirm no
   conflicts introduced, confirm DRY is maintained.
