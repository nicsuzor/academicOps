# Training Data Extraction: Review with Inline Comments

Workflow for extracting training data from peer review documents with inline comments (DOCX with tracked changes, Google Docs with comments, etc.).

## Input

Document containing:

- Source text (the work being reviewed)
- Inline comments/feedback (from reviewer)
- Optional: tracked changes, suggestions, revisions

**Common formats**:

- DOCX with Word comments and track changes
- Google Docs export with comments
- PDF with annotations (limited support)

## Output

### Sensitive Data → `$ACA_DATA/processed/review_training/{collection_name}/`

1. **`extracted_examples.json`**: All text/feedback pairs with full context
2. **`training_pairs.jsonl`**: Machine-readable format (one example per line)
3. **`collection_summary.md`**: Overview with identifying information intact
4. **`source_documents/`**: Original files if retained

### Generalized Patterns → Framework (public repo)

1. **Update `aops-core/workflows/peer-review.md`**: Add depersonalized principles
2. **Constructed examples**: Create generic examples illustrating principles
3. **No identifying information**: Remove names, titles, institutional details

## Process

### Phase 1: Document Preparation

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

### Phase 2: Extraction

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

### Phase 3: Pattern Identification

**Step 3.1: Group by Pattern Type**

Group extracted pairs by:

- Feedback type (structural, methodological, etc.)
- Teaching approach (principle explanation, strategic framing, etc.)
- Pedagogical technique (providing options, teaching self-review, etc.)
- Scope (document, section, specific)

**Step 3.2: Identify Effective Patterns**

For each pattern cluster, analyze:

- What makes it distinctive?
- Why does it work?
- What makes it transferable?

**Step 3.3: Extract Underlying Principle**

For each pattern, create:

```markdown
## Principle N: [Title]

**Pattern observed**: [specific example from document]

**Generalised principle**: [abstract pattern into transferable form]

- What to do
- When to do it
- How to do it

**Why it works**: [explain the mechanism]

**Application guide**: [conditions for use]

- When to apply
- What situations call for it
- How to recognize the opportunity

**Example applications**: [3-4 concrete examples across contexts]

**Limits**: [when NOT to use this]
```

**Abstraction test**:

- Too specific: "When reviewing AI papers, start positive"
- Too general: "Be nice to authors"
- **Sweet spot**: "When providing detailed feedback, explicitly contextualize volume upfront"

### Phase 4: Separation of Sensitive/Public

**Step 4.1: Store Sensitive Data**

Create in `$ACA_DATA/processed/review_training/{collection_name}/`:

```
{collection_name}/
├── extracted_examples.json       # Full pairs with identifying info
├── training_pairs.jsonl          # JSONL format
├── collection_summary.md         # Overview with names/details
└── extraction_workflow_notes.md  # Process notes for this extraction
```

**Step 4.2: Depersonalize for Public Framework**

From extracted examples, create depersonalized version:

**Remove**:

- Author names → "Author" or "Student"
- Reviewer names → "Reviewer" or omit
- Specific work titles → "Paper on topic X"
- Institutional affiliations
- Identifying contextual details

**Generalize**:

- "This abstract about AI bias" → "Abstract submissions"
- "Sadia's work" → "The author's work"
- Specific references → Generic placeholders

**Create constructed examples**:

- If real example can't be depersonalized, create illustrative example
- Ensure example captures the principle
- Mark as constructed

### Phase 5: Update Framework Documentation

**Step 5.1: Update Peer Review Workflow**

Add to `aops-core/workflows/peer-review.md`:

```markdown
## Composition Principles (Updated YYYY-MM-DD)

### [New Principle Name]

[Depersonalized principle description]

**Example**: [Constructed or depersonalized example]

**Application**: [When and how to use]
```

**Step 5.2: Add Error Type Examples**

Based on patterns in extracted feedback, add to peer review skill:

```markdown
## Common Error Types to Watch For

### [Error Type]

**Pattern**: [What the error looks like]
**Example**: [Depersonalized example]
**Feedback approach**: [How to address this type]
**Why it matters**: [Impact on work]
```

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

**Access control**:

- Not in public repo
- Personal data directory
- Separate backup strategy
- Restricted access

### Public Patterns: Framework docs

```bash
aops-core/
├── workflows/
│   └── peer-review.md  # Updated with principles
├── skills/
│   └── extract/
│       ├── SKILL.md
│       └── workflows/
│           └── review-inline-comments.md  # This file
└── references/
    └── peer-review-examples.md  # Depersonalized examples
```

## Validation Checklist

Before completing:

**Extraction**:

- [ ] All feedback units identified and categorized
- [ ] Patterns grouped and analyzed
- [ ] Principles extracted with examples
- [ ] Quality assessment complete

**Separation**:

- [ ] Sensitive data stored in `$ACA_DATA/processed/`
- [ ] Public framework updated with depersonalized content only
- [ ] No identifying information in public docs
- [ ] Constructed examples created where needed

**Documentation**:

- [ ] Collection summary written
- [ ] Extraction notes documented
- [ ] Workflow improvements noted
- [ ] Framework docs updated

## Example: From Raw to Stored

### Raw Extraction (Sensitive)

**File**: `$ACA_DATA/processed/review_training/aoir2026-sadia/extracted_examples.json`

```json
{
  "example_id": "aoir2026_003",
  "source": {
    "text": "have revolutionised content creation",
    "location": "Background section, line 18-19",
    "metadata": {
      "document": "AoIR 2026 submission - Cultural Bias in Generative AI",
      "type": "conference abstract",
      "author": "Sadia"
    }
  },
  "feedback": {
    "comment": "This is the sort of word that you should look out for: it's a really strong value judgment...",
    "type": "substantive",
    "action": "revise"
  }
}
```

### Generalized Principle (Public)

**File**: `aops-core/workflows/peer-review.md`

```markdown
### Teach Strategic Word Choice

Frame word choice feedback as strategic protection: identify when strong claims
invite unnecessary criticism, explain why revision strengthens rather than
weakens the work.

**Example**: When an author uses hyperbolic language ("revolutionized",
"unprecedented", "completely transformed"), point out that strong value
judgments attract criticism and may not be core to the argument. Suggest
softer alternatives that are easier to defend.

**Application**: Use when encountering strong claims that aren't central to
the argument and would require substantial defense.
```

## Common Patterns to Extract

Based on validated extractions, watch for:

1. **Positive framing** - How to contextualize detailed critique
2. **Teaching principles** - Explaining patterns not just fixing instances
3. **Strategic framing** - Positioning revisions as strengthening
4. **Providing options** - Multiple solutions with author agency
5. **Audience awareness** - Framing in terms of reader experience
6. **Habit formation** - Teaching self-review practices
7. **Identity choices** - Surfacing hidden assumptions
8. **Concrete language** - Providing actual text for reorganization

## Workflow Improvements

Document what worked and what didn't:

- Challenges encountered
- Process refinements discovered
- Tools that would help
- Quality issues to watch for

These notes feed back into improving this workflow.
