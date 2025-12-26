# Review Training Data Extraction

Automated system for extracting training pairs (review feedback → source evidence) from matched peer review/source document pairs. Builds a dataset for teaching LLMs to perform academic peer review in Nic's style.

## Quick Start

### Check Status

```bash
uv run python bots/skills/review-training/scripts/batch_next.py status
```

### Process Next Pair

Run the slash command:

```
/review-training
```

This will:

1. Get next matched pair from `archive/matched/`
2. Read source document and review
3. Extract feedback → evidence training pairs
4. Create training data files in `data/review-training/{pair_id}/`
5. Delete the source pair (after confirmation)
6. Log all decisions

### Process Multiple Pairs

Run `/review-training` repeatedly to process all 16 matched pairs.

## Architecture

```
archive/matched/                   # Input: 16 matched pairs
├── 006_IJOC-review/
│   ├── review.txt
│   ├── source.txt
│   └── metadata.json
├── 011_DP260100770 Bowrey/
└── ... (16 total)

bots/skills/review-training/
├── SKILL.md                       # Extraction guidelines
├── README.md                      # This file
├── scripts/
│   └── batch_next.py             # Batch management
└── tests/
    └── test_integration.sh       # Integration tests

bots/commands/
└── review-training.md            # /review-training slash command

data/review-training/             # Output: training data
├── 006_IJOC-review/
│   ├── source_summary.md         # Summary of source
│   ├── feedback_units.json       # Structured feedback
│   └── training_pairs.jsonl      # Training pairs
└── ... (16 pairs when complete)

archive/
├── review_processing.log         # Decision log
├── review_processing_state.json  # Resume state
└── failed_extraction/            # Failed pairs
```

## Components

### 1. Review Training Skill (`SKILL.md`)

Defines extraction approach for three types of feedback:

**Type 1: Specific Text Match**

- Feedback references exact text in source
- Extract: exact quote + page ref + feedback

**Type 2: Pattern Recognition**

- Feedback identifies structural/methodological issue
- Extract: representative examples + synthesized pattern + feedback

**Type 3: High-Level Synthesis**

- Feedback addresses overall approach
- Extract: sufficient context + synthesis + feedback

### 2. Batch Manager (`scripts/batch_next.py`)

Stateful processing of matched pairs:

```bash
# Get next pair
uv run python bots/skills/review-training/scripts/batch_next.py next

# Confirm complete (deletes source)
uv run python bots/skills/review-training/scripts/batch_next.py confirm <pair_name>

# Mark as failed (moves to failed/)
uv run python bots/skills/review-training/scripts/batch_next.py fail <pair_name> "reason"

# Check status
uv run python bots/skills/review-training/scripts/batch_next.py status
```

### 3. Slash Command (`/review-training`)

Process one pair per invocation to manage context windows.

## Training Data Format

### source_summary.md

```markdown
# Source Document Summary

**Title**: [Document title] **Type**: [journal article | grant | thesis] **Topic**: [Brief description]

## Main Argument

[1-2 paragraph summary]
```

### feedback_units.json

```json
{
  "pair_id": "064_HRRE",
  "source_title": "Power and Humility in OSI",
  "feedback_units": [
    {
      "unit_id": "064_HRRE_001",
      "source_context": {
        "section": "Part II",
        "page_ref": "p2, p14",
        "text_excerpt": "exact quote",
        "synthesized_context": null
      },
      "feedback": {
        "comment": "This quote is repeated...",
        "scope": "specific",
        "type": "style",
        "action": "remove"
      },
      "training_value": {
        "pattern_type": "Detect duplicate content",
        "teaching_point": "Learn to identify repeated text"
      }
    }
  ]
}
```

### training_pairs.jsonl

One JSON object per line (easy loading):

```jsonl
{"pair_id": "064_HRRE_001", "source_context": {...}, "feedback": {...}}
{"pair_id": "064_HRRE_002", "source_context": {...}, "feedback": {...}}
```

## Categorization System

### Scope

- **specific**: References specific text/quote
- **section**: Addresses a section
- **document**: Overall structure/approach

### Type

- **structural**: Organization, flow
- **methodological**: Research methods, validity
- **substantive**: Argument, claims, evidence
- **clarity**: Writing quality, explanation
- **citation**: References, attribution
- **style**: Formatting, presentation

### Action

- **revise**: Change existing content
- **add**: Include missing content
- **remove**: Delete content
- **clarify**: Improve explanation
- **reorganize**: Restructure
- **strengthen**: Enhance argument

## Source File Handling

### PDF Files

- Extract text with PyPDF2 or pdftotext
- Preserve page numbers
- Verify extraction quality

### DOCX Files

- Extract with python-docx
- Preserve structure (headings, sections)
- Handle tables/figures appropriately

### TXT Files

- Already plain text
- Use structure markers if present
- Infer sections from content

## Processing Guidelines

### Quality Standards

✓ **High-quality training pairs**:

- Clear connection between feedback and source
- Specific enough to teach pattern recognition
- Representative of Nic's review style
- Sufficient context included

❌ **Skip or flag**:

- Generic feedback with no source connection
- Administrative comments only
- Formatting-only feedback (unless pedagogically valuable)

### Handling Ambiguity

- Flag with `"ambiguous": true` if unclear
- Include best-effort interpretation
- May still have training value
- Document in teaching_point

## Current Status

```bash
# Check current status
uv run python bots/skills/review-training/scripts/batch_next.py status
```

Expected output:

```json
{
  "remaining": 16,
  "processed": 0,
  "failed": 0
}
```

## Example Extraction

### Input

- Review: "This quote is repeated on p2 and 14: [quote]"
- Source: PDF with repeated quote on pages 2 and 14

### Output

```json
{
  "pair_id": "064_HRRE_001",
  "source_context": {
    "page_ref": "p2, p14",
    "text_excerpt": "[exact quote]"
  },
  "feedback": {
    "comment": "This quote is repeated on p2 and 14",
    "scope": "specific",
    "type": "style",
    "action": "remove"
  },
  "training_value": {
    "pattern_type": "Detect duplicate content",
    "teaching_point": "LLM should learn to identify and flag repeated quotes"
  }
}
```

## Safety Features

1. **Destructive processing**: Source deleted only after confirmation
2. **State tracking**: Can resume from interruption
3. **Error handling**: Failed pairs moved to `archive/failed_extraction/`
4. **Logging**: All decisions logged to `archive/review_processing.log`

## Troubleshooting

**No pairs to process**:

```bash
ls -la archive/matched/
```

**Processing stuck**:

```bash
# Check state
uv run python bots/skills/review-training/scripts/batch_next.py status

# Reset if needed (WARNING: cannot recover deleted pairs)
uv run python bots/skills/review-training/scripts/batch_next.py reset
```

**Cannot extract text from PDF**:

- Check if PDF is text-based (not scanned image)
- Try alternative extraction tools
- Mark as failed if cannot extract

**Pair failed**:

- Check `archive/failed_extraction/` for failed pairs
- Review `archive/review_processing.log` for error details
- Fix issue and move back to `archive/matched/` if recoverable

## Goal

Build a comprehensive training dataset that teaches LLMs to:

1. **Recognize patterns** that warrant feedback
2. **Formulate feedback** in Nic's academic review style
3. **Identify evidence** in source documents
4. **Categorize feedback** appropriately
5. **Provide actionable guidance** to authors

## Next Steps

1. **Start processing**: Run `/review-training` to process first pair
2. **Review output**: Manually inspect first extraction to ensure quality
3. **Iterate**: Refine extraction approach based on early examples
4. **Batch process**: Run `/review-training` repeatedly to complete all 16 pairs

