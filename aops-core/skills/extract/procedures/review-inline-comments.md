# Training Data Extraction: Review with Inline Comments

Workflow for extracting training data from peer review documents with inline comments.

## Input

Document containing source text and inline comments/feedback (DOCX, Google Docs, etc.).

## Output

### Sensitive Data → `$ACA_DATA/processed/review_training/{collection_name}/`

1. **`extracted_examples.json`**: All text/feedback pairs with full context
2. **`training_pairs.jsonl`**: Machine-readable format
3. **`collection_summary.md`**: Overview with identifying information intact
4. **`source_documents/`**: Original files if retained

### Generalized Patterns → Framework (public repo)

1. **Update `aops-core/skills/hydrator/workflows/peer-review.md`**: Add depersonalized principles
2. **Constructed examples**: Create generic examples illustrating principles
3. **No identifying information**: Remove names, titles, institutional details

## Process

For detailed step-by-step procedures and patterns, see **[[review-extraction-details]]**.

### Phases

1. **Document Preparation** - Convert to markdown and perform full read.
2. **Extraction** - Identify feedback units and extract source context.
3. **Pattern Identification** - Group by type and extract underlying principles.
4. **Separation of Sensitive/Public** - Store sensitive data in `$ACA_DATA` and depersonalize for framework.
5. **Update Framework Documentation** - Update peer review workflow and skill docs.

## Storage Locations

- **Sensitive Data**: `$ACA_DATA/processed/review_training/` (Personal data directory, restricted access)
- **Public Patterns**: Framework docs in `aops-core/` (Depersonalized, safe for public repo)

## Validation Checklist

- [ ] All feedback units identified and categorized
- [ ] Sensitive data stored in `$ACA_DATA/processed/`
- [ ] Public framework updated with depersonalized content only
- [ ] No identifying information in public docs
- [ ] Collection summary and extraction notes documented

## Example: From Raw to Stored

See **[[review-extraction-details#Example: From Raw to Stored]]** for full example of depersonalization.
