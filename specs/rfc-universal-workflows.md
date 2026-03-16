---
title: "RFC: Universal Academic Workflow Architecture"
type: rfc
status: draft
created: 2026-03-16
---

# RFC: Universal Academic Workflow Architecture

## Problem

The framework currently has ~35 workflow files in `aops-core/skills/hydrator/workflows/` plus another 13 in `.agent/skills/*/workflows/`. Most are skill procedures masquerading as workflows — they describe HOW to do a specific task type, not WHAT sequence of steps applies across task types. This violates the core framework principle:

> **Workflows define WHAT steps to take and in WHAT order. Skills define HOW to execute each step.**

The result: bloat, duplication, ambiguous hydrator routing, and workflows that are 1:1 with skills.

## Design Principles

1. **Workflows are process structures, not activity taxonomies.** The question is not "what kinds of things do academics do?" but "what distinct process shapes exist?"
2. **Workflows are meta to skills.** A workflow step like "support claims with sources" applies to writing, reviewing, AND responding to reviewers. The skill (literature-search) is the mechanism. The step is the obligation.
3. **Composable overlays enforce universal quality gates.** "Don't forget to save a memory" is not a step inside one workflow — it's an overlay that applies to all workflows. Overlays are the truly meta layer.
4. **Small and excellent over large and mediocre.** A handful of excellent, well-maintained workflows beats dozens of stale task-specific procedures.

## Proposed Architecture

### Universal Workflows (3)

These live in `aops-core/workflows/` and are the only workflows the hydrator routes from.

---

#### `create` — Producing any output for external consumption

**When**: User is making something for someone else — paper, review, response, reference letter, report, PR description.

**Steps**:

1. `plan` — Clarify intent, scope, and audience
2. `draft` — Produce first version (skill-dependent: writing, analyst, hdr, etc.)
3. `source-check` — Support all claims with appropriate sources `[[base-source-integrity]]`
4. `self-review` — Evaluate against acceptance criteria
5. `independent-review` — Get a second opinion before shipping `[[base-verification]]`
6. `revise` — Address review findings
7. `ship` — Submit/publish/merge `[[base-commit]]` `[[base-handoff]]`
8. `capture` — Save what was learned `[[base-memory]]`

---

#### `investigate` — Understanding something currently unclear

**When**: User is researching, debugging, root-causing, reviewing literature, or reflecting on work.

**Steps**:

1. `scope` — Define the question precisely
2. `gather` — Collect relevant information (skill-dependent: literature-search, read-code, recall-memory)
3. `synthesize` — Integrate findings into a coherent picture
4. `assess-confidence` — Identify gaps and uncertainty explicitly
5. `document` — Record findings in appropriate location `[[base-task-tracking]]`
6. `capture` — Save durable knowledge `[[base-memory]]`

---

#### `triage` — Processing a batch of incoming items

**When**: User is clearing inbox, processing tasks, reviewing a stack of PRs, handling a queue.

**Steps**:

1. `collect` — Gather all items in scope
2. `classify` — Categorise by type and urgency
3. `act-or-defer` — For each item: action now, delegate, or defer with explicit reason
4. `capture-tasks` — Any new commitments go into task system `[[base-task-tracking]]`
5. `archive` — Clear processed items
6. `capture` — Save patterns noticed `[[base-memory]]`

---

### Composable Process Overlays

These are named steps that appear across multiple workflows. Defined once, referenced everywhere. These are the "meta to skills" layer — universal quality gates.

| Overlay                     | Enforces                                                           | Applied in              |
| --------------------------- | ------------------------------------------------------------------ | ----------------------- |
| `[[base-memory]]`           | Check memory before starting; save findings after completing       | All workflows           |
| `[[base-task-tracking]]`    | Bind to a task; update progress; complete when done                | All non-trivial work    |
| `[[base-source-integrity]]` | Support factual claims with citable sources                        | `create`, `investigate` |
| `[[base-verification]]`     | Independent QA check before marking complete                       | `create`                |
| `[[base-commit]]`           | Format, lint, commit, push                                         | Any file modifications  |
| `[[base-handoff]]`          | Write context for next agent/session; don't implement beyond phase | Multi-phase work        |

---

### Hydrator Decision Tree

```
User intent arrives
    |
    +--> Producing an artifact for someone else?   → workflow: create
    |
    +--> Trying to understand/learn/debug?          → workflow: investigate
    |
    +--> Processing a batch of incoming items?      → workflow: triage
    |
    +--> Simple question or direct skill invocation? → no workflow (direct)
```

No ambiguity. The process structure — not the domain — determines the workflow.

---

## Migration Plan

### Delete (exact duplicates already superseded)

- `.agent/skills/framework/workflows/03-experiment-design.md`
- `.agent/skills/framework/workflows/04-monitor-prevent-bloat.md`

### Move to project-local (`.agent/workflows/`)

These describe how to build THIS framework, not universal academic work:

- `.agent/skills/framework/workflows/01-design-new-component.md`
- `.agent/skills/framework/workflows/02-debug-framework-issue.md`
- `.agent/skills/framework/workflows/05-feature-development.md`
- `.agent/skills/framework/workflows/06-develop-specification.md`
- `.agent/skills/framework/workflows/07-learning-log.md`
- `.agent/skills/framework/workflows/08-decision-briefing.md`
- `aops-core/skills/hydrator/workflows/feature-dev.md`
- `aops-core/skills/hydrator/workflows/dogfooding.md`
- `aops-core/skills/hydrator/workflows/framework-gate.md`
- `aops-core/skills/hydrator/workflows/audit.md`
- `aops-core/skills/hydrator/workflows/pr-review.md`
- `aops-core/skills/hydrator/workflows/develop-specification.md`
- `aops-core/skills/hydrator/workflows/experiment-design.md`
- `aops-core/skills/hydrator/workflows/decision-briefing.md`
- (and other framework-development-specific files)

### Absorb into skill SKILL.md or references/

Skill procedures currently in workflows/ that belong in the skill itself:

- `.agent/skills/remember/workflows/` (all 4) → into remember skill
- `.agent/skills/audit/workflows/session-effectiveness.md` → into audit skill

### Collapse into the 3 universal workflows

- `hydrator/workflows/email-capture`, `email-triage`, `email-reply` → instances of `triage` / `create`
- `hydrator/workflows/report-finalization` → instance of `create`
- `hydrator/workflows/reference-letter` → instance of `create`
- `hydrator/workflows/reflect` → instance of `investigate`
- `hydrator/workflows/peer-review`, `review-response`, `outbound-review` → instances of `create`

### Keep and evolve

- `aops-core/skills/planning/workflows/decompose.md` and `strategic-intake.md` — review for fit with new architecture

---

## Open Questions

1. Is three workflows the right number, or are there academic task shapes missing?
2. Should overlays live as standalone files in `aops-core/workflows/overlays/` or be embedded in the workflow files?
3. How do project-local workflows in `.agent/workflows/` relate to these — do they extend/compose the universal ones, or are they fully independent?
4. The `reflect` workflow step (in `investigate`) — should reflection be its own workflow since it has a distinct cadence (daily/weekly) rather than being task-triggered?

---

## References

- [[VISION.md]] — Workflow/skill architecture definition
- [[TAXONOMY.md]] — Canonical concept definitions
- Critic review conducted 2026-03-16
