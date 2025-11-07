---
title: "academicOps Framework Audit"
type: audit
description: "Current state of the repository for comparison against README.md specification, including compliance status, missing components, and drift from architectural principles."
tags:
  - audit
  - compliance
  - framework-state
relations:
  - "[[README]]"
  - "[[ARCHITECTURE]]"
---

# academicOps Framework Audit

**Purpose**: Document current state of the repository for comparison against README.md specification.

**Last Updated**: 2025-11-06

---

## Current Repository Statistics

### Component Counts

- **Agents**: 7 total
- **Skills**: 20 total (19 shown in instruction tree)
- **Slash Commands**: 8 total
- **Hooks**: 17 total (16 shown in instruction tree)
- **Chunks**: 4 core files (AXIOMS, INFRASTRUCTURE, SKILL-PRIMER, AGENT-BEHAVIOR)

### File Sizes (Lines)

**Agents** (target: <500 lines):

- SUPERVISOR.md: 24 KB
- STRATEGIST.md: 9.9 KB
- task-manager.md: 11 KB
- scribe.md: 11 KB
- end-of-session.md: 8.9 KB
- DEVELOPER.md: 6.4 KB
- ANALYST.md: 1.7 KB

**Skills** (target: SKILL.md <300 lines):

-  skill-creator: 162 lines (23% reduction completed)
- L python-dev: 797 lines (59% over budget) - Issue #142
- L git-commit: 516 lines (3% over budget) - Issue #142

**Documentation**:

- docs/bots/BEST-PRACTICES.md: 705 lines
- docs/INSTRUCTION-INDEX.md: 24 KB
- docs/hooks_guide.md: 26 KB
- docs/DEPLOYMENT.md: 15 KB

### Anti-Bloat Status

**Compliant**:

-  skill-creator (162 lines)
-  Most agents under 500 lines

**Violations** (Issue #142):

- L python-dev skill (797 lines)
- L git-commit skill (516 lines)

**Architectural Solutions Implemented**:

- resources/ symlinks pattern (skill-creator )
- DRY via chunks/ references
- Anti-bloat checklist enforcement

---

## Component Inventory

### Agents (7)

| Agent          | Purpose                    | Size   | Status       |
| -------------- | -------------------------- | ------ | ------------ |
| ANALYST        | Data analysis workflows    | 1.7 KB |  Minimal     |
| DEVELOPER      | Development workflows      | 6.4 KB |  Good        |
| STRATEGIST     | Strategic thinking partner | 9.9 KB |  Check bloat |
| SUPERVISOR     | Multi-agent orchestration  | 24 KB  |  Check bloat |
| scribe         | Silent context capture     | 11 KB  |  Check bloat |
| task-manager   | Email-to-task extraction   | 11 KB  |  Check bloat |
| end-of-session | Session cleanup            | 8.9 KB |  Good        |

### Skills (20)

**Framework Skills** (8):

- agent-initialization
- aops-bug
- aops-trainer (has resources/)
- claude-hooks
- claude-md-maintenance
- skill-creator (has resources/, 162 lines) 
- skill-maintenance
- document-skills

**Development Skills** (4):

- git-commit (516 lines - needs reduction)
- github-issue
- test-writing
- no-throwaway-code

**Utility Skills** (8):

- analyst
- archiver
- email
- pdf
- scribe
- strategic-partner
- tasks
- tja-research (may be project-specific?)

### Slash Commands (8)

| Command      | Invokes            | Pattern                |
| ------------ | ------------------ | ---------------------- |
| /analyst     | analyst skill      | Mandatory skill-first  |
| /dev         | dev skill          | Needs verification     |
| /email       | email skill        | Needs verification     |
| /error       | aops-bug skill     | Needs verification     |
| /log-failure | aops-bug skill     | Needs verification     |
| /ops         | Framework help     | Direct                 |
| /STRATEGIST  | strategist agent   | Needs verification     |
| /trainer     | aops-trainer skill | Mandatory skill-first  |

### Hooks (17)

**SessionStart** (1):

- load_instructions.py

**PreToolUse** (1):

- validate_tool.py (26 KB)

**PostToolUse** (1):

- stack_instructions.py (8.6 KB)

**Stop** (2):

- validate_stop.py
- request_scribe_stop.py

**Logging Hooks** (9):

- log_todowrite.py
- log_sessionend.py
- log_session_stop.py
- log_subagentstop.py
- log_posttooluse.py
- log_precompact.py
- log_userpromptsubmit.py
- log_notification.py
- hook_debug.py

**Other** (3):

- autocommit_tasks.py
- sync_environment.sh
- hook_models.py

---

## Documentation Structure

### Core Documentation (agents/)

**Auto-loaded at SessionStart**:

- core/_CORE.md ' References chunks/

**Available via commands**:

- DEVELOPMENT.md
- TESTING.md
- DEBUGGING.md
- STYLE.md
- INSTRUCTIONS.md

### Agent Documentation (docs/bots/)

**Framework development**:

- BEST-PRACTICES.md (705 lines) - Evidence-based guidance
- skills-inventory.md (11.5 KB)
- skill-invocation-guide.md (3.5 KB)
- delegation-architecture.md (13 KB)
- challenge-responses.md (14 KB)
- dev-tools-reference.md (12 KB)
- INDEX.md, MAINTENANCE.md

### Domain Documentation (docs/_CHUNKS/)

**Loaded by specific skills**:

- HYDRA.md (19 KB)
- PYTHON-DEV.md (19 KB)
- SEABORN.md (19 KB)
- STATSMODELS.md (19 KB)
- STREAMLIT.md (15 KB)
- MATPLOTLIB.md (10 KB)
- E2E-TESTING.md (6.6 KB)
- GIT-WORKFLOW.md (1.5 KB)
- FAIL-FAST.md (1.8 KB)
- DBT.md (1.7 KB)
- TESTS.md (1.2 KB)

### Archived Documentation (docs/_UNUSED/)

**35 archived files** - Legacy patterns, old architectures

---

## Architecture Patterns

### resources/ Symlinks

**Status**: Partially implemented

**Implemented**:

-  skill-creator/resources/ (AXIOMS, INFRASTRUCTURE, SKILL-PRIMER)
-  aops-trainer/resources/ (assumed from skill invocation)

**Needs Implementation**:

- L 18 other skills lack resources/
- L No validation script to check compliance

### Mandatory Skill-First Pattern

**Status**: Partially implemented

**Implemented**:

-  /trainer command (mandatory skill-first)
-  /analyst command (mandatory skill-first)

**Needs Verification**:

-  /dev, /email, /error, /log-failure commands
-  Agent delegation patterns

### Anti-Bloat Enforcement

**Status**: Recently added to skill-creator

**Checklist exists**:  In skill-creator SKILL.md **Hard limits defined**:  (<300 lines for skills, <500 for agents) **Pre-commit enforcement**: L Not yet implemented **CI validation**: L Not yet implemented

---

## Experiment Log Summary

**Total Experiments**: 18+ logs in experiments/

**Recent Experiments**:

- 2025-11-06: skill-creator rewrite (SUCCESS - 23% reduction)
- 2025-10-30: Supervisor tight orchestration
- 2025-10-30: Scribe detail balance
- 2025-10-29: Supervisor multi-stage quality gates
- 2025-10-27: TJA context loading
- 2025-10-26: Canonical settings symlink
- 2025-10-24: Skills-first architecture
- 2025-10-24: Task process regex fix

---

## Known Issues

### Open GitHub Issues (Relevant to Framework)

**Bloat Issues**:

- #142: python-dev (797 lines) and git-commit (516 lines) exceed budget
- #116: TRAINER.md exceeds 500-line target (729 lines)

**Architecture Issues**:

- #179: /dev command should invoke supervisor agent
- #175: Create validation scripts for supervisor references
- #149: test-writing skill not auto-invoked (TDD violated)
- #193: Integrate Basic Memory as core knowledge system

**Skill Issues**:

- #157: aops-bug scope boundaries unclear
- #180: Agents use generic voice instead of user style
- #184: Stop hook regression (end-of-session broken)

---

## Orphaned Files

**6 orphaned files** identified in instruction tree:

- AGENT-BEHAVIOR.md
- INSTRUCTIONS.md
- DBT.md
- HYDRA.md
- README.md (this audit addresses)
- STREAMLIT.md

**Action needed**: Verify whether orphaned or improperly detected.

---

## Compliance Summary

###  Strengths

1. **Modular chunks architecture** working correctly
2. **Three-tier loading** system functional
3. **Experiment-driven development** established
4. **Anti-bloat pattern** documented in skill-creator
5. **DRY compliance** via symlinks proven effective

###  Areas for Improvement

1. **resources/ symlinks** not universally applied (2/20 skills)
2. **Anti-bloat violations** in 3 components (python-dev, git-commit, TRAINER.md)
3. **Skill-first pattern** not consistently enforced across commands
4. **CI validation** missing for anti-bloat rules
5. **Documentation bloat** in several large files

### <¯ Immediate Priorities

1. Apply modular references pattern to python-dev and git-commit (Issue #142)
2. Add resources/ symlinks to remaining 18 skills
3. Verify/fix mandatory skill-first pattern in all slash commands
4. Create CI validation for anti-bloat rules
5. Audit and refine bloated agents (SUPERVISOR, STRATEGIST, scribe, task-manager)

---

## Measurement Methodology

**How to regenerate this audit**:

```bash
# Component counts
find agents/ -name "*.md" | wc -l
find skills/ -name "SKILL.md" | wc -l
find commands/ -name "*.md" | wc -l
find hooks/ -name "*.py" -o -name "*.sh" | wc -l

# File sizes
wc -l agents/*.md
wc -l skills/*/SKILL.md
wc -l docs/bots/*.md

# resources/ compliance
find skills/ -type d -name "resources" | wc -l

# Instruction tree
python scripts/generate_instruction_tree.py
python scripts/validate_instruction_tree.py
```

**Update frequency**: After each major structural change or quarterly review.

---

## Change Log

- **2025-11-06**: Initial audit created, separated from README.md
- skill-creator rewrite completed (162 lines, resources/ added)
