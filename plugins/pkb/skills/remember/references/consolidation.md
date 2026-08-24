# Knowledge Extraction & Consolidation Workflow

This is the single definitive summarisation and knowledge-extraction workflow for the Personal Knowledge Base (PKB). It supersedes all prior consolidation and sleep-cycle documentation. Every batch pass, scheduled cycle, and ad-hoc consolidation composes this workflow and nothing else.

Extraction is an **agent session requiring human-like semantic judgment, not an unguided script**. Tools provide candidates and signals; you read prose, evaluate durability, and make the decisions. Stop when the next action would be lower quality than the last.

Quality over coverage, everywhere. One well-sourced, synthesised note beats five superficial fragments, and leaving content untouched in a completed task is infinitely better than gutting it into oblivion.

---

## Ground Truth — The Failure This Workflow Prevents

On 2026-08-23, commit [`71516fc016`](https://github.com/nicsuzor/brain/commit/71516fc016) touched **300 files (+21,440 / −102,915)** in the PKB data repository, resulting in net destruction of ~81,000 lines of durable knowledge against only 18 shallow notes added.

The specific failure modes observed in that incident are the acceptance evidence this workflow is designed to prevent:

1. **Net destruction without a landing zone:** ~81k lines deleted while producing generic stubs. Deleted prose with nowhere to land is catastrophic.
2. **Tautological summaries:** `academic-0fbdd4ee` was reduced to _"Completed [[Consider GNI academic membership]]. Consider GNI academic membership"_ — echoing the title twice with zero substance.
3. **Fabricated boilerplate:** Identical invented `## Key Knowledge` bullets (_"Framework components require strict fail-loud verification …"_) were pasted onto unrelated tasks — `academic-0fbdd4ee` (GNI academic membership) and `academic-3a12ff04` (a strategic memo for Kylie) — neither of which touched fail-loud verification.
4. **Irreplaceable facts deleted with no destination:**
   - On `academic-1184d18d`: A full ReFrame findings table ($293.9M vs $117.8M), a metric comparison, four strategic options, and two source URLs were permanently erased.
   - On `academic-0fbdd4ee`: Two GNI contact emails and a brochure URL were destroyed.
   - On `academic-3a12ff04`: Two vital SharePoint links were deleted.
5. **Graph edges destroyed:** Structural metadata like `## Relationships` and `[parent] [[academic-0869f984]]` were stripped from source tasks.
6. **Malformed wikilinks:** Broken link formats like `[[academic-3a12ff04-…-advice.md]]` (filenames with `.md` extensions) were written to the store.
7. **Cancelled tasks stubbed with fake knowledge:** Tasks cancelled without completion had generic sentences and fabricated `Key Knowledge` bullets stamped onto them.

### The Ancestor Rule to Preserve

The foundational rule carried forward from ancestor doctrine is:

> **Route durable knowledge to the canonical topic note, mark the source `consolidated: <date>`, and LEAVE ITS CONTENT UNTOUCHED.**

A task body is not a primary record, but an in-place rewrite during extraction must never gut or delete facts from a task body until and unless every durable fact has safely landed by ID in a permanent topic note. Furthermore, an in-place rewrite never alters `status`, `id`, `parent`, `depends_on`, or `contributes_to`.

---

## Two Invariants Before Starting

1. **Bulk mutators default to preview:** `batch_update`, `batch_reparent`, `batch_merge`, `batch_reclassify`, `batch_archive`, and `merge_node` default to `dry_run=true`. Always inspect the simulation before executing with `dry_run=false`.
2. **A missing tool is a HALT, not a workaround:** If an environment lacks a necessary tool, emit `HALT: <tool_name>` immediately rather than fabricating data or guessing. Report all halts at the very top of the cycle summary.

---

## Out-of-Scope Declarations (§4 and §7 Resolution)

To avoid unowned gaps and maintain strict architectural boundaries:

1. **Staleness and closure (former §4) is OUT OF SCOPE:**
   Closure loop logic, staleness sweeps across non-terminal tasks, pull request reconciliation, and artifact rot are owned exclusively by the `/reconcile` skill ([`../../reconcile/SKILL.md`](../../reconcile/SKILL.md)) per [`specs/workflows/reconcile.md`](../../../../specs/workflows/reconcile.md#L102)(../../../../specs/workflows/reconcile.md#L102) (_"No other skill carries closure-loop logic of its own"_). This workflow does not inspect unclosed task claims or execute closure sweeps.
2. **Maintaining graph hierarchy (former §7) is OUT OF SCOPE:**
   Broad structural graph reorganization (reparenting trees, deep container resizing, global metric balancing) is a separate maintenance duty tracked under successor epic [[aops-574a4ff6]]. This workflow focuses solely on knowledge extraction, deduplication, and note synthesis.

---

## The Rubric: Four Pass/Fail Tests

Every extraction must pass all four tests evaluated by **recoverability, not tidiness** (diffing the old body against the new body plus every note it points to):

| Test              | Status   | Condition                                                                                                                                                                                                                                          |
| ----------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Lossy**      | **FAIL** | Any durable fact, number, path, decision, date, contact, link, or supersession statement in the source body is unreachable from the new body within **one `[[wikilink]]` hop**. Deleted prose with nowhere to land fails.                          |
| **2. Accretive**  | **FAIL** | The source body is pasted verbatim under a dated heading, or a new note is created 1:1 per task. Where a canonical topic note exists, it must be **augmented**, not duplicated.                                                                    |
| **3. Fabricated** | **FAIL** | Any bullet, claim, or summary statement is not strictly verifiable against the source body or a cited commit/PR. Fabricating generic platitudes fails.                                                                                             |
| **4. Good**       | **PASS** | Source body remains intact or becomes short and navigational (<1,500 chars) with verified pointers; each extracted fact sits in a canonical topic note beside its siblings; the reader opens **one** topic note instead of walking the task chain. |

Every extraction report must record an explicit per-extraction verdict against all four tests (`Test 1: PASS/FAIL | Test 2: PASS/FAIL | Test 3: PASS/FAIL | Test 4: PASS/FAIL`).

---

## The Seven Defect Classes Lint Checklist

A reviewer or worker must lint every note against these seven defect classes:

1. **Duplicate canonical/narrow pairs:** Check whether a narrow note (e.g. `gni-brief-memo`) was created when a broader canonical note (`gni-membership`) already exists.
2. **Title-encoded dates and session IDs:** Check whether the title contains timestamps, dates (`2026-08-24`), or session IDs (`session-02e0350c`) instead of clean conceptual names.
3. **Missing `sources:`:** Check whether frontmatter `sources:` lists the explicit task ID (`[[task-id]]`), session ID, or document reference.
4. **Missing `confidence:`:** Check whether frontmatter contains an explicit confidence rating (`established`, `provisional`, `speculative` or float 0.0–1.0).
5. **Status content misfiled as `type: knowledge`:** Check whether transient project progress, meeting logistics, or checklist updates were wrongly saved as permanent knowledge notes.
6. **Zero wikilinks despite obvious targets:** Check whether the note body fails to embed `[[wikilink]]` pointers to related canonical concepts, parent frameworks, or Maps of Content (MOCs).
7. **Notes never advancing past `status: inbox`:** Check whether newly created or updated knowledge notes remain abandoned in `inbox` status rather than being triaged to `ready` or active knowledge.

---

## Triaging Content: What Moves, What Stays, What Goes

| Move to a Canonical Topic Note                                                                                                                                                                                                                                                                                    | Keep in the Task Body                                                                                                                                                                                   | Discard (Do Not Save)                                                                                                                                                |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| • Conceptual models, formulas, and algorithms<br>• Architecture patterns and invariants<br>• Behavioural rules and constraints<br>• Empirical findings, numbers, and metrics<br>• Post-mortems and generalisable lessons<br>• Infrastructure constraints and APIs<br>• **Contacts, emails, URLs, document links** | • One-sentence Goal statement<br>• Completed checklist items<br>• Backlinks to extracted topic notes (`[[kb_...]]`)<br>• Graph edges (`parent`, `depends_on`, `contributes_to`)<br>• PR and commit URLs | • Retry loops and terminal spam<br>• Intermediate debug traces<br>• Routine status timestamps<br>• Raw transcript dumps and PIDs<br>• Retracted scratchpad proposals |

---

## Concrete Step-by-Step Extraction Procedure

Execute this inline method directly. Do not consult or delegate to external documents for the _how_.

### Step 1: Candidate Discovery and Batch Bounding

1. **Find unconsolidated episodic sources:**
   - Completed tasks: Query `pkb__list_tasks(status="done")` or `pkb__list_tasks(status="in_progress")` with substantive bodies lacking `consolidated:` in frontmatter.
   - Meeting and daily notes: Query `pkb__list_documents(tag="daily-note")` or `pkb__list_documents(tag="meeting-note")` without `consolidated:` in frontmatter.
   - Session transcripts: Transcripts without `mined: <date>` in frontmatter.
2. **Bound the batch:** Limit batch size to 5–10 items per cycle to maintain high semantic precision.

### Step 2: Source Analysis and Extraction Decision

Read the source body in full.

> [!IMPORTANT]
> **The Empty Extraction Rule (AC3):**
> If a source contains no durable knowledge — only routine execution, project-specific coordination, transient debugging, or ephemeral status — **WRITE NOTHING**.
> Do not generate a summary section. Do not add a `## Key Knowledge` header. Do not write generic advice.
> **A generic or templated bullet is an explicit FAIL, not a fallback.**
> Mark the source `consolidated: <date>` and advance its status, leaving its content untouched.

### Step 3: Clustering and Destination Resolution

1. For each durable insight identified:
   - Identify the first-class topic concept (e.g. `gni-academic-membership`, `reframe-financial-model`).
   - Search the PKB: `pkb__search(query="<topic_concept>")` and check `pkb__get_semantic_neighbors`.
2. **Cluster siblings:** Group related findings across tasks into a single canonical topic note rather than creating N fragmented notes.
3. Determine destination:
   - If a canonical topic note exists: Plan to **AUGMENT** it (`pkb__update_body`).
   - If no canonical note exists: Plan to **CREATE** a new topic note (`pkb__create` with `type: knowledge` or `type: note`).

### Step 4: Destination-First Execution Sequence (Mandatory Order)

To guarantee that content is never lost, enforce this strict sequence:

```
[1. Resolve Destination] ──> [2. Write Destination Note] ──> [3. Verify Write & Node ID] ──> [4. Mark Source Consolidated]
                                                                        │
                                                                 (If Write Fails)
                                                                        │
                                                                        └──> [HALT IMMEDIATELY: Do not touch source]
```

1. **Format the Destination Content:**
   - Write synthesised, non-accreted prose integrating new observations into existing sections.
   - Ensure complete attribution in frontmatter:
     ```yaml
     sources: ["[[source-task-id]]"]
     confidence: established # or provisional / speculative
     synthesized: YYYY-MM-DD
     maturity: seedling # or budding / evergreen
     ```
   - Embed wikilinks (`[[topic-concept]]`) in prose to densify graph reachability.
2. **Execute Destination Write:**
   - Call `pkb__update_body` (for existing notes) or `pkb__create` (for new notes).
3. **Verify Destination Write:**
   - Confirm the tool returned success and record the destination `node_id` (e.g. `kb_634e639c`).
   - **FAILURE GUARD:** If the destination write fails or returns an error, **HALT IMMEDIATELY**. Do not modify the source task body. Do not mark the source consolidated. Abort the operation and report the failure.
4. **Update Source Record:**
   - Only after destination write verification succeeds, update the source frontmatter: set `consolidated: YYYY-MM-DD`.
   - In the source body, record the destination link under `## Pointers`:
     `- [[kb_destination_id]] — Extracted durable findings on <topic>`
   - Leave primary facts untouched, or if trimming bloated execution traces, ensure Goal, checklist, backlinks, and graph edges (`parent`, `depends_on`) are strictly preserved.
   - Never alter `status`, `id`, `parent`, `depends_on`, or `contributes_to` during an extraction pass.

---

## Data Quality: Duplication and Misclassification

### Duplicates Sweep

`pkb__find_duplicates(mode="both")` returns candidate clusters, not verdicts.

1. **Read member titles:** Titles are authoritative. Similarity scores can be misleading.
2. **Heterogeneous titles:** Heterogeneous titles in a cluster mean it is NOT a duplicate set, regardless of score. Ignore or reject.
3. **Merge actions:** Call `pkb__merge_node(canonical_id=..., merge_ids=[...], dry_run=true)` first to preview, then `dry_run=false` to execute. Keep the survivor with the most context and backlinks.

### Misclassification Sweep

Identify untriaged captures masquerading as tasks:

- `Email:` prefix items with high age and no subtasks/actions.
- Informational notes filed with `type: task`.
- Reclassify via `pkb__batch_reclassify` or `pkb__update_task(id=..., type="memory")`.

---

## Transcript Mining Rules

Session transcripts (`_sessions/*.jsonl`) hold ephemeral decisions and context:

1. Transcripts are primary historical records: **NEVER modify transcript body text**.
2. Read up to 10–15 unmined transcripts per pass.
3. Extract generalisable architectural decisions, invariants, or system patterns.
4. Write findings to canonical topic notes following the Destination-First sequence.
5. Record completion by updating frontmatter only: `mined: YYYY-MM-DD`.

---

## Cycle Summary & Reporting

Every consolidation pass emits a structured report with the following mandatory sections:

1. **Halt Count (Top Line):** Total count of tool gaps or halt events encountered (e.g. `HALT COUNT: 0` or `HALT COUNT: 1 (missing tool: ...)`).
2. **Baseline & Delta:** Knowledge layer orphan count before and after the pass.
3. **Extraction Log:** Per-item table including:
   - Source ID
   - Destination Node ID(s)
   - Extraction Type (Augmented / Created / Empty)
   - Verdicts on the Four Tests (`T1: PASS, T2: PASS, T3: PASS, T4: PASS`)
   - 7-Defect Lint Result (`PASS` or specific flagged defect)
4. **Follow-ups & Triaged Candidates:** Explicit list of tasks created for human review or ambiguous duplicate clusters flagged.
