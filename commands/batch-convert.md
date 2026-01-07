---
name: batch-convert
category: instruction
description: Batch convert documents to markdown, preserving tracked changes and comments
---

Use the Skill tool to invoke the `convert-to-md` skill: `Skill(skill="convert-to-md")` - this will load instructions for batch document conversion.

**Usage**: `/convert-to-md [directory]`

Converts DOCX, PDF, XLSX, TXT, PPTX, MSG, DOC files to markdown. Preserves Word tracked changes and comments via pandoc `--track-changes=all`.

After conversion, original files are deleted.
