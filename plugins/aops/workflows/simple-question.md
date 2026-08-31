---
title: Simple Question
type: template
category: process
description: Pure information lookup — answer the user's question directly and halt. Select when the request asks for facts, explanation, or locations without requiring code edits, file modifications, or task tracking. Not for requests requiring action, debugging, or modifications.
tags: [routing, information, lookup, q-and-a, process]
---

# Process: Simple Question

Zero-overhead information response workflow.

## 1. Query Analysis

- Identify the factual question or information requested by the user (`<question>`).
- Confirm that no file modifications, system changes, or persistent side-effects are requested.

## 2. Information Retrieval

- Search repository files, documentation, or knowledge graph to locate authoritative answers.
- Retrieve exact verbatim references and line citations.

## 3. Direct Response and Clean Exit

- Provide a direct, concise answer with pinpoint markdown links to referenced sources.
- Halt immediately without creating tasks, proposing unsolicited plans, or modifying files.
