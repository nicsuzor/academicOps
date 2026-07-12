---
name: pkb-capture
parent_skill: deep-research
---

# Capturing a deep-research document into the PKB

## Step 0: Sanity checks

1. **Sourcing task exists.** Every capture must point at a PKB task that asked for this research. If the user gives you a URL without naming a task, search for it (`task_search` by topic) and confirm before writing anything. If no task exists, create one first or HALT and ask.
2. **Rclone is configured.** Run `rclone lsd gdrive:` — any error halts capture. Tell the user: "run `rclone config` to add a `gdrive` remote". Never fall back to gcloud ADC, API keys, or share-link scraping.
3. **Working directory.** Do capture work under `/tmp/deep-research-<date>/` so artefacts are out of the way. Final outputs get moved into the PKB.

## Step 1: Download

```
scripts/fetch.sh <gdoc-url-or-id> /tmp/deep-research-<date>/<slug>
```

The script produces, in that output directory:

- `<slug>.md` — markdown export (the primary content)
- `<slug>.docx` — docx export (source for image extraction)
- `figures/image1.png, image2.png, …` — extracted from the `.docx`'s `word/media/` folder in storage order (NOT necessarily matching `![][imageN]` prose order — see Step 3)

If the script fails, halt with the error. Do not invent alternative downloads.

## Step 2: Match docs to tasks

If more than one doc is being captured, write an explicit mapping before anything else:

```
<slug-1> (<doc title>) → task-XXX
<slug-2> (<doc title>) → task-YYY
```

Match by the H1 title and opening paragraph. If ambiguous, ask.

## Step 3: Transcribe figures

Gemini Deep Research (and other tools that export through Google Docs) **rasterize every formula** on export. No export format (md, docx, html, odt, epub) preserves text-representable math — the source MathML is destroyed. Agent vision is the only recovery path. Do not waste time trying to extract text from the source.

**IMPORTANT — docx/markdown image numbering does NOT match.** The markdown export references images as `![][image1]`, `![][image2]` in _prose order_, but the docx `word/media/` folder numbers them in _storage order_. A single docx `imageN.png` can correspond to any markdown `imageM`. You MUST map by visual context — read the markdown refs and match each to the correct PNG by content, then rename the staged PNGs to match the markdown numbering before rewriting.

For each `![][imageN]` reference in the markdown:

1. Read the surrounding sentence — what is this formula or diagram _supposed_ to say?
2. Load the candidate PNGs via Read and identify the match.
3. Classify:
   - Math formula → LaTeX: `$S \times O \times D$` or block `$$…$$`
   - Diagram → one-sentence caption + bulleted structural description
   - Table → markdown table
   - Decorative → skip
4. Build a map JSON (`{"1": {"kind": "latex", "tex": "..."}, ...}`) keyed by markdown ref number.

**Batching**: for docs with more than ~10 figures, transcribe all of them, then present the transcription table (not each image) to the user in a single batch. Per-image HITL is fine for short docs but exhausts longer ones. Default to batch.

**Never** send images to an external transcription service (Mathpix, OCR.space, Vertex AI, etc.). Agent vision only.

## Step 4: Stage figures and rewrite image references

1. Stage the diagram/chart PNGs (not single-symbol formulas that become LaTeX) under `knowledge/<topic>/figures/<note-id>/`, renamed to match markdown numbering.
2. Run `scripts/rewrite.py <source.md> <note-id> <map.json> <output.md>` — replaces every `![][imageN]` with either `$LaTeX$` or `![alt-text](figures/<note-id>/imageN.png)`, and strips the trailing base64 `[imageN]: <data:image/...>` definitions that Google Docs emits.
3. Verify: `grep -c '!\[\]\[image' <output>` must return 0; `grep -c 'data:image' <output>` must return 0.

## Step 5: Assemble frontmatter

```yaml
---
id: <common-theme>-<task-id>-<slug>
title: <human title>
type: knowledge
topic: <topic — matches the directory under knowledge/>
source: <tool name> — <full gdoc URL>
gdoc_id: <doc id>
date: <today YYYY-MM-DD>
spike: <task-id>
parent_epic: <epic id>
feeds: [<ids of tasks that will consume this brief>]
tags: [deep-research, <topic-specific tags>, ...]
---
```

**Filename convention**:

- Single brief: `<topic-slug>-<task-id>-<short-slug>.md`
- Set of related briefs (same epic, same theme): shared prefix + task-id + slug, e.g. `pkb-weight-<task-id-1>-edge-elicitation.md`, `pkb-weight-<task-id-2>-target-severity.md`. The shared prefix makes them sort together and scan as a series.

## Step 6: Write the body

Above the raw content:

1. One-paragraph context block with `[[wikilinks]]` to: the spike task, parent epic, sibling briefs, downstream consumers.
2. A horizontal rule (`---`).
3. The raw markdown, including preserved Works Cited and citation numbers, with image refs rewritten per Step 4.

Use `Write` tool for the file write — MCP `create` is unwieldy for 100KB+ bodies.

## Step 7: Update the sourcing task

```
mcp__plugin_aops-core_pkb__update_task(
  id="<task-id>",
  updates={
    "research_output": "<note-id>",
    "status": "done",
    "completion_evidence": "Deep-research output captured to knowledge/<topic>/<filename>.md. Figures transcribed and verified by user. Feeds [downstream task ids]."
  }
)
```

Also append to the task body: `**Captured**: <YYYY-MM-DD> to [[<note-id>]]`.

## Step 8: Verify

- File exists, frontmatter parses, wikilinks present
- Every `![` image reference has real alt-text (grep for `!\[\]` must return nothing)
- Every figure image file exists at the referenced path
- `rg "<note title>"` the PKB to confirm it's findable (indexing may take a minute)
- Sourcing task shows `research_output` in its frontmatter

## Archival of working files

After successful capture:

- Move `/tmp/deep-research-<date>/<slug>/` contents out of /tmp (they'll be wiped on reboot). The `.docx` and raw images live under `knowledge/<topic>/figures/<note-id>/` — the only artefact that's NOT under the PKB is the intermediate `.docx`, which can be discarded.

## Failure modes and responses

| Failure                                 | Response                                                                                            |
| --------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `rclone lsd gdrive:` errors             | Halt. Tell user to `rclone config`. No fallback.                                                    |
| Doc title doesn't match any spike       | Halt. Ask user which task this belongs to.                                                          |
| Vision can't parse a formula            | Transcribe best-effort, flag to user as "uncertain — please verify".                                |
| Image extraction returns 0 files        | Inspect the `.docx` structure. If the doc genuinely has no figures, proceed with just the markdown. |
| Frontmatter validation fails when saved | Halt. Fix the frontmatter — do NOT bypass validation.                                               |
