---
name: pdf
description: Render markdown files as typeset PDFs via pandoc and weasyprint using academic (A4, justified, headings, callouts, footnotes) or letter stylesheets. Use for reports, grant reviews, or formal letters.
---

# PDF Generation

Generate typeset PDFs from markdown using bundled Roboto typography and house stylesheets.

## Generation Command

```bash
uv run python scripts/generate_pdf.py <input.md> [output.pdf] [--title "Title"] [--type letter|academic]
```

Auto-detects document type (letter if initial text contains "Dear", "Re:", or lacks an H1; academic otherwise). Defaults output to `<input>.pdf`.

## Stylesheets

- **`assets/academic-style.css`**: Standard A4 format with justified text, hierarchical bordered headings, code syntax highlighting, tables, callouts (`.note`, `.warning`, `.tip`, `.important`), and footnotes.
- **`assets/letter-style.css`**: Suppresses H1, formats recipient address blocks, and prepares signature spacing.

## Letter Structure Requirements

Letters styled with `letter-style.css` require paragraph-position ordering:

```markdown
[Date]
[Recipient Name]
[Recipient Title]
[Organization]

Dear [Name],

**Re: [Subject]**

[Body paragraphs...]

Yours sincerely,

<img src="$ACA_DATA/assets/signature.png" style="height: 50px;" />

[Signer Name]
[Signer Title]
[Signer Email]
```

Insert signature image from `$ACA_DATA/assets/signature.png` if not already present.

## Dependencies

Requires `pandoc` and `weasyprint` (`uv tool install weasyprint`).
