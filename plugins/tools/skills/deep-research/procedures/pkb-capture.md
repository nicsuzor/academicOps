---
name: pkb-capture
parent_skill: deep-research
---

# Capturing Deep Research into PKB

## Workflow

### 1. Pre-flight & Download

- When the composed workflow tracks a sourcing PKB task, verify it exists (via PKB search); verify `rclone lsd gdrive:` succeeds.
- Download artifacts to temporary workspace:
  ```bash
  scripts/fetch.sh <gdoc-url-or-id> /tmp/deep-research-<date>/<slug>
  ```
  Produces `<slug>.md`, `<slug>.docx`, and extracted raw images in `figures/`.

### 2. Transcribe Figures (Local Vision)

Google Docs rasterizes equations and math. Recover using local agent vision:

- Map markdown prose references (`![][imageN]`) to storage-order PNGs in `figures/` by visual inspection.
- Classify each figure: LaTeX (`$...$` or `$$...$$`), diagram (caption + structural description), markdown table, or decorative (skip).
- Build transcription JSON mapping ref IDs to LaTeX or alt-text. In interactive workflows, present the table to the user for batch confirmation; in headless workflows, proceed per task instructions.

### 3. Stage Figures & Rewrite Markdown

- Stage non-formula images in the workflow-specified figure directory (default `knowledge/<topic>/figures/<note-id>/` when PKB capture is selected).
- Rewrite markdown references:
  ```bash
  uv run python scripts/rewrite.py <source.md> <note-id> <map.json> <output.md>
  ```
- Verify zero untranscribed image tags remain (`grep -c '!\[\]\[image' <output.md>` equals 0).

### 4. Create Knowledge Note

Assemble the note at the destination directed by the composed workflow and task (default `knowledge/<topic>/<slug>.md` when PKB capture is selected), applying PKB frontmatter when storing in the PKB:

```yaml
---
id: <topic>-<task-id>-<slug>
title: <title>
type: knowledge
topic: <topic>
source: <tool-name> -- <gdoc-url>
gdoc_id: <doc-id>
date: <YYYY-MM-DD>
probe: <task-id>
feeds: [<downstream-task-ids>]
tags: [deep-research, <topic-tags>]
---
```

Body layout: one-paragraph context block (with `[[wikilinks]]` to tasks when PKB-tracked), separator `---`, and raw markdown with preserved citations.

### 5. Update Task & Cleanup

- When the composed workflow directs sourcing-task updates, update the sourcing task per workflow instructions (e.g., setting `research_output` to the note ID, status as directed such as `done`, and completion evidence).
- Remove working files from `/tmp/`.

## Failure Handling

- **Rclone failure**: Halt and report verbatim (in interactive workflows, prompt the user to run `rclone config`).
- **Missing task**: When a sourcing task is required by the composed workflow and missing, halt and request the target task ID (from the user in interactive workflows or the supervisor in headless workflows) before proceeding.
- **Unclear formula**: Transcribe best-effort and flag for verification (to the user in interactive workflows, or in task/handback notes in headless workflows).
