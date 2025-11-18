---
name: training-set-builder
description: Extract structured training examples (source → feedback → revised → context) from document sets to build datasets for teaching LLMs specific tasks or styles. Use when processing review documents, feedback annotations, or revision histories to create pedagogically valuable training data.
---

# Training Example Extractor Skill

Extract structured training examples (source → feedback → revised → context) from document sets to build datasets for teaching LLMs specific tasks or styles.

## Framework Context

@resources/AXIOMS.md

## Purpose

Process document collections to create training data that captures:

1. **Source material** - the original text or content that received feedback
2. **Feedback/intervention** - specific comments, suggestions, critiques, or edits
3. **Revised output** - the improved version (if available)
4. **Context** - sufficient information for an LLM to learn the underlying pattern

## Core Training Example Structure

Each training example should contain:

```json
{
  "example_id": "unique_identifier",
  "source": {
    "text": "Original content before feedback/revision",
    "location": "Section/page reference (if applicable)",
    "metadata": {
      "document": "Source document name/title",
      "type": "document type (article, grant, code, etc.)",
      "additional_context": "Any relevant contextual information"
    }
  },
  "feedback": {
    "comment": "The specific feedback, critique, or intervention",
    "type": "Category of feedback (structural, substantive, clarity, etc.)",
    "action": "What action is being recommended (revise, add, remove, etc.)"
  },
  "revised": {
    "text": "Improved version after applying feedback (if available)",
    "location": "Where the revision appears (if applicable)"
  },
  "context": {
    "pattern_type": "What pattern should the LLM learn to recognize?",
    "teaching_point": "What is this example teaching?",
    "scope": "How broad is this feedback (specific, section-level, document-level)"
  }
}
```

## Input Expectations

The user will provide documents and explain their structure. Common patterns include:

- **Paired documents**: Original + feedback, or original + revised version
- **Annotated documents**: Single document with embedded feedback/comments
- **Multi-version documents**: Original, revised, and feedback all separate
- **Custom structures**: User-defined organization

**Your job**: Extract training-worthy patterns from whatever structure the user provides.

## Extraction Philosophy

### What Makes a Good Training Example?

A high-quality training example should:

✓ Show a clear before/after or problem/solution pattern
✓ Be specific enough to teach pattern recognition
✓ Include sufficient context for learning
✓ Represent a replicable skill or judgment
✓ Capture the style/approach being taught

### What to Skip or Flag

❌ Generic comments with no actionable content ("Good work")
❌ Administrative/procedural comments ("Due date extended")
❌ Context-free feedback that can't teach a pattern
⚠️ Ambiguous examples (include but flag with `"quality": "ambiguous"`)

## Extraction Process

### Step 1: Understand the Documents

When the user provides documents, first:

1. **Understand the structure**
   - What types of documents are present?
   - How are they organized?
   - What relationships exist between them?

2. **Identify training opportunities**
   - Where is feedback provided?
   - Where are revisions visible?
   - What patterns are being demonstrated?

3. **Clarify with the user**
   - Ask about unclear structures
   - Confirm what they want extracted
   - Understand the learning goal

### Step 2: Extract Examples

For each extractable training example:

1. **Identify the source material**
   - What is the original content?
   - Where does it appear?
   - What context is needed?

2. **Capture the feedback/intervention**
   - What specific comment or change was made?
   - What type of feedback is this?
   - What action is recommended?

3. **Document the revision (if available)**
   - What is the improved version?
   - How was it changed?
   - What specific improvements were made?

4. **Extract the pattern**
   - What is this example teaching?
   - What pattern should an LLM learn?
   - What scope does this apply to?

### Step 3: Categorize and Contextualize

Provide appropriate categorization for the examples:

**Type categories** (adapt to the domain):
- structural (organization, flow, arrangement)
- substantive (content, claims, arguments)
- clarity (explanation, coherence, readability)
- methodological (approach, validity, rigor)
- stylistic (tone, formatting, presentation)
- technical (accuracy, precision, correctness)

**Action categories**:
- revise (change existing content)
- add (include missing content)
- remove (delete or reduce content)
- clarify (improve explanation)
- reorganize (restructure or reorder)
- strengthen (enhance quality or rigor)

**Scope categories**:
- specific (references specific text or element)
- section (addresses a section or component)
- document (overall structure or approach)

## Output Format

### Directory Structure

```
data/training-examples/
├── {collection_name}/
│   ├── collection_summary.md       # Overview of the document set
│   ├── extracted_examples.json     # All extracted examples as structured data
│   └── training_examples.jsonl     # One example per line (for easy loading)
```

### collection_summary.md

```markdown
# Training Data Collection: {Name}

**Purpose**: {What is this dataset teaching?}
**Source**: {Where did these documents come from?}
**Example Count**: {Number of extracted examples}

## Document Overview

- Document 1: {description}
- Document 2: {description}
...

## Training Focus

{1-2 paragraphs describing what patterns/skills this dataset teaches}

## Extraction Notes

{Any important context about the extraction process, ambiguities, or decisions made}
```

### extracted_examples.json

```json
{
  "collection_name": "descriptive_name",
  "purpose": "What this dataset teaches",
  "extraction_date": "2025-01-18",
  "examples": [
    {
      "example_id": "collection_001",
      "source": {...},
      "feedback": {...},
      "revised": {...},
      "context": {...},
      "quality": "high | medium | low | ambiguous"
    },
    ...
  ],
  "metadata": {
    "total_examples": 42,
    "document_count": 5,
    "extractor_notes": "Any relevant notes"
  }
}
```

### training_examples.jsonl

One JSON object per line for efficient loading:

```jsonl
{"example_id": "collection_001", "source": {...}, "feedback": {...}, "revised": {...}, "context": {...}}
{"example_id": "collection_002", "source": {...}, "feedback": {...}, "revised": {...}, "context": {...}}
```

## Handling Different Document Types

### PDF Documents
- Extract text preserving structure where possible
- Note page numbers for references
- Handle multi-column layouts carefully
- Flag extraction quality issues

### Word/DOCX Documents
- Preserve track changes if present
- Extract comments and annotations
- Note heading structure
- Handle embedded tables/figures appropriately

### Plain Text/Markdown
- Use existing structure markers
- Infer sections from content
- Preserve formatting indicators

### Code Files
- Capture file/function/line references
- Include surrounding context
- Note language-specific patterns
- Preserve diff information if available

### Annotated/Commented Documents
- Extract comments as feedback
- Link to their reference points
- Preserve comment threading if present

## Handling Ambiguity

**If feedback doesn't clearly map to source**:
- Flag with `"quality": "ambiguous"`
- Include best-effort interpretation
- Document the ambiguity in `context.teaching_point`

**If multiple interpretations possible**:
- Choose the most specific interpretation
- Document alternatives in extraction notes
- Prefer conservative extraction

**If source/revised text is unclear**:
- Note extraction quality in metadata
- Include available context
- May still have value for pattern recognition

**If no clear revision available**:
- Set `revised` to `null` or empty
- Focus on feedback → implied improvement
- Document in teaching point what the revision should achieve

## Quality Standards

### High-Quality Examples

✓ Clear relationship between source/feedback/revision
✓ Specific enough to teach pattern recognition
✓ Representative of the target style/skill
✓ Sufficient context for learning
✓ Well-categorized and contextualized

### Minimum Requirements

- Source material must be present and clear
- Feedback must be specific and actionable
- Context must articulate the teaching point
- Categorization must be accurate

## Processing Workflow

When the user provides documents:

1. **Discovery**
   - Examine the document structure
   - Ask clarifying questions about organization
   - Understand the learning goal

2. **Extraction**
   - Identify extractable examples
   - Capture source/feedback/revised/context
   - Categorize and tag appropriately

3. **Formatting**
   - Create collection_summary.md
   - Create extracted_examples.json
   - Create training_examples.jsonl

4. **Validation**
   - Check completeness
   - Verify quality standards
   - Ensure teaching value is articulated

5. **Output**
   - Save to appropriate directory
   - Confirm extraction complete
   - Provide summary of what was extracted

## Validation Checklist

Before confirming extraction complete:

1. **Completeness**
   - All extractable examples captured
   - All required fields present
   - Metadata complete

2. **Quality**
   - Examples are pedagogically valuable
   - Context is sufficient for learning
   - Categorization is accurate

3. **Format**
   - JSON is valid
   - Files saved correctly
   - Summary is informative

## Example Extraction

### Example 1: Specific Text Feedback

**User provides**: Review comment on a paper

```
This quote is repeated on p2 and 14: "high-profile investigators
receive[] accolades for their valuable work, while the people who
made that work possible remain unacknowledged" (Rahman 2020).
```

**Extracted example**:

```json
{
  "example_id": "example_001",
  "source": {
    "text": "high-profile investigators receive[] accolades for their valuable work, while the people who made that work possible remain unacknowledged (Rahman 2020)",
    "location": "p2, p14",
    "metadata": {
      "document": "Power and Humility in OSI",
      "type": "journal article",
      "section": "multiple"
    }
  },
  "feedback": {
    "comment": "This quote is repeated on p2 and 14",
    "type": "stylistic",
    "action": "remove"
  },
  "revised": {
    "text": "[Quote appears only once in revised version]",
    "location": "p2"
  },
  "context": {
    "pattern_type": "Detect duplicate content across document",
    "teaching_point": "LLM should identify repeated quotes/text and flag for removal",
    "scope": "specific"
  }
}
```

### Example 2: Structural Feedback

**User provides**: Review comment on introduction

```
The introduction almost seems to make a broader claim about power
in tech, but doesn't quite make the critique explicit enough and
comes off a little disjoint as a result.
```

**Extracted example**:

```json
{
  "example_id": "example_002",
  "source": {
    "text": "[Introduction section discussing power in tech and OSI without explicit connection]",
    "location": "Introduction",
    "metadata": {
      "document": "Power and Humility in OSI",
      "type": "journal article",
      "section": "Introduction"
    }
  },
  "feedback": {
    "comment": "The introduction almost seems to make a broader claim about power in tech, but doesn't quite make the critique explicit enough and comes off a little disjoint as a result.",
    "type": "clarity",
    "action": "clarify"
  },
  "revised": {
    "text": null,
    "location": null
  },
  "context": {
    "pattern_type": "Identify implied arguments needing explicit articulation",
    "teaching_point": "Recognize when connections between broader claims and specific context are insufficiently explicit, particularly in introductions",
    "scope": "section"
  }
}
```

## Notes

- **Flexibility**: Work with whatever document structure the user provides
- **Clarity**: Ask questions when structure is unclear
- **Value**: Focus on extracting pedagogically useful examples
- **Context**: Always articulate what the example teaches
- **Iteration**: Format and approach may evolve based on use cases

## Error Handling

**Cannot extract text from document**:
- Notify user of extraction issue
- Request alternative format or clarification
- Document failed extraction

**Ambiguous structure**:
- Ask user to clarify
- Make reasonable assumptions and document them
- Flag uncertain extractions

**No clear training value**:
- Flag as low-quality
- Include for completeness if requested
- Note limited pedagogical value
