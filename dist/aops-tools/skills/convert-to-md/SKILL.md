---
name: convert-to-md
category: instruction
description: Batch convert documents (DOCX, PDF, XLSX, TXT, PPTX, MSG, DOC) to markdown, preserving tracked changes and comments.
allowed-tools: Bash,Read
version: 1.0.0
permalink: skills-convert-to-md
---

# Document to Markdown Conversion

Batch convert documents to markdown format, preserving tracked changes, comments, and other markup.

## Usage

```
/convert-to-md [directory]
```

## Supported Formats

| Format | Method                       | Notes                                |
| ------ | ---------------------------- | ------------------------------------ |
| DOCX   | pandoc `--track-changes=all` | Preserves comments & tracked changes |
| PDF    | PyMuPDF                      | Text extraction                      |
| XLSX   | pandas                       | Converts to markdown tables          |
| TXT    | rename                       | Direct rename to .md                 |
| PPTX   | pandoc                       | Slide content to markdown            |
| MSG    | extract-msg                  | Email metadata + body                |
| DOC    | textutil                     | macOS native (fallback)              |
| DOTX   | pandoc                       | Word templates                       |

## Process

1. **Install dependencies** (if needed):
   ```bash
   uv add pymupdf pandas openpyxl tabulate extract-msg
   ```

2. **Convert DOCX** (preserves comments/edits):
   ```bash
   for f in *.docx; do
     pandoc --track-changes=all -f docx -t markdown -o "${f%.docx}.md" "$f" && rm "$f"
   done
   ```

3. **Convert PDF**:
   ```python
   import fitz
   from pathlib import Path
   for pdf in Path(".").glob("*.pdf"):
       doc = fitz.open(pdf)
       text = "\n\n".join(page.get_text() for page in doc)
       pdf.with_suffix(".md").write_text(text.strip())
       pdf.unlink()
   ```

4. **Convert XLSX** to tables:
   ```python
   import pandas as pd
   for xlsx in Path(".").glob("*.xlsx"):
       xls = pd.ExcelFile(xlsx)
       content = f"# {xlsx.stem}\n\n"
       for sheet in xls.sheet_names:
           df = pd.read_excel(xlsx, sheet_name=sheet)
           content += f"## {sheet}\n\n{df.to_markdown(index=False)}\n\n"
       xlsx.with_suffix(".md").write_text(content)
       xlsx.unlink()
   ```

5. **Convert TXT**: `for f in *.txt; do mv "$f" "${f%.txt}.md"; done`

6. **Convert MSG**:
   ```python
   import extract_msg
   msg = extract_msg.Message("file.msg")
   content = f"# {msg.subject}\n\n**From:** {msg.sender}\n**Date:** {msg.date}\n\n{msg.body}"
   ```

7. **Clean up**: Remove `*:Zone.Identifier` files (Windows metadata)

## Behavior

- Deletes original files after successful conversion
- Skips files that already have a .md counterpart
- Reports failures without stopping batch

## Dependencies

- `pandoc` (system): DOCX, PPTX, DOTX conversion
- `textutil` (macOS): DOC fallback
- `pymupdf` (Python): PDF text extraction
- `pandas`, `openpyxl`, `tabulate` (Python): XLSX tables
- `extract-msg` (Python): Outlook MSG files
