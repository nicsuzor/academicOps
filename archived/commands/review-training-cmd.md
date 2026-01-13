---
name: review-training-cmd
category: instruction
description: Process one matched review/source pair to extract training data
allowed-tools: Task
permalink: commands/review-training-cmd
---

# Review Training Data Extraction

Process one matched review/source pair to extract training data for teaching LLMs to perform peer review.

## Action

1. Read review
2. Read source document (PDF/DOCX/TXT)
3. Identify distinct feedback units in review
4. Extract source evidence for each feedback unit
5. Categorize feedback (scope, type, action)
6. Create training data files
7. Confirm processing (deletes source pair)
8. Return summary
