---
name: deep-research
description: Author high-quality deep-research prompts (Gemini / ChatGPT Pro / Perplexity Deep Research), then capture the resulting documents into the PKB — including figure extraction, agent-transcribed alt-text for load-bearing images, frontmatter, and wikilink wiring to the sourcing task.
---

# Deep Research

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

- `rclone` installed with a configured Google Drive remote named `gdrive` (`rclone config` → new remote of type `drive`). Verify with `rclone lsd gdrive:` (should not error).
- Capture relies on `rclone` for download, `unzip` for image extraction from `.docx` exports, and your own vision capability for alt-text transcription. **Never** route image transcription through an external service — the agent transcribes, the user verifies.

## Process

### Authoring a prompt

Follow [[prompt-authoring]].

### Capturing a deep-research document

Follow [[pkb-capture]].

## Guardrails

- **Raw content is evidence.** Never summarise, truncate, or reformat the raw output. Synthesis is a separate task.
- **Citations are load-bearing.** Preserve the Works Cited / footnote blocks verbatim.
- **Images are not optional.** If the source uses figures, extract and transcribe them. An image without alt-text in the PKB is a broken reference.
- **User verifies transcriptions.** Present each image + your transcription side-by-side. Do not commit transcriptions until the user confirms (or corrects).

## How to verify

1. Run `scripts/fetch.sh` on a known gdoc — it must produce `.md`, `.docx`, and a `figures/` directory.
2. Capture produces a knowledge note with: valid frontmatter, `[[wikilinks]]` to task and siblings, alt-text on every figure, preserved Works Cited.
3. Sourcing task has `research_output:` frontmatter field pointing at the new note's id.
4. `mcp__services__pkb__search` for the note title returns the note within a minute (indexing).
