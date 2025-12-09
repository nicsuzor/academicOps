---
name: osb-drafting
description: Generate draft OSB case decisions with IRAC analysis, position variants, and precedent support. Use when preparing case analysis for Oversight Board deliberation.
allowed-tools: Read,Grep,Glob,mcp__osb__search,mcp__osb__get_case_summary,mcp__osb__get_document,mcp__osb__get_similar_documents,mcp__bmem__search_notes,mcp__bmem__read_note
version: 1.0.0
permalink: skills-osb-drafting-skill
---

# OSB Case Drafting Skill

**When to invoke**: Preparing analysis for Oversight Board case deliberation.

**What it provides**: Structured case analysis with IRAC reasoning, position variants, precedent mapping.

**What it doesn't do**: Make final decisions, substitute for Board deliberation, guess at facts not in record.

## Prerequisites

- OSB MCP server running (test: `mcp__osb__search` available)
- Case announcement or full case document accessible
- If MCP unavailable: HALT and report infrastructure gap (per AXIOMS.md fail-fast)

## Workflow

### Phase 1: Case Intake

1. **Read case announcement** - Extract:
   - Content description (format, platform, reach)
   - Procedural history (reports, reviews, appeals)
   - Meta's stated rationale
   - Board's stated selection reason
   - Strategic priorities engaged

2. **Identify applicable policies**:
   - Primary policy (most direct violation alleged)
   - Secondary policies (related standards)
   - Policy exceptions that might apply
   - Policy gaps exposed by facts

### Phase 2: Precedent Research

3. **Search OSB jurisprudence** using `mcp__osb__search`:
   - Same/similar policies applied
   - Same content type (AI-generated, crisis, political)
   - Same context (conflict, elections, public health)
   - Same procedural issues (automation, fact-checking)

4. **Retrieve key precedents** using `mcp__osb__get_case_summary`:
   - Extract established legal tests
   - Note defined terms and their scope
   - Identify prior recommendations (implemented or not)
   - Document ratio decidendi (binding principles)

**Minimum searches per case**:
- Primary policy name + "violation"
- Content type + "precedent"
- Context keyword + "crisis" or "conflict"
- Procedural issue (e.g., "automated enforcement" or "fact-checking")

### Phase 3: Tension Mapping

5. **Identify decision points** where reasonable Board members could disagree:
   - Policy interpretation questions
   - Fact characterization questions
   - Balancing/proportionality questions
   - Remedy selection questions

6. **Map fault lines** for each decision point:

| Dimension | Position A | Position B |
|-----------|-----------|------------|
| Textualist vs Purposivist | Strict policy text | Harm-based/intent reading |
| Speech-protective vs Harm-preventive | Favor expression | Favor safety |
| Individual vs Systemic | Case-specific remedy | Policy-level change |
| Global vs Contextual | Consistent application | Regional sensitivity |

### Phase 4: IRAC Analysis

7. **For each major issue**, structure as:

```markdown
### Issue: [Precise legal question]

#### Position A (likely [majority/minority]): [Outcome]
**Rule**: [Applicable policy text + IHRL standard]
**Analysis**: [Application to facts]
**Precedent**: [Case citations with relevance]
**Conclusion**: [Why this position prevails under this reading]

#### Position B (likely [minority/majority]): [Outcome]
**Rule**: [Alternative reading or emphasis]
**Analysis**: [Application highlighting different facts]
**Precedent**: [Contrary or distinguishable cases]
**Conclusion**: [Why this position has merit]

#### What determines the split:
- [Key factual/value difference 1]
- [Key factual/value difference 2]
```

### Phase 5: Recommendations

8. **Draft recommendations** addressing:
   - **Immediate remedy**: Content disposition
   - **Policy clarification**: Terms needing definition
   - **Enforcement process**: Procedural improvements
   - **Transparency**: Disclosure requirements

Recommendations must be:
- Actionable (specific enough to implement)
- Measurable (can verify compliance)
- Precedent-consistent (cite supporting prior decisions)

### Phase 6: Citation Verification

9. **Extract all case citations** from draft:
   - Scan for case IDs (format: `XX-XXXXXXX` or `XXX-XXXXXXXX`)
   - Note each quoted passage with its attributed source
   - List all claimed principles and recommendations

10. **Verify each citation**:

For each cited case, **always retrieve full document text**:
```
mcp__osb__get_document(record_id, include_full_text=true)
```

**Why full text is required**: Summaries are AI-generated abstractions that may not contain exact quoted phrases. Only the full decision text can verify:
- Exact quote accuracy
- Context of statements
- Complete recommendation wording
- Nuanced legal reasoning

| Check | Criteria | Verification Method |
|-------|----------|---------------------|
| Case ID exists | Must return valid result | get_document returns content |
| Case name matches | Exact or close match | Compare to official title |
| Quoted text accurate | **Exact phrase in full text** | Search full document |
| Principle attributed | Ratio/reasoning section supports claim | Read legal reasoning |
| Recommendation accurate | Matches verbatim recommendation text | Check recommendations section |

11. **Generate verification report**:

```markdown
## Citation Verification Report

### VERIFIED ✓
- [Case ID]: [Cited principle] - CONFIRMED at [location in full text]

### NEEDS CORRECTION ✗
- [Case ID]: [Issue description]
  - Draft says: "[quoted text]"
  - Actual text: "[exact text from full document]"
  - Fix: [correction]
```

**Note**: There should be NO "UNVERIFIABLE" category. All citations must be verified against full document text. If OSB MCP is unavailable, HALT per AXIOMS fail-fast principle.

12. **Quality gate** - Draft NOT complete until:
    - All citations verified against full document text
    - 0 items in NEEDS CORRECTION
    - Corrections made and re-verified

**Common error types**:
- Case mislabeling (wrong case name for ID)
- Quote fabrication (phrase not in case text)
- Principle misattribution (case doesn't establish cited holding)
- Recommendation misstatement (wrong implementation status)

## Decision Point Checklist

Common tensions to evaluate in every case:

- [ ] **Policy scope**: Does content fit policy as written?
- [ ] **Harm threshold**: Standard met (imminent/direct)?
- [ ] **Context weight**: How much does setting matter?
- [ ] **Speaker identity**: Newsworthy figure? Official statement?
- [ ] **Remedy proportionality**: Removal vs label vs nothing?
- [ ] **Regional equity**: Comparable treatment globally?
- [ ] **Automation role**: Human review required?
- [ ] **Fact-checker capacity**: Realistic at scale?

## Human Rights Framework

Apply international standards consistently:

- **ICCPR Art. 19**: Expression (necessity, proportionality, legality)
- **ICCPR Art. 25**: Political participation
- **Rabat Plan**: Six factors for incitement analysis
- **UNGPs**: Business responsibility for human rights

## Output Format

### Full Case Draft

```markdown
# [Case Title] - Draft Analysis

## Summary
[2-3 sentence overview]

## Facts
[Key facts from record]

## Procedural History
[Reports, reviews, appeals, Meta's position]

## Applicable Policies
- Primary: [Policy name and text]
- Secondary: [Related policies]

## Issue 1: [First major question]
[Full IRAC with position variants per Phase 4]

## Issue 2: [Second major question]
[Full IRAC with position variants]

[Continue for each issue]

## Recommendations
1. [Recommendation with precedent support]
2. [Recommendation with precedent support]

## Precedent Map
| Case | Relevance | Key Principle |
|------|-----------|---------------|
| [ID] | [Topic] | [Holding] |
```

## Quality Checks

Before finalizing draft:
- [ ] Every legal claim has specific precedent citation
- [ ] Both sides of each tension articulated fairly
- [ ] Human rights standards applied consistently
- [ ] Recommendations are actionable and measurable
- [ ] No speculation beyond case record
- [ ] Position variants reflect genuine disagreement potential
- [ ] **Phase 6 verification complete**: All citations verified, 0 corrections needed

## Anti-Patterns

**Avoid**:
- Guessing at Board member positions (analyze arguments, not people)
- Over-reliance on single precedent (triangulate multiple sources)
- Ignoring contrary precedent (address and distinguish)
- Policy advocacy (present options, don't predetermine outcome)
- Ungrounded factual claims (cite record or mark as unknown)
