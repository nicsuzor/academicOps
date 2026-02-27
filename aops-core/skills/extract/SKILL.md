---
name: extract
category: instruction
description: General extraction/ingestion skill that routes to specific workflows based on input type. Extracts structured information from documents, emails, reviews, feedback, and other sources.
allowed-tools: Read,Grep,Glob,Edit,Write,Skill,Bash
version: 1.0.0
permalink: skills-extract
---

# Extraction & Ingestion Skill

General-purpose extraction skill that intelligently routes to specialized workflows based on input type. Extracts structured information from various sources and stores it appropriately (public framework vs. private data).

## Framework Context

[[AXIOMS.md]]

## Purpose

Provide a unified entry point for all extraction tasks:
- Training data extraction from feedback documents
- Archive information extraction (emails, correspondence)
- Decision extraction from task queues
- Knowledge extraction from documents
- Review pair extraction for LLM training

## Workflow Routing

When invoked, analyze the input and route to the appropriate workflow:

### 1. Training Data Extraction

**Signals**:
- Input contains review feedback + source document
- User mentions "training", "extract patterns", "learning", "dataset"
- Documents contain tracked changes, comments, or annotations
- Goal is to build LLM training data

**Route to**: `workflows/extraction/training-data.md`

**Storage**:
- **Sensitive data** (actual review content, source documents): `$ACA_DATA/processed/review_training/`
- **Generalized patterns** (depersonalized principles): Framework docs or peer-review skill

### 2. Archive Information Extraction

**Signals**:
- Input is email archive, correspondence, receipts
- User mentions "archive", "preserve", "remember"
- Goal is to capture significant events/relationships
- Source is historical documents

**Route to**: Existing `archived/skills/extractor/SKILL.md` logic

**Storage**: Use `Skill(skill="remember")` for PKB storage

### 3. Decision Extraction

**Signals**:
- User mentions "decisions", "pending", "blocking"
- Goal is to surface approval/choice items
- Source is task queue

**Route to**: Existing `aops-core/skills/decision-extract/SKILL.md`

**Storage**: Daily note with decision formatting

### 4. Document Knowledge Extraction

**Signals**:
- Single document needs key information extracted
- User mentions "extract", "parse", "ingest"
- Not training data, not archive, not decisions
- Goal is structured information retrieval

**Route to**: `workflows/extraction/document-knowledge.md` (to be created)

**Storage**: Depends on content - PKB or framework docs

## Workflow: Training Data Extraction

### Input Types

#### Type A: Review with Inline Comments (DOCX with tracked changes)
- **Example**: Peer review with inline comments and suggestions
- **Workflow**: `workflows/extraction/review-inline-comments.md`
- **Output**: Training pairs + generalized principles

#### Type B: Separate Review + Source Documents
- **Example**: `review.txt` + `source.pdf` + `metadata.json`
- **Workflow**: `archived/skills/review-training/SKILL.md`
- **Output**: Training pairs matching feedback to source evidence

#### Type C: Revision History
- **Example**: Git history, Google Docs revision history, track changes
- **Workflow**: `workflows/extraction/revision-history.md` (to be created)
- **Output**: Before/after pairs with change rationales

### Extraction Process

See `workflows/extraction/review-inline-comments.md` for detailed workflow.

**Quick summary**:
1. **Convert to workable format** (preserve markup)
2. **Extract feedback units** (text + comment pairs)
3. **Categorize feedback** (type, scope, action)
4. **Identify patterns** (group similar feedback)
5. **Generalize principles** (abstract to transferable form)
6. **Separate sensitive/public** (raw data vs. patterns)
7. **Store appropriately** (sensitive → $ACA_DATA, patterns → framework)

### Storage Rules

**CRITICAL**: Training data often contains sensitive information (author names, unpublished work, specific critiques).

**Sensitive data** → `$ACA_DATA/processed/review_training/{collection_name}/`:
- `extracted_examples.json` (full text/feedback pairs)
- `training_pairs.jsonl` (machine-readable format)
- `collection_summary.md` (with identifying information)
- Source documents (if retained)

**Generalized patterns** → Framework (public repo):
- `aops-core/workflows/peer-review.md` (update with principles)
- `aops-core/skills/*/references/` (depersonalized examples)
- No names, no specific unpublished content, no identifying details

### Quality Standards

**High-quality extraction**:
- Clear connection between feedback and source
- Sufficient context for learning
- Well-categorized with teaching points
- Patterns are transferable

**Generalization quality**:
- Principles are specific enough to apply
- Principles are general enough to transfer
- Examples span different contexts
- Limitations are documented

## Workflow: Archive Information Extraction

Delegate to `archived/skills/extractor/SKILL.md`.

**Key principle**: Most archival documents have NO long-term value. Be highly selective.

**Extract**: Concrete outcomes, significant relationships, financial records
**Skip**: Newsletters, invitations, administrative routine, mass communications

**Storage**: Use `Skill(skill="remember")` with proper tags and canonical identifiers.

## Workflow: Decision Extraction

Delegate to `aops-core/skills/decision-extract/SKILL.md`.

**Key principle**: Extract tasks requiring approval/choice that are blocking other work.

**Storage**: Daily note with formatted decision list for batch processing.

## Sensitive Data Handling

### What is Sensitive?

- Author names and identifying information
- Unpublished work content
- Specific critiques of individuals' work
- Email content and correspondence
- Personal information
- Institutional confidential information

### Storage Location: `$ACA_DATA/processed/`

**Directory structure**:
```
$ACA_DATA/processed/
├── review_training/
│   ├── {collection_name}/
│   │   ├── extracted_examples.json
│   │   ├── training_pairs.jsonl
│   │   ├── collection_summary.md
│   │   └── source_documents/
│   └── ...
├── email_archive/
│   └── ...
└── ...
```

**Access**: This directory is:
- Outside the public academicOps repo
- In personal data directory ($ACA_DATA = `/home/nic/brain`)
- Should be backed up separately
- Not committed to git

### Depersonalization for Public Framework

When adding examples to public framework docs:
1. Remove all names (use "Author", "Reviewer", or generic placeholders)
2. Remove specific work titles (use generic descriptions)
3. Remove institutional affiliations
4. Generalize to principle, not specific instance
5. Use constructed examples if real ones can't be depersonalized

## Integration with Other Skills

### When to use `/extract` vs. specialized skills

**Use `/extract`**:
- Unclear what type of extraction is needed
- Multiple types of documents to process
- Want intelligent routing to appropriate workflow

**Use specialized skill directly**:
- `/remember` - When you know you want to add to knowledge base
- `/decision-extract` - When specifically extracting decisions
- `/review-training` - When processing matched review/source pairs (legacy)

### Skill Composition

```
/extract → analyze input → route to:
  - /remember (for archival preservation)
  - /decision-extract (for pending decisions)
  - training-data workflow (for LLM training data)
  - document-knowledge workflow (for general extraction)
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Unclear input type | Ask user to clarify extraction goal |
| Cannot convert document format | Try alternative conversion, document failure |
| Ambiguous feedback | Flag with `"quality": "ambiguous"`, include with caveats |
| No clear extraction value | Ask user if they want to skip or force extraction |
| Storage location unclear | Default to `$ACA_DATA/processed/`, confirm with user |

## Examples

### Example 1: Peer Review Extraction

**Input**: DOCX file with inline comments from peer review

**User**: `/extract /path/to/review.docx --type peer-review`

**Agent**:
1. Detects inline comments → routes to review-inline-comments workflow
2. Converts DOCX with `pandoc --track-changes=all`
3. Extracts 18 feedback units
4. Identifies 10 generalisable principles
5. Stores sensitive data in `$ACA_DATA/processed/review_training/aoir2026/`
6. Updates `aops-core/workflows/peer-review.md` with depersonalized principles

### Example 2: Email Archive

**Input**: Directory of email MSG files

**User**: `/extract emails/2025-Q1/ --type archive`

**Agent**:
1. Detects email archive → routes to extractor skill logic
2. Processes each email, applies judgment criteria
3. Extracts significant events/relationships
4. Uses `/remember` to store in PKB
5. Skips 90% of emails as noise

### Example 3: Auto-Detection

**Input**: Mixed documents without type specified

**User**: `/extract documents/`

**Agent**:
1. Analyzes each document
2. Detects: 2 peer reviews (tracked changes), 5 emails, 1 grant application
3. Routes peer reviews → training-data workflow
4. Routes emails → archive extraction
5. Asks user about grant application (unclear extraction goal)

## Validation Checklist

Before completing extraction:

**Completeness**:
- [ ] All extractable items identified
- [ ] All items processed (or skipped with reason)
- [ ] Output files created in correct locations

**Quality**:
- [ ] Teaching value is clear (for training data)
- [ ] Categorization is accurate
- [ ] Context is sufficient

**Sensitivity**:
- [ ] Sensitive data stored in `$ACA_DATA/processed/`
- [ ] Public framework contains only depersonalized content
- [ ] No identifying information in public docs

**Documentation**:
- [ ] Extraction process documented
- [ ] Decisions and ambiguities noted
- [ ] Collection summary created

## Future Enhancements

- Semi-automated pattern detection
- Batch processing for multiple documents
- Integration with continuous ingestion pipeline
- Quality metrics and validation tools
- Cross-collection pattern analysis
