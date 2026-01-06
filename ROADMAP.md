---
title: Framework Status
type: note
category: spec
permalink: aops-roadmap
tags:
  - framework
  - status
---

# Framework Status

**Last updated**: 2025-12-30

> **Why this file matters**: Agents have no persistent memory. ROADMAP.md is the current status - what's done, in progress, blocked. Update after completing significant work. Keep out: detailed how-to, specs, future speculation.

## Done

### Core Infrastructure

- ✅ **Session start loading** - AXIOMS.md, FRAMEWORK.md paths, user context injected
- ✅ **Prompt router v4** - LLM-first routing; only slash commands get direct routing, everything else → Haiku classifier with full capability index
- ✅ **Framework v3.0** - Categorical imperative, file boundary enforcement, skill delegation
- ✅ **Hook architecture** - Hooks inject context, never call LLM APIs directly
- ✅ **Hypervisor agent** - Full 6-phase pipeline (context → classify → plan → execute → verify → cleanup), QA checkpoints baked into TodoWrite
- ✅ **Effectual Planning agent** - Strategic planning under uncertainty; receives fragments, surfaces assumptions, proposes high-value next steps. See `specs/effectual-planning-agent.md`
- ✅ **Learning system** - 22+ thematic log files, /log command captures patterns
- ✅ **E2E testing** - 270 tests, 98% pass rate, multi-agent spawn validation
- ✅ **Documentation consolidation** - VISION grounded, ROADMAP simplified, AXIOMS pure, HEURISTICS added

### Skills

- ✅ **analyst** - Research data analysis (dbt, Streamlit, stats)
- ✅ **remember** - Knowledge persistence (markdown + memory server sync)
- ✅ **framework** - Convention reference, categorical imperative enforcement
- ✅ **osb-drafting** - IRAC analysis, citation verification
- ✅ **pdf** - Markdown → professional PDF
- ✅ **python-dev** - Production Python (fail-fast, type safety)
- ✅ **tasks** - Task management + email extraction + subtask checklists
- ✅ **task-expand** - Intelligent task breakdown with dependencies, automation detection (invoked by prompt-writer, /add)
- ✅ **transcript** - Session JSONL → markdown (full + abridged versions)
- ✅ **session-insights** - Orchestrates transcripts → daily summary → Gemini mining → experiment evaluation (consolidated from session-analyzer)
- ✅ **reference-map** - Extract framework file references → graph (JSON + CSV) for visualization

### Automations

- ✅ **Email → Tasks** - `/email` extracts action items, creates tasks
- ✅ **Task visualization** - `/task-viz` generates Excalidraw strategic overview
- ✅ **Citation management** - zotmcp + Zotero plugins
- ✅ **Writing style** - STYLE.md, STYLE-QUICK.md guides
- ✅ **Voice capture** - Chunked audio transcription (GCS/Chirp)
- ✅ **iOS note capture** - GitHub webhook → memory
- ✅ **Cognitive Load Dashboard** - Streamlit dashboard showing tasks + session activity + subtask progress
  - ✅ **Session Context Panel** - Active sessions with prompts from R2, TodoWrite state from local JSONL
- ✅ **Prompt Queue** - Zero-friction idea capture with chained prompts (`/q` capture, `/pull` execute). See `specs/prompt-queue.md`
- ✅ **bmem → memory migration** - 52 files migrated to memory server MCP tools
  - ⚠️ **TODO**: Audit `$ACA_DATA/` for remaining bmem references in user data files

## User Stories (Requirements)

| Story                                                                                    | Status       | Spec                                                             |
| ---------------------------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------- |
| Command Discoverability - users can easily find commands/skills to achieve their goals   | Implemented  | `specs/command-discoverability.md`                               |
| Plan Quality Gate - plans must be critiqued before presenting to user                    | Implemented  | `specs/plan-quality-gate.md`                                     |
| Framework-Aware Operations - agents have accurate architectural knowledge                | Requirement  | `specs/framework-aware-operations.md`                            |
| Multi-Terminal Sync - transparent version control across terminals/machines              | Implementing | `specs/multi-terminal-sync.md` (obsidian-git + PostToolUse hook) |
| Informed Improvement Options - fixes informed by tool docs + external research           | In Progress  | `specs/informed-improvement-options.md`                          |
| Memory Synthesis - specs synthesized after implementation per H23                        | Requirement  | `specs/` (convention, not file)                                  |
| Skill Specifications - every skill needs a spec per AXIOMS #29                           | Requirement  | See gap list below                                               |
| Session-End Sync - session insights update tasks/sub-tasks and daily.md with cross-links | Requirement  | `specs/session-sync-user-story.md`                               |

### Skills Without Specs (AXIOMS #29 Gap)

Per AXIOMS #29: "ONE SPEC PER FEATURE". Skills need specs to justify existence and document how they fit together.

| Skill                | Has Spec? | Priority                                       |
| -------------------- | --------- | ---------------------------------------------- |
| analyst              | ❌        | P2 - research support                          |
| dashboard            | ✅        | `dashboard-skill.md`                           |
| excalidraw           | ❌        | P3 - utility                                   |
| extractor            | ❌        | P2 - email workflow                            |
| feature-dev          | ✅        | `feature-dev-skill.md`                         |
| framework            | ✅        | `framework-skill.md`                           |
| framework-debug      | ❌        | P2 - debugging                                 |
| framework-review     | ❌        | P2 - review                                    |
| garden               | ❌        | P2 - maintenance                               |
| ground-truth         | ❌        | P2 - research                                  |
| learning-log         | ✅        | `learning-log-skill.md`                        |
| link-audit           | ❌        | P3 - maintenance                               |
| osb-drafting         | ❌        | P2 - domain-specific                           |
| pdf                  | ❌        | P3 - utility                                   |
| python-dev           | ✅        | `python-dev-skill.md`                          |
| reference-map        | ❌        | P3 - visualization                             |
| remember             | ✅        | `remember-skill.md`                            |
| review-training      | ❌        | P3 - training data                             |
| session-insights     | ✅        | `session-insights-skill.md`                    |
| ~~skill-creator~~    | N/A       | Replaced by plugin-dev@claude-plugins-official |
| supervisor           | ✅        | `supervisor-skill.md`                          |
| tasks                | ✅        | `tasks-skill.md`                               |
| training-set-builder | ❌        | P3 - training data                             |
| transcript           | ✅        | `session-transcript-extractor.md`              |

**P1 skills**: All P1 skills now have specs
**Total without specs**: 14 of 24

## In Progress

| Item                    | Status         | Next Step                                           |
| ----------------------- | -------------- | --------------------------------------------------- |
| Verification System     | P1             | Design decision needed                              |
| Self-Curating Framework | P1             | Working through 5 sub-items below                   |
| Plan Quality Gate       | ✅ Implemented | `agents/planner.md` - memory search + critic review |
| Claude Code Dev Skills  | ✅ Done        | Installed plugin-dev@claude-plugins-official        |

### Enforcement Improvements (from 2025-12-22 transcript analysis)

See `docs/ENFORCEMENT.md` for mechanism ladder. Choose enforcement level based on root cause.

| Fix                               | Level | Effort  | Root Cause                                           |
| --------------------------------- | ----- | ------- | ---------------------------------------------------- |
| Pre-Edit auto-read hook           | 4     | 1h      | Mechanical precondition - hook can enforce           |
| ROADMAP injection at SessionStart | 2     | 2h      | Missing context, not rule violation                  |
| Project CLAUDE.md entry points    | 2     | ongoing | Agents explore because they lack execution context   |
| Skill bypass enforcement          | 4     | TBD     | Rules don't compete with training priors - need hook |

### Self-Curating Framework

Goal: Framework becomes self-aware enough to curate its own evolution. See VISION.md "Self-Curating Framework" section.

| # | Item                     | Goal                                                                                        | Status                                              |
| - | ------------------------ | ------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 1 | Agent-ready instructions | Strip AXIOMS.md, HEURISTICS.md to bare rules; evidence lives in learning/                   | Baseline (current format, manual observation)       |
| 2 | Framework introspection  | Framework skill loads full structure, enforces consistency before accepting changes         | Implemented (v4.1.0)                                |
| 3 | Log consolidation        | Extract patterns from LOG.md → create targeted diagnostic files → inform experiments        | Designed (learning-log skill)                       |
| 4 | Bounded log growth       | LOG.md as inbox; archive after consolidation                                                | Designed (LOG-ARCHIVE.md)                           |
| 5 | Better log entry format  | Category + descriptive slug instead of session ID                                           | Implemented (learning-log skill)                    |
| 6 | Session-end reflection   | Auto-analyze session, map to heuristics, present approve/dismiss. Extends session-insights. | Planned (spec: `plans/splendid-plotting-muffin.md`) |

### Claude Code Dev Skills Integration ✅

Installed Anthropic's official `plugin-dev` plugin from `claude-plugins-official` marketplace.

**What was done** (2025-12-26):

1. Empirically tested skill discovery: nested directories NOT discovered, flat required
2. Installed `plugin-dev@claude-plugins-official` via settings.json
3. Updated prompt routing to guide agents to use plugin-dev skills
4. Added task classification patterns for CC component development

**Available skills** (invoke as `plugin-dev:<skill-name>`):

- `hook-development` - hook events, validation, security patterns
- `mcp-integration` - MCP server configuration, tool usage
- `plugin-structure` - plugin manifests, directory layout
- `command-development` - slash commands, frontmatter
- `agent-development` - agent creation, system prompts
- `skill-development` - skill structure, progressive disclosure

**Also includes**: 3 agents (agent-creator, plugin-validator, skill-reviewer), 1 command (create-plugin)

**Verification System** (meta-spec: `specs/verification-enforcement-gates.md`):

- [ ] Layer 1: Prompt enhancement - add examples to AXIOMS.md
- [ ] Layer 2: TodoWrite convention - document in framework skill
- [ ] Layer 3: Detection hook - `specs/2025-12-02-conclusion-verification-hook.md` (draft)
- [ ] Layer 4: /advocate agent - `specs/Advocate Agent Specification.md` (not implemented)
- [x] Layer 5: User habits - already happening
- [x] Layer 6: Learning logs - already happening

## Planned

### P0: Prompt Hydration Enforcement

Ensure prompt hydration is working to enforce framework rules. Spec exists but needs implementation via UserPromptSubmit hook.

**Spec**: [[specs/prompt-hydration]]
**Open question**: How do we verify agents follow guidance? See spec for options.

### P2: Live Progress Tracker

Real-time visibility into what's happening across terminals/sessions. Pipeline: prompt submit hook → Cloudflare → analysis → tasks & state updates.

**Acceptance criteria**: TBD - needs spec

### P2: Task Dashboard

Visualise tasks, priorities, current work. Builds on existing Cognitive Load Dashboard but focused on actionable task management.

**Acceptance criteria**: TBD - needs spec

### P3: Terminal Visualization

Show progress/status directly in terminal. Lightweight UX for seeing what's happening without leaving the CLI.

**Acceptance criteria**: TBD - needs spec (extends existing `specs/Terminal UX Spec.md`)

### P3: Domain-Specific Planning Skills

Hypervisor currently uses generic planning. Domain-specific planning skills would create specialized TodoWrite with domain-appropriate checkpoints.

**Gap**: Planning skills for specific domains:

1. `framework` planning - includes introspection, critic review, INDEX updates
2. `python-dev` planning - includes TDD cycle, type checking, test verification
3. `feature-dev` planning - includes acceptance criteria, e2e testing

**Current workaround**: Hypervisor uses generic planning; domain-specific requirements manually added to prompts or via existing skills.

### Framework Observability (spec needed)

| Item                       | Purpose                                                                |
| -------------------------- | ---------------------------------------------------------------------- |
| LOG.md pattern aggregation | Count/categorize recurring failures to identify enforcement priorities |
| Enforcement metrics        | Track hook fires, successful redirects, ignored interventions          |

TODO: Develop full spec for framework observability tooling.

### Specs complete, not yet implemented:

| Item                          | Spec Location                      | Priority                    |
| ----------------------------- | ---------------------------------- | --------------------------- |
| Dashboard: Balanced task view | -                                  | P2                          |
| Tasks MCP Server              | `specs/task-management-rebuild.md` | P3 (current approach works) |
| Terminal UX                   | `specs/Terminal UX Spec.md`        | P3                          |

### Dashboard: Balanced Task View

Mix strategic/important tasks (P0/P1 papers, major projects) with urgent/deadline items so daily view ensures progress on big things while ticking off time-sensitive items. Interleave rather than sort by single criterion.

### Dashboard: Actionable Next Steps (Overwhelm Prevention)

**Problem**: Dashboard shows accomplishments and high-level tasks, but doesn't answer "what should I be doing now?" Tasks like "finish TJA paper" are too broad - they cause paralysis, not action.

**Solution**: Use existing subtasks infrastructure (implemented 2025-12-18). No new mechanisms needed.

1. **Break down P0/P1 tasks into concrete subtasks** - each subtask should be a single clear action
2. **Keep subtasks current** - when completing work, update the task's subtask list with actual next steps
3. **Dashboard shows first incomplete subtask** - not just task title, but the concrete next action

**Key insight**: The infrastructure exists (tasks have subtasks, dashboard shows progress). The gap is discipline: keeping subtasks populated with real next steps, not leaving high-level tasks as vague goals.

**Done**: Click-to-Obsidian for notes (2025-12-18) - notes now link to open in Obsidian for full content.

## Known Issues

### Active Bugs

| Bug                                         | Priority | Task                                 |
| ------------------------------------------- | -------- | ------------------------------------ |
| Transcript missing error codes              | P2       | (planned: transcript error handling) |
| Duplicate agent conversation in transcripts | P2       | (same task)                          |

### Recently Fixed

| Bug                                  | Fix                                                                       | Date       |
| ------------------------------------ | ------------------------------------------------------------------------- | ---------- |
| Intent-router can't read cache files | Removed `tools:` restriction - Claude Code bug with restricted tool lists | 2025-12-25 |

### Open Design Questions

| Question                              | Context                                     |
| ------------------------------------- | ------------------------------------------- |
| Memory server ↔ markdown sync         | Do we maintain two copies? Auto-sync?       |
| How do skills declare needed context? | Latency budget, token cost balance          |
| Cleanup triggers and criteria         | When to auto-cleanup, duplication detection |

### Failure Patterns

See `learning/` for detailed patterns. Key failure modes:

- `learning/instruction-ignore.md` - Agents ignoring explicit instructions
- `learning/verification-skip.md` - Agents claiming success without verification
- `learning/validation-bypass.md` - Git/validation rule violations
- `learning/skill-bypass.md` - Agents bypassing skills, using wrong tools

## Testing

- **Unit tests**: `$AOPS/tests/` - 270 tests, 98% pass
- **Integration tests**: `$AOPS/tests/integration/` - require Claude CLI
- **Strong coverage**: Path resolution, hook contracts, git safety, deny rules
- **Moderate coverage**: Task operations, skill discovery
- **Intentionally minimal**: Individual skill behavior (tracked via learning logs)
