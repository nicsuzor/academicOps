---
name: pdf
description: This skill should be used when converting markdown documents to professionally
  formatted PDFs. It provides academic-style typography with Roboto fonts, proper
  page layouts, and styling suitable for research documents, reviews, reports, and
  academic writing. Use when users request PDF generation from markdown files or need
  professional document formatting.
permalink: aops/skills/pdf/skill
---

# PDF Generation Skill

## Overview

Convert markdown documents to professionally formatted PDFs with academic-style typography. This skill uses pandoc with weasyprint to generate beautiful PDFs with Roboto fonts, proper margins, and styling optimized for research documents, reviews, and academic writing.

## When to Use This Skill

Use this skill when:
- User requests converting a markdown file to PDF
- User asks to create a "nice looking PDF" or "professional PDF"
- User mentions wanting academic-style or professional formatting
- User needs a PDF with custom typography or styling
- User requests PDF generation with specific fonts

## Quick Start

For most PDF generation tasks, use the bundled script:

```bash
python scripts/generate_pdf.py <input.md> [output.pdf] [--title "Document Title"]
```

**Example:**
```bash
python scripts/generate_pdf.py reviews/chapter7.md --title "Chapter 7: Moderating Misogyny"
```

This automatically applies the academic style with proper fonts and formatting.

## Typography and Styling

### Font Stack

The skill bundles professional Roboto fonts:
- **Body text and headings**: Roboto (Regular, Bold, Italic, Light, Medium)
- **Code blocks**: RobotoMono Nerd Font

All fonts are embedded in `assets/fonts/` and automatically loaded via the CSS stylesheet.

### Style Features

The `assets/academic-style.css` provides:

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
3. **Extract title**: From filename or ask user if important
4. **Choose approach**:
   - Use `scripts/generate_pdf.py` for standard academic formatting (recommended)
   - Use pandoc directly if user needs custom options
5. **Generate PDF**: Execute the chosen command
6. **Report results**: Confirm success and show output path

## Common Patterns

### Standard Academic Document
```bash
python scripts/generate_pdf.py thesis-chapter.md --title "Chapter 3: Methodology"
```

### Multiple Documents
```bash
for file in reviews/lucinda/*.md; do
  python scripts/generate_pdf.py "$file"
done
```

### Custom Title Override
```bash
python scripts/generate_pdf.py document.md output.pdf --title "Professional Title"
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
Professional stylesheet with:
- Complete `@font-face` declarations for bundled fonts
- Academic typography optimized for readability
- Responsive heading hierarchy
- Code block styling
- Table formatting
- Blockquote and callout box styles
- Print-specific optimizations

### assets/fonts/
Embedded Roboto font family:
- `Roboto-Regular.ttf`, `Roboto-Bold.ttf`, `Roboto-Italic.ttf`, `Roboto-BoldItalic.ttf`
- `Roboto-Light.ttf`, `Roboto-Medium.ttf`
- `RobotoMonoNerdFont-Regular.ttf`, `RobotoMonoNerdFont-Bold.ttf`, `RobotoMonoNerdFont-Italic.ttf`

### scripts/generate_pdf.py
Python script that wraps pandoc with sensible defaults:
- Automatically applies academic stylesheet
- Derives title from filename if not specified
- Handles output path resolution
- Provides clear error messages
- Can be imported as a module for programmatic use
