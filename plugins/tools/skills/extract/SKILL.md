---
name: extract
description: Extract structured information from source documents into appropriate storage -- training pairs from peer reviews, durable facts from correspondence archives, single document key facts, or format conversion (DOCX/PDF/XLSX/PPTX/MSG) to markdown. Enforces sensitive data boundaries.
---

# Extract

Extract structured data from diverse document sources while enforcing strict privacy boundaries.

## Pre-Extraction Search

Search existing PKB knowledge before extracting to augment rather than duplicate:

```
mcp__services__pkb__search(query="[topic/person/subject]")
```

## Routing

| Input                                        | Target Workflow                                         |
| -------------------------------------------- | ------------------------------------------------------- |
| Marked-up peer review & source document      | Training data extraction                                |
| Email archives, correspondence, receipts     | Archive extraction (`remember` skill)                   |
| Single document key information              | Extract directly to PKB notes or framework references   |
| File conversion (DOCX, PDF, XLSX, PPTX, MSG) | `scripts/pdf2md.py` for PDF; `pandoc` for other formats |

## Extraction Workflows

### Training Data Extraction

1. Convert source to markdown; inspect entire document before parsing.
2. Extract feedback units: pair each source text span with its reviewer critique.
3. Categorise units by scope, type, and direction; group recurring principles.
4. Generalise transferable lessons; tag ambiguous feedback as `"quality": "ambiguous"`.
5. Partition outputs across the privacy boundary below.

### Archive Extraction

Extract durable records selectively (decisions, relationships, financial outcomes); discard routine operational chatter. Store entities via `remember` skill.

## Storage Boundary

- **Sensitive materials (Private)**:
  - Store under `$ACA_DATA/processed/review_training/{collection_name}/` (never committed to git).
  - Artifacts: `extracted_examples.json`, `training_pairs.jsonl`, `collection_summary.md`.
  - Correspondence archives: `$ACA_DATA/processed/email_archive/`.
- **Generalised patterns (Public Framework)**:
  - Depersonalise completely: strip author names, institution identifiers, and specific project titles.
  - Store generalised principles in `plugins/tools/skills/peer-review/references/`.

## Verification

Confirm before declaring completion: all inputs are either extracted or skipped with recorded justification; private data resides exclusively in `$ACA_DATA/processed/`; public references contain zero identifying details.
