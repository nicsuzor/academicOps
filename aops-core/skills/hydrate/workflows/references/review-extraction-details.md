# Review Extraction Detailed Procedures

Detailed procedures, patterns, and examples for extracting training data from peer reviews.

## Phase 1: Document Preparation

**Step 1.1: Convert to Markdown with Markup Preserved**

```bash
# For DOCX with comments and track changes
pandoc --track-changes=all -f docx -t markdown -o output.md input.docx
```

**Verify**:

- Comments are readable and attributed
- Comment text is clearly separated from source text
- Location/context is preserved
- Markup shows comment boundaries

**Step 1.2: Full Document Read**

Read the complete document without extracting yet. Understand:

- Overall assessment (positive, critical, mixed)
- Document type (paper, grant, thesis, etc.)
- Reviewer relationship (peer, supervisor, editor)
- Feedback structure and style
- Distinctive patterns

## Phase 2: Extraction

**Step 2.1: Identify Extractable Feedback Units**

What counts as feedback:
✓ Specific comments on particular text
✓ Structural suggestions
✓ Methodological guidance
✓ Teaching comments about practice
✓ Meta-commentary about writing

What to skip:
❌ Administrative notes
❌ Generic praise with no content
❌ Pure copyediting (unless part of pattern)

**Step 2.2: Extract Source Context + Feedback**

For each feedback unit, extract:

```json
{
  "example_id": "unique_id_001",
  "source": {
    "text": "exact text or null if general",
    "location": "section/page reference",
    "metadata": {
      "document": "title",
      "type": "document type",
      "section": "section name"
    }
  },
  "feedback": {
    "comment": "full feedback text",
    "type": "structural|methodological|substantive|clarity|citation|style",
    "action": "revise|add|remove|clarify|reorganize|strengthen"
  },
  "revised": {
    "text": "revised version if available",
    "location": "where revision appears"
  },
  "context": {
    "pattern_type": "what pattern this represents",
    "teaching_point": "what this teaches",
    "scope": "specific|section|document"
  },
  "quality": "high|medium|low|ambiguous"
}
```

**Step 2.3: Quality Assessment**

High quality:

- Clear connection between feedback and source
- Teaches transferable pattern
- Sufficient context
- Well-categorized

Flag for review:

- Ambiguous mapping
- Unclear teaching value
- Very context-specific

## Phase 3: Pattern Identification

**Step 3.1: Group by Pattern Type**

Group extracted pairs by feedback type, teaching approach, pedagogical technique, and scope.

**Step 3.2: Identify Effective Patterns**

Analyze what makes each pattern cluster distinctive, why it works, and what makes it transferable.

**Step 3.3: Extract Underlying Principle**

For each pattern, create a generalised principle including what, when, and how to do it, why it works, and an application guide with examples and limits.

**Abstraction test**:

- Too specific: "When reviewing AI papers, start positive"
- Too general: "Be nice to authors"
- **Sweet spot**: "When providing detailed feedback, explicitly contextualize volume upfront"

## Phase 4: Separation of Sensitive/Public

**Step 4.1: Store Sensitive Data**

Create in `$ACA_DATA/processed/review_training/{collection_name}/`:

- `extracted_examples.json`: Full pairs with identifying info
- `training_pairs.jsonl`: JSONL format
- `collection_summary.md`: Overview with names/details
- `extraction_workflow_notes.md`: Process notes

**Step 4.2: Depersonalize for Public Framework**

Remove author/reviewer names, work titles, affiliations, and identifying contextual details. Use generic placeholders (e.g., "Author", "Student"). Create constructed examples if real ones can't be safely depersonalized.

## Phase 5: Update Framework Documentation

Update `aops-core/workflows/peer-review.md` with depersonalized principles and add common error type examples to the peer review skill.

## Common Patterns to Extract

Watch for:

1. **Positive framing** - How to contextualize detailed critique
2. **Teaching principles** - Explaining patterns not just fixing instances
3. **Strategic framing** - Positioning revisions as strengthening
4. **Providing options** - Multiple solutions with author agency
5. **Audience awareness** - Framing in terms of reader experience
6. **Habit formation** - Teaching self-review practices
7. **Identity choices** - Surfacing hidden assumptions
8. **Concrete language** - Providing actual text for reorganization

## Storage Locations

### Sensitive Data: `$ACA_DATA/processed/review_training/`

```bash
$ACA_DATA/processed/review_training/
├── aoir2026-sadia/
│   ├── extracted_examples.json
│   ├── training_pairs.jsonl
│   ├── collection_summary.md
│   └── extraction_workflow_notes.md
├── grant-review-batch-2025/
│   └── ...
└── README.md  # Index of all collections
```

### Public Patterns: Framework docs

```bash
aops-core/
├── workflows/
│   └── peer-review.md  # Updated with principles
├── skills/
│   └── extract/
│       ├── SKILL.md
│       └── workflows/
│           └── review-inline-comments.md
└── references/
    └── peer-review-examples.md  # Depersonalized examples
```

## Example: From Raw to Stored

### Raw Extraction (Sensitive)

```json
{
  "example_id": "aoir2026_003",
  "source": {
    "text": "have revolutionised content creation",
    "location": "Background section, line 18-19",
    "metadata": { "author": "Sadia" }
  },
  "feedback": {
    "comment": "This is the sort of word that you should look out for...",
    "type": "substantive",
    "action": "revise"
  }
}
```

### Generalized Principle (Public)

**Principle**: Teach Strategic Word Choice
Identify when strong claims invite unnecessary criticism; explain why revision strengthens the work.
**Example**: Hyperbolic language ("revolutionized") attracts criticism; suggest softer, defensible alternatives.
