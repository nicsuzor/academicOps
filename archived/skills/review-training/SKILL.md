---
name: skill
title: Skill
category: instruction
---

# Review Training Data Extraction Skill

Extract training pairs (review feedback → source evidence) from matched peer review/source document pairs to build a dataset for teaching LLMs to perform academic peer review in Nic's style.

## Purpose

Process matched review/source pairs to create training data that captures:

1. **Review feedback units** - specific comments, suggestions, critiques
2. **Source evidence** - the text/pattern in the source that prompted the feedback
3. **Feedback categorization** - type and scope of feedback
4. **Context** - enough information for an LLM to learn the pattern

## Input Structure

Each matched pair in `archive/matched/{num}_{name}/`:

- `review.txt` - The review comments
- `source.{ext}` - The source document (PDF, DOCX, TXT)
- `metadata.json` - Matching metadata

## Extraction Approach

For each review/source pair, extract training examples that teach an LLM to:

1. **Recognize patterns** - identify issues that warrant feedback
2. **Formulate feedback** - express critiques in Nic's style
3. **Locate evidence** - find the specific text that needs addressing

### Three Types of Feedback Matches

**Type 1: Specific Text Match**

- Feedback references specific text in the source
- Example: "This quote is repeated on p2 and 14: [exact quote]"
- **Extract**: Exact source text + feedback comment + page references

**Type 2: Pattern Recognition**

- Feedback identifies a structural or methodological issue
- Example: "The introduction almost seems to make a broader claim about power in tech, but doesn't quite make the critique explicit enough"
- **Extract**: Relevant source sections + synthesized description of pattern + feedback

**Type 3: High-Level Synthesis**

- Feedback addresses overall approach or missing elements
- Example: "The authors' own work is disproportionately provided in support of claims about the OSI field in general"
- **Extract**: Representative evidence from source + synthesis of the issue + feedback

## Extraction Process

### Step 1: Read and Understand

1. **Read the review** fully
   - Identify distinct feedback units (separate comments/suggestions)
   - Categorize feedback type (structural, methodological, substantive, style)
   - Note scope (specific text, section-level, document-level)

2. **Read the source** document
   - Understand the overall argument and structure
   - Note key sections, claims, and evidence
   - Identify what the review is responding to

### Step 2: Extract Feedback Units

For each distinct piece of feedback in the review:

1. **Identify the feedback unit**
   - What is the specific comment/suggestion?
   - What is the reviewer asking for?
   - What issue is being identified?

2. **Locate source evidence**
   - **If specific text**: Extract exact quote with page/location
   - **If pattern**: Extract 2-3 representative examples
   - **If synthesis**: Extract enough context to demonstrate the issue

3. **Categorize the feedback**
   - **Scope**: specific | section | document
   - **Type**: structural | methodological | substantive | clarity | citation | style
   - **Action**: revise | add | remove | clarify | reorganize | strengthen

### Step 3: Format Training Pair

For each extracted feedback unit, create a training example:

```json
{
  "pair_id": "064_HRRE_001",
  "source_context": {
    "document": "Power and Humility in Open Source Investigations",
    "section": "Part II - Literature Review",
    "page_ref": "p2, p14" | null,
    "text_excerpt": "Exact quoted text from source" | null,
    "synthesized_context": "Description of pattern when no exact quote" | null
  },
  "feedback": {
    "comment": "The exact feedback text from review",
    "scope": "specific | section | document",
    "type": "structural | methodological | substantive | clarity | citation | style",
    "action": "revise | add | remove | clarify | reorganize | strengthen"
  },
  "training_value": {
    "pattern_type": "What pattern should LLM learn to recognize?",
    "teaching_point": "What is this example teaching?"
  }
}
```

## Output Format

### File Structure

```
data/review-training/
├── {pair_num}_{name}/
│   ├── source_summary.md          # Summary of source document
│   ├── feedback_units.json        # All extracted feedback units
│   └── training_pairs.jsonl       # One training pair per line
```

### source_summary.md

```markdown
# Source Document Summary

**Title**: [Document title] **Type**: [journal article | grant application | PhD thesis | etc.] **Topic**: [Brief topic description]

## Key Sections

- Section 1: [description]
- Section 2: [description] ...

## Main Argument

[1-2 paragraph summary of main argument/contribution]

## Review Context

**Review Type**: [peer review | grant assessment | thesis examination] **Overall Assessment**: [positive | mixed | critical] **Main Themes**: [key themes in feedback]
```

### feedback_units.json

```json
{
  "pair_id": "064_HRRE",
  "source_title": "Power and Humility in Open Source Investigations",
  "review_summary": "Critical but supportive review recommending structural changes",
  "feedback_units": [
    {
      "unit_id": "064_HRRE_001",
      "source_context": {...},
      "feedback": {...},
      "training_value": {...}
    },
    ...
  ]
}
```

### training_pairs.jsonl

One JSON object per line (for easy loading):

```jsonl
{"pair_id": "064_HRRE_001", "source_context": {...}, "feedback": {...}, "training_value": {...}}
{"pair_id": "064_HRRE_002", "source_context": {...}, "feedback": {...}, "training_value": {...}}
```

## Feedback Categorization

### Scope Categories

- **specific**: References specific text, quote, or sentence
- **section**: Addresses a section or subsection
- **document**: Overall structure or approach

### Type Categories

- **structural**: Organization, flow, section structure
- **methodological**: Research methods, approach, validity
- **substantive**: Argument, claims, evidence, analysis
- **clarity**: Writing quality, explanation, coherence
- **citation**: References, literature review, attribution
- **style**: Formatting, presentation, tone

### Action Categories

- **revise**: Change existing content
- **add**: Include missing content
- **remove**: Delete or reduce content
- **clarify**: Improve explanation
- **reorganize**: Restructure or reorder
- **strengthen**: Enhance argument/evidence

## Processing Guidelines

### When Source is PDF

- Use text extraction (pdftotext, PyPDF2, or similar)
- Note page numbers for references
- Handle multi-column layouts carefully
- Verify extracted text quality

### When Source is DOCX

- Extract text with python-docx
- Preserve structure (headings, sections)
- Note section numbers if used
- Handle tables and figures appropriately

### When Source is TXT

- Already plain text
- Use structure markers if present
- Infer sections from content

### Handling Ambiguity

**If feedback doesn't clearly map to source**:

- Flag with `"ambiguous": true` in training pair
- Include best-effort source context
- Add note in `training_value.teaching_point`

**If multiple interpretations possible**:

- Choose most specific interpretation
- Document alternative in comments
- Prefer conservative extraction

**If source text is unclear**:

- Note extraction quality issue
- Include context around unclear text
- May still be valuable for teaching pattern recognition

## Quality Standards

### Minimum Requirements

- Each feedback unit must have clear comment text
- Source context must be relevant to feedback
- Categorization must be accurate
- Training value must be articulated

### High-Quality Training Pairs

✓ Clear connection between feedback and source ✓ Specific enough to teach pattern recognition ✓ Representative of Nic's review style ✓ Includes sufficient context ✓ Well-categorized

### Skip or Flag

❌ Generic feedback with no source connection ("Good paper") ❌ Administrative comments ("Thank you for the opportunity") ❌ Feedback about formatting only (unless pedagogically valuable) ⚠️ Ambiguous feedback (include but flag)

## Example Extraction

### Input Review Excerpt

```
This quote is repeated on p2 and 14: "high-profile investigators
receive[] accolades for their valuable investigative work, while
the people who made that work possible remain unacknowledged,
perhaps even unaware that the video or image that they recorded
even used" (Rahman and Ivens 2020).
```

### Extracted Training Pair

```json
{
  "pair_id": "064_HRRE_001",
  "source_context": {
    "document": "Power and Humility in Open Source Investigations",
    "section": null,
    "page_ref": "p2, p14",
    "text_excerpt": "high-profile investigators receive[] accolades for their valuable investigative work, while the people who made that work possible remain unacknowledged, perhaps even unaware that the video or image that they recorded even used (Rahman and Ivens 2020)",
    "synthesized_context": null
  },
  "feedback": {
    "comment": "This quote is repeated on p2 and 14",
    "scope": "specific",
    "type": "style",
    "action": "remove"
  },
  "training_value": {
    "pattern_type": "Detect duplicate content across document",
    "teaching_point": "LLM should learn to identify repeated quotes/text and flag for removal"
  }
}
```

### Input Review Excerpt (Pattern)

```
The introduction almost seems to make a broader claim about
power in tech, but doesn't quite make the critique explicit
enough and comes off a little disjoint as a result.
```

### Extracted Training Pair

```json
{
  "pair_id": "064_HRRE_002",
  "source_context": {
    "document": "Power and Humility in Open Source Investigations",
    "section": "Introduction",
    "page_ref": null,
    "text_excerpt": null,
    "synthesized_context": "Introduction discusses power in tech and OSI but does not explicitly articulate the critique of how power operates in open source investigations. The connection between general claims about tech power and the specific OSI context is implied but not clearly stated."
  },
  "feedback": {
    "comment": "The introduction almost seems to make a broader claim about power in tech, but doesn't quite make the critique explicit enough and comes off a little disjoint as a result.",
    "scope": "section",
    "type": "clarity",
    "action": "clarify"
  },
  "training_value": {
    "pattern_type": "Identify implied arguments that need explicit articulation",
    "teaching_point": "LLM should recognize when connections between broader claims and specific context are not sufficiently explicit, particularly in introductions"
  }
}
```

## Processing Workflow

When processing a matched pair:

1. **Load pair**
   - Read review.txt
   - Read source document (handle format appropriately)
   - Read metadata.json

2. **Analyze review**
   - Split into distinct feedback units
   - Categorize each unit

3. **Extract evidence**
   - For each feedback unit, locate corresponding source context
   - Extract text or synthesize pattern

4. **Format output**
   - Create source_summary.md
   - Create feedback_units.json
   - Create training_pairs.jsonl

5. **Validate**
   - Check all required fields present
   - Verify categorizations
   - Ensure training value articulated

6. **Save and confirm**
   - Write output files to `data/review-training/{pair_id}/`
   - Confirm processing complete (triggers source deletion)

## Validation

Before confirming processing:

1. **Completeness check**
   - All feedback units extracted
   - All have source context (or flagged as ambiguous)
   - All categorized

2. **Quality check**
   - Training pairs are pedagogically valuable
   - Source context is relevant
   - Feedback is clear

3. **Format check**
   - JSON is valid
   - Required fields present
   - Files saved correctly

## Notes

- **Goal**: Build dataset to teach LLMs to perform peer review in Nic's style
- **Value**: Both specific feedback-evidence pairs AND patterns to recognize
- **Context**: Each pair should have enough context for learning
- **Iteration**: Format and approach may evolve based on early examples

## Error Handling

**Cannot extract text from source**:

- Move pair to `archive/failed_extraction/`
- Log issue
- Continue to next pair

**Ambiguous feedback**:

- Extract with `"ambiguous": true` flag
- Include best-effort interpretation
- May still have training value

**No clear feedback units**:

- Create minimal extraction
- Flag as low-value
- Include for completeness but note quality
