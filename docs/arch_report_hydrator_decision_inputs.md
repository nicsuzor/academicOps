# Hydrator Decision Input Analysis

Analysis for task-96c4f07f: What do WORKFLOWS.md and SKILLS.md actually need to contain?

## Stage 1: Hydrator Decision Needs Map

### What questions does the hydrator answer?

1. **What is the user's intent?** - Parse terse prompt into clear intent
2. **Which workflow(s) apply?** - Use WORKFLOWS.md decision tree to route
3. **Which task to bind to?** - Match existing task or specify new task creation
4. **What context does the agent need?** - Curate relevant background from pre-loaded content
5. **What is the execution scope?** - Single-session vs multi-session
6. **Is this a verification task?** - Detect verification trigger patterns
7. **Is this an interactive follow-up?** - Continuation of session work
8. **Is this a skill invocation?** - Direct routing via `/skill` or trigger match

### What signals does the hydrator consume?

| Signal                    | Source                                                              | How loaded                             | Used for                          |
| ------------------------- | ------------------------------------------------------------------- | -------------------------------------- | --------------------------------- |
| `{prompt}`                | User input                                                          | Direct injection                       | Intent detection                  |
| `{session_context}`       | Transcript                                                          | `extract_router_context()`             | Follow-up detection, task binding |
| `{workflows_index}`       | WORKFLOWS.md + project workflows + keyword-matched workflow content | `load_workflows_index(prompt)`         | Workflow selection                |
| `{skills_index}`          | SKILLS.md                                                           | `load_skills_index()` (static load)    | Skill routing                     |
| `{task_state}`            | Task CLI query                                                      | `get_task_work_state()`                | Task binding                      |
| `{glossary}`              | GLOSSARY.md                                                         | `load_glossary()`                      | Term resolution                   |
| `{mcp_tools}`             | TOOLS.md                                                            | `load_tools_index()`                   | Feasibility assessment            |
| `{project_context_index}` | `.agent/context-map.json`                                           | `load_project_context_index()`         | Project-specific context          |
| `{project_rules}`         | `.agent/rules/*.md`                                                 | `load_project_rules()`                 | Constraint awareness              |
| `{relevant_files}`        | `file_index.py` keyword match                                       | `get_formatted_relevant_paths(prompt)` | JIT file injection                |
| `{project_paths}`         | `polecat.yaml`                                                      | `load_project_paths_context()`         | Path resolution                   |
| `{scripts_index}`         | SCRIPTS.md                                                          | `load_scripts_index()`                 | Script awareness                  |

### Key observation: asymmetric loading

- **WORKFLOWS.md** gets _enhanced_ loading: the index PLUS full content of keyword-matched workflows AND their base workflows (via `_load_global_workflow_content()`). The hydrator can read workflow files it selects.
- **SKILLS.md** gets _static_ loading: just the index content, no content injection of individual skill files. The hydrator is told "DO NOT SEARCH", so it relies entirely on what's in the index.
- This asymmetry matters: workflow selection gets rich content, skill routing gets only the flat table.

### Decision flow reconstruction

```
1. Parse prompt → detect intent
2. Check: is this a /skill invocation or trigger match?
   YES → route to [[direct-skill]], done
3. Check: is this a simple question?
   YES → route to [[simple-question]], done
4. Check: is this a follow-up to current session work?
   YES → route to [[interactive-followup]], done
5. Otherwise: walk the WORKFLOWS.md decision tree
   → Select workflow(s)
   → Read workflow file content (if keyword-matched, already loaded)
   → Compose execution steps from workflow + bases
6. Bind to task (existing or new)
7. Output hydration result with curated context + execution plan
```

### Gaps identified

1. **WORKFLOWS.md lacks trigger phrases** - SKILLS.md has explicit triggers ("process email", "email to task") but WORKFLOWS.md relies on a prose decision tree. The hydrator must interpret the tree, not match triggers.

2. **No output-type metadata on workflows** - The hydrator can't tell what a workflow _produces_ (code change, document, task decomposition, information). This would help scope detection.

3. **No explicit conflict/composition rules** - WORKFLOWS.md says "one workflow per intent" but doesn't encode which workflows conflict. The `bases` field on individual workflows encodes composition, but the index doesn't surface it in a way the hydrator can use for selection without reading each file.

4. **Skills lack mode/domain metadata** - Can't tell from SKILLS.md:
   - Which skills modify files vs are read-only
   - Which need a task vs don't
   - Which are conversational vs execution-oriented
   - Which can be invoked mid-workflow vs are standalone

5. **Keyword-dependent workflow injection is brittle** - `_load_global_workflow_content()` uses `file_index.py` keyword matching. If the user prompt doesn't contain expected keywords, the hydrator won't see workflow content. The decision tree routing and the content injection use different matching strategies.

6. **Scope detection has no explicit signals** - The hydrator must infer single-session vs multi-session from workflow characteristics, but workflows don't declare their typical scope.

## Stage 2: WORKFLOWS.md as a Hydrator Input

### Current structure assessment

WORKFLOWS.md has three main sections the hydrator uses:

1. **Base Workflows table** - Lists composable patterns with "Pattern" and "Skip When" columns
2. **Decision Tree** - ASCII flowchart for routing user requests to workflows
3. **Available Workflows** - Tables grouped by category with "When to Use" and "Bases" columns

### What works well

- The **decision tree** is the hydrator's primary routing tool and it's clear and comprehensive
- The **bases table** gives good composability hints
- Categorical grouping (Planning, Development, QA, etc.) provides useful signal
- The **Key Distinctions** table at the bottom handles ambiguous cases well

### Critical problem: index-to-file integrity

Cross-referencing WORKFLOWS.md wikilinks against actual files in `workflows/`:

**Exist as files (26):**
base-task-tracking, base-tdd, base-verification, base-commit, base-handover, base-memory-capture, base-qa, base-batch, base-investigation, decompose, feature-dev, interactive-followup, simple-question, dogfooding, audit, constraint-check, framework-gate, email-triage, email-capture, email-reply, peer-review, reference-letter, worktree-merge, qa, reflect, external-batch-submission

**Referenced in WORKFLOWS.md but NO file exists (18):**
design, collaborate, strategy, tdd-cycle, debugging, qa-demo, qa-test, prove-feature, qa-design, batch-processing, batch-task-processing, task-triage, classify-task, email-classify, hdr-supervision, direct-skill, framework-change, skill-pilot, merge-conflict, version-bump

**Name mismatches:**

- `[[triage-email]]` in index → file is `email-triage.md`
- `[[batch-processing]]` in index → closest file is `base-batch.md`

**Impact**: The hydrator is told to "Read all workflow files you have selected." If it selects a workflow that has no file, the read silently fails. The hydrator's context template step 5 says: "Read all workflow files you have selected, including any local workflows." For 18 of the ~44 referenced workflows, this yields nothing.

### What the index provides vs what the hydrator needs

| What's in the index      | Hydrator can use it for     | Missing                              |
| ------------------------ | --------------------------- | ------------------------------------ |
| Workflow name (wikilink) | Identification, file lookup | File may not exist                   |
| "When to Use" column     | Routing decision            | No structured triggers - prose only  |
| "Bases" column           | Composition planning        | Only names, not what bases provide   |
| Category headings        | Domain filtering            | Not structured, just visual grouping |
| Decision tree            | Primary routing             | No fallback or confidence signal     |

### What would help the hydrator

1. **Trigger phrases per workflow** (like SKILLS.md has) - enables fast matching before decision tree traversal
2. **`modifies_files: yes/no`** - instant task-requirement signal
3. **`typical_scope: single-session | multi-session`** - direct scope detection
4. **`outputs: [code, document, tasks, information]`** - what the workflow produces
5. **File existence indicator** - or eliminate phantom workflows from the index
6. **Consistent naming** - index names must match filenames exactly

## Stage 3: SKILLS.md as a Hydrator Input

### SKILLS.md structure

SKILLS.md has two sections:

1. **Skills and Commands table** - Flat table with Skill, Triggers, Description columns
2. **Routing Rules** - 4-tier matching priority (explicit → trigger → context → no match)

### What SKILLS.md does well

- **Triggers column** is exactly what the hydrator needs for fast matching
- **Routing Rules** are clear and actionable
- Descriptions are concise and informative
- The `/skill` syntax is unambiguous for explicit invocations

### Problems identified

#### 1. Commands and skills are conflated

The index mixes two distinct implementation types under one heading:

| Type                       | Location                 | Examples                                                    | Count |
| -------------------------- | ------------------------ | ----------------------------------------------------------- | ----- |
| **Skills** (SKILL.md)      | `skills/<name>/SKILL.md` | `/audit`, `/daily`, `/pdf`, `/python-dev`, `/strategy`      | ~20   |
| **Commands** (command .md) | `commands/<name>.md`     | `/q`, `/dump`, `/bump`, `/learn`, `/pull`, `/path`, `/aops` | 7     |

The hydrator treats them identically but they have different implementation mechanisms. This hasn't caused problems yet because routing works the same way, but it means the index can't accurately describe capabilities (commands don't have `allowed-tools` frontmatter, for example).

#### 2. No structured metadata beyond triggers

SKILLS.md provides:

- Name (invocation syntax)
- Trigger phrases (free text)
- Description (free text)

Missing metadata that would help the hydrator:

| Metadata                                                        | Why it helps                              |
| --------------------------------------------------------------- | ----------------------------------------- |
| `modifies_files: yes/no`                                        | Determines whether a task is needed       |
| `needs_task: yes/no`                                            | Direct task-gate signal                   |
| `mode: conversational/execution/batch`                          | Affects scope detection and composition   |
| `domain: [framework, academic, email, development, operations]` | Domain routing                            |
| `standalone: yes/no`                                            | Whether skill can be invoked mid-workflow |
| `type: skill/command`                                           | Disambiguates implementation type         |

#### 3. No composability information

The hydrator doesn't know:

- Which skills work together (e.g., `/python-dev` + `/commit`)
- Which skills conflict (e.g., `/strategy` shouldn't compose with `/pull`)
- Which skills are "advice" (injected as context) vs "action" (execute and produce output)

#### 4. Skills don't declare their relationship to workflows

Some skills effectively ARE workflow implementations (e.g., `/pull` implements task-tracking + execution). Others are orthogonal tools (e.g., `/pdf`). The hydrator can't distinguish these.

#### 5. Trigger overlap

Some triggers could match multiple skills:

- "framework" → `/framework` or `/audit`?
- "batch" → `/hypervisor` or `/swarm-supervisor`?
- "task" → `/pull` or `/q`?

The routing rules handle this (explicit > trigger > context) but the index doesn't surface priority between ambiguous matches.

### Proposed improvements to SKILLS.md

1. **Separate commands from skills** or at minimum add a `type` column
2. **Add `modifies_files` and `needs_task` columns** - direct routing signals
3. **Add `mode` column** - conversational vs execution vs batch
4. **Add `domain` tags** - enable domain-based filtering
5. **Document trigger disambiguation** - which skill wins on overlapping triggers

## Stage 4: Workflow Frontmatter Schema

### Current schema (from reading all 26 workflow files)

| Field         | Presence | Purpose                  |
| ------------- | -------- | ------------------------ |
| `id`          | 26/26    | Identifier (kebab-case)  |
| `category`    | 26/26    | Classification           |
| `bases`       | 23/26    | Composable base patterns |
| `triggers`    | 2/26     | Routing trigger phrases  |
| `title`       | 1/26     | Human-readable name      |
| `description` | 2/26     | What the workflow does   |

Plus 5 fields used only by `email-capture.md`: `name`, `permalink`, `tags`, `version`, `phase`, `backend`.

### Assessment for hydrator use

**The `triggers` field is the biggest missed opportunity.** It exists in the schema (used by `interactive-followup` and `worktree-merge`) but isn't populated on 24 other workflows. If every workflow had triggers, `load_workflows_index()` could build a trigger-matching table similar to SKILLS.md, giving the hydrator fast routing before falling back to the decision tree.

**The `category` field has too many values with unclear semantics:**

12 distinct categories for 26 files: `base`, `governance`, `planning`, `meta`, `verification`, `instruction`, `operations`, `routing`, `session`, `development`, `quality-assurance`, `academic`, `integration`. Some categories have only 1 member. The hydrator can't use this for meaningful filtering.

**Missing fields the hydrator needs:**

| Proposed field   | Type                                  | Why                                             |
| ---------------- | ------------------------------------- | ----------------------------------------------- |
| `triggers`       | `string[]`                            | Fast routing (already exists, just unpopulated) |
| `modifies_files` | `boolean`                             | Task-gate signal                                |
| `scope`          | `enum: single-session, multi-session` | Scope detection                                 |
| `outputs`        | `string[]`                            | What the workflow produces                      |
| `description`    | `string`                              | Already exists, just unpopulated on 24/26       |

### Integrity issues

1. **`reflect.md` has `id: meta-improvement`** - filename doesn't match id
2. **`email-capture.md` has anomalous rich metadata** that no other workflow uses
3. **`bases` field omitted vs empty array** - inconsistent (both `bases: []` and field-absent appear)
4. **Category overlap** - `qa.md` uses `quality-assurance` while similar workflows use `operations`

## Stage 5: Skill Frontmatter Schema

### Current schema (from reading skills and commands)

Skills (`skills/<name>/SKILL.md`) and commands (`commands/<name>.md`) share the same frontmatter schema:

| Field           | Presence                       | Purpose                                            |
| --------------- | ------------------------------ | -------------------------------------------------- |
| `name`          | ~all                           | Identifier                                         |
| `category`      | most                           | Always "instruction" - has no discriminating value |
| `description`   | ~all                           | One-line purpose description                       |
| `allowed-tools` | most                           | Comma-separated tool names                         |
| `version`       | some                           | Semantic version                                   |
| `permalink`     | some                           | URL-friendly slug                                  |
| `triggers`      | 2 skills (swarm-supervisor, q) | Routing trigger phrases                            |
| `title`         | 1 (python-dev)                 | Human-readable name                                |

### Skill frontmatter and the hydrator

**The hydrator never reads skill frontmatter directly.** It only sees what SKILLS.md provides. This means:

1. Skill frontmatter serves the audit/indexing tools, not the hydrator
2. Any metadata the hydrator needs must be surfaced in SKILLS.md
3. The `triggers` field in frontmatter is only used if the audit tool copies it to SKILLS.md

**Implications for the frontmatter schema:**

The skill frontmatter should be the **source of truth** that SKILLS.md is generated from. Currently:

- `triggers` exists in frontmatter on only 2 items (swarm-supervisor, q command) - all other triggers live only in SKILLS.md
- `description` in frontmatter → maps to Description column in SKILLS.md (this works)
- No frontmatter field maps to the metadata the hydrator needs (modifies_files, needs_task, mode, domain)

### Schema inconsistencies

1. **`swarm-supervisor` omits `category` and `allowed-tools`** - the two most common fields
2. **`category` is always "instruction"** - provides zero discriminating value; should either be removed or given meaningful values
3. **`triggers` appears in 2/~27 items** - same problem as workflows: the field exists but is almost never populated
4. **Commands have identical schema to skills** - no structural way to distinguish them

### Proposed schema additions

To make skill frontmatter the source of truth for SKILLS.md generation:

```yaml
---
name: example-skill
type: skill | command        # NEW: distinguish implementation type
description: One-line description
triggers:                    # EXISTING: populate on all items
  - "trigger phrase 1"
  - "trigger phrase 2"
modifies_files: true         # NEW: does this skill write/edit files?
needs_task: true             # NEW: does the hydrator need to bind a task?
mode: execution              # NEW: conversational | execution | batch
domain:                      # NEW: domain tags for filtering
  - framework
  - development
allowed-tools: Read,Edit,Write
version: 1.0.0
---
```

## Stage 6: Index-Building Instructions

### How indexes are currently built

The `/audit` skill (Phase 2: Index Curation) is responsible for generating both SKILLS.md and WORKFLOWS.md:

| Index        | Source of truth                 | Method              |
| ------------ | ------------------------------- | ------------------- |
| SKILLS.md    | `skills/*/SKILL.md` frontmatter | LLM-judged curation |
| WORKFLOWS.md | `workflows/*.md` files          | LLM-judged curation |

The SKILLS.md header confirms: `> **Generated by audit skill** - Do not edit manually. Triggers are preserved from previous version; add new triggers to frontmatter.`

### Critical observation: LLM-judged curation

The audit skill says "Curate root-level index files **using LLM judgment**." This is not programmatic extraction. The LLM reads source files and decides what to include. Consequences:

1. **No schema enforcement** - New frontmatter fields won't automatically appear in indexes unless the audit instructions specify them
2. **Trigger preservation hack** - "Triggers are preserved from previous version" means triggers primarily live in SKILLS.md itself, not in frontmatter. Only 2/27 items have triggers in frontmatter.
3. **Missing files aren't caught** - The audit reads what exists and builds the index, but WORKFLOWS.md references 18 workflows that don't exist as files. The audit doesn't validate wikilink targets against filesystem.
4. **No validation of hydrator compatibility** - The audit doesn't check whether the generated index actually serves the hydrator's needs.

### The feedback loop is broken

```
Ideal:  frontmatter → audit → index → hydrator
                ↑                        |
                └── hydrator needs ──────┘

Actual: frontmatter → audit → index → hydrator
        (incomplete)   (LLM)   (inconsistent)  (works around gaps)
```

The hydrator works around index gaps by:

- Using the decision tree (prose, not structured data)
- Reading workflow files directly (via `_load_global_workflow_content()`)
- Relying on `file_index.py` keyword matching for content injection

### What needs to change

1. **Frontmatter must be the single source of truth** for index-relevant fields
2. **Audit instructions must enumerate exact fields** to extract from frontmatter and format into the index
3. **Audit must validate index integrity** - every wikilink in WORKFLOWS.md must have a corresponding file
4. **Audit must validate hydrator compatibility** - indexes should serve the hydrator, and the audit should verify they do
5. **Triggers should migrate from SKILLS.md to frontmatter** - then the audit generates them, not preserves them

## Stage 7: Synthesis and Implementation

### Changes implemented in this PR

#### 1. WORKFLOWS.md rewrite

- Removed 18 phantom workflows (referenced but no files) from all tables
- Fixed naming: `[[triage-email]]` → `[[email-triage]]` (matches actual file)
- Consolidated 4 QA variants (qa-demo, qa-test, prove-feature, qa-design) → single `[[qa]]`
- Redirected decision tree: `[[design]]`/`[[debugging]]` → `[[feature-dev]]`/`[[base-investigation]]`
- Removed `[[direct-skill]]` concept (skill invocation uses `[[simple-question]]` + invoke directly)
- Fixed `[[batch-processing]]` → `[[base-batch]]`
- Fixed `[[framework-change]]` → `[[framework-gate]]`
- Every wikilink in the index now points to an actual file

#### 2. Workflow frontmatter enrichment

Added `triggers` and `description` to 12 non-base workflows:
decompose, feature-dev, simple-question, qa, email-triage, email-reply, peer-review, dogfooding, audit, external-batch-submission, framework-gate. Also: interactive-followup and worktree-merge already had triggers.

The `triggers` field was already in the schema (used by 2 workflows). Now 13/14 non-base workflows have it.

#### 3. Category consistency fix

Changed `peer-review` from `category: operations` → `category: academic` (matches its index grouping).

### Remaining work (follow-up tasks)

These changes are deferred to avoid scope explosion:

1. **Migrate SKILLS.md triggers to frontmatter** - Move trigger phrases from SKILLS.md to each skill/command's frontmatter, then update audit to generate SKILLS.md from frontmatter
2. **Add routing metadata to skill frontmatter** - `modifies_files`, `needs_task`, `mode`, `domain` fields
3. **Update audit skill instructions** - Enumerate exact fields to extract; add integrity validation (wikilink → file check)
4. **Clean up email-capture frontmatter** - Remove anomalous fields (name, permalink, tags, version, phase, backend) that no other workflow uses
5. **Fix reflect.md id mismatch** - `id: meta-improvement` should match filename `reflect`
6. **Standardize `category` values** - Reduce from 12 to ~6 meaningful categories
