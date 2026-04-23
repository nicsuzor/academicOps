---
name: deep-research
type: skill
category: instruction
description: Author high-quality deep-research prompts (Gemini / ChatGPT Pro / Perplexity Deep Research), then capture the resulting documents into the PKB — including figure extraction, agent-transcribed alt-text for load-bearing images, frontmatter, and wikilink wiring to the sourcing task.
triggers:
  - "deep research"
  - "run a deep-research spike"
  - "capture deep research"
  - "pull this research into the PKB"
  - "save this gdoc"
modifies_files: true
needs_task: true
mode: execution
domain:
  - operations
  - research
allowed-tools: Bash,Read,Write,Edit,Glob,Grep,Skill
version: 1.0.0
permalink: skills-deep-research
---

# Deep Research

> **Taxonomy note**: This skill provides domain expertise (HOW) for the two halves of a deep-research loop: (1) authoring prompts that return usable output, and (2) capturing the resulting document into the PKB with citation fidelity and linked context. See [[aops-core/skills/remember/references/TAXONOMY.md]].

## When to invoke

Two distinct entry points, often used in sequence (sometimes days apart):

- **Authoring**: "help me write a deep-research prompt for X", "I want to spike this question with Gemini". Route to [[prompt-authoring]].
- **Capture**: "I ran this deep-research, pull it in", "save this gdoc into the PKB". Route to [[pkb-capture]].

If the user gives you a URL and asks to "capture", go straight to capture — no prompt authoring needed.

## The deep-research loop (overview)

1. **Frame the question** as an affordable-loss spike task in the PKB with a well-written prompt in the body (`/planner` or direct task creation).
2. **Run the prompt** in the external tool (Gemini Deep Research, ChatGPT Pro, Perplexity Deep Research). The tool returns a Google Doc or similar.
3. **Capture** the output back into the PKB as a `knowledge` note — raw content preserved, figures transcribed, wikilinks back to the sourcing task.
4. **Mark the spike done** with `completion_evidence` pointing at the knowledge note; downstream design tasks can now consume it.

## Prerequisites

- `rclone` installed with a configured Google Drive remote named `gdrive`. To configure: `rclone config` → `n` (new) → name `gdrive` → type `drive` → accept defaults → authorise via browser URL. Verify with `rclone lsd gdrive:` (should not error).
- Capture relies on `rclone` for download, `unzip` for image extraction from `.docx` exports, and your own vision capability for alt-text transcription. **Never** route image transcription through an external service — the agent transcribes, the user verifies.

## Process

### Authoring a prompt

Follow [[prompt-authoring]]. Short version:

- Frame as a _comparison/synthesis_ across 4-6 named bodies of practice (not "tell me about X")
- Require citations and flagging of thin-consensus areas
- End with explicit context: who the user is, what the output must feed, what decisions hinge on it

### Capturing a deep-research document

Follow [[pkb-capture]]. Short version:

- Identify the sourcing task (no guessing — if ambiguous, ask)
- `scripts/fetch.sh <url> <outdir>` — pulls markdown + docx, extracts images
- For every image in the doc: load it, transcribe (LaTeX if math, prose if diagram), rewrite the image reference in the markdown with real alt-text AND keep the image file committed
- Frontmatter with `source`, `gdoc_id`, `spike`, `parent_epic`, `feeds`
- Filename convention: `<common-theme>-<task-id>-<slug>.md` when multiple briefs form a set (e.g. `pkb-weight-<task-id-1>-edge-elicitation.md`); a single standalone brief uses `<topic>-<task-id>-<slug>.md`
- Store images under `knowledge/<topic>/figures/<note-id>/<imageN>.png`
- Update the sourcing task: set `research_output: <note-id>`, add `**Captured**: <date> to [[<note-id>]]`, and mark `done` if acceptance criteria are met

## Reference Files

| Task                                                 | Reference            |
| ---------------------------------------------------- | -------------------- |
| Writing a new deep-research prompt                   | [[prompt-authoring]] |
| Downloading + ingesting a finished research document | [[pkb-capture]]      |

## Guardrails

- **Raw content is evidence.** Never summarise, truncate, or reformat the raw output. Synthesis is a separate task.
- **Citations are load-bearing.** Preserve the Works Cited / footnote blocks verbatim.
- **Images are not optional.** If the source uses figures, extract and transcribe them. An image without alt-text in the PKB is a broken reference.
- **User verifies transcriptions.** Present each image + your transcription side-by-side. Do not commit transcriptions until the user confirms (or corrects).
- **No third-party transcription services.** Vision + transcription is done by the agent running the skill. Never send images to Mathpix, OCR.space, Vertex, or any other external endpoint.
- **Fail fast on auth.** If `rclone lsd gdrive:` errors, halt and tell the user to run `rclone config`. Do not paper over with gcloud ADC or API-key workarounds.

## How to verify

1. Run `scripts/fetch.sh` on a known gdoc — it must produce `.md`, `.docx`, and a `figures/` directory.
2. Capture produces a knowledge note with: valid frontmatter, `[[wikilinks]]` to task and siblings, alt-text on every figure, preserved Works Cited.
3. Sourcing task has `research_output:` frontmatter field pointing at the new note's id.
4. `mcp__plugin_aops-core_pkb__search` for the note title returns the note within a minute (indexing).
