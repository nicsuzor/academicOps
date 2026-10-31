---
title: Agent Comment Standard
status: draft
---

# Agent Comment Standard

The agent comment standard governs text posted by automated agents for a human to read in passing, establishing concision, scannability, and evidentiary clarity so that the recipient can make decisions and take action without decoding dense reports or navigating duplicated text.

## User stories

### US-1 Outcome-First Discovery

As a human developer or reviewer scanning repository events, I want the bottom-line verdict or change stated on the first line, so that I immediately understand what occurred without reading preamble or navigational summaries.

- **AC-1.1** Given an agent comment posted for a human reader, when the reader stops after the first non-empty line, then the line states the explicit verdict or concrete change and identifies its object.

### US-2 Verifiable Claims

As a human reviewer auditing an agent's claims, I want every factual assertion to carry inline evidence, so that I can independently inspect proof without hunting through logs.

- **AC-2.1** Given an agent comment making factual or evaluative claims, when reading each claim, then the claim carries its concrete evidence on the same line or is omitted.

### US-3 Accessible Language

As a contributor reading an agent comment, I want plain terminology rather than invented phrases, so that I can understand the comment without consulting internal framework specifications.

- **AC-3.1** Given an agent comment conveying technical results, when terminology is used, then concepts are expressed in standard plain words, with any novel technical term defined inline at first use.

### US-4 Structural Bold Headings

As a reader scanning a comment, I want bold text used exclusively as structural headings, so that bold markers introduce content without repeating it in subsequent prose.

- **AC-4.1** Given a bold phrase ending in a colon in an agent comment, when examining the subsequent sentence, then the sentence presents the itemized content beneath rather than repeating the meaning of the bold phrase.

### US-5 Discrete List Items

As a human reviewer parsing bulleted points, I want each bullet to contain exactly one discrete idea, so that compound assertions do not obscure individual findings.

- **AC-5.1** Given any bullet list in an agent comment, when inspecting each bullet item, then the item contains one claim and contains no coordinating conjunctions (such as "; and" or "; or") chaining multiple claims.

### US-6 Consolidated Passing Checks

As a human reviewer reading evaluation results, I want passing checks collapsed into a single summary line, so that my attention focuses on failures and judgment calls.

- **AC-6.1** Given a set of evaluation criteria where all items pass, when presenting the results, then all passing items are summarized on a single line with their count and source, and no list appears where every item concludes with "Yes" or "passed".

### US-7 Objective Attribution

As an auditor evaluating report provenance, I want findings attributed to their actual observer, so that agents reporting third-party results do not apply unverified words of endorsement.

- **AC-7.1** Given an agent reporting findings, when evaluative endorsement words (such as "verified", "confirmed", "validated", "independent", or "clean") appear, then each word reflects the authoring agent's own direct observation rather than an unverified blessing of a relayed result.

### US-8 Single-Statement Concision

As a reviewer navigating pull requests and tasks, I want comments to point to governing documents rather than restating them, so that text is not duplicated across comments and files.

- **AC-8.1** Given an agent comment discussing an artifact or specification, when referencing contents, then the comment provides a pointer to the target document rather than reproducing paragraphs that appear in the linked file, and states the verdict exactly once.

### US-9 Glossed Tokens

As a human reader encountering specialized identifiers, I want every token, acronym, flag, and rule id glossed at first mention, so that cryptic codes do not impede comprehension.

- **AC-9.1** Given an agent comment containing paths, identifiers, status flags, or acronyms, when a token appears for the first time, then it is accompanied by a two-to-five-word explanatory gloss.

### US-10 Single-Screen Bounded Length

As a busy developer reading notifications in passing, I want comments bounded to a single screen, so that routine updates do not overwhelm cognitive bandwidth.

- **AC-10.1** Given any agent comment, when measuring length, then the comment contains at most 12 non-empty lines and approximately 120 words, using section headings only when presenting three or more distinct sections.

## Design

### 1. Scope and Boundary

The comment standard applies to all short-form text posted by agents for human consumption in passing, including pull request descriptions, review comments, status notifications, and handover notes.

### 2. The Ten Comment Invariants

Every comment produced under this standard satisfies ten positive invariants:

1. **Outcome First:** The first line identifies the decisive verdict or change and names the target entity.
2. **Inline Evidence:** Every load-bearing assertion is paired with a verifiable pointer, citation, or raw metric on that line.
3. **Plain Language:** Standard vocabulary replaces coined multi-word compounds.
4. **Heading Colons:** Bold phrases act as section headers followed by lists, with no redundant echo sentences.
5. **Atomic Bullets:** Each list bullet represents a single falsifiable statement.
6. **Summary of Passes:** Unanimous pass results collapse to a single count line; itemization is reserved for defects, deviations, and discretionary judgments.
7. **Direct Observation:** Descriptive attribution replaces words of secondary endorsement.
8. **Deduplication:** Comments link to specifications and diffs instead of excerpting paragraphs, and state verdicts once.
9. **Token Glossing:** Every shorthand token or identifier receives an inline explanation of two to five words upon first occurrence.
10. **Screen Constraint:** Total text does not exceed 12 lines or 120 words.

## Open questions

None. The ten rules and their observational tests are fully specified.
