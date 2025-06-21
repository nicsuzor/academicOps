# CLAUDE.md: Core Workflow and Integrity Guidelines

> Essential principles and procedures for maintaining academic integrity while leveraging AI assistance in scholarly writing.

## Table of Contents

1. [Fundamental Principles](#fundamental-principles)
2. [Integrity Safeguards](#integrity-safeguards)
3. [Workflow Stages](#workflow-stages)
4. [AI Usage Guidelines](#ai-usage-guidelines)
5. [Verification Protocols](#verification-protocols)
6. [Documentation Requirements](#documentation-requirements)
7. [Red Lines - Never Cross These](#red-lines---never-cross-these)

## Fundamental Principles

### 1. Author Sovereignty
- The human author maintains **complete responsibility** for every word in the final text
- AI serves only as an **assistant**, never as a co-author
- All content must reflect the author's **genuine understanding** and expertise

### 2. Transparent Attribution
- All AI assistance must be **explicitly documented**
- Citation of AI-generated ideas follows the same rigor as human sources
- Maintain a clear **audit trail** of AI interactions

### 3. Source Primacy
- **Primary sources** always take precedence over AI suggestions
- Every factual claim requires **independent verification**
- AI interpretations must be **cross-checked** against original texts

### 4. Iterative Refinement
- Work in **small, manageable chunks** (max 1000 words)
- Each chunk undergoes **multiple review cycles**
- Continuous improvement through **version control**

## Integrity Safeguards

### Three-Layer Verification System

#### Layer 1: AI-Assisted Drafting
```markdown
## Chunk Metadata
- Chunk ID: [unique-identifier]
- AI Assistant: Claude Opus 4
- Session Date: [YYYY-MM-DD]
- Prompt Types Used: [structure/expression/ideation]
```

**Process:**
1. Author provides context and requirements
2. AI assists with structure, expression, or idea development
3. All AI outputs logged with timestamps

#### Layer 2: Source Verification
```markdown
## Verification Log
- Claim: "[specific claim from text]"
- AI Source: [yes/no]
- Primary Source: [citation]
- Verification Status: [verified/pending/disputed]
- Verifier: [author/reviewer name]
- Date: [YYYY-MM-DD]
```

**Requirements:**
- Every factual claim must have a primary source
- AI-suggested references must be independently verified
- Disputed claims must be resolved before proceeding

#### Layer 3: Human Authority Review
- Author reads every word in context
- Confirms alignment with intended meaning
- Ensures voice consistency
- Takes full responsibility for final text

### The VERIFY Protocol

**V**alidate - Check all facts against primary sources  
**E**xamine - Review AI suggestions critically  
**R**eference - Ensure proper attribution  
**I**ntegrate - Blend AI assistance with human expertise  
**F**inalize - Author approval of every element  
**Y**ield - Document ready for peer review  

## Workflow Stages

### Stage 1: Project Initialization

```bash
# Create project structure
./tools/new-project.sh "Project Title"

# Initialize AI context
cat > projects/[project-name]/AI_CONTEXT.md << EOF
## Project Context for AI Assistant

### Research Question
[Clear statement of research question]

### Key Arguments
1. [Main argument 1]
2. [Main argument 2]
...

### Theoretical Framework
[Description of theoretical approach]

### Target Audience
[Journal/conference and anticipated readers]

### Style Guidelines
[Specific style requirements]
EOF
```

### Stage 2: Chunk Development

Each chunk follows this structure:

```markdown
# Chunk: [descriptive-name]

## Metadata
- ID: [project-id]-[chunk-number]
- Version: [semantic version]
- Status: [draft/review/approved]
- Last Modified: [date]

## AI Assistance Log
| Timestamp | Request Type | Prompt Summary | Output Used |
|-----------|--------------|----------------|-------------|
| [time]    | [type]       | [summary]      | [yes/partial/no] |

## Content
[The actual text of the chunk]

## Verification Notes
[Any claims requiring verification]

## Review Comments
[Feedback from reviewers]
```

### Stage 3: Integration and Assembly

```yaml
# assembly-config.yml
project: "Project Name"
chunks:
  - introduction/context
  - introduction/problem-statement
  - literature/theoretical-framework
  - methodology/approach
  - findings/main-results
  - discussion/implications
  - conclusion/summary
  
output:
  format: ["markdown", "latex", "pdf", "docx"]
  style: "journal-specific"
  citations: "bibtex"
```

### Stage 4: Quality Assurance

Run automated checks:
```bash
# Check for unverified claims
./tools/validation/check-claims.sh

# Verify all citations
./tools/validation/verify-citations.sh

# Check AI attribution
./tools/validation/ai-attribution-check.sh

# Style consistency
./tools/validation/style-check.sh
```

## AI Usage Guidelines

### Appropriate AI Assistance

✅ **DO use AI for:**
- Improving clarity and structure of your own ideas
- Generating alternative phrasings for complex concepts
- Identifying potential logical gaps in arguments
- Suggesting organizational frameworks
- Grammar and style improvements
- Creating initial outlines for refinement

### Inappropriate AI Usage

❌ **DO NOT use AI for:**
- Generating core arguments or thesis statements
- Creating analysis of primary sources you haven't read
- Producing literature reviews without reading sources
- Making empirical claims without data
- Writing sections you don't fully understand
- Replacing your academic voice

### AI Prompt Templates

**For Structure:**
```
I'm organizing a section on [topic]. My key points are:
1. [point 1]
2. [point 2]
3. [point 3]

Suggest an effective paragraph structure that maintains academic rigor.
```

**For Expression:**
```
I want to express this idea: [your idea in plain language]

The context is: [academic context]

Suggest 2-3 academic phrasings that maintain precision.
```

**For Clarity:**
```
This sentence feels unclear: "[your sentence]"

The intended meaning is: [explanation]

Suggest a clearer version maintaining the same scholarly tone.
```

## Verification Protocols

### Fact-Checking Checklist

- [ ] Is this claim supported by a primary source?
- [ ] Have I read the primary source myself?
- [ ] Does the source actually say what I claim it says?
- [ ] Is this the most authoritative source available?
- [ ] Are there contradicting sources I should acknowledge?

### Citation Verification

1. **For every citation:**
   - Locate the exact page/section referenced
   - Verify quote accuracy (if applicable)
   - Confirm context hasn't changed meaning
   - Check publication details are correct

2. **For AI-suggested sources:**
   - Verify the source exists
   - Obtain and read the full text
   - Confirm relevance to your argument
   - Check for more authoritative alternatives

### The "Would I Defend This?" Test

Before finalizing any chunk, ask:
- Would I confidently defend this in a conference?
- Could I explain every claim to a skeptical reviewer?
- Do I truly understand what I've written?
- Would I stake my reputation on this being accurate?

## Documentation Requirements

### 1. Project-Level Documentation

**PROJECT.md must include:**
- Complete AI usage disclosure
- List of all AI tools used
- General types of assistance received
- Statement of author responsibility

**Example:**
```markdown
## AI Assistance Disclosure

This project used Claude (Anthropic) for:
- Structural organization suggestions
- Grammar and clarity improvements
- Alternative phrasing generation

All content represents the author's original thinking. 
AI was not used for generating arguments, analysis, or 
empirical claims. Every fact has been independently verified.

The author takes full responsibility for all content.
```

### 2. Chunk-Level Documentation

Every chunk must maintain:
- Complete AI interaction log
- Verification status for all claims
- Review history and changes
- Version control commits

### 3. Final Submission Documentation

Include supplementary file with:
- Aggregated AI usage statistics
- Complete verification log
- Chunk development timeline
- Reviewer comment integration record

## Red Lines - Never Cross These

### 🚫 Absolute Prohibitions

1. **Never** submit AI-generated text without reading and understanding every word
2. **Never** use AI to fabricate data, quotes, or sources
3. **Never** let AI write about sources you haven't personally read
4. **Never** use AI to generate core theoretical contributions
5. **Never** hide or minimize AI assistance in your work
6. **Never** sacrifice accuracy for eloquence
7. **Never** bypass the verification protocol
8. **Never** claim AI ideas as your own original thinking
9. **Never** use AI to respond to peer review without disclosure
10. **Never** compromise your academic integrity for efficiency

### ⚠️ Warning Signs

You're relying too heavily on AI if:
- You can't explain a paragraph in your own words
- You're unsure what a sentence means
- You haven't read most of your citations
- The text doesn't "sound like you"
- You're generating more than editing
- You feel disconnected from your work

### 🛟 Recovery Protocols

If you've crossed a line:
1. Stop immediately
2. Review all AI-assisted content
3. Rewrite sections you don't fully own
4. Verify all claims independently
5. Document the issue in your project log
6. Consider seeking mentor guidance

## Continuous Improvement

### Regular Audits

Monthly reviews should assess:
- AI assistance patterns
- Verification completeness
- Voice consistency
- Integrity maintenance

### Community Feedback

- Share experiences in project retrospectives
- Contribute to best practices documentation
- Report tools or techniques that compromise integrity
- Celebrate successes in maintaining standards

## Conclusion

Academic integrity is not negotiable. AI tools offer powerful assistance, but they must never replace the scholar's responsibility to think, analyze, and communicate with authenticity. Every word you publish represents your contribution to human knowledge—ensure it truly represents your understanding and expertise.

---

*Remember: Your reputation is built over a career but can be destroyed in a moment. Use AI wisely, transparently, and always with integrity.*