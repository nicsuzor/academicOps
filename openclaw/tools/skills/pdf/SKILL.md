---
name: pdf
description: Render a markdown file as a typeset PDF via pandoc and weasyprint, using bundled Roboto fonts and one of two house stylesheets — academic (A4, justified, bordered heading hierarchy, callouts, footnotes, figure captions) or letter (condensed recipient block, suppressed title, signature block). Use for "make this a PDF", "generate a PDF of this review", "typeset this letter", "export to PDF", or preparing a reference letter, report, review, or research document for sending. Not for HTML or slide output, not for converting a PDF back to markdown (use `extract`), and not for authoring the document's content.
---

# PDF Generation

## Generate

```bash
uv run python scripts/generate_pdf.py <input.md> [output.pdf] [--title "Document Title"] [--type letter|academic]
```

Output defaults to the input path with a `.pdf` extension. The script derives the title,
picks the stylesheet, and detects the document type:

- **letter** — no h1 heading, or "Dear", "Re:", "Sincerely", or "Best," in the first 10 lines
- **academic** — an h1 heading and formal document structure

Override with `--type letter` or `--type academic`. The script is importable as a module.

Fall back to pandoc directly only when the user needs options beyond `--type` and `--title`:

```bash
pandoc input.md -o output.pdf \
  --pdf-engine=weasyprint \
  --metadata title="Document Title" \
  --css=assets/academic-style.css
```

Repeat `--css` to layer a custom stylesheet over a bundled one.

## Stylesheets

- **`assets/academic-style.css`** — A4, justified text with hyphenation, hierarchical
  bordered headings, syntax-highlighted code blocks, tables, callout boxes (`.note`,
  `.warning`, `.tip`, `.important`), footnotes, figure captions.
- **`assets/letter-style.css`** — hides the h1 title, condenses the recipient header block,
  and formats the signature block (space for a handwritten signature; name, title and
  contact in smaller grey text). It assumes the structure below.

Fonts live in `assets/fonts/` and load through `@font-face`, so no system install is needed:
Roboto (Regular, Bold, Italic, Light, Medium) for body and headings, RobotoMono Nerd Font
for code.

## Letter structure

`letter-style.css` styles by paragraph position, so a letter must be laid out this way:

```markdown
[Date] ← paragraph 1: reduced spacing, grey
[Recipient Name] ← paragraph 2
[Recipient Title] ← paragraph 3
[Organization] ← paragraph 4

Dear [Name], ← paragraph 5: margin top

**Re: [Subject]**

[Body paragraphs...] ← justified, 1.5 line height

Yours sincerely,

<img src="$ACA_DATA/assets/signature.png" style="height: 50px;" />

[Your Name] ← smaller, grey
[Your Title] ← smaller, grey
[Your Email]
```

Before generating a letter, check whether the markdown already carries a signature image;
if it does not, insert one from `$ACA_DATA/assets/signature.png` between the closing line
and the name block, using the inline HTML above.

## Requirements

`pandoc` and `weasyprint` must both be present — check with `pandoc --version` and
`weasyprint --version`, and install the latter with `uv tool install weasyprint`. Weasyprint
warns about CSS properties it does not support (`overflow-x`, `gap`); those warnings do not
affect the rendered PDF.
