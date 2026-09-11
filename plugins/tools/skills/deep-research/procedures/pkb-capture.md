---
name: pkb-capture
parent_skill: deep-research
---

# Capturing Deep Research into PKB

## Workflow

### 1. Pre-flight & Download

- Verify sourcing task exists in PKB (`task_search`) and `rclone lsd gdrive:` succeeds.
- Download artifacts to temporary workspace:
  ```bash
  scripts/fetch.sh <gdoc-url-or-id> /tmp/deep-research-<date>/<slug>
  ```
  Produces `<slug>.md`, `<slug>.docx`, and extracted raw images in `figures/`.

### 2. Transcribe Figures (Local Vision)

Google Docs rasterizes equations and math. Recover using local agent vision:

- Map markdown prose references (`![][imageN]`) to storage-order PNGs in `figures/` by visual inspection.
- Classify each figure: LaTeX (`$...$` or `$$...$$`), diagram (caption + structural description), markdown table, or decorative (skip).
- Build transcription JSON mapping ref IDs to LaTeX or alt-text. Present table to user for batch confirmation.

### 3. Stage Figures & Rewrite Markdown

- Stage non-formula images under `knowledge/<topic>/figures/<note-id>/`.
- Rewrite markdown references:
  ```bash
  scripts/rewrite.py <source.md> <note-id> <map.json> <output.md>
  ```
- Verify zero untranscribed image tags remain (`grep -c '!\[\]\[image' <output.md>` equals 0).

### 4. Create Knowledge Note

Assemble note at `knowledge/<topic>/<slug>.md`:

```yaml
---
id: <topic>-<task-id>-<slug>
title: <title>
type: knowledge
topic: <topic>
source: <tool-name> -- <gdoc-url>
gdoc_id: <doc-id>
date: <YYYY-MM-DD>
spike: <task-id>
feeds: [<downstream-task-ids>]
tags: [deep-research, <topic-tags>]
---
```

Body layout: one-paragraph context block with `[[wikilinks]]` to tasks/epics, separator `---`, and raw markdown with preserved citations.

### 5. Update Task & Cleanup

- Update sourcing task via `mcp__plugin_pkb_services__pkb__update_task`: set `research_output` to note ID, status to `done`, and record completion evidence.
- Remove working files from `/tmp/`.

## Failure Handling

- **Rclone failure**: Halt and prompt user to run `rclone config`.
- **Missing task**: Halt and ask user for target task ID before proceeding.
- **Unclear formula**: Transcribe best-effort and flag to user for manual verification.
