---
name: "argument-map"
description: "Build a reviewable map of a text's argument (thesis chapter, paper, submission, judgment, policy, or an author's own mind map). Gives a charitable reconstruction with every gap tagged, a list of what the argument still needs, and a readable overview page. Use for \"map the argument\", \"what does this argument still need\", \"show me how the chapter hangs together\", or for weaving an author's new notes or diagrams into an existing map. Not for plain extraction without assessment (use ida:argument-extraction), for a formal sufficiency audit without a page (use ida:argument-audit), or for mind maps and concept maps with no inferential structure (use tools:diagram)."
---

# Argument Map

Produce three deliverables:

- **Canonical Argdown source**: The single record from which every diagram and page is derived.
- **"What the argument still needs"**: Open issues listed part by part.
- **A readable overview page**: Leads with the synthesis overview and places detailed maps below.

## Before Starting

- **Name four things**: The text, its author, the map's reader, and the map's job (supervising a draft, reviewing a submission, testing a case). If the job is unclear, ask first so there is a standard to judge against.
- **Extend, don't duplicate**: Search for an existing map of the text and extend it rather than starting a duplicate.

## Reconstruct & Integrate

- **Grammar & extraction**: Extract first with `ida:argument-extraction`, then write and validate against `ida:argdown-toulmin` (grammar, metadata, relations, tags, parser validation).
- **Match the text's structure**: Lead with the thesis, followed by one Argdown section per part in the text's order.
- **Reconstruct charitably at supportable strength**: Supply unstated premises and warrants needed for validity as assumed items. When wording overstates the evidence (e.g. "veto" where evidence shows "sometimes limits"), narrow the label, preserve verbatim text in `source`, and record the narrowed reading as a decision.
- **Tag open items & preserve author calls**: Define the tag legend in frontmatter (`#conflict` covers out-of-thesis branches too; preserve author categories as tags). Tag conflicts, scope choices, and cut-offs and state the question raised rather than deciding them for the author.
- **Integrate new material in place**: Insert new items into the part where they do work (never append as a separate section), merge restatements while keeping both locators, and re-check all touching relations.

## Rebuild from Source

Rebuild Excalidraw canvases, SVGs, and the overview page from the canonical Argdown source or PKB note:

```bash
python3 "${CLAUDE_SKILL_DIR:-plugins/ida/skills/argument-map}/scripts/render.py" <source-path-or-note-id> [--out <dir>]
```

The rebuild runs through four stages:

1. **Syntax Parsing**: Compiles Argdown source to a JSON AST via `@argdown/cli`.
2. **Hierarchical Assembly & Layout**: Maps AST nodes to visual hierarchy per `tools:diagram` ("nest first, arrow last": thesis headline, part zone panels, section columns, rectangular claim cards, dashed open-gap cards, dotted warrant blocks).
3. **Automated Audit**: Runs `pkb-excalidraw check` (referential integrity, reciprocal `boundElements`, monotonic base-62 fractional indices without trailing zeros), `pkb-excalidraw overlap`, and `pkb-excalidraw arrows-check`.
4. **Rendering & Page Synthesis**: Renders vector SVGs via `pkb-excalidraw screenshot` and generates `<stem>-overview.md` with rendered SVGs, summary metrics, and open-issue audits.

## Check Before Delivering & Record

- **Sound & complete**: Argdown parses cleanly; every `#missing` item has a reason; every quote has a locator; every source relation is drawn, noted on a box, or listed under skipped attributions; spot-check three links back to the text.
- **Readable & faithful**: Inspect rendered SVGs and the overview page at desktop and mobile widths until visually clear, verify all prose cross-references match page order, and confirm the output answers the original ask.
- **One home & rebuild-only**: Store the Argdown source and one-line-per-decision log in the map's PKB note. When creating the note with `pkb.create`, pass the source artefact's PKB-relative path in `source` (or set `parent` to a node in that sub-project) so it files in the sub-project directory rather than `notes/`. Never hand-edit derived renders; always rebuild from source.
