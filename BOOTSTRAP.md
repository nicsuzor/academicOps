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
| Accommodations | `$ACA_DATA/data/ACCOMMODATIONS.md` | ✅ Authoritative |
| Skills (manual read) | `$AOPS/skills/*/SKILL.md` | ✅ Read and follow |
| Reflection log | `$ACA_DATA/data/framework-reflections.md` | ✅ Append-only |

---

## Not Trusted (Do Not Rely On)

| Component | Location | Issue |
|-----------|----------|-------|
| Claude Code hooks | `$AOPS/hooks/` | Not functional in Gemini |
| Automated skill invocation | N/A | Hook-dependent |
| Test suite | `$AOPS/tests/` | May be stale |
| Memory server | MCP tools | Connectivity unknown |
| Symlinks | `~/.claude/` | May not exist |

---

## Bootstrap Protocol

### Session Start
1. Read `GEMINI.md` (instructions — loaded via MEMORY)
2. Read `BOOTSTRAP.md` (this file — operational state)
3. Read core docs only when doing significant framework work

### During Work
- Read skill files manually before following procedures
- Document any missing infrastructure encountered
- Do not assume prior context exists

### Session End
- Append reflection to `$ACA_DATA/data/framework-reflections.md`
- Note any infrastructure gaps discovered

---

## Graduation Criteria

To move beyond bootstrap:

1. [ ] Verify memory server connectivity
2. [ ] Verify at least one skill works end-to-end
3. [ ] Verify reflection persistence across sessions
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
