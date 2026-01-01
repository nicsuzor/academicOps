---
name: fact-check
description: Verify factual claims in documents against authoritative sources. Catches hallucinations, fabricated quotes, and misattributed claims.
allowed-tools: Read,Grep,Glob,WebSearch,WebFetch,Write,TodoWrite
version: 1.0.0
permalink: skills-fact-check
tags:
  - verification
  - research-integrity
  - hallucination-detection
---

# Fact-Check Skill

**Purpose**: Verify factual claims in documents against authoritative sources. Assume any quotes or references are hallucinated unless demonstrably proven.

**When to invoke**:
- User asks to "triple check", "verify", "fact-check" a document
- Before submitting reviews, reports, or assessments with factual claims
- When reviewing AI-generated content that cites sources

## Core Principle: Guilty Until Proven Innocent

Every factual claim is assumed **hallucinated** until you can demonstrate otherwise with evidence. This is the opposite of normal reading where we assume good faith.

**Why?** LLM-generated content confidently produces plausible-sounding details that don't exist: invented statistics, misattributed quotes, fabricated publication dates, non-existent researchers.

## Workflow

### Phase 1: Identify Claims

Read the document and extract ALL factual claims requiring verification:

| Claim Type | Examples |
|------------|----------|
| **Names** | Researchers, institutions, organizations |
| **Numbers** | Sample sizes, percentages, dates, funding amounts |
| **Publications** | Paper titles, journals, publication years |
| **Quotes** | Direct quotes attributed to sources |
| **Credentials** | Degrees, positions, affiliations |
| **Events** | Presentations, grants, collaborations |
| **Timelines** | Duration claims ("10-year collaboration") |

Use TodoWrite to track each claim category.

### Phase 2: Identify Authoritative Sources

For each claim, determine what would constitute authoritative verification:

| Claim Type | Authoritative Sources |
|------------|----------------------|
| Researcher details | University profiles, Google Scholar, dblp, ORCID |
| Publications | Publisher websites, DOI links, preprint servers |
| Institutions | Official websites, LinkedIn (for existence) |
| Project details | Grant databases, project websites, research plans |
| Statistics | Primary source documents, methodology sections |
| Quotes | Original source (book, paper, interview) |

**Critical**: If the document references a primary source (e.g., "research plan PDF"), READ THAT FIRST. It's the authoritative source for claims about the project.

### Phase 3: Cross-Reference Each Claim

For each claim:

1. **Search authoritative sources** using WebSearch, WebFetch, or Read
2. **Quote exact evidence** found (or note absence)
3. **Compare** claim against evidence
4. **Classify** the result

### Phase 4: Classify Results

| Status | Meaning | Format |
|--------|---------|--------|
| ✅ **Verified** | Claim matches authoritative source | Cite source with link/page |
| ⚠️ **Clarification needed** | Source exists but details differ | Note discrepancy |
| 🔍 **Unverifiable** | No authoritative source accessible | Note what was searched |
| 📝 **Professional judgment** | Opinion/assessment, not factual claim | Note this is not a verification target |

### Phase 5: Compile Report

Create verification report using template:

```markdown
## Verified Claims (Accurate)

| Claim | Source |
|-------|--------|
| [claim] | [source with link/page] |

## Claims Requiring Clarification

| Claim | Issue | Evidence |
|-------|-------|----------|
| [claim] | [discrepancy] | [what was found] |

## Unverifiable Claims

| Claim | Search Attempted |
|-------|------------------|
| [claim] | [sources checked] |

## Professional Judgments (Not Verifiable)

- [assessment 1]
- [assessment 2]

## Conclusion

[Summary: hallucinations found? / clean? / caveats?]
```

### Phase 6: Save Companion File

Save report as `{document-name}-verification.md` in same directory as source document.

## Common Hallucination Patterns

Watch especially for:

1. **Plausible-sounding statistics** - "n=825" sounds specific, verify it
2. **Timeline inflation** - "10-year collaboration" - check earliest joint publication
3. **Credential enhancement** - Verify actual titles/positions
4. **Quote fabrication** - Direct quotes are often invented
5. **Publication conflation** - Mixing details from different papers
6. **Institutional misattribution** - Wrong university/department

## What This Skill Does NOT Do

- **Evaluate quality** of claims (that's reviewer judgment)
- **Check methodology** soundness (domain expertise)
- **Assess writing quality** (editorial review)
- **Verify opinions** (professional judgment isn't factual)

This skill verifies **factual accuracy only**.

## Example Invocation

```
User: "Triple check everything in my SNSF review - assume any quotes or references are hallucinated unless proven otherwise."

Agent:
1. Reads review document
2. TodoWrite: Lists all factual claims by category
3. Reads primary source (research plan PDF)
4. WebSearch: Verifies researcher profiles, publications, institutions
5. Cross-references each claim
6. Compiles verification report
7. Saves as {review}-verification.md
```
