---
title: Bootstrap Operational State
type: reference
description: Current framework operational state during bootstrap phase
permalink: bootstrap
tags: [framework, bootstrap, operational-state]
---

# Bootstrap Operational State

**Last updated**: 2026-01-05

The framework is in **bootstrap mode**. Automated integration is non-functional. This document tracks what's trusted vs what needs verification.

---

## Trusted (Use These)

| Component | Location | Status |
|-----------|----------|--------|
| AXIOMS.md | `$AOPS/AXIOMS.md` | ✅ Authoritative |
| VISION.md | `$AOPS/VISION.md` | ✅ Authoritative |
| ROADMAP.md | `$AOPS/ROADMAP.md` | ✅ Authoritative |
| User context | `$ACA_DATA/data/CORE.md` | ✅ Authoritative |
| ACCOMMODATIONS.md | `$ACA_DATA/data/ACCOMMODATIONS.md` | ✅ Authoritative |
| Skills (manual read) | `$AOPS/skills/*/SKILL.md` | ✅ Read and follow |
| Observations | GitHub Issues (nicsuzor/academicOps) | ✅ Via `/log` command (see [[specs/reflexivity]]) |
| Tasks Skill | `$AOPS/skills/tasks/` | ✅ Manual script usage |
| Remember Skill | `$AOPS/skills/remember/` | ⚠️ Manual file creation (No Sync) |

---

## Not Trusted (Do Not Rely On)

| Component | Location | Issue |
|-----------|----------|-------|
| Claude Code hooks | `$AOPS/hooks/` | Not functional in Gemini |
| Automated skill invocation | N/A | Hook-dependent |
| Test suite | `$AOPS/tests/` | May be stale |
| Memory server | MCP tools | **FAILED** (Connectivity check) |
| Symlinks | `~/.claude/` | May not exist |

---

## Bootstrap Protocol

### Session Start
1. Run `commands/bootstrap-session.sh` to dump context (replace SessionStart hook).
2. Read `GEMINI.md` (instructions — loaded via MEMORY)
3. Read `BOOTSTRAP.md` (this file — operational state)
4. Read core docs only when doing significant framework work

### During Work
- **Skills**: Read `SKILL.md` first. Execute scripts manually via `uv run` in `$AOPS`.
    - Example: `cd $AOPS && uv run python skills/tasks/scripts/task_view.py`
- **Memory**: Use GitHub Issues for observations (per [[specs/reflexivity]]). Memory MCP supplements search.
- **Context**: Do not assume prior context exists.
- **Infrastructure**: Document gaps. Halt if blocked.

### No Ad-Hoc Automation (CRITICAL)
- **Use Existing Tools Only**: Do not create new scripts (e.g., `verify_foundation.sh`) to test the framework.
- **Manual Verification**: If a check is needed, run the commands manually in the shell or check the file content directly.
- **Reason**: Creating ad-hoc scripts introduces unverified code and noise. We verify the foundation by *inspecting* it, not by writing more code on top of it.

### Artifact Persistence (CRITICAL)
- **NO EPHEMERAL ARTIFACTS**: Do not save governance docs, plans, or reports to `.gemini/` or similar scratchpads.
- **Specs**: Compliance docs, rubrics, and standards go to `$AOPS/specs/`.
- **Project Data**: Audit reports, plans, and session records go to `$ACA_DATA/projects/<project-name>/`.
- **Reason**: We trust version control (Axiom 15) and data boundaries (Axiom 5). Ephemeral files violate self-documentation.

### Session End
- Log observations via `/log [observation]` → GitHub Issues (see [[specs/reflexivity]])
- Note any infrastructure gaps discovered

---

## Graduation Criteria

To move beyond bootstrap:

1. [x] Verify memory server connectivity (FAILED - Use files)
2. [x] Verify at least one skill works end-to-end (`tasks`)
3. [x] Verify reflection persistence across sessions (Confirmed)
4. [ ] Document which skills are verified working

Each component is activated individually after verification.

---

## Known Gaps

*Updated as gaps are discovered during sessions.*

| Gap | Discovered | Impact |
|-----|------------|--------|
| Hooks non-functional | 2026-01-05 | Manual context loading required |
| Symlinks may not exist | 2026-01-05 | Use $AOPS path directly |

---

## Next Steps

1. Test this session's reflection persists
2. Verify memory server access (if MCP available)
3. Test one skill (suggest: `tasks` or `remember`)
