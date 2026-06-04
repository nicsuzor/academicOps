---
title: Monitor and Prevent Bloat
type: automation
category: instruction
permalink: workflow-monitor-prevent-bloat
description: Process for monitoring file sizes and preventing framework bloat
---

# Workflow 4: Monitor and Prevent Bloat

**When**: Regular maintenance, before major commits, when file sizes growing.

**Steps**:

1. **Check file sizes**
   ```bash
   find "$AOPS" -name "*.md" -exec wc -l {} \; | sort -rn
   ```

2. **Flag approaching limits**
   - Skills >400 lines (80% of 500)
   - Docs >240 lines (80% of 300)
   - Any file growing rapidly

3. **Analyze for duplication**
   - Search for repeated content across files
   - Check for summaries that duplicate referenced content
   - Identify information that should be referenced, not repeated

4. **Extract and reference**
   - Move duplicated content to single authoritative source
   - Replace with references to that source
   - Verify all references resolve correctly

5. **Validate improvement**
   - Run integration tests
   - Verify no conflicts introduced
   - Confirm DRY principle maintained
