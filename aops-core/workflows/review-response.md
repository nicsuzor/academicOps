---

## id: review-responsename: review-response-workflowcategory: academicbases: [base-task-tracking]description: Respond to reviewer comments in a Word document, showing how each has been addressed in an updated draftpermalink: workflows/review-responsetags: [workflow, academic, writing, revision, docx, comments]version: 1.0.0

# Review Response Workflow

**Purpose**: Reply to reviewer comments in a Word document by adding threaded reply comments that explain how each point has been addressed in a revised draft.

**When to invoke**: A collaborator returns a document with reviewer comments. You have an updated draft that incorporates their feedback. The task is to go through each comment and confirm (via a reply comment in Word) how it was addressed.

## Phase 1: Unpack and Catalogue

1. **Unpack the docx** using `scripts/office/unpack.py` (or equivalent XML extraction)
2. **Extract all comments** from `word/comments.xml` — get comment ID, author, and text
3. **Map the thread structure** from `word/commentsExtended.xml` — find which comments are replies to other comments (have `paraIdParent`). Build a map of `paraId → comment_id` to identify sub-threads
4. **Find anchor text** for each comment in `word/document.xml` — the text the comment is attached to. This is essential for understanding vague comments like "I'm not sure what this means"

## Phase 2: Classify Comments

Group comments by type. This determines the reply approach:

| Type                       | Example                                          | Reply approach                                      |
| -------------------------- | ------------------------------------------------ | --------------------------------------------------- |
| **Actionable suggestion**  | "Should use X, not Y"                            | Terse: "Done." / "Fixed." / "Adopted."              |
| **Thread reply**           | Comment replying to another comment              | Skip — address in reply to the parent thread        |
| **Confirm/verify**         | "Confirm this pattern holds across X"            | **Show, don't tell** — extract evidence             |
| **Structural feedback**    | "Needs new title and framing"                    | Brief: state what changed                           |
| **Future work suggestion** | "Would be interesting to test X"                 | "Noted in Future Work." / "Added to [section]."     |
| **Positive feedback**      | "This is great!"                                 | Brief acknowledgment: "Thanks!"                     |
| **Clarification request**  | "I don't understand this" / "Could you explain?" | State what was changed at the location they flagged |
| **Compound thread**        | Multiple reviewers replying to same parent       | Reply once to parent, acknowledge all contributors  |

### Anti-patterns

- **Don't duplicate replies** — if comment B is a reply to comment A, reply only to A and mention B's contributor. Don't add separate replies to sub-comments.
- **Don't cop-out on clarification requests** — "Clarified in section 2.4" is insufficient if the problem is _where they noticed it_. Fix the text at that location and say what you changed.
- **Don't parrot back changes** — if the tracked change speaks for itself, "Done" is enough. Don't quote the new text in the reply. The reviewer can see the tracked changes.
- **Match the author's voice** — for terse collaborators: "Done." / "Fixed." / "Good point. Addressed." Not effusive gratitude for every suggestion.
- **Show, don't tell for verification requests** — when asked to "confirm across X" or "check this isn't an outlier", pull actual evidence and quote it. e.g. "All 5 instances show pattern: [instance 1] '...', [instance 2] '...'" etc.

## Phase 3: Gather Evidence (for verification-type comments)

When a reviewer asks you to confirm or verify something, don't just assert "confirmed." Instead:

1. Identify the relevant data source (dataset, code output, other sections of the document, prior literature)
2. Filter to the specific instances referenced
3. Extract the relevant evidence
4. Summarise the pattern and quote key text from each instance
5. Include the count: "5/5 show X" or "4/4 comply"

This is the most important part of the workflow. Reviewers asking to "confirm" want to see evidence, not just hear "confirmed."

## Phase 4: Build Reply Comments

### Technical steps (docx XML)

1. **Add reply comments** to `word/comments.xml` and `word/commentsExtended.xml`. Use the document owner as the reply author.
2. **Add markers to `word/document.xml`**:
   - Find `<w:commentRangeEnd w:id="{parent_id}"/>` for each parent
   - Insert `<w:commentRangeStart w:id="{reply_id}"/><w:commentRangeEnd w:id="{reply_id}"/>` just before it
   - Find `<w:commentReference w:id="{parent_id}"/>` and its containing `</w:r>`
   - Insert a new `<w:r>` with `<w:commentReference w:id="{reply_id}"/>` after it
3. **Don't hardcode XML whitespace** — the `commentReference` runs in the document have varied formatting (indentation, extra rPr elements). Find `<w:commentReference w:id="X"/>` and work outward to its containing `</w:r>`.

### ID allocation

- Find the highest existing `w:id` in both `comments.xml` and `document.xml`
- Start reply IDs well above (e.g. max + 1000) to avoid conflicts with tracked change IDs

### Batch processing

For large comment sets (30+), write a Python script rather than manual insertion. Build a dict of `{parent_id: reply_text}`, iterate, add comments, then do a single pass over document.xml for markers — this avoids the insert-position-shifting problem.

## Phase 5: Pack and Validate

```bash
python scripts/office/pack.py unpacked/ output.docx --original input.docx

- Pre-existing validation issues (e.g. duplicate IDs in documenttasks/) may require --validate false
- Always test by opening in Word to verify comments render as threaded replies

General Lessons

1. Start from a fresh unpack if you need to retry. Don't layer edits on failed attempts — you'll get duplicate markers.
2. Process all replies in a single script run — modifying document.xml in one pass avoids insert-position-shifting.
3. Escape special characters in XML — use &#x201C; &#x201D; &#x2019; for smart quotes/apostrophes in comment text. All text must be valid XML.
4. Match the reply to the concern, not the comment text — a comment saying "I'm confused here" requires a reply about what you changed at that location, not a pointer to another section.
5. When in doubt, be brief — reviewers are busy. "Done." for an accepted suggestion is better than a paragraph explaining what you did. Save length for verification-type responses where evidence matters.
```
