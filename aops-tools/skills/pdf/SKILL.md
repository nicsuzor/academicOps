---
name: pdf
description: Convert markdown documents to professionally formatted PDFs with academic-style
  typography, Roboto fonts, proper page layouts, and styling suitable for research
  documents, reviews, reports, and academic writing.
---

# PDF Generation Skill

> **Taxonomy note**: This skill provides domain expertise (HOW) for markdown to PDF conversion with academic typography. See [[aops/skills/remember/references/TAXONOMY.md]] for the skill/workflow distinction.

## Overview

Convert markdown documents to professionally formatted PDFs with appropriate typography. This skill uses pandoc with weasyprint to generate beautiful PDFs with Roboto fonts, proper margins, and styling optimized for different document types:

- **Academic documents**: Research documents, reviews, reports with formal heading hierarchy
- **Letters**: Professional correspondence with condensed header spacing, hidden h1 titles, and signature blocks

The skill automatically detects document type based on content structure.

## Quick Start

For most PDF generation tasks, use the bundled script:

```bash
uv run python scripts/generate_pdf.py <input.md> [output.pdf] [--title "Document Title"] [--type letter|academic]
```

**Examples:**

Academic document (auto-detected or explicit):

```bash
uv run python scripts/generate_pdf.py reviews/chapter7.md --title "Chapter 7: Moderating Misogyny"
uv run python scripts/generate_pdf.py paper.md --type academic
```

Letter (auto-detected or explicit):

```bash
uv run python scripts/generate_pdf.py reference-letter.md
uv run python scripts/generate_pdf.py letter.md --type letter
```

The script automatically detects document type:

- **Letter**: No h1 heading OR contains "Dear", "Re:", "Sincerely", "Best," in first 10 lines
- **Academic**: Has h1 heading and formal document structure

You can override auto-detection with `--type letter` or `--type academic`.

## Typography and Styling

### Font Stack

The skill bundles professional Roboto fonts:

- **Body text and headings**: Roboto (Regular, Bold, Italic, Light, Medium)
- **Code blocks**: RobotoMono Nerd Font

All fonts are embedded in `assets/fonts/` and automatically loaded via the CSS stylesheet.

### Style Features

Two bundled stylesheets, applied automatically by the script:

- **`academic-style.css`** — A4, justified text with hyphenation, hierarchical bordered headings, syntax-highlighted code blocks, tables, callout boxes (`.note`, `.warning`, `.tip`, `.important`), footnotes, figure captions.
- **`letter-style.css`** — hides the h1 title, condenses the recipient header block, and formats a signature block (space for a handwritten signature; name/title/contact in smaller gray text). Assumes the structure below.

**Letter Structure Assumptions:**

```markdown
[Date] ← Paragraph 1: reduced spacing, gray
[Recipient Name] ← Paragraph 2: reduced spacing
[Recipient Title] ← Paragraph 3: reduced spacing
[Organization] ← Paragraph 4: reduced spacing

Dear [Name], ← Paragraph 5: margin top

**Re: [Subject]** ← Bold subject line

[Body paragraphs...] ← Justified, 1.5 line height

Yours sincerely, ← Closing

<img src="/path/to/signature.png" style="height: 50px;" />

[Your Name] ← smaller, gray
[Your Title] ← smaller, gray
[Your Email]
```

### Signature Insertion (Letters)

Before generating a PDF for a letter, check whether the markdown already contains a signature image; if not, insert one between the closing line (e.g., "Yours sincerely,") and the name block, using inline HTML:

```markdown
Yours sincerely,

<img src="$ACA_DATA/assets/signature.png" style="height: 50px;" />

Nicolas Suzor
```

**Signature location**: `$ACA_DATA/assets/signature.png` (user's personal data directory)

## Using Pandoc Directly

For more control, invoke pandoc directly:

```bash
pandoc input.md -o output.pdf \
  --pdf-engine=weasyprint \
  --metadata title="Document Title" \
  --css=assets/academic-style.css
```

### Custom Styling

To override or extend the default styling:

1. Create a custom CSS file
2. Reference it with `--css=path/to/custom.css`
3. Or combine multiple CSS files:
   ```bash
   pandoc input.md -o output.pdf \
     --pdf-engine=weasyprint \
     --css=assets/academic-style.css \
     --css=custom-additions.css
   ```

## Requirements

The skill requires:

- **pandoc**: Markdown processor (usually pre-installed)
- **weasyprint**: PDF rendering engine
  ```bash
  uv tool install weasyprint
  ```

Check if requirements are met:

```bash
pandoc --version
weasyprint --version
```

## Workflow

Default to the same directory with a `.pdf` extension when no output path is given. Prefer `scripts/generate_pdf.py` — it auto-detects document type and applies the right stylesheet; fall back to invoking pandoc directly only when the user needs custom options beyond the script's `--type`/`--title` flags.

## Common Patterns

The Quick Start invocations cover single documents. To batch a directory:

```bash
for file in reviews/lucinda/*.md; do
  uv run python scripts/generate_pdf.py "$file"
done
```

## Troubleshooting

**Fonts not rendering:**

- Fonts are bundled in `assets/fonts/` and referenced in CSS
- Weasyprint automatically loads fonts from CSS `@font-face` rules
- No system font installation required

**Weasyprint not found:** see Requirements above for the install command.

**CSS warnings:**

- Weasyprint may show warnings about unsupported CSS properties
- These are usually safe to ignore (e.g., `overflow-x`, `gap`)
- The PDF will still render correctly

**Pandoc not found:**

```bash
# Ubuntu/Debian
sudo apt install pandoc

# macOS
brew install pandoc
```

## Bundled Resources

- **`assets/academic-style.css`**, **`assets/letter-style.css`** — the two stylesheets (see Style Features above).
- **`assets/fonts/`** — embedded Roboto family (Regular/Bold/Italic/Light/Medium) plus RobotoMono Nerd Font; loaded via `@font-face`, no system install needed.
- **`scripts/generate_pdf.py`** — pandoc wrapper: auto-detects document type, applies the stylesheet, derives the title, resolves the output path, supports `--type` override, and can be imported as a module.
