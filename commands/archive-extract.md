---
description: Extract archived information into personal knowledge base
permalink: commands/archive-extract
---
# Archive Email Knowledge Extraction

Process archived to extract important professional knowledge.

## Action

1. Identify all source information the user wants you to process.
2. Use your task tool to create a TODO list to track EACH file individually
3. Invoke the `email-extractor` agent to process each file individually
4. Commit your changes after each file is processed

You may invoke multiple simultaneous `email-extractor` agents to process multiple files concurrently (no more than 8 at a time).
