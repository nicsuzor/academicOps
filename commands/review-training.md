# Review Training Data Extraction

Process one matched review/source pair to extract training data for teaching LLMs to perform peer review.

## Action

Launch the batch-extractor agent to process the next matched pair.

The agent will:

1. Get next matched pair from batch queue
2. Read review and source document (PDF/DOCX/TXT)
3. Identify distinct feedback units in review
4. Extract source evidence for each feedback unit
5. Categorize feedback (scope, type, action)
6. Create training data files
7. Confirm processing (deletes source pair)
8. Return summary

## Agent Invocation

Use the Task tool to launch the batch-extractor agent:

**Agent**: batch-extractor (located at `bots/agents/batch-extractor/AGENT.md`)

**Task description**: "Process next review training pair"

**Prompt**:

```
Process the next matched review/source pair from the review training queue:
- Task type: review-training
- Follow the batch-extractor agent workflow
- Use the review-training skill for extraction and categorization
- Process ONE pair only
- Return structured summary

Configuration:
- Batch script: bots/skills/review-training/scripts/batch_next.py
- Skill: bots/skills/review-training/SKILL.md
- Output dir: data/review-training/
```

The agent has access to:

- Review-training skill with three extraction strategies
- Categorization system (scope, type, action)
- Batch management scripts
- Tools for reading PDF/DOCX/TXT files

## Status Check

To check remaining items:

```bash
uv run python bots/skills/review-training/scripts/batch_next.py status
```
