---
name: pdf
description: Convert markdown documents to professionally formatted PDFs with academic-style typography, Roboto fonts, proper page layouts, and styling suitable for research documents, reviews, reports, and academic writing.
allowed-tools: Read,Bash
version: 2.0.0
permalink: skills-pdf
---

# PDF Generation Skill

## Overview

Convert markdown documents to professionally formatted PDFs with appropriate typography. This skill uses pandoc with weasyprint to generate beautiful PDFs with Roboto fonts, proper margins, and styling optimized for different document types:

- **Academic documents**: Research documents, reviews, reports with formal heading hierarchy
- **Letters**: Professional correspondence with condensed header spacing, hidden h1 titles, and signature blocks

The skill automatically detects document type based on content structure.

## When to Use This Skill

Use this skill when:
- User requests converting a markdown file to PDF
- User asks to create a "nice looking PDF" or "professional PDF"
- User mentions wanting academic-style or professional formatting
- User needs a PDF with custom typography or styling
- User requests PDF generation with specific fonts
- User needs to generate a letter or reference with proper formatting

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

Two stylesheets are available:

#### Academic Style (`assets/academic-style.css`)

**Page Layout:**
- A4 page size
- 2.5cm top/bottom margins, 2cm left/right margins
- Justified text with proper hyphenation
- Orphan/widow control

**Typography:**
- 11pt body text with 1.6 line height
- Hierarchical heading sizes (24pt → 11pt)
- Heading borders for h1 and h2
- Page break control (avoid breaking after headings)

**Code Formatting:**
- 9pt monospaced code in RobotoMono Nerd Font
- Syntax-highlighted code blocks with left border
- Shaded background for readability

**Special Elements:**
- Blockquotes with left border and italic styling
- Professional table formatting with alternating row colors
- Callout boxes (.note, .warning, .tip, .important)
- Footnote support
- Figure captions

#### Letter Style (`assets/letter-style.css`)

**Page Layout:**
- A4 page size with same margins as academic
- Justified body text with proper hyphenation

**Typography:**
- **Hidden h1 headers** - letters shouldn't show document titles
- **Condensed header block** - Date, recipient name, title with reduced spacing (0.2em)
- **Body paragraphs** - 11pt with 1.5 line height, justified
- **Signature block** - Last 4 paragraphs formatted with:
  - Closing (e.g., "Best,") with top margin
  - 2.5em space for handwritten signature
  - Name, title, contact info in smaller font (10pt, gray)

**Letter Structure Assumptions:**
```markdown
[Date]                    ← Paragraph 1: reduced spacing, gray
[Recipient Name]          ← Paragraph 2: reduced spacing
[Recipient Title]         ← Paragraph 3: reduced spacing
[Organization]            ← Paragraph 4: reduced spacing

Dear [Name],             ← Paragraph 5: margin top

**Re: [Subject]**        ← Bold subject line

[Body paragraphs...]     ← Justified, 1.5 line height

Yours sincerely,         ← Closing

<img src="/path/to/signature.png" style="height: 50px;" />

[Your Name]              ← smaller, gray
[Your Title]             ← smaller, gray
[Your Email]
```

### Signature Insertion (Letters)

For letters, insert the user's signature image between the closing and name. Use inline HTML:

```markdown
Yours sincerely,

<img src="$ACA_DATA/assets/signature.png" style="height: 50px;" />

Nicolas Suzor
```

**Signature location**: `$ACA_DATA/assets/signature.png` (user's personal data directory)

**Before generating PDF for a letter**: Check if the markdown already contains a signature image. If not, insert one between the closing line (e.g., "Yours sincerely,") and the name block.

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

When a user requests PDF generation:

1. **Identify the input file**: Confirm the markdown file path
2. **Determine output location**: Use same directory with `.pdf` extension if not specified
3. **Detect document type**: Script auto-detects based on content (letter vs academic)
4. **Extract title**: From filename or ask user if important (less relevant for letters)
5. **Choose approach**:
   - Use `scripts/generate_pdf.py` for automatic styling (recommended)
   - Use pandoc directly if user needs custom options
   - Override auto-detection with `--type` if needed
6. **Generate PDF**: Execute the chosen command
7. **Report results**: Confirm success and show output path

## Common Patterns

### Standard Academic Document
```bash
uv run python scripts/generate_pdf.py thesis-chapter.md --title "Chapter 3: Methodology"
```

### Reference Letter or Formal Letter
```bash
# Auto-detection will use letter style
uv run python scripts/generate_pdf.py reference-letter.md

# Or explicit
uv run python scripts/generate_pdf.py letter.md --type letter
```

### Multiple Documents
```bash
for file in reviews/lucinda/*.md; do
  uv run python scripts/generate_pdf.py "$file"
done
```

### Override Auto-Detection
```bash
# Force academic style even if it looks like a letter
uv run python scripts/generate_pdf.py document.md --type academic

# Force letter style even with h1 heading
uv run python scripts/generate_pdf.py document.md --type letter
```

### Custom Title Override
```bash
uv run python scripts/generate_pdf.py document.md output.pdf --title "Professional Title"
```

## Troubleshooting

**Fonts not rendering:**
- Fonts are bundled in `assets/fonts/` and referenced in CSS
- Weasyprint automatically loads fonts from CSS `@font-face` rules
- No system font installation required

**Weasyprint not found:**
```bash
uv tool install weasyprint
```

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

## Resources

### assets/academic-style.css
Professional stylesheet for research documents with:
- Complete `@font-face` declarations for bundled fonts
- Academic typography optimized for readability
- Responsive heading hierarchy with visible h1
- Code block styling
- Table formatting
- Blockquote and callout box styles
- Print-specific optimizations

### assets/letter-style.css
Professional stylesheet for formal correspondence with:
- Same font declarations as academic style
- **Hidden h1 headers** (letters shouldn't show document titles)
- **Condensed header spacing** for recipient info
- **Signature block formatting** with space for handwritten signature
- Body text optimized for letter format
- Assumes specific letter structure (see Letter Style section)

### assets/fonts/
Embedded Roboto font family:
- `Roboto-Regular.ttf`, `Roboto-Bold.ttf`, `Roboto-Italic.ttf`, `Roboto-BoldItalic.ttf`
- `Roboto-Light.ttf`, `Roboto-Medium.ttf`
- `RobotoMonoNerdFont-Regular.ttf`, `RobotoMonoNerdFont-Bold.ttf`, `RobotoMonoNerdFont-Italic.ttf`

### scripts/generate_pdf.py
Python script that wraps pandoc with intelligent defaults:
- **Auto-detects document type** (letter vs academic) from content
- Automatically applies appropriate stylesheet
- Derives title from filename if not specified
- Handles output path resolution
- Provides clear error messages
- Supports `--type` override for manual control
- Can be imported as a module for programmatic use
