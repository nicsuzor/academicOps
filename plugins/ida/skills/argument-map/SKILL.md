---
name: "argument-map"
description: "Build a reviewable map of a text's argument (thesis chapter, paper, submission, judgment, policy, or an author's own mind map). Gives a charitable reconstruction with every gap tagged, a list of what the argument still needs, and a readable overview page. Use for \"map the argument\", \"what does this argument still need\", \"show me how the chapter hangs together\", or for weaving an author's new notes or diagrams into an existing map. Not for plain extraction without assessment (use ida:argument-extraction), for a formal sufficiency audit without a page (use ida:argument-audit), or for mind maps and concept maps with no inferential structure (use tools:diagram)."
---

# Argument map

Produce three things:

- **Canonical Argdown source.** This is the record; every picture is derived from it.
- **"What the argument still needs".** The open issues, part by part.
- **A readable page.** It leads with an overview and keeps the detailed maps below.

## Before starting

- **Name four things:** the text, its author, the reader of the map, and the map's job (supervising a draft, reviewing a submission, testing your own case). The job decides how hard to press. If you cannot name the job, ask, because a map with no stated purpose has nothing to be judged against.
- **Extend, don't duplicate.** Look for an existing map of the same text and extend it rather than starting a second one.

## Reconstruct

- **Write to `ida:argdown-toulmin`.** It sets the grammar, metadata, relations, tags, and parser validation.
- **Extract first with `ida:argument-extraction`**, then reconstruct on top of what it produces.
- **Follow the text's own structure.** Put the thesis first, then one Argdown section per part of the text, in the text's order. A reader checks a map against the text, so the map should match it.
- **Reconstruct charitably.** Build the strongest valid version of each step, adding as assumed items the premises and warrants validity needs that the author never states.
- **Read claims at the strength the evidence can carry.** When the wording overstates (for example "veto" where the evidence shows "sometimes limits"), narrow your label but keep the author's words verbatim in `source`. Record the narrower reading as a decision.
- **Tag what is open.** Define the legend in the frontmatter. Use `#conflict` also for a branch that falls outside the thesis as stated. Keep any categories the author already uses (for example evidence versus theory) as extra tags.
- **Leave the author's judgement calls to the author.** Conflicts, scope choices and cut-offs are theirs. Tag each one and state the question it raises.

## Integrate new material

- **Put each new item in the part where it does its work.** Do not append it as a new part, because an appended block reads as a separate argument and hides how it changes the existing steps.
- **Merge restatements.** If an item restates an existing claim, merge it into that claim and keep both locators.
- **Re-check relations.** Afterwards, re-check every relation that touches a changed claim.

## Rebuild from source

Rebuild the Excalidraw canvases, SVGs, and overview page automatically from the canonical Argdown source or PKB note:

```bash
python3 plugins/ida/skills/argument-map/scripts/render.py <source-path-or-note-id> [--out <dir>]
```

Execution runs through the four-stage rebuild contract ([specs/tools/argument-map-rendering.md](../../../../specs/tools/argument-map-rendering.md)):

1. **Syntax Parsing**: Compiles Argdown source to a JSON AST via `@argdown/cli`.
2. **Hierarchical Assembly & Layout**: Maps AST nodes to visual hierarchy following `tools:diagram` ("nest first, arrow last": hero headline for root thesis, zone panels for parts/chapters, vertical columns for sections, sharp rectangular cards for claims, dashed cards for open gaps/objections, dotted warrant blocks beside per-part canvases).
3. **Automated Audit**: Audits generated canvases with `pkb-excalidraw check` (referential integrity, reciprocal `boundElements`, monotonic base-62 fractional indices without trailing fractional zeros), `pkb-excalidraw overlap` (zero shape collisions), and `pkb-excalidraw arrows-check` (zero connector intersections).
4. **Rendering & Page Synthesis**: Renders vector SVGs via `pkb-excalidraw screenshot` and synthesizes the overview markdown document (`<stem>-overview.md`) linking rendered SVGs, summary metrics, and open issue audits.

## Check before delivering

- **The source is sound.** The Argdown parses without errors. Every `#missing` item has a reason, and every quoted source has a locator.
- **The overview is complete.** No argument is left isolated. Every relation in the source is drawn, written on a box, or skipped under the attribution rule. List the skipped ones.
- **The links are real.** Trace three relations back to the text and check that the text makes each link.
- **The page renders.** Look at it at desktop and phone width. Check every cross-reference in the prose ("see the next section") against the actual order of the page.
- **It answers the ask.** Re-read the original ask and check that the page answers it.
- **The map is readable.** Ensure you check the visual renderings, not just the Argdown source. Revise the layout, labels, and colors until the output is clear and legible.

## Record

- **One home.** Keep the Argdown source and the decisions (narrowed readings, merges, dropped views) in the map's PKB note, one line per decision.
- **Pass the sub-project signal.** When creating the note with `pkb.create`, pass the source artefact's PKB-relative path as `source` (e.g. `<subproject>/<canvas>.excalidraw`), or set `parent` to a node whose file lives in that sub-project directory. Under the home-directory placement rule, passing an existing file path as `source` routes the note into that sub-project directory rather than falling back to `notes/`.
- **Rebuild, don't patch.** Rebuild the page from the source. Do not hand-edit the derived renders.
