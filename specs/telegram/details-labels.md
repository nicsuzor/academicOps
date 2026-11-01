---
title: Telegram Reply Details Page Labels and Overflow
status: ready
---

# Telegram Reply Details Page Labels and Overflow

This specification defines the labeling and overflow handling contracts for reply messages in the `ida-telegram` plugin. It ensures that the trailing label pointing an operator to a reply's Details page accurately communicates whether the Details page carries continuing substantive prose or references and citations.

## User stories

### US-1 Accurate Attribution of Details Content

As an operator reading agent replies with content on a Details page, I want the label pointing to the Details page to accurately distinguish between real content overflow and references, so that I am never misled into opening Details expecting more of the substantive answer when it contains only sources.

- **AC-1.1 References-Only Details (Overflow):** Given a reply whose chat text exceeds the budget and whose overflow content moved to Details holds only references, sources, citations, or bibliography entries, when processed, then the chat text ends with `… references in Details` with no "continued" wording, and the `🔍 Details` button is attached.
- **AC-1.2 References-Only Details (Explicit Detail):** Given a reply whose chat text fits within budget and whose explicit `detail` parameter holds only references, sources, citations, or bibliography entries, when processed, then the chat text ends with `… references in Details` with no "continued" wording, and the `🔍 Details` button is attached.
- **AC-1.3 Real Overflow:** Given a reply whose substantive narrative text exceeds the chat budget, whether or not references are also present on the Details page, when processed, then the chat text ends with `… continued in Details`, and the `🔍 Details` button is attached.
- **AC-1.4 Explicit Non-Reference Details Without Overflow:** Given a reply whose chat text fits within budget and whose explicit `detail` parameter holds non-reference content (such as deep diagnostic logs, investigation notes, or extended methodology), when processed, then the chat text remains intact without appending a continuation or reference label, and the `🔍 Details` button is attached.
- **AC-1.5 Short Reply Without Details:** Given a reply whose chat text fits within budget and no `detail` parameter was provided, when processed, then the chat text remains intact with no label and no `🔍 Details` button is attached.

## Design

### 1. Details Content Classification and Label Mapping

Each category of Details content maps directly to a distinct presentation label:

| Kind of Details Content | Content Characteristics | Chat Label Suffix | Details Button |
| - | - | - | - |
| **References Only** | Details page holds exclusively references, sources, citations, or bibliography entries (via overflow or `detail`). | `… references in Details` | `🔍 Details` |
| **Real Overflow** | Substantive narrative text exceeded chat budget and continues on Details (with or without references). | `… continued in Details` | `🔍 Details` |
| **Explicit Non-Reference Details** | Explicit `detail` provided with non-reference content; chat text fits within budget. | _(none / intact text)_ | `🔍 Details` |
| **No Details** | Chat text fits within budget; no `detail` provided. | _(none / intact text)_ | _(none)_ |

### 2. Overflow Processing and Paragraph Budgeting

1. **Budget Calculation:**
   When chat text exceeds the configured limit (`maxChatChars`, default 1,200), paragraphs are fitted into an effective budget subtracting the maximum suffix length (`\n\n… continued in Details` or `\n\n… references in Details`).
2. **Orphan Heading Prevention:**
   If the final fitted paragraph is a markdown heading (`#` through `######`) and remaining paragraphs exist, the heading is relocated to the beginning of the overflow content to avoid leaving an empty trailing heading in chat above the label.
3. **Reference Detection (`isReferencesOnly`):**
   Content is classified as references-only if:
   - Its opening line matches a reference header (such as `## References`, `### Sources`, `# Citations`, `## Bibliography`, `**References:**`, or `References:`) and all subsequent lines contain citations or subheadings without introducing non-reference narrative sections; or
   - Every non-empty line constitutes a citation, list item with links/citations (`- [1]`, `1. https://...`, `* [title](url)`), DOI, or wikilink pointer.
4. **Label Application:**
   - If real overflow exists (the overflowed text contains substantive non-reference paragraphs), `\n\n… continued in Details` is appended.
   - If no real overflow occurred and the combined Details content is references-only, `\n\n… references in Details` is appended.
   - Pre-existing label suffixes on incoming text are preserved without duplicate concatenation.
