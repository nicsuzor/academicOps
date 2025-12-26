---
title: Design New Component
type: workflow
permalink: workflow-design-new-component
description: Process for adding new framework capability (hook, skill, script, command)
---

# Workflow 1: Design New Component

**When**: Adding new framework capability (hook, skill, script, command).

**Steps**:

1. **Verify necessity**
   - Search existing components for similar functionality
   - Document why existing components insufficient
   - Confirm alignment with framework philosophy

2. **Design integration test FIRST**
   - Define success criteria
   - Create test that validates component works end-to-end
   - Test must fail before component exists (prove it's testing correctly)

3. **Document in experiment log**
   - Create `data/projects/aops/experiments/YYYY-MM-DD_component-name.md`
   - Include hypothesis, design, expected outcomes

4. **Implement component**
   - Follow single source of truth principles
   - Reference existing documentation, don't duplicate
   - Keep scope minimal and bounded
   - **For hooks**: Add to settings.json and create script, but create no-op stub FIRST if removing (see hook safety below)

5. **Run integration test**
   - Test must pass completely
   - No partial success
   - Document actual vs expected behavior

6. **Update authoritative sources**
   - Update [[README.md]] if directory structure changes
   - Update [[hooks/prompts/intent-router.md]] if adding skill, command, or agent
   - Update relevant documentation to reference new component
   - Verify no documentation conflicts introduced

   **Documentation congruence check** (run after ANY component change):
   ```bash
   # Compare documentation claims to actual structure
   ls -d $AOPS/skills/*/       # vs INDEX.md skills section
   ls $AOPS/commands/*.md      # vs INDEX.md commands section
   ls $AOPS/agents/*.md        # vs INDEX.md agents section
   ls $AOPS/hooks/*.py         # vs INDEX.md hooks section
   ```

   **Verify all match**:
   - [[INDEX.md]] file tree (detailed authoritative structure)
   - [[README.md]] overview (brief summary, consistent with INDEX.md)
   - [[hooks/prompts/intent-router.md]] (intent router flowchart + capabilities)
   - Actual filesystem (ground truth)
   - [[ROADMAP.md]] (if they claim counts or completion percentages)

7. **Commit only if all tests pass**
   - Verify documentation integrity
   - Confirm single source of truth maintained
   - Validate no bloat introduced

## Hook Safety

**CRITICAL**: Claude Code loads hook configuration at session start and cannot reload mid-session.

**Adding hooks** (safe):
1. Add hook script to `hooks/`
2. Add hook entry to `config/claude/settings.json`
3. Commit and push
4. Next session loads new hook automatically

**Removing hooks** (requires stub):
1. ❌ NEVER delete hook script while session is active
2. ✅ ALWAYS create no-op stub first:
   ```python
   #!/usr/bin/env python3
   import sys
   print("{}")
   sys.exit(0)
   ```
3. Remove hook from `config/claude/settings.json`
4. Commit stub + settings change
5. After session restart, delete stub in separate commit

**Why**: Deleting hook script while session runs causes repeated errors until restart. Settings change won't take effect until new session loads config.
