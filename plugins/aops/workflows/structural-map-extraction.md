---
title: Structural Map Extraction
type: template
category: process
description: Extract a structured research map (Aims, Methodology, Analytical Theory, Contribution) from an academic manuscript or research proposal. Select when ingesting or analyzing academic papers. Not for writing code or general text summarization.
tags: [academic, research, extraction, structural-map, analysis, process]
---

# Process: Structural Map Extraction

Structured extraction procedure for academic research papers.

## 1. Source Ingestion

- Ingest full text or sections of the target academic manuscript (`<manuscript-source>`).
- Identify target field, discipline conventions, and publication venue context.

## 2. Four-Pillar Extraction

- Extract core structural components into four standard pillars:
  - **Aims**: Core research questions, hypotheses, and intended objectives.
  - **Methodology**: Empirical data sources, sampling strategy, experimental design, and identification strategy.
  - **Analytical Theory**: Theoretical models, conceptual frameworks, and formal mechanisms.
  - **Contribution**: Novel empirical findings, theoretical extensions, and policy/practical implications.

## 3. Claim-to-Evidence Verification

- For every extracted contribution claim, cite specific table, figure, equation, or section numbers in the source text.
- Note any unsupported claims or unstated methodological assumptions as explicit caveats.

## 4. Output Formatting

- Format the structural map according to standard research schema.
- Store output in project memory or literature index.
