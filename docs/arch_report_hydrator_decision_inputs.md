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

| Signal | Source | How loaded | Used for |
|--------|--------|-----------|----------|
| `{prompt}` | User input | Direct injection | Intent detection |
| `{session_context}` | Transcript | `extract_router_context()` | Follow-up detection, task binding |
| `{workflows_index}` | WORKFLOWS.md + project workflows + keyword-matched workflow content | `load_workflows_index(prompt)` | Workflow selection |
| `{skills_index}` | SKILLS.md | `load_skills_index()` (static load) | Skill routing |
| `{task_state}` | Task CLI query | `get_task_work_state()` | Task binding |
| `{glossary}` | GLOSSARY.md | `load_glossary()` | Term resolution |
| `{mcp_tools}` | TOOLS.md | `load_tools_index()` | Feasibility assessment |
| `{project_context_index}` | `.agent/context-map.json` | `load_project_context_index()` | Project-specific context |
| `{project_rules}` | `.agent/rules/*.md` | `load_project_rules()` | Constraint awareness |
| `{relevant_files}` | `file_index.py` keyword match | `get_formatted_relevant_paths(prompt)` | JIT file injection |
| `{project_paths}` | `polecat.yaml` | `load_project_paths_context()` | Path resolution |
| `{scripts_index}` | SCRIPTS.md | `load_scripts_index()` | Script awareness |

### Key observation: asymmetric loading

- **WORKFLOWS.md** gets *enhanced* loading: the index PLUS full content of keyword-matched workflows AND their base workflows (via `_load_global_workflow_content()`). The hydrator can read workflow files it selects.
- **SKILLS.md** gets *static* loading: just the index content, no content injection of individual skill files. The hydrator is told "DO NOT SEARCH", so it relies entirely on what's in the index.
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

2. **No output-type metadata on workflows** - The hydrator can't tell what a workflow *produces* (code change, document, task decomposition, information). This would help scope detection.

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

| What's in the index | Hydrator can use it for | Missing |
|---------------------|------------------------|---------|
| Workflow name (wikilink) | Identification, file lookup | File may not exist |
| "When to Use" column | Routing decision | No structured triggers - prose only |
| "Bases" column | Composition planning | Only names, not what bases provide |
| Category headings | Domain filtering | Not structured, just visual grouping |
| Decision tree | Primary routing | No fallback or confidence signal |

### What would help the hydrator

1. **Trigger phrases per workflow** (like SKILLS.md has) - enables fast matching before decision tree traversal
2. **`modifies_files: yes/no`** - instant task-requirement signal
3. **`typical_scope: single-session | multi-session`** - direct scope detection
4. **`outputs: [code, document, tasks, information]`** - what the workflow produces
5. **File existence indicator** - or eliminate phantom workflows from the index
6. **Consistent naming** - index names must match filenames exactly
